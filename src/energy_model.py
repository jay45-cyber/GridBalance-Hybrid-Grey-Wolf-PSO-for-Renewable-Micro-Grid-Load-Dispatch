"""
src/energy_model.py
Defines the physical renewable microgrid energy model:
- Power balance equations
- Battery Energy Storage System (BESS) state transitions and dynamics
- Renewable dispatch and grid interaction
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional


class MicrogridEnergyModel:
    """
    Physical energy balance and battery state-of-charge transition model
    for renewable microgrid dispatch.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # BESS parameters
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

        # Grid parameters
        g_cfg = config["grid"]
        self.p_grid_max = float(g_cfg["max_import_power_kw"])
        self.p_export_max = float(g_cfg.get("max_export_power_kw", 0.0))

        # Generator parameters
        self.p_solar_rated = float(config["solar_pv"]["rated_capacity_kw"])
        self.p_wind_rated = float(config["wind_turbine"]["rated_capacity_kw"])

    def simulate_dispatch(
        self,
        p_solar: np.ndarray,
        p_wind: np.ndarray,
        p_battery: np.ndarray,
        p_load: np.ndarray,
        dt: float = 1.0,
        soc_initial: Optional[float] = None
    ) -> Dict[str, np.ndarray]:
        """
        Simulates the microgrid dispatch over the horizon.
        
        Args:
            p_solar: Dispatched solar active power array (kW)
            p_wind: Dispatched wind active power array (kW)
            p_battery: Battery power array (kW; positive = discharge, negative = charge)
            p_load: Load demand array (kW)
            dt: Time step duration in hours (e.g. 1.0 for hourly, 0.25 for 15-min)
            soc_initial: Initial SOC (defaults to config value)

        Returns:
            Dictionary containing:
            - p_grid: Main grid exchange power array (kW)
            - soc_trajectory: SOC array of length T+1
            - p_battery_actual: Net battery power after physical limits
            - power_imbalance: Any residual power mismatch (kW)
            - soc_violations: Boolean array of SOC bound violations
        """
        T = len(p_load)
        soc = np.zeros(T + 1, dtype=np.float64)
        soc[0] = self.soc_init if soc_initial is None else soc_initial

        p_bat_actual = np.zeros(T, dtype=np.float64)
        p_grid = np.zeros(T, dtype=np.float64)
        power_imbalance = np.zeros(T, dtype=np.float64)
        soc_violations = np.zeros(T, dtype=bool)

        for t in range(T):
            soc_prev = soc[t]
            soc_after_sd = soc_prev * (1.0 - self.self_discharge * dt)
            requested_bat = p_battery[t]

            # Enforce physical charge/discharge power limits
            if requested_bat >= 0:
                # Discharging: cannot discharge more than available usable energy
                max_allowable_dis = (soc_after_sd - self.soc_min) * self.e_bat_kwh * self.eta_dis / dt
                max_allowable_dis = max(0.0, min(self.p_dis_max, max_allowable_dis))
                act_bat = min(requested_bat, max_allowable_dis)
                delta_soc = -(act_bat * dt) / (self.e_bat_kwh * self.eta_dis)
            else:
                # Charging: requested_bat < 0
                ch_power = abs(requested_bat)
                max_allowable_ch = (self.soc_max - soc_after_sd) * self.e_bat_kwh / (self.eta_ch * dt)
                max_allowable_ch = max(0.0, min(self.p_ch_max, max_allowable_ch))
                act_ch = min(ch_power, max_allowable_ch)
                act_bat = -act_ch
                delta_soc = (act_ch * dt * self.eta_ch) / self.e_bat_kwh

            # Update SOC
            soc_next = soc_after_sd + delta_soc
            soc[t + 1] = np.clip(soc_next, self.soc_min, self.soc_max)
            p_bat_actual[t] = act_bat

            # Check SOC bound violations
            if soc[t + 1] < (self.soc_min - 1e-4) or soc[t + 1] > (self.soc_max + 1e-4):
                soc_violations[t] = True

            # Calculate Grid power required for exact power balance:
            # P_load(t) = P_solar(t) + P_wind(t) + P_battery(t) + P_grid(t)
            # => P_grid(t) = P_load(t) - P_solar(t) - P_wind(t) - P_battery(t)
            req_grid = p_load[t] - p_solar[t] - p_wind[t] - act_bat

            # Clamp grid within physical connection limits
            # Allowing export if p_export_max > 0, otherwise non-negative import
            min_grid = -self.p_export_max if self.p_export_max > 0 else 0.0
            act_grid = np.clip(req_grid, min_grid, self.p_grid_max)
            p_grid[t] = act_grid

            # Any unbalance left (e.g. if req_grid exceeds p_grid_max or below export limit)
            power_imbalance[t] = req_grid - act_grid

        return {
            "p_solar": p_solar,
            "p_wind": p_wind,
            "p_battery": p_bat_actual,
            "p_grid": p_grid,
            "soc_trajectory": soc,
            "power_imbalance": power_imbalance,
            "soc_violations": soc_violations
        }
