"""
src/objective_function.py
Calculates microgrid dispatch operational costs, constraint penalties, and objective fitness:
- Solar & Wind O&M costs
- Battery degradation throughput costs
- Main grid TOU import costs & feed-in export credits
- Renewable energy curtailment penalties & carbon emissions costs
- Value of Lost Load (unserved demand) and excess generation penalties
- Strict terminal SOC penalty ensuring sustainable cyclic dispatch
- Rigorous non-double-counted renewable energy metrics:
  A. Renewable utilization (%) = RE dispatched / RE available * 100
  B. Renewable share (%) = RE serving demand / Total served demand * 100
  C. Grid dependency (%) = Grid import / Total served demand * 100
  D. Renewable curtailment (%) = Unused RE / Available RE * 100
"""

import numpy as np
from typing import Dict, Any, Tuple
from src.energy_model import MicrogridEnergyModel
from src.constraints import MicrogridConstraints


class MicrogridObjective:
    """
    Evaluates microgrid dispatch cost components, constraint violations,
    and true objective fitness.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.energy_model = MicrogridEnergyModel(config)
        self.constraints = MicrogridConstraints(config)

        # Operational cost parameters ($/kWh)
        self.c_solar_om = float(config["solar_pv"]["unit_om_cost_per_kwh"])
        self.c_wind_om = float(config["wind_turbine"]["unit_om_cost_per_kwh"])
        self.c_bat_deg = float(config["battery"]["degradation_cost_per_kwh"])
        self.c_curt = float(config["solar_pv"].get("curtailment_penalty_per_kwh", 0.05))
        self.c_export = float(config["grid"]["tou_tariff"].get("export_credit_rate", 0.04))
        
        # Carbon emissions
        self.co2_factor = float(config["grid"].get("co2_emission_factor_kg_per_kwh", 0.52))
        self.carbon_tax = float(config["grid"].get("carbon_tax_per_kg_co2", 0.03))

        # Penalty parameters ($/kWh or $/violation)
        opt_cfg = config.get("optimization", {})
        self.penalty_unserved_voll = float(config["load"].get("unserved_energy_penalty_per_kwh", 2.00))
        self.penalty_excess = float(opt_cfg.get("penalty_multiplier_excess_gen", 0.20))
        self.penalty_soc_bounds = float(opt_cfg.get("penalty_multiplier_soc_violation", 100.0))
        self.penalty_terminal_soc = float(opt_cfg.get("penalty_multiplier_terminal_soc", 500.0))

    def evaluate(
        self,
        candidate_vector: np.ndarray,
        scenario: Dict[str, Any],
        apply_repair: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate dispatch solution vector:
        candidate_vector = [P_solar (T), P_wind (T), P_battery (T)]
        """
        T = scenario["horizon_steps"]
        dt = scenario.get("dt_hours", 1.0)
        p_load = scenario["load_demand_kw"]
        p_solar_avail = scenario["solar_available_kw"]
        p_wind_avail = scenario["wind_available_kw"]
        tariffs = scenario["grid_tariff_per_kwh"]

        # 1. Unpack candidate decision variables
        p_solar_raw = candidate_vector[0:T]
        p_wind_raw = candidate_vector[T:2*T]
        p_bat_raw = candidate_vector[2*T:3*T]

        # 2. Feasibility repair (if requested)
        if apply_repair:
            p_solar, p_wind, p_bat = self.constraints.repair_candidate(
                p_solar_raw, p_wind_raw, p_bat_raw, scenario
            )
        else:
            p_solar, p_wind, p_bat = p_solar_raw, p_wind_raw, p_bat_raw

        # 3. Physical microgrid simulation
        sim = self.energy_model.simulate_dispatch(
            p_solar=p_solar,
            p_wind=p_wind,
            p_battery=p_bat,
            p_load=p_load,
            dt=dt
        )

        p_grid = sim["p_grid"]
        p_grid_import = sim["p_grid_import"]
        p_grid_export = sim["p_grid_export"]
        p_bat_act = sim["p_battery"]
        p_bat_dis = sim["p_battery_discharge"]
        p_bat_ch = sim["p_battery_charge"]
        soc = sim["soc_trajectory"]
        unserved_load = sim["unserved_load"]
        excess_gen = sim["excess_generation"]
        terminal_soc_error = sim["terminal_soc_error"]
        terminal_soc_violated = sim["terminal_soc_violated"]

        # 4. Pure Operating Cost Breakdown ($)
        # Solar & Wind O&M
        c_solar = float(np.sum(p_solar * self.c_solar_om * dt))
        c_wind = float(np.sum(p_wind * self.c_wind_om * dt))

        # Battery throughput degradation ($0.018/kWh throughput)
        c_battery = float(np.sum(np.abs(p_bat_act) * self.c_bat_deg * dt))

        # Grid exchange cost (Import cost minus export credit)
        c_grid = float(np.sum(p_grid_import * tariffs * dt) - np.sum(p_grid_export * self.c_export * dt))

        # Renewable curtailment cost
        curtailed_solar_kw = np.maximum(0.0, p_solar_avail - p_solar)
        curtailed_wind_kw = np.maximum(0.0, p_wind_avail - p_wind)
        total_curtailment_kwh = float(np.sum(curtailed_solar_kw + curtailed_wind_kw + excess_gen) * dt)
        c_curtailment = float(total_curtailment_kwh * self.c_curt)

        # Carbon emissions tax on imported grid energy
        grid_import_total_kwh = float(np.sum(p_grid_import * dt))
        c_carbon = float(grid_import_total_kwh * self.co2_factor * self.carbon_tax)

        operating_cost = float(c_solar + c_wind + c_battery + c_grid + c_curtailment + c_carbon)

        # 5. Constraint Penalties ($)
        unserved_total_kwh = float(np.sum(unserved_load * dt))
        excess_total_kwh = float(np.sum(excess_gen * dt))
        penalty_unserved = float(unserved_total_kwh * self.penalty_unserved_voll)
        penalty_excess = float(excess_total_kwh * self.penalty_excess)

        # Terminal SOC penalty (heavily penalizes consuming stored energy without returning it)
        soc_tol = self.energy_model.terminal_soc_tolerance
        term_excess_error = max(0.0, terminal_soc_error - soc_tol)
        penalty_terminal = float(term_excess_error * self.energy_model.e_bat_kwh * self.penalty_terminal_soc)

        # Step-by-step SOC bound violations
        soc_viol_under = np.maximum(0.0, (self.energy_model.soc_min - 1e-4) - soc)
        soc_viol_over = np.maximum(0.0, soc - (self.energy_model.soc_max + 1e-4))
        penalty_soc_val = float(np.sum(soc_viol_under + soc_viol_over) * self.energy_model.e_bat_kwh * self.penalty_soc_bounds)

        total_penalty = float(penalty_unserved + penalty_excess + penalty_terminal + penalty_soc_val)
        fitness = float(operating_cost + total_penalty)

        # 6. Independent Constraint Verification
        c_report = self.constraints.evaluate_constraints(
            p_solar=p_solar,
            p_wind=p_wind,
            p_battery=p_bat_act,
            p_grid=p_grid,
            soc_trajectory=soc,
            scenario=scenario
        )
        is_feasible = bool(c_report["is_feasible"] and not terminal_soc_violated and unserved_total_kwh < 1e-3 and excess_total_kwh < 1e-3)

        # 7. Rigorous Renewable Energy Metrics (Corrected)
        total_re_avail_kwh = float(np.sum(p_solar_avail + p_wind_avail) * dt)
        total_re_dispatched_kwh = float(np.sum(p_solar + p_wind) * dt)
        total_load_kwh = float(np.sum(p_load * dt))
        total_served_load_kwh = max(1e-6, total_load_kwh - unserved_total_kwh)

        # Metric A: Renewable utilization (%) = RE dispatched / RE available * 100
        re_utilization_pct = float((total_re_dispatched_kwh / total_re_avail_kwh) * 100.0) if total_re_avail_kwh > 0 else 0.0

        # Metric D: Renewable curtailment (%) = Unused RE / Available RE * 100
        re_curtailment_pct = float((total_curtailment_kwh / total_re_avail_kwh) * 100.0) if total_re_avail_kwh > 0 else 0.0

        # Metric B: Renewable share (%) = RE serving demand / Total served demand * 100
        # Track clean energy dispatched directly plus clean battery throughput without double counting
        re_serving_demand_kwh = 0.0
        bat_stored_re_kwh = 0.0
        bat_stored_total_kwh = 0.0

        for t in range(T):
            re_gen_t = (p_solar[t] + p_wind[t]) * dt
            load_t = p_load[t] * dt

            # Direct renewable power serving demand at hour t
            direct_re_served = min(load_t, re_gen_t)
            re_serving_demand_kwh += direct_re_served

            # Renewable surplus charging battery
            re_surplus = max(0.0, re_gen_t - load_t)
            ch_kwh = p_bat_ch[t] * dt
            if ch_kwh > 1e-6:
                clean_fraction = min(1.0, re_surplus / ch_kwh)
                bat_stored_re_kwh += ch_kwh * clean_fraction * self.energy_model.eta_ch
                bat_stored_total_kwh += ch_kwh * self.energy_model.eta_ch

            # Discharging battery to serve demand
            dis_kwh = p_bat_dis[t] * dt
            if dis_kwh > 1e-6 and bat_stored_total_kwh > 1e-6:
                clean_dis_ratio = min(1.0, bat_stored_re_kwh / bat_stored_total_kwh)
                clean_dis_kwh = min(dis_kwh, dis_kwh * clean_dis_ratio)
                re_serving_demand_kwh += clean_dis_kwh
                bat_stored_re_kwh = max(0.0, bat_stored_re_kwh - clean_dis_kwh)
                bat_stored_total_kwh = max(0.0, bat_stored_total_kwh - dis_kwh)

        re_share_pct = float(min(100.0, (re_serving_demand_kwh / total_served_load_kwh) * 100.0))

        # Metric C: Grid dependency (%) = Grid import energy / Total served demand * 100
        grid_dependency_pct = float(min(100.0, (grid_import_total_kwh / total_served_load_kwh) * 100.0))

        return {
            "fitness": fitness,
            "operating_cost": operating_cost,
            "total_penalty": total_penalty,
            "c_solar": c_solar,
            "c_wind": c_wind,
            "c_battery": c_battery,
            "c_grid": c_grid,
            "c_curtailment": c_curtailment,
            "c_carbon": c_carbon,
            "penalty_unserved": penalty_unserved,
            "penalty_excess": penalty_excess,
            "penalty_terminal_soc": penalty_terminal,
            "penalty_soc_bounds": penalty_soc_val,
            "is_feasible": is_feasible,
            "re_utilization_pct": re_utilization_pct,
            "re_share_pct": re_share_pct,
            "grid_dependency_pct": grid_dependency_pct,
            "re_curtailment_pct": re_curtailment_pct,
            "curtailment_kwh": total_curtailment_kwh,
            "grid_import_kwh": grid_import_total_kwh,
            "grid_export_kwh": float(np.sum(p_grid_export * dt)),
            "unserved_load_kwh": unserved_total_kwh,
            "excess_generation_kwh": excess_total_kwh,
            "soc_initial": sim["soc_initial"],
            "soc_final": sim["soc_final"],
            "terminal_soc_error": terminal_soc_error,
            "terminal_soc_violated": terminal_soc_violated,
            "constraint_report": c_report,
            "p_solar": p_solar,
            "p_wind": p_wind,
            "p_battery": p_bat_act,
            "p_battery_discharge": p_bat_dis,
            "p_battery_charge": p_bat_ch,
            "p_grid": p_grid,
            "p_grid_import": p_grid_import,
            "p_grid_export": p_grid_export,
            "soc_trajectory": soc,
            "power_imbalance": sim["power_imbalance"]
        }
