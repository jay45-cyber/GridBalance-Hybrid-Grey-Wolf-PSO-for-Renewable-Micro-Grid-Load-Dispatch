"""
src/energy_model.py
Defines the physical renewable microgrid energy model:
- Rigorous power balance equations with unserved load & excess generation detection
- Battery Energy Storage System (BESS) state transitions and terminal SOC tracking
- Strict prevention of simultaneous charging and discharging
- Dynamic tracking of grid import and export limits
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
        self.terminal_soc_target = float(b_cfg.get("terminal_soc_target", self.soc_init))
        self.terminal_soc_tolerance = float(b_cfg.get("terminal_soc_tolerance", 0.01))

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
    ) -> Dict[str, Any]:
        """
        Simulates the microgrid dispatch over the horizon T.
        
        Args:
            p_solar: Dispatched solar active power array (kW)
            p_wind: Dispatched wind active power array (kW)
            p_battery: Battery power array (kW; positive = discharge, negative = charge)
            p_load: Load demand array (kW)
            dt: Time step duration in hours (e.g. 1.0 for hourly, 0.25 for 15-min)
            soc_initial: Initial SOC (defaults to self.soc_init)

        Returns:
            Dictionary containing comprehensive physical simulation outputs:
            - p_solar, p_wind, p_battery, p_battery_discharge, p_battery_charge
            - p_grid, p_grid_import, p_grid_export
            - unserved_load, excess_generation, power_imbalance
            - soc_trajectory, soc_final, terminal_soc_error, terminal_soc_violated
            - soc_violations, is_power_balanced
        """
        T = len(p_load)
        init_soc = self.soc_init if soc_initial is None else soc_initial
        soc = np.zeros(T + 1, dtype=np.float64)
        soc[0] = init_soc

        p_bat_actual = np.zeros(T, dtype=np.float64)
        p_bat_discharge = np.zeros(T, dtype=np.float64)
        p_bat_charge = np.zeros(T, dtype=np.float64)
        p_grid = np.zeros(T, dtype=np.float64)
        p_grid_import = np.zeros(T, dtype=np.float64)
        p_grid_export = np.zeros(T, dtype=np.float64)
        unserved_load = np.zeros(T, dtype=np.float64)
        excess_generation = np.zeros(T, dtype=np.float64)
        power_imbalance = np.zeros(T, dtype=np.float64)
        soc_violations = np.zeros(T, dtype=bool)

        for t in range(T):
            soc_prev = soc[t]
            soc_after_sd = soc_prev * (1.0 - self.self_discharge * dt)
            requested_bat = p_battery[t]

            # Enforce non-simultaneous charge/discharge and physical power limits
            if requested_bat >= 0:
                # Discharging: cannot discharge more than stored energy above soc_min
                max_allowable_dis = (soc_after_sd - self.soc_min) * self.e_bat_kwh * self.eta_dis / dt
                max_allowable_dis = max(0.0, min(self.p_dis_max, max_allowable_dis))
                act_bat = min(requested_bat, max_allowable_dis)
                delta_soc = -(act_bat * dt) / (self.e_bat_kwh * self.eta_dis)
                p_bat_discharge[t] = act_bat
                p_bat_charge[t] = 0.0
            else:
                # Charging: requested_bat < 0
                ch_power = abs(requested_bat)
                max_allowable_ch = (self.soc_max - soc_after_sd) * self.e_bat_kwh / (self.eta_ch * dt)
                max_allowable_ch = max(0.0, min(self.p_ch_max, max_allowable_ch))
                act_ch = min(ch_power, max_allowable_ch)
                act_bat = -act_ch
                delta_soc = (act_ch * dt * self.eta_ch) / self.e_bat_kwh
                p_bat_discharge[t] = 0.0
                p_bat_charge[t] = act_ch

            # Update SOC at next step
            soc_next = soc_after_sd + delta_soc
            soc[t + 1] = np.clip(soc_next, self.soc_min, self.soc_max)
            p_bat_actual[t] = act_bat

            # Verify SOC boundary compliance
            if soc[t + 1] < (self.soc_min - 1e-4) or soc[t + 1] > (self.soc_max + 1e-4):
                soc_violations[t] = True

            # Calculate Grid power required for exact power balance:
            # P_load(t) = P_solar(t) + P_wind(t) + P_battery(t) + P_grid(t)
            # => req_grid = P_load(t) - P_solar(t) - P_wind(t) - act_bat
            req_grid = p_load[t] - p_solar[t] - p_wind[t] - act_bat

            min_grid = -self.p_export_max if self.p_export_max > 0 else 0.0

            if req_grid > self.p_grid_max:
                # Grid import capped at maximum rating; remaining deficit is unserved load
                act_grid = self.p_grid_max
                unserved = req_grid - self.p_grid_max
                excess = 0.0
            elif req_grid < min_grid:
                # Excess renewable generation exceeds maximum export capacity; surplus is excess/curtailed
                act_grid = min_grid
                unserved = 0.0
                excess = min_grid - req_grid
            else:
                # Grid can absorb or supply the required balance exactly
                act_grid = req_grid
                unserved = 0.0
                excess = 0.0

            p_grid[t] = act_grid
            p_grid_import[t] = max(0.0, act_grid)
            p_grid_export[t] = max(0.0, -act_grid)
            unserved_load[t] = unserved
            excess_generation[t] = excess
            # Net imbalance is unserved load or unhandled excess
            power_imbalance[t] = unserved + excess

        # Terminal SOC constraint evaluation
        soc_final = soc[-1]
        target_terminal_soc = self.terminal_soc_target if soc_initial is None else init_soc
        terminal_soc_error = abs(soc_final - target_terminal_soc)
        terminal_soc_violated = bool(terminal_soc_error > self.terminal_soc_tolerance)

        # Power balance check
        is_power_balanced = bool(np.max(power_imbalance) < 1e-3)

        return {
            "p_solar": p_solar,
            "p_wind": p_wind,
            "p_battery": p_bat_actual,
            "p_battery_discharge": p_bat_discharge,
            "p_battery_charge": p_bat_charge,
            "p_grid": p_grid,
            "p_grid_import": p_grid_import,
            "p_grid_export": p_grid_export,
            "unserved_load": unserved_load,
            "excess_generation": excess_generation,
            "soc_trajectory": soc,
            "soc_initial": init_soc,
            "soc_final": soc_final,
            "terminal_soc_error": float(terminal_soc_error),
            "terminal_soc_violated": terminal_soc_violated,
            "power_imbalance": power_imbalance,
            "soc_violations": soc_violations,
            "is_power_balanced": is_power_balanced
        }
