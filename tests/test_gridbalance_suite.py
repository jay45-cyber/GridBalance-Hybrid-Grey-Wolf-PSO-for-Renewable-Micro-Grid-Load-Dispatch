"""
tests/test_gridbalance_suite.py
Comprehensive automated test suite for GridBalance:
- Dataset integrity and audit
- Data loader and scenario sampling
- Energy model and physical balance
- Battery SOC dynamics and efficiency
- Constraint checks and feasibility repair
- PSO standalone optimization
- GWO standalone optimization
- Hybrid GWO-PSO optimization
- Reproducibility with random seeds
- Metric export and result persistence
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_preprocessing import DDRE33Preprocessor
from src.data_loader import DataLoader
from src.energy_model import MicrogridEnergyModel
from src.constraints import MicrogridConstraints
from src.objective_function import MicrogridObjective
from src.pso import ParticleSwarmOptimizer
from src.gwo import GreyWolfOptimizer
from src.hybrid_gwo_pso import HybridGWOPSO
from src.evaluation import ExperimentEvaluator


@pytest.fixture(scope="session")
def loaded_system():
    loader = DataLoader("config/system_parameters.yaml")
    scenario = loader.get_dispatch_scenario(day_index=15)
    objective = MicrogridObjective(loader.config)
    return {
        "loader": loader,
        "config": loader.config,
        "scenario": scenario,
        "objective": objective,
        "energy_model": objective.energy_model,
        "constraints": objective.constraints
    }


# ------------------------------------------------------------------------------
# 1. Dataset & Preprocessing Tests
# ------------------------------------------------------------------------------
def test_dataset_files_exist():
    """Verify raw DDRE-33 files exist and are non-empty."""
    assert os.path.exists("data/raw/node_33_solar_1.csv"), "Solar file missing"
    assert os.path.exists("data/raw/node_22_wind_1.csv"), "Wind file missing"
    assert os.path.getsize("data/raw/node_33_solar_1.csv") > 10000
    assert os.path.getsize("data/raw/node_22_wind_1.csv") > 10000


def test_preprocessing_audit():
    """Audit should confirm zero NaNs, zero negative values, and valid per-unit ranges."""
    pre = DDRE33Preprocessor()
    audit = pre.audit_raw_data()
    assert audit["files"]["solar_pv_bus33"]["missing_values"] == 0
    assert audit["files"]["wind_bus22"]["missing_values"] == 0
    assert audit["files"]["solar_pv_bus33"]["negative_count"] == 0
    assert audit["files"]["wind_bus22"]["negative_count"] == 0
    assert audit["files"]["solar_pv_bus33"]["max_value_pu"] <= 1.0
    assert audit["files"]["wind_bus22"]["max_value_pu"] <= 1.0


def test_scenario_dimensions(loaded_system):
    """Scenario vectors must match horizon steps (24 hours)."""
    scen = loaded_system["scenario"]
    assert scen["horizon_steps"] == 24
    assert len(scen["solar_available_kw"]) == 24
    assert len(scen["wind_available_kw"]) == 24
    assert len(scen["load_demand_kw"]) == 24
    assert len(scen["grid_tariff_per_kwh"]) == 24
    assert np.all(scen["solar_available_kw"] >= 0.0)
    assert np.all(scen["wind_available_kw"] >= 0.0)
    assert np.all(scen["load_demand_kw"] > 0.0)


# ------------------------------------------------------------------------------
# 2. Energy Model & Battery SOC Tests
# ------------------------------------------------------------------------------
def test_battery_soc_dynamics(loaded_system):
    """Test battery charging and discharging updates SOC accurately according to efficiencies."""
    em = loaded_system["energy_model"]
    dt = 1.0
    p_load = np.full(5, 500.0)
    p_solar = np.zeros(5)
    p_wind = np.zeros(5)

    # Discharging at 200 kW for 1 hour from initial SOC 0.50
    # Expected delta_soc = -(200 * 1.0) / (2000 * 0.95) = -0.10526
    p_bat_dis = np.array([200.0, 0, 0, 0, 0])
    sim = em.simulate_dispatch(p_solar, p_wind, p_bat_dis, p_load, dt=dt, soc_initial=0.50)
    soc1 = sim["soc_trajectory"][1]
    expected_soc1 = 0.50 * (1.0 - em.self_discharge) - (200.0 * dt) / (em.e_bat_kwh * em.eta_dis)
    assert pytest.approx(soc1, abs=1e-4) == expected_soc1

    # Charging at 200 kW for 1 hour from initial SOC 0.50
    # Expected delta_soc = +(200 * 1.0 * 0.95) / 2000 = +0.0950
    p_bat_ch = np.array([-200.0, 0, 0, 0, 0])
    sim_ch = em.simulate_dispatch(p_solar, p_wind, p_bat_ch, p_load, dt=dt, soc_initial=0.50)
    soc1_ch = sim_ch["soc_trajectory"][1]
    expected_soc1_ch = 0.50 * (1.0 - em.self_discharge) + (200.0 * dt * em.eta_ch) / em.e_bat_kwh
    assert pytest.approx(soc1_ch, abs=1e-4) == expected_soc1_ch


def test_battery_soc_boundaries(loaded_system):
    """Enforce that battery cannot discharge below soc_min or charge above soc_max."""
    em = loaded_system["energy_model"]
    # Attempt extreme discharge for 24 hours
    p_bat_extreme_dis = np.full(24, 600.0)
    p_load = np.full(24, 1000.0)
    sim = em.simulate_dispatch(np.zeros(24), np.zeros(24), p_bat_extreme_dis, p_load)
    soc_traj = sim["soc_trajectory"]
    assert np.all(soc_traj >= em.soc_min - 1e-4), f"SOC dipped below min: {np.min(soc_traj)}"
    assert np.all(soc_traj <= em.soc_max + 1e-4), f"SOC exceeded max: {np.max(soc_traj)}"


def test_power_balance_equality(loaded_system):
    """Verify that generation + battery + grid strictly balances load demand."""
    em = loaded_system["energy_model"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]

    p_sol = scen["solar_available_kw"] * 0.8
    p_wnd = scen["wind_available_kw"] * 0.8
    p_bat = np.full(T, 50.0)
    p_load = scen["load_demand_kw"]

    sim = em.simulate_dispatch(p_sol, p_wnd, p_bat, p_load)
    p_grid = sim["p_grid"]
    p_bat_act = sim["p_battery"]

    total_supplied = p_sol + p_wnd + p_bat_act + p_grid
    mismatch = np.abs(total_supplied - p_load)
    assert np.all(mismatch < 1e-3), f"Power balance violated: max mismatch {np.max(mismatch)}"


# ------------------------------------------------------------------------------
# 3. Constraints and Feasibility Repair Tests
# ------------------------------------------------------------------------------
def test_feasibility_repair(loaded_system):
    """Test feasibility repair operator converts invalid values to valid ones."""
    constraints = loaded_system["constraints"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]

    # Candidate with intentional violations: negative solar, excessive wind, out-of-bound battery
    bad_solar = np.full(T, -50.0)
    bad_wind = scen["wind_available_kw"] + 5000.0
    bad_battery = np.full(T, 2000.0)  # Exceeds max discharge of 600 kW

    rep_solar, rep_wind, rep_bat = constraints.repair_candidate(bad_solar, bad_wind, bad_battery, scen)

    assert np.all(rep_solar >= 0.0)
    assert np.all(rep_solar <= scen["solar_available_kw"])
    assert np.all(rep_wind >= 0.0)
    assert np.all(rep_wind <= scen["wind_available_kw"])
    assert np.all(rep_bat <= constraints.p_dis_max)
    assert np.all(rep_bat >= -constraints.p_ch_max)


# ------------------------------------------------------------------------------
# 4. Objective Function & Cost Calculation Tests
# ------------------------------------------------------------------------------
def test_objective_evaluation(loaded_system):
    """Test objective evaluation returns non-negative cost components and valid metrics."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]

    candidate = np.concatenate([
        scen["solar_available_kw"],
        scen["wind_available_kw"],
        np.zeros(T)
    ])
    res = obj.evaluate(candidate, scen, apply_repair=True)

    assert res["operating_cost"] > 0.0
    assert res["c_solar"] >= 0.0
    assert res["c_wind"] >= 0.0
    assert res["c_grid"] >= 0.0
    assert res["re_utilization_pct"] >= 0.0
    assert res["re_utilization_pct"] <= 100.0
    assert bool(res["is_feasible"]) is True


