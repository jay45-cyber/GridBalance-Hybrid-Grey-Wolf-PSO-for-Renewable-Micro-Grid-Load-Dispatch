"""
experiments/run_hybrid.py
Standalone experimental runner for Hybrid GWO-PSO.
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from src.data_loader import DataLoader
from src.objective_function import MicrogridObjective
from src.hybrid_gwo_pso import HybridGWOPSO
from src.visualization import MicrogridVisualizer


def run(day_index: int = 15, seed: int = 42, pop_size: int = 30, max_iter: int = 100):
    loader = DataLoader()
    scen = loader.get_dispatch_scenario(day_index=day_index)
    obj = MicrogridObjective(loader.config)

    T = scen["horizon_steps"]
    p_solar_avail = scen["solar_available_kw"]
    p_wind_avail = scen["wind_available_kw"]
    p_bat_ch_max = loader.config["battery"]["max_charge_power_kw"]
    p_bat_dis_max = loader.config["battery"]["max_discharge_power_kw"]

    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, p_bat_ch_max)])
    ub = np.concatenate([p_solar_avail, p_wind_avail, np.full(T, p_bat_dis_max)])

    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)

    print(f"=== Starting Hybrid GWO-PSO Experiment (Day {day_index}, Seed {seed}, Pop {pop_size}, Iter {max_iter}) ===")
    hybrid = HybridGWOPSO(
        objective_evaluator=eval_func,
        lower_bounds=lb,
        upper_bounds=ub,
        pop_size=pop_size,
        max_iter=max_iter,
        seed=seed
    )
    result = hybrid.optimize()

    d = result["best_details"]
    print("\n--- Hybrid GWO-PSO Optimal Dispatch Results ---")
    print(f"Total Operating Cost: ${result['best_fitness']:.2f}")
    print(f"  - Grid Energy Cost: ${d['c_grid']:.2f}")
    print(f"  - Solar O&M Cost:   ${d['c_solar']:.2f}")
    print(f"  - Wind O&M Cost:    ${d['c_wind']:.2f}")
    print(f"  - Battery Deg Cost: ${d['c_battery']:.2f}")
    print(f"  - Curtailment Cost: ${d['c_curtailment']:.2f}")
    print(f"  - Carbon Tax Cost:  ${d['c_carbon']:.2f}")
    print(f"Renewable Utilization: {d['re_utilization_pct']:.2f}%")
    print(f"Grid Dependency:       {d['grid_dependency_pct']:.2f}%")
    print(f"Feasibility Status:    {'FEASIBLE' if d['is_feasible'] else 'INFEASIBLE'}")
    print(f"Execution Time:        {result['execution_time']:.3f} seconds")

    # Save dispatch schedule CSV
    df_dispatch = pd.DataFrame({
        "hour": range(T),
        "solar_dispatched_kw": d["p_solar"],
        "wind_dispatched_kw": d["p_wind"],
        "battery_net_kw": d["p_battery"],
        "grid_import_kw": d["p_grid"],
        "soc_start": d["soc_trajectory"][:-1],
        "load_demand_kw": scen["load_demand_kw"]
    })
    os.makedirs("results/metrics", exist_ok=True)
    df_dispatch.to_csv("results/metrics/hybrid_dispatch_schedule.csv", index=False)
    print("Saved schedule to results/metrics/hybrid_dispatch_schedule.csv")

    # Generate all related visualization figures
    viz = MicrogridVisualizer()
    viz.plot_solar_profile(scen)
    viz.plot_wind_profile(scen)
    viz.plot_load_demand(scen)
    viz.plot_single_convergence(
        result["convergence_curve"],
        algorithm_name="Hybrid GWO-PSO",
        color="#E74C3C",
        save_name="07_hybrid_convergence_curve.png"
    )
    viz.plot_energy_dispatch_distribution(
        result,
        scen,
        algorithm_name="Hybrid GWO-PSO",
        save_name="04_energy_dispatch_distribution.png"
    )
    viz.plot_battery_soc(
        result,
        loader.config,
        algorithm_name="Hybrid GWO-PSO",
        save_name="10_battery_soc_profile.png"
    )

    return result


if __name__ == "__main__":
    run()
