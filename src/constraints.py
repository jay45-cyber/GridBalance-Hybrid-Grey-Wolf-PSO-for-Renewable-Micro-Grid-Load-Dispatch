"""
src/constraints.py
Microgrid dispatch constraints evaluator and feasibility repair mechanism.
Ensures generation, battery SOC, terminal SOC, and grid constraints are strictly observed.
Provides detailed independent violation metrics and feasibility reporting.
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional


class MicrogridConstraints:
    """
    Evaluates microgrid physical constraints and repairs candidate dispatch
    solutions onto the feasible manifold.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        b_cfg = config["battery"]
        self.e_bat_kwh = float(b_cfg["nominal_energy_capacity_kwh"])
        self.p_ch_max = float(b_cfg["max_charge_power_kw"])
        self.p_dis_max = float(b_cfg["max_discharge_power_kw"])
        self.eta_ch = float(b_cfg["charge_efficiency"])
        self.eta_dis = float(b_cfg["discharge_efficiency"])
        self.soc_init = float(b_cfg["initial_soc"])
        self.soc_min = float(b_cfg["soc_min"])
        self.soc_max = float(b_cfg["soc_max"])
        self.self_discharge = float(b_cfg.get("self_discharge_rate_per_hour", 0.0001))
        self.terminal_soc_target = float(b_cfg.get("terminal_soc_target", self.soc_init))
        self.terminal_soc_tolerance = float(b_cfg.get("terminal_soc_tolerance", 0.01))

        g_cfg = config["grid"]
        self.p_grid_max = float(g_cfg["max_import_power_kw"])
        self.p_export_max = float(g_cfg.get("max_export_power_kw", 0.0))

    def evaluate_constraints(
        self,
        p_solar: np.ndarray,
        p_wind: np.ndarray,
        p_battery: np.ndarray,
        p_grid: Optional[np.ndarray] = None,
        soc_trajectory: Optional[np.ndarray] = None,
        scenario: Dict[str, Any] = None,
        p_grid_import: Optional[np.ndarray] = None,
        p_grid_export: Optional[np.ndarray] = None,
        unserved_load: Optional[np.ndarray] = None,
        excess_generation: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Evaluates individual constraint violations for a candidate dispatch schedule.
        Returns detailed numerical violations and Boolean feasibility flags.
        
        Enforces consistent power balance identity:
        P_solar + P_wind + P_battery + P_grid_import - P_grid_export + P_unserved - P_excess = P_load
        """
        p_solar_avail = scenario["solar_available_kw"]
        p_wind_avail = scenario["wind_available_kw"]
        p_load = scenario["load_demand_kw"]
        T = len(p_load)

        # Derive import/export and imbalance if not provided directly
        if p_grid is not None:
            if p_grid_import is None:
                p_grid_import = np.maximum(0.0, p_grid)
            if p_grid_export is None:
                p_grid_export = np.maximum(0.0, -p_grid)
        else:
            if p_grid_import is None:
                p_grid_import = np.zeros(T, dtype=np.float64)
            if p_grid_export is None:
                p_grid_export = np.zeros(T, dtype=np.float64)
            p_grid = p_grid_import - p_grid_export

        if unserved_load is None:
            unserved_load = np.zeros(T, dtype=np.float64)
        if excess_generation is None:
            excess_generation = np.zeros(T, dtype=np.float64)

        if soc_trajectory is None:
            soc_trajectory = np.full(T + 1, self.soc_init, dtype=np.float64)

        # 1. Solar generation bounds: 0 <= P_solar <= P_solar_avail
        solar_lower_viol = float(np.sum(np.maximum(0.0, -p_solar)))
        solar_upper_viol = float(np.sum(np.maximum(0.0, p_solar - p_solar_avail)))
        solar_valid = bool(solar_lower_viol < 1e-4 and solar_upper_viol < 1e-4)

        # 2. Wind generation bounds: 0 <= P_wind <= P_wind_avail
        wind_lower_viol = float(np.sum(np.maximum(0.0, -p_wind)))
        wind_upper_viol = float(np.sum(np.maximum(0.0, p_wind - p_wind_avail)))
        wind_valid = bool(wind_lower_viol < 1e-4 and wind_upper_viol < 1e-4)

        # 3. Battery power bounds: -P_ch_max <= P_battery <= P_dis_max
        charge_viol = float(np.sum(np.maximum(0.0, -p_battery - self.p_ch_max)))
        discharge_viol = float(np.sum(np.maximum(0.0, p_battery - self.p_dis_max)))
        battery_power_valid = bool(charge_viol < 1e-4 and discharge_viol < 1e-4)

        # 4. Battery SOC bounds across trajectory: SOC_min <= SOC(t) <= SOC_max
        soc_min_viol = float(np.sum(np.maximum(0.0, (self.soc_min - 1e-4) - soc_trajectory)))
        soc_max_viol = float(np.sum(np.maximum(0.0, soc_trajectory - (self.soc_max + 1e-4))))
        soc_bounds_valid = bool(soc_min_viol < 1e-4 and soc_max_viol < 1e-4)

        # 5. Initial and Terminal SOC constraints
        initial_soc_viol = float(abs(soc_trajectory[0] - self.soc_init))
        initial_soc_valid = bool(initial_soc_viol < 1e-4)

        terminal_soc_error = float(abs(soc_trajectory[-1] - self.terminal_soc_target))
        terminal_soc_valid = bool(terminal_soc_error <= (self.terminal_soc_tolerance + 1e-5))

        # 6. Grid power limits: P_import <= max_import_power_kw, P_export <= max_export_power_kw
        grid_import_viol = float(np.sum(np.maximum(0.0, p_grid_import - self.p_grid_max)))
        grid_export_viol = float(np.sum(np.maximum(0.0, p_grid_export - self.p_export_max)))
        grid_import_valid = bool(grid_import_viol < 1e-4)
        grid_export_valid = bool(grid_export_viol < 1e-4)
        grid_valid = bool(grid_import_valid and grid_export_valid)

        # 7. Power Balance Identity at every time step:
        # P_solar + P_wind + P_battery + P_grid_import - P_grid_export + P_unserved - P_excess = P_load
        pb_identity_residual = np.abs(
            p_solar + p_wind + p_battery + p_grid_import - p_grid_export + unserved_load - excess_generation - p_load
        )
        pb_max_identity_residual = float(np.max(pb_identity_residual))
        pb_total_identity_residual = float(np.sum(pb_identity_residual))
        power_balance_identity_valid = bool(pb_max_identity_residual < 1e-3)

        # 8. Unserved load & excess generation independent feasibility checks
        unserved_load_total = float(np.sum(unserved_load))
        excess_gen_total = float(np.sum(excess_generation))
        unserved_load_valid = bool(unserved_load_total < 1e-3)
        excess_generation_valid = bool(excess_gen_total < 1e-3)

        # Overall Feasibility: All independent criteria must be satisfied
        is_feasible = bool(
            solar_valid and
            wind_valid and
            battery_power_valid and
            soc_bounds_valid and
            initial_soc_valid and
            terminal_soc_valid and
            grid_import_valid and
            grid_export_valid and
            power_balance_identity_valid and
            unserved_load_valid and
            excess_generation_valid
        )

        total_violation = float(
            solar_lower_viol + solar_upper_viol +
            wind_lower_viol + wind_upper_viol +
            charge_viol + discharge_viol +
            (soc_min_viol + soc_max_viol) * 100.0 +
            initial_soc_viol * 100.0 +
            terminal_soc_error * 100.0 +
            grid_import_viol + grid_export_viol +
            pb_total_identity_residual +
            unserved_load_total * 10.0 +
            excess_gen_total * 5.0
        )

        return {
            "is_feasible": is_feasible,
            "total_violation": total_violation,
            "solar_valid": solar_valid,
            "solar_lower_violation": solar_lower_viol,
            "solar_upper_violation": solar_upper_viol,
            "wind_valid": wind_valid,
            "wind_lower_violation": wind_lower_viol,
            "wind_upper_violation": wind_upper_viol,
            "battery_power_valid": battery_power_valid,
            "battery_charge_violation": charge_viol,
            "battery_discharge_violation": discharge_viol,
            "soc_bounds_valid": soc_bounds_valid,
            "soc_min_violation": soc_min_viol,
            "soc_max_violation": soc_max_viol,
            "initial_soc_valid": initial_soc_valid,
            "initial_soc_violation": initial_soc_viol,
            "terminal_soc_valid": terminal_soc_valid,
            "terminal_soc_error": terminal_soc_error,
            "grid_valid": grid_valid,
            "grid_import_valid": grid_import_valid,
            "grid_export_valid": grid_export_valid,
            "grid_import_violation": grid_import_viol,
            "grid_export_violation": grid_export_viol,
            "power_balance_valid": power_balance_identity_valid,
            "power_balance_max_mismatch": pb_max_identity_residual,
            "power_balance_total_mismatch": pb_total_identity_residual,
            "unserved_load_valid": unserved_load_valid,
            "unserved_load_total_kw": unserved_load_total,
            "excess_generation_valid": excess_generation_valid,
            "excess_generation_total_kw": excess_gen_total
        }

    def _simulate_battery_forward(
        self,
        p_bat_raw: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulates battery step-by-step enforcing non-simultaneous charge/discharge,
        physical power limits, and hourly SOC boundaries.
        """
        T = len(p_bat_raw)
        repaired_bat = np.zeros(T, dtype=np.float64)
        soc = np.zeros(T + 1, dtype=np.float64)
        soc[0] = self.soc_init

        for t in range(T):
            soc_prev = soc[t]
            soc_after_sd = soc_prev * (1.0 - self.self_discharge * dt)
            req_bat = p_bat_raw[t]

            if req_bat >= 0:
                # Discharging: cannot exceed energy above soc_min
                max_dis = (soc_after_sd - self.soc_min) * self.e_bat_kwh * self.eta_dis / dt
                max_dis = max(0.0, min(self.p_dis_max, max_dis))
                act_bat = min(req_bat, max_dis)
                delta_soc = -(act_bat * dt) / (self.e_bat_kwh * self.eta_dis)
            else:
                # Charging: cannot exceed energy headroom below soc_max
                ch_req = abs(req_bat)
                max_ch = (self.soc_max - soc_after_sd) * self.e_bat_kwh / (self.eta_ch * dt)
                max_ch = max(0.0, min(self.p_ch_max, max_ch))
                act_ch = min(ch_req, max_ch)
                act_bat = -act_ch
                delta_soc = (act_ch * dt * self.eta_ch) / self.e_bat_kwh

            repaired_bat[t] = act_bat
            soc[t + 1] = np.clip(soc_after_sd + delta_soc, self.soc_min, self.soc_max)

        return repaired_bat, soc

    def repair_candidate(
        self,
        p_solar: np.ndarray,
        p_wind: np.ndarray,
        p_battery: np.ndarray,
        scenario: Dict[str, Any]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Feasibility Repair Operator:
        Projects candidate variables onto the physically feasible space:
        1. Clamps renewable dispatch to [0, available]
        2. Enforces non-simultaneous charge/discharge and dynamic hourly SOC bounds
        3. Adjusts battery charge/discharge balance toward cyclic terminal SOC target
        4. Returns repaired (p_solar, p_wind, p_battery)
        """
        p_solar_avail = scenario["solar_available_kw"]
        p_wind_avail = scenario["wind_available_kw"]
        dt = scenario.get("dt_hours", 1.0)
        T = len(p_solar)

        repaired_solar = np.clip(p_solar, 0.0, p_solar_avail)
        repaired_wind = np.clip(p_wind, 0.0, p_wind_avail)

        # Initial forward pass for battery
        bat_cand = np.clip(p_battery.copy(), -self.p_ch_max, self.p_dis_max)
        rep_bat, soc = self._simulate_battery_forward(bat_cand, dt)

        # Iterative cyclic terminal SOC balancing (up to 4 passes)
        for _ in range(4):
            final_soc = soc[-1]
            soc_diff = final_soc - self.terminal_soc_target

            if abs(soc_diff) <= self.terminal_soc_tolerance:
                break

            if soc_diff < 0:
                # Battery depleted too much (terminal SOC too low)
                # Scale down discharge or boost charge during high solar hours
                dis_mask = rep_bat > 0
                if np.any(dis_mask):
                    dis_energy = np.sum(rep_bat[dis_mask]) * dt
                    needed_energy = abs(soc_diff) * self.e_bat_kwh * self.eta_dis
                    if dis_energy > 1e-3:
                        scale = max(0.0, 1.0 - (needed_energy / dis_energy))
                        bat_cand[dis_mask] *= scale
                else:
                    # If no discharge, increase charging during off-peak/midday
                    ch_mask = rep_bat <= 0
                    bat_cand[ch_mask] -= 50.0

            else:
                # Battery finished with surplus energy (terminal SOC too high)
                # Scale down charging
                ch_mask = rep_bat < 0
                if np.any(ch_mask):
                    ch_energy = np.sum(np.abs(rep_bat[ch_mask])) * dt
                    surplus_energy = soc_diff * self.e_bat_kwh / self.eta_ch
                    if ch_energy > 1e-3:
                        scale = max(0.0, 1.0 - (surplus_energy / ch_energy))
                        bat_cand[ch_mask] *= scale
                else:
                    dis_mask = rep_bat >= 0
                    bat_cand[dis_mask] += 50.0

            bat_cand = np.clip(bat_cand, -self.p_ch_max, self.p_dis_max)
            rep_bat, soc = self._simulate_battery_forward(bat_cand, dt)

        return repaired_solar, repaired_wind, rep_bat