# ------------------------------------------------------------------------------
# 5. Standalone Optimization Algorithms Tests
# ------------------------------------------------------------------------------
def test_pso_optimization(loaded_system):
    """Verify PSO runs and reduces cost from initialization."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]
    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, 600.0)])
    ub = np.concatenate([scen["solar_available_kw"], scen["wind_available_kw"], np.full(T, 600.0)])

    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)
    pso = ParticleSwarmOptimizer(eval_func, lb, ub, pop_size=15, max_iter=15, seed=42)
    res = pso.optimize()

    assert res["best_fitness"] > 0.0
    assert res["convergence_curve"][-1] <= res["convergence_curve"][0]
    assert bool(res["best_details"]["is_feasible"]) is True


def test_gwo_optimization(loaded_system):
    """Verify GWO runs and reduces cost from initialization."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]
    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, 600.0)])
    ub = np.concatenate([scen["solar_available_kw"], scen["wind_available_kw"], np.full(T, 600.0)])

    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)
    gwo = GreyWolfOptimizer(eval_func, lb, ub, pop_size=15, max_iter=15, seed=42)
    res = gwo.optimize()

    assert res["best_fitness"] > 0.0
    assert res["convergence_curve"][-1] <= res["convergence_curve"][0]
    assert bool(res["best_details"]["is_feasible"]) is True


