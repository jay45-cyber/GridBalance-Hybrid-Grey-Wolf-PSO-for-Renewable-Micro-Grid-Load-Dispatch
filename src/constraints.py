"""
src/constraints.py
Microgrid dispatch constraints evaluator and feasibility repair mechanism.
Ensures generation, battery SOC, and grid constraints are strictly observed.
"""

import numpy as np
from typing import Dict, Any, Tuple


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

        g_cfg = config["grid"]
        self.p_grid_max = float(g_cfg["max_import_power_kw"])
        self.p_export_max = float(g_cfg.get("max_export_power_kw", 0.0))

    def evaluate_constraints(
        self,
        p_solar: np.ndarray,
        p_wind: np.ndarray,
        p_battery: np.ndarray,
        p_grid: np.ndarray,
        soc_trajectory: np.ndarray,
        scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates constraint violations for a candidate dispatch schedule.
        """
        p_solar_avail = scenario["solar_available_kw"]
        p_wind_avail = scenario["wind_available_kw"]
        p_load = scenario["load_demand_kw"]

        # 1. Solar limits: 0 <= P_solar <= P_solar_avail
        solar_viol_lower = np.maximum(0.0, -p_solar)
        solar_viol_upper = np.maximum(0.0, p_solar - p_solar_avail)
        solar_violation = np.sum(solar_viol_lower + solar_viol_upper)

        # 2. Wind limits: 0 <= P_wind <= P_wind_avail
        wind_viol_lower = np.maximum(0.0, -p_wind)
        wind_viol_upper = np.maximum(0.0, p_wind - p_wind_avail)
        wind_violation = np.sum(wind_viol_lower + wind_viol_upper)

        # 3. Grid limits: -P_export_max <= P_grid <= P_grid_max
        min_grid = -self.p_export_max if self.p_export_max > 0 else 0.0
        grid_viol_lower = np.maximum(0.0, min_grid - p_grid)
        grid_viol_upper = np.maximum(0.0, p_grid - self.p_grid_max)
        grid_violation = np.sum(grid_viol_lower + grid_viol_upper)

        # 4. Battery SOC bounds: SOC_min <= SOC(t) <= SOC_max
        soc_viol_lower = np.maximum(0.0, self.soc_min - soc_trajectory)
        soc_viol_upper = np.maximum(0.0, soc_trajectory - self.soc_max)
        soc_violation = np.sum(soc_viol_lower + soc_viol_upper)

        # 5. Power Balance Violation: |P_solar + P_wind + P_battery + P_grid - P_load|
        pb_mismatch = np.abs(p_solar + p_wind + p_battery + p_grid - p_load)
        pb_violation = np.sum(pb_mismatch)

        total_violation = float(
            solar_violation + wind_violation + grid_violation + (soc_violation * 100.0) + pb_violation
        )
        is_feasible = (total_violation < 1e-3)

        return {
            "is_feasible": is_feasible,
            "total_violation": total_violation,
            "power_balance_violation": float(pb_violation),
            "soc_violation": float(soc_violation),
            "solar_violation": float(solar_violation),
            "wind_violation": float(wind_violation),
            "grid_violation": float(grid_violation)
        }

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
        2. Enforces non-simultaneous charge/discharge and dynamic SOC bounds
        3. Returns repaired (p_solar, p_wind, p_battery)
        """
        p_solar_avail = scenario["solar_available_kw"]
        p_wind_avail = scenario["wind_available_kw"]
        dt = scenario.get("dt_hours", 1.0)
        T = len(p_solar)

        repaired_solar = np.clip(p_solar, 0.0, p_solar_avail)
        repaired_wind = np.clip(p_wind, 0.0, p_wind_avail)
        repaired_battery = np.zeros(T, dtype=np.float64)

        current_soc = self.soc_init

        for t in range(T):
            req_bat = p_battery[t]
            soc_after_sd = current_soc * (1.0 - self.self_discharge * dt)
            if req_bat >= 0:
                # Discharging: ensure soc_after_sd - act_bat*dt/(e_bat*eta_dis) >= soc_min
                max_dis = (soc_after_sd - self.soc_min) * self.e_bat_kwh * self.eta_dis / dt
                max_dis = max(0.0, min(self.p_dis_max, max_dis))
                act_bat = min(req_bat, max_dis)
                delta_soc = -(act_bat * dt) / (self.e_bat_kwh * self.eta_dis)
            else:
                # Charging: ensure soc_after_sd + act_ch*dt*eta_ch/e_bat <= soc_max
                ch_req = abs(req_bat)
                max_ch = (self.soc_max - soc_after_sd) * self.e_bat_kwh / (self.eta_ch * dt)
                max_ch = max(0.0, min(self.p_ch_max, max_ch))
                act_ch = min(ch_req, max_ch)
                act_bat = -act_ch
                delta_soc = (act_ch * dt * self.eta_ch) / self.e_bat_kwh

            repaired_battery[t] = act_bat
            current_soc = np.clip(soc_after_sd + delta_soc, self.soc_min, self.soc_max)

        return repaired_solar, repaired_wind, repaired_battery
