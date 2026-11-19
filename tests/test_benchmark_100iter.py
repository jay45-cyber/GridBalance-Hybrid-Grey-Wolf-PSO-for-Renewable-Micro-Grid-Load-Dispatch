import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from src.data_loader import DataLoader
from src.objective_function import MicrogridObjective
from src.pso import ParticleSwarmOptimizer
from src.gwo import GreyWolfOptimizer
from src.hybrid_gwo_pso import HybridGWOPSO

def main():
    loader = DataLoader()
    scen = loader.get_dispatch_scenario(day_index=15)
    obj = MicrogridObjective(loader.config)
    T = scen['horizon_steps']
    p_bat_ch_max = loader.config['battery']['max_charge_power_kw']
    p_bat_dis_max = loader.config['battery']['max_discharge_power_kw']
    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, p_bat_ch_max)])
    ub = np.concatenate([scen['solar_available_kw'], scen['wind_available_kw'], np.full(T, p_bat_dis_max)])
    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)

    for name, cls in [('PSO', ParticleSwarmOptimizer), ('GWO', GreyWolfOptimizer), ('Hybrid GWO-PSO', HybridGWOPSO)]:
        opt = cls(eval_func, lb, ub, pop_size=30, max_iter=100, seed=42)
        res = opt.optimize()
        print(f"{name:15s} | Best: ${res['best_fitness']:.2f} | Time: {res['execution_time']:.2f}s | Start: ${res['convergence_curve'][0]:.2f} -> End: ${res['convergence_curve'][-1]:.2f}")

if __name__ == "__main__":
    main()
