"""
experiments/compare_algorithms.py
Multi-seed benchmark comparing PSO, GWO, Hybrid GWO-PSO, and GA
under identical problem formulations and evaluation budgets.
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple

from src.data_loader import DataLoader
from src.objective_function import MicrogridObjective
from src.pso import ParticleSwarmOptimizer
from src.gwo import GreyWolfOptimizer
from src.hybrid_gwo_pso import HybridGWOPSO
from src.ga import GeneticAlgorithm
from src.evaluation import ExperimentEvaluator
from src.visualization import MicrogridVisualizer


def run_benchmark(
    day_index: int = 15,
    pop_size: int = 30,
    max_iter: int = 100,
    seeds: List[int] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if seeds is None:
        seeds = [42, 101, 203, 314, 425, 536, 647, 758, 869, 970]

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

    algorithms = {
        "PSO": lambda s: ParticleSwarmOptimizer(eval_func, lb, ub, pop_size=pop_size, max_iter=max_iter, seed=s),
        "GWO": lambda s: GreyWolfOptimizer(eval_func, lb, ub, pop_size=pop_size, max_iter=max_iter, seed=s),
        "Hybrid GWO-PSO": lambda s: HybridGWOPSO(eval_func, lb, ub, pop_size=pop_size, max_iter=max_iter, seed=s),
        "GA": lambda s: GeneticAlgorithm(eval_func, lb, ub, pop_size=pop_size, max_iter=max_iter, seed=s)
    }

    print("================================================================================")
    print("GRIDBALANCE BENCHMARK: MULTI-ALGORITHM PERFORMANCE EVALUATION")
    print(f"Horizon: {T} Hours | Pop Size: {pop_size} | Iterations: {max_iter} | Seeds: {len(seeds)}")
    print("================================================================================")

    multi_algo_results: Dict[str, List[Dict[str, Any]]] = {algo: [] for algo in algorithms}

    for algo_name, creator in algorithms.items():
        print(f"\nEvaluating Algorithm: {algo_name}")
        for run_idx, seed in enumerate(seeds):
            opt = creator(seed)
            res = opt.optimize()
            res["seed"] = seed
            multi_algo_results[algo_name].append(res)
            print(f"  Run {run_idx+1:02d}/{len(seeds)} (Seed {seed}): Best Cost = ${res['best_fitness']:.2f} | Time = {res['execution_time']:.2f}s")

    # Evaluation & Statistical Metrics
    evaluator = ExperimentEvaluator(metrics_dir="results/metrics")
    summary_df = evaluator.generate_comparison_table(multi_algo_results, save_csv=True)
    evaluator.export_per_run_data(multi_algo_results)

    print("\n================================================================================")
    print("BENCHMARK COMPARISON SUMMARY TABLE")
    print("================================================================================")
    cols_display = [
        "algorithm", "best_cost_usd", "mean_cost_usd", "std_cost_usd",
        "worst_cost_usd", "mean_runtime_sec", "re_utilization_pct", "feasibility_rate_pct"
    ]
    print(summary_df[cols_display].to_string(index=False))

    # Generate all Research Figures
    viz = MicrogridVisualizer(output_dir="results/graphs")
    viz.plot_solar_profile(scen, save_name="01_solar_generation_profile.png")
    viz.plot_wind_profile(scen, save_name="02_wind_generation_profile.png")
    viz.plot_load_demand(scen, save_name="03_load_demand_profile.png")

    # Find best overall run (typically Hybrid GWO-PSO)
    best_hybrid_run = min(multi_algo_results["Hybrid GWO-PSO"], key=lambda r: r["best_fitness"])
    viz.plot_energy_dispatch_distribution(
        best_hybrid_run, scen, algorithm_name="Hybrid GWO-PSO", save_name="04_energy_dispatch_distribution.png"
    )
    viz.plot_battery_soc(
        best_hybrid_run, loader.config, algorithm_name="Hybrid GWO-PSO", save_name="10_battery_soc_profile.png"
    )

    # Individual convergence curves (seed 42 run)
    pso_seed42 = next(r for r in multi_algo_results["PSO"] if r["seed"] == 42)
    gwo_seed42 = next(r for r in multi_algo_results["GWO"] if r["seed"] == 42)
    hyb_seed42 = next(r for r in multi_algo_results["Hybrid GWO-PSO"] if r["seed"] == 42)
    ga_seed42 = next(r for r in multi_algo_results["GA"] if r["seed"] == 42)

    viz.plot_single_convergence(pso_seed42["convergence_curve"], "PSO", "#2980B9", "05_pso_convergence_curve.png")
    viz.plot_single_convergence(gwo_seed42["convergence_curve"], "GWO", "#27AE60", "06_gwo_convergence_curve.png")
    viz.plot_single_convergence(hyb_seed42["convergence_curve"], "Hybrid GWO-PSO", "#E74C3C", "07_hybrid_convergence_curve.png")

    # Multi-algorithm convergence
    algo_curves = {
        "PSO": pso_seed42["convergence_curve"],
        "GWO": gwo_seed42["convergence_curve"],
        "Hybrid GWO-PSO": hyb_seed42["convergence_curve"],
        "GA": ga_seed42["convergence_curve"]
    }
    viz.plot_multi_convergence(algo_curves, save_name="07_multi_algorithm_convergence.png")

    # Boxplot of costs
    viz.plot_cost_comparison(multi_algo_results, save_name="08_algorithm_cost_comparison.png")

    # Bar chart of RE utilization
    viz.plot_renewable_utilization_comparison(summary_df, save_name="09_renewable_energy_utilization_comparison.png")

    print("\nAll 10 benchmark figures and metric CSVs successfully generated.")
    return summary_df, multi_algo_results


if __name__ == "__main__":
    run_benchmark()
