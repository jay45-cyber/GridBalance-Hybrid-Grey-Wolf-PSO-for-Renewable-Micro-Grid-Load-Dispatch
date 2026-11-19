"""
tests/validate_end_to_end.py
Comprehensive End-to-End Mathematical & Physical Validation Script.
"""

import os
import sys
import numpy as np
import pandas as pd

# Add repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_loader import DataLoader


def validate_all():
    print("================================================================================")
    print("GRIDBALANCE: FINAL RIGOROUS END-TO-END VALIDATION")
    print("================================================================================")

    # 1. Inspect detailed_runs_metrics.csv
    runs_path = "results/metrics/detailed_runs_metrics.csv"
    assert os.path.exists(runs_path), f"Missing {runs_path}"
    df_runs = pd.read_csv(runs_path)
    
    print(f"\n1. Multi-Seed Benchmark Data Integrity (Total Runs: {len(df_runs)})")
    algos = df_runs['algorithm'].unique().tolist()
    print(f"   - Algorithms evaluated: {algos}")
    seeds_per_algo = df_runs.groupby('algorithm')['seed'].count().to_dict()
    print(f"   - Runs per algorithm: {seeds_per_algo}")
    assert all(count >= 10 for count in seeds_per_algo.values()), "Fewer than 10 seeds evaluated!"

    # Feasibility check
    infeasible_count = (df_runs['is_feasible'] == False).sum()
    feas_rate = 100.0 * (1 - infeasible_count / len(df_runs))
    print(f"   - Feasibility Rate across all 40 runs: {feas_rate:.1f}% ({infeasible_count} infeasible)")
    assert infeasible_count == 0, f"Found {infeasible_count} infeasible runs!"

    # Penalties check
    total_penalties = df_runs['total_penalty'].sum()
    print(f"   - Total Constraint Penalties across all 40 runs: ${total_penalties:.4f}")
    assert total_penalties == 0.0, "Non-zero constraint penalties present!"

    # Terminal SOC check
    max_term_err = df_runs['terminal_soc_error'].max()
    mean_term_err = df_runs['terminal_soc_error'].mean()
    print(f"   - Terminal SOC Error: Max = {max_term_err*100:.3f}%, Mean = {mean_term_err*100:.3f}% (Cyclic limit: 1.0%)")
    assert max_term_err <= 0.010001, f"Terminal SOC error exceeded 1.0% limit: {max_term_err}"

    # Power balance & unserved load
    max_unserved = df_runs['unserved_load_kwh'].max()
    print(f"   - Maximum Unserved Load across all runs: {max_unserved:.4f} kWh")
    assert max_unserved == 0.0, "Unserved load found in feasible runs!"

    # Standardized Metrics check (A + D == 100%)
    metric_sum = df_runs['re_utilization_pct'] + df_runs['re_curtailment_pct']
    print(f"   - Metric A (Utilization) + Metric D (Curtailment) Conservation Identity: Min = {metric_sum.min():.4f}%, Max = {metric_sum.max():.4f}%")
    np.testing.assert_allclose(metric_sum.values, 100.0, atol=1e-3, err_msg="Metric A + D != 100.0%!")

    # Summary Statistics per Algorithm
    print("\n2. Algorithm Performance & Dispersion Statistics (Pure Operating Cost):")
    summary = []
    for algo in ['PSO', 'Hybrid GWO-PSO', 'GA', 'GWO']:
        sub = df_runs[df_runs['algorithm'] == algo]
        best_cost = sub['operating_cost'].min()
        mean_cost = sub['operating_cost'].mean()
        std_cost = sub['operating_cost'].std()
        worst_cost = sub['operating_cost'].max()
        mean_time = sub['execution_time_sec'].mean()
        re_util = sub['re_utilization_pct'].mean()
        grid_dep = sub['grid_dependency_pct'].mean()
        print(f"   [{algo:14s}] Best: ${best_cost:7.2f} | Mean: ${mean_cost:7.2f} | Std: ${std_cost:5.2f} | Worst: ${worst_cost:7.2f} | Time: {mean_time:4.2f}s | Util: {re_util:5.2f}% | GridDep: {grid_dep:5.2f}%")
        summary.append({
            "algorithm": algo,
            "best": best_cost,
            "mean": mean_cost,
            "std": std_cost,
            "worst": worst_cost
        })

    # 3. Hourly Physical Constraints & Power Balance Validation on 4 schedules
    print("\n3. Hourly Physical Limits & Power Balance Identity Verification on 24-Hour Schedules:")
    loader = DataLoader()
    scen = loader.get_dispatch_scenario(day_index=15)
    p_load = scen["load_demand_kw"]
    p_solar_avail = scen["solar_available_kw"]
    p_wind_avail = scen["wind_available_kw"]
    p_ch_max = loader.config["battery"]["max_charge_power_kw"]
    p_dis_max = loader.config["battery"]["max_discharge_power_kw"]
    p_grid_max = loader.config["grid"]["max_import_power_kw"]

    for algo in ['pso', 'gwo', 'hybrid', 'ga']:
        sched_file = f"results/metrics/{algo}_dispatch_schedule.csv"
        assert os.path.exists(sched_file), f"Missing {sched_file}"
        df_s = pd.read_csv(sched_file)
        
        solar_disp = df_s['solar_dispatched_kw'].values
        wind_disp = df_s['wind_dispatched_kw'].values
        bat_net = df_s['battery_net_kw'].values
        bat_dis = df_s['battery_discharge_kw'].values
        bat_ch = df_s['battery_charge_kw'].values
        grid_imp = df_s['grid_import_kw'].values
        grid_exp = df_s['grid_export_kw'].values
        unserved = df_s['unserved_load_kw'].values
        excess = df_s['excess_generation_kw'].values if 'excess_generation_kw' in df_s else df_s['excess_gen_kw'].values
        soc_series = df_s['soc_start'].values

        # Power balance equation
        grid_net = grid_imp - grid_exp
        imbalance = np.abs(solar_disp + wind_disp + bat_net + grid_net + unserved - excess - p_load)
        max_imbalance = np.max(imbalance)
        assert max_imbalance < 1e-4, f"Power balance violated in {algo}: {max_imbalance}"

        # Bound checks
        assert np.all(solar_disp >= -1e-5) and np.all(solar_disp <= p_solar_avail + 1e-4), f"Solar bounds violated in {algo}"
        assert np.all(wind_disp >= -1e-5) and np.all(wind_disp <= p_wind_avail + 1e-4), f"Wind bounds violated in {algo}"
        assert np.all(bat_ch >= -1e-5) and np.all(bat_ch <= p_ch_max + 1e-4), f"Battery charge limit violated in {algo}"
        assert np.all(bat_dis >= -1e-5) and np.all(bat_dis <= p_dis_max + 1e-4), f"Battery discharge limit violated in {algo}"
        assert np.all(bat_ch * bat_dis < 1e-4), f"Simultaneous charge and discharge detected in {algo}!"
        assert np.all(grid_imp >= -1e-5) and np.all(grid_imp <= p_grid_max + 1e-4), f"Grid import limit violated in {algo}"
        assert np.all(grid_exp >= -1e-5) and np.all(grid_exp <= p_grid_max + 1e-4), f"Grid export limit violated in {algo}"
        assert np.all(soc_series >= 0.20 - 1e-4) and np.all(soc_series <= 0.90 + 1e-4), f"SOC bounds violated in {algo}"
        
        print(f"   [{algo.upper():6s}] Max Imbalance = {max_imbalance:10.4e} kW | Solar: [0, {np.max(solar_disp):.1f}] kW | Wind: [0, {np.max(wind_disp):.1f}] kW | BatNet: [{np.min(bat_net):.1f}, {np.max(bat_net):.1f}] kW -> ALL CONSTRAINTS STRICTLY SATISFIED")

    print("\n================================================================================")
    print("VERIFICATION RESULT: ALL PHYSICAL, MATHEMATICAL, AND LOGICAL CHECKS PASSED (100%)")
    print("================================================================================")


if __name__ == "__main__":
    validate_all()
