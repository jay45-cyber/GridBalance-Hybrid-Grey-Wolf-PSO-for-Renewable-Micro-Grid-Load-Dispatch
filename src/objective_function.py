"""
src/objective_function.py
Calculates microgrid dispatch operational costs, penalties, and objective fitness:
- Solar & Wind O&M costs
- Battery degradation throughput costs
- Main grid TOU import costs & feed-in export credits
- Renewable energy curtailment penalties
- Carbon emissions costs
"""

import numpy as np
from typing import Dict, Any, Tuple
from src.energy_model import MicrogridEnergyModel
from src.constraints import MicrogridConstraints


class MicrogridObjective:
    """
    Evaluates microgrid dispatch cost components and objective fitness.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.energy_model = MicrogridEnergyModel(config)
        self.constraints = MicrogridConstraints(config)

        # Cost parameters
        self.c_solar_om = float(config["solar_pv"]["unit_om_cost_per_kwh"])
        self.c_wind_om = float(config["wind_turbine"]["unit_om_cost_per_kwh"])
        self.c_bat_deg = float(config["battery"]["degradation_cost_per_kwh"])
        self.c_curt = float(config["solar_pv"].get("curtailment_penalty_per_kwh", 0.05))
        self.c_export = float(config["grid"]["tou_tariff"].get("export_credit_rate", 0.04))
        
        # Carbon emissions
        self.co2_factor = float(config["grid"].get("co2_emission_factor_kg_per_kwh", 0.52))
        self.carbon_tax = float(config["grid"].get("carbon_tax_per_kg_co2", 0.03))

        # Penalty factors
        opt_cfg = config.get("optimization", {})
        self.penalty_pb = float(opt_cfg.get("penalty_multiplier_power_balance", 50.0))
        self.penalty_soc = float(opt_cfg.get("penalty_multiplier_soc_violation", 100.0))

    def evaluate(
        self,
        candidate_vector: np.ndarray,
        scenario: Dict[str, Any],
        apply_repair: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate solution vector.
        
        Vector structure:
        If dimension is 3*T:
            candidate_vector = [P_solar (T), P_wind (T), P_battery (T)]
        If dimension is 2*T (curtailment factors or battery + curtailment):
            Flexible unpacking supported. Default: 3*T (solar, wind, battery)

        Returns dictionary of fitness, costs, metrics, and profiles.
        """
        T = scenario["horizon_steps"]
        dt = scenario.get("dt_hours", 1.0)
        p_load = scenario["load_demand_kw"]
        p_solar_avail = scenario["solar_available_kw"]
        p_wind_avail = scenario["wind_available_kw"]
        tariffs = scenario["grid_tariff_per_kwh"]

        # Unpack candidate
        p_solar_raw = candidate_vector[0:T]
        p_wind_raw = candidate_vector[T:2*T]
        p_bat_raw = candidate_vector[2*T:3*T]

        # Feasibility repair if requested
        if apply_repair:
            p_solar, p_wind, p_bat = self.constraints.repair_candidate(
                p_solar_raw, p_wind_raw, p_bat_raw, scenario
            )
        else:
            p_solar, p_wind, p_bat = p_solar_raw, p_wind_raw, p_bat_raw

        # Run physical simulation
        sim = self.energy_model.simulate_dispatch(
            p_solar=p_solar,
            p_wind=p_wind,
            p_battery=p_bat,
            p_load=p_load,
            dt=dt
        )

        p_grid = sim["p_grid"]
        p_bat_act = sim["p_battery"]
        soc = sim["soc_trajectory"]
        p_imbalance = sim["power_imbalance"]

        # Cost calculations ($)
        # 1. Solar & Wind O&M
        c_solar = np.sum(p_solar * self.c_solar_om * dt)
        c_wind = np.sum(p_wind * self.c_wind_om * dt)

        # 2. Battery throughput degradation
        c_battery = np.sum(np.abs(p_bat_act) * self.c_bat_deg * dt)

        # 3. Grid costs (import cost minus export credit)
        grid_import_kwh = np.maximum(0.0, p_grid) * dt
        grid_export_kwh = np.maximum(0.0, -p_grid) * dt
        c_grid = np.sum(grid_import_kwh * tariffs) - np.sum(grid_export_kwh * self.c_export)

        # 4. Curtailment cost
        solar_curtailed_kwh = np.maximum(0.0, p_solar_avail - p_solar) * dt
        wind_curtailed_kwh = np.maximum(0.0, p_wind_avail - p_wind) * dt
        total_curtailment_kwh = np.sum(solar_curtailed_kwh + wind_curtailed_kwh)
        c_curtailment = total_curtailment_kwh * self.c_curt

        # 5. Carbon emission cost
        c_carbon = np.sum(grid_import_kwh * self.co2_factor * self.carbon_tax)

        # Pure operating cost ($)
        operating_cost = float(c_solar + c_wind + c_battery + c_grid + c_curtailment + c_carbon)

        # Penalties for constraints (with 1e-4 numerical tolerance)
        penalty_power = np.sum(np.maximum(0.0, np.abs(p_imbalance) - 1e-4)) * self.penalty_pb
        soc_viol_under = np.maximum(0.0, (self.energy_model.soc_min - 1e-4) - soc)
        soc_viol_over = np.maximum(0.0, soc - (self.energy_model.soc_max + 1e-4))
        penalty_soc_val = np.sum(soc_viol_under + soc_viol_over) * self.penalty_soc

        total_penalty = float(penalty_power + penalty_soc_val)
        fitness = float(operating_cost + total_penalty)

        # Key performance indicators
        total_load_kwh = np.sum(p_load * dt)
        re_gen_kwh = np.sum((p_solar + p_wind) * dt)
        re_utilization_pct = float(min(100.0, (re_gen_kwh / total_load_kwh) * 100.0)) if total_load_kwh > 0 else 0.0
        grid_import_total_kwh = float(np.sum(grid_import_kwh))
        grid_dependency_pct = float(min(100.0, (grid_import_total_kwh / total_load_kwh) * 100.0)) if total_load_kwh > 0 else 0.0

        is_feasible = bool(np.max(np.abs(p_imbalance)) < 1e-3 and penalty_soc_val < 1e-3)

        return {
            "fitness": fitness,
            "operating_cost": operating_cost,
            "c_solar": float(c_solar),
            "c_wind": float(c_wind),
            "c_battery": float(c_battery),
            "c_grid": float(c_grid),
            "c_curtailment": float(c_curtailment),
            "c_carbon": float(c_carbon),
            "total_penalty": total_penalty,
            "is_feasible": is_feasible,
            "re_utilization_pct": re_utilization_pct,
            "grid_dependency_pct": grid_dependency_pct,
            "curtailment_kwh": float(total_curtailment_kwh),
            "grid_import_kwh": grid_import_total_kwh,
            "p_solar": p_solar,
            "p_wind": p_wind,
            "p_battery": p_bat_act,
            "p_grid": p_grid,
            "soc_trajectory": soc,
            "power_imbalance": p_imbalance
        }