def test_hybrid_gwo_pso_optimization(loaded_system):
    """Verify Hybrid GWO-PSO runs and produces feasible optimal dispatch."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]
    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, 600.0)])
    ub = np.concatenate([scen["solar_available_kw"], scen["wind_available_kw"], np.full(T, 600.0)])

    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)
    hybrid = HybridGWOPSO(eval_func, lb, ub, pop_size=15, max_iter=15, seed=42)
    res = hybrid.optimize()

    assert res["best_fitness"] > 0.0
    assert res["convergence_curve"][-1] <= res["convergence_curve"][0]
    assert bool(res["best_details"]["is_feasible"]) is True
    assert len(res["best_position"]) == 3 * T


# ------------------------------------------------------------------------------
# 6. Reproducibility Test
# ------------------------------------------------------------------------------
def test_seed_reproducibility(loaded_system):
    """Verify identical seeds produce bitwise identical results."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]
    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, 600.0)])
    ub = np.concatenate([scen["solar_available_kw"], scen["wind_available_kw"], np.full(T, 600.0)])

    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)
    run1 = HybridGWOPSO(eval_func, lb, ub, pop_size=10, max_iter=10, seed=123).optimize()
    run2 = HybridGWOPSO(eval_func, lb, ub, pop_size=10, max_iter=10, seed=123).optimize()

    assert run1["best_fitness"] == run2["best_fitness"]
    np.testing.assert_allclose(run1["best_position"], run2["best_position"], atol=1e-10)


# ------------------------------------------------------------------------------
# 7. Metrics & File Persistence Tests
# ------------------------------------------------------------------------------
def test_results_exported():
    """Verify metric CSV files and graphs exist and are populated."""
    assert os.path.exists("results/metrics/algorithm_comparison_summary.csv")
    assert os.path.exists("results/metrics/detailed_runs_metrics.csv")
    df_sum = pd.read_csv("results/metrics/algorithm_comparison_summary.csv")
    assert len(df_sum) >= 3
    assert "mean_cost_usd" in df_sum.columns
    assert "feasibility_rate_pct" in df_sum.columns

    # Verify key figures
    assert os.path.exists("results/graphs/01_solar_generation_profile.png")
    assert os.path.exists("results/graphs/02_wind_generation_profile.png")
    assert os.path.exists("results/graphs/04_energy_dispatch_distribution.png")
    assert os.path.exists("results/graphs/07_multi_algorithm_convergence.png")
    assert os.path.exists("results/graphs/10_battery_soc_profile.png")
