import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from src.data_loader import DataLoader
from src.objective_function import MicrogridObjective
from src.pso import ParticleSwarmOptimizer
from src.gwo import GreyWolfOptimizer
from src.hybrid_gwo_pso import HybridGWOPSO

def run_test():
    loader = DataLoader()
    scen = loader.get_dispatch_scenario(day_index=15)
    obj = MicrogridObjective(loader.config)

    T = scen['horizon_steps']
    p_solar_avail = scen['solar_available_kw']
    p_wind_avail = scen['wind_available_kw']
    p_bat_ch_max = loader.config['battery']['max_charge_power_kw']
    p_bat_dis_max = loader.config['battery']['max_discharge_power_kw']

    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, p_bat_ch_max)])
    ub = np.concatenate([p_solar_avail, p_wind_avail, np.full(T, p_bat_dis_max)])

    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)

    print("--- Running PSO ---")
    pso = ParticleSwarmOptimizer(eval_func, lb, ub, pop_size=20, max_iter=25, seed=42)
    res_pso = pso.optimize()
    print(f"PSO Best Cost: ${res_pso['best_fitness']:.2f}, Feasible: {res_pso['best_details']['is_feasible']}")

    print("--- Running GWO ---")
    gwo = GreyWolfOptimizer(eval_func, lb, ub, pop_size=20, max_iter=25, seed=42)
    res_gwo = gwo.optimize()
    print(f"GWO Best Cost: ${res_gwo['best_fitness']:.2f}, Feasible: {res_gwo['best_details']['is_feasible']}")

    print("--- Running Hybrid GWO-PSO ---")
    hybrid = HybridGWOPSO(eval_func, lb, ub, pop_size=20, max_iter=25, seed=42)
    res_hyb = hybrid.optimize()
    print(f"Hybrid Best Cost: ${res_hyb['best_fitness']:.2f}, Feasible: {res_hyb['best_details']['is_feasible']}")

if __name__ == "__main__":
    run_test()
