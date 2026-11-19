"""
tests/test_gridbalance_suite.py
Comprehensive automated test suite for GridBalance:
- Battery terminal SOC constraint & cyclic conservation
- Battery energy conservation & efficiencies
- Battery charging limits & discharging limits
- Solar & Wind generation bounds
- Grid import/export limits & unserved load / excess power
- Power balance verification
- Standardized renewable utilization & curtailment metrics
- Objective function cost components & penalty separation
- Standalone PSO optimization
- Standalone GWO optimization
- Hybrid GWO-PSO optimization
- Seed reproducibility & result export
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
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


# ------------------------------------------------------------------------------
# 2. Battery Terminal SOC & Energy Conservation Tests
# ------------------------------------------------------------------------------
def test_battery_terminal_soc(loaded_system):
    """
    Verify terminal SOC constraint for cyclic dispatch:
    Battery terminal SOC must equal initial SOC within tolerance.
    """
    em = loaded_system["energy_model"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]

    # Simulating a balanced battery dispatch (charge 200kW for 2h, discharge equivalent)
    p_bat_balanced = np.zeros(T)
    # Charge 200kW at hour 0 (adds 200 * 0.95 = 190 kWh)
    p_bat_balanced[0] = -200.0
    # Discharge at hour 1: to deplete 190 kWh, discharge 190 * 0.95 = 180.5 kW
    p_bat_balanced[1] = 180.5

    sim = em.simulate_dispatch(scen["solar_available_kw"], scen["wind_available_kw"], p_bat_balanced, scen["load_demand_kw"])
    assert sim["soc_initial"] == em.soc_init
    # Terminal SOC error should be very small
    assert sim["terminal_soc_error"] <= 0.02


def test_battery_energy_conservation(loaded_system):
    """Verify discrete SOC equation rigorously conserves energy including efficiencies."""
    em = loaded_system["energy_model"]
    dt = 1.0
    p_load = np.full(3, 500.0)

    # Discharge test: 100 kW for 1 h from 0.50 SOC
    sim = em.simulate_dispatch(np.zeros(3), np.zeros(3), np.array([100.0, 0, 0]), p_load, dt=dt, soc_initial=0.50)
    expected_soc_1 = 0.50 * (1.0 - em.self_discharge) - (100.0 * dt) / (em.e_bat_kwh * em.eta_dis)
    assert pytest.approx(sim["soc_trajectory"][1], abs=1e-5) == expected_soc_1

    # Charge test: -100 kW for 1 h from 0.50 SOC
    sim_ch = em.simulate_dispatch(np.zeros(3), np.zeros(3), np.array([-100.0, 0, 0]), p_load, dt=dt, soc_initial=0.50)
    expected_soc_ch = 0.50 * (1.0 - em.self_discharge) + (100.0 * dt * em.eta_ch) / em.e_bat_kwh
    assert pytest.approx(sim_ch["soc_trajectory"][1], abs=1e-5) == expected_soc_ch


def test_battery_charging_limits(loaded_system):
    """Enforce that charging power does not exceed max charging rate."""
    em = loaded_system["energy_model"]
    # Request extreme charge of -1500 kW (max is 600 kW)
    sim = em.simulate_dispatch(np.zeros(5), np.zeros(5), np.full(5, -1500.0), np.full(5, 500.0))
    assert np.all(sim["p_battery_charge"] <= em.p_ch_max + 1e-4)
    assert np.all(sim["p_battery"] >= -em.p_ch_max - 1e-4)


def test_battery_discharging_limits(loaded_system):
    """Enforce that discharging power does not exceed max discharge rate or dip below soc_min."""
    em = loaded_system["energy_model"]
    # Request extreme discharge of +1500 kW (max is 600 kW)
    sim = em.simulate_dispatch(np.zeros(5), np.zeros(5), np.full(5, 1500.0), np.full(5, 500.0))
    assert np.all(sim["p_battery_discharge"] <= em.p_dis_max + 1e-4)
    assert np.all(sim["p_battery"] <= em.p_dis_max + 1e-4)
    assert np.all(sim["soc_trajectory"] >= em.soc_min - 1e-4)


# ------------------------------------------------------------------------------
# 3. Generation, Grid, and Power Balance Tests
# ------------------------------------------------------------------------------
def test_solar_generation_limits(loaded_system):
    """Solar dispatch cannot be negative or exceed available resource."""
    c = loaded_system["constraints"]
    scen = loaded_system["scenario"]
    rep_solar, _, _ = c.repair_candidate(np.array([-10.0, 5000.0] + [0.0]*22), scen["wind_available_kw"], np.zeros(24), scen)
    assert np.all(rep_solar >= 0.0)
    assert np.all(rep_solar <= scen["solar_available_kw"])


def test_wind_generation_limits(loaded_system):
    """Wind dispatch cannot be negative or exceed available resource."""
    c = loaded_system["constraints"]
    scen = loaded_system["scenario"]
    _, rep_wind, _ = c.repair_candidate(scen["solar_available_kw"], np.array([-20.0, 8000.0] + [0.0]*22), np.zeros(24), scen)
    assert np.all(rep_wind >= 0.0)
    assert np.all(rep_wind <= scen["wind_available_kw"])


def test_grid_limits_and_power_balance(loaded_system):
    """
    Verify:
    1. Grid power is capped at p_grid_max.
    2. Any excess deficit is recorded as unserved load.
    3. Power balance identity: P_solar + P_wind + P_bat + P_grid + unserved - excess = P_load.
    """
    em = loaded_system["energy_model"]
    # Create extreme load that exceeds grid capacity (e.g. 5000 kW load when grid max is 2500 kW)
    extreme_load = np.full(5, 5000.0)
    sim = em.simulate_dispatch(np.zeros(5), np.zeros(5), np.zeros(5), extreme_load)
    
    assert np.all(sim["p_grid"] <= em.p_grid_max + 1e-4)
    assert np.all(sim["unserved_load"] > 2000.0)  # At least 5000 - 2500 = 2500 kW unserved
    
    # Check exact balance identity
    balance_identity = sim["p_solar"] + sim["p_wind"] + sim["p_battery"] + sim["p_grid"] + sim["unserved_load"] - sim["excess_generation"]
    np.testing.assert_allclose(balance_identity, extreme_load, atol=1e-4)


# ------------------------------------------------------------------------------
# 4. Standardized Metrics & Objective Function Tests
# ------------------------------------------------------------------------------
def test_renewable_utilization_metric(loaded_system):
    """Verify Metric A (utilization) = RE dispatched / RE available * 100."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]

    candidate = np.concatenate([
        scen["solar_available_kw"],
        scen["wind_available_kw"],
        np.zeros(T)
    ])
    res = obj.evaluate(candidate, scen, apply_repair=True)

    total_avail = np.sum(scen["solar_available_kw"] + scen["wind_available_kw"])
    total_dispatched = np.sum(res["p_solar"] + res["p_wind"])
    expected_util = (total_dispatched / total_avail) * 100.0
    assert pytest.approx(res["re_utilization_pct"], abs=1e-3) == expected_util


def test_curtailment_metric(loaded_system):
    """Verify Metric D (curtailment) = Unused RE / Available RE * 100."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]

    # Candidate with 50% curtailment
    candidate = np.concatenate([
        scen["solar_available_kw"] * 0.5,
        scen["wind_available_kw"] * 0.5,
        np.zeros(T)
    ])
    res = obj.evaluate(candidate, scen, apply_repair=False)
    # Utilization + Curtailment should equal 100%
    assert pytest.approx(res["re_utilization_pct"] + res["re_curtailment_pct"], abs=1e-2) == 100.0


def test_objective_function_components(loaded_system):
    """Verify that pure operating cost is separated from constraint penalties."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]

    candidate = np.concatenate([scen["solar_available_kw"], scen["wind_available_kw"], np.zeros(T)])
    res = obj.evaluate(candidate, scen, apply_repair=True)

    assert "operating_cost" in res
    assert "total_penalty" in res
    assert "fitness" in res
    assert pytest.approx(res["fitness"], abs=1e-4) == (res["operating_cost"] + res["total_penalty"])
    assert res["operating_cost"] > 0.0


# ------------------------------------------------------------------------------
# 5. Optimization Algorithms & Reproducibility Tests
# ------------------------------------------------------------------------------
def test_pso_optimization(loaded_system):
    """Verify PSO runs, reduces cost, and respects terminal SOC and constraints."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]
    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, 600.0)])
    ub = np.concatenate([scen["solar_available_kw"], scen["wind_available_kw"], np.full(T, 600.0)])

    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)
    pso = ParticleSwarmOptimizer(eval_func, lb, ub, pop_size=15, max_iter=20, seed=42)
    res = pso.optimize()

    assert res["best_fitness"] > 0.0
    assert res["convergence_curve"][-1] <= res["convergence_curve"][0]
    assert res["best_details"]["is_feasible"] is True
    assert res["best_details"]["terminal_soc_error"] <= 0.02


def test_gwo_optimization(loaded_system):
    """Verify GWO runs, reduces cost, and respects terminal SOC and constraints."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]
    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, 600.0)])
    ub = np.concatenate([scen["solar_available_kw"], scen["wind_available_kw"], np.full(T, 600.0)])

    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)
    gwo = GreyWolfOptimizer(eval_func, lb, ub, pop_size=15, max_iter=20, seed=42)
    res = gwo.optimize()

    assert res["best_fitness"] > 0.0
    assert res["convergence_curve"][-1] <= res["convergence_curve"][0]
    assert res["best_details"]["is_feasible"] is True
    assert res["best_details"]["terminal_soc_error"] <= 0.02


def test_hybrid_gwo_pso_optimization(loaded_system):
    """Verify Hybrid GWO-PSO runs, reduces cost, and respects terminal SOC."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]
    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, 600.0)])
    ub = np.concatenate([scen["solar_available_kw"], scen["wind_available_kw"], np.full(T, 600.0)])

    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)
    hybrid = HybridGWOPSO(eval_func, lb, ub, pop_size=15, max_iter=20, seed=42)
    res = hybrid.optimize()

    assert res["best_fitness"] > 0.0
    assert res["convergence_curve"][-1] <= res["convergence_curve"][0]
    assert res["best_details"]["is_feasible"] is True
    assert res["best_details"]["terminal_soc_error"] <= 0.02


def test_seed_reproducibility(loaded_system):
    """Verify identical seeds produce bitwise identical results."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]
    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, 600.0)])
    ub = np.concatenate([scen["solar_available_kw"], scen["wind_available_kw"], np.full(T, 600.0)])

    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)
    run1 = HybridGWOPSO(eval_func, lb, ub, pop_size=10, max_iter=10, seed=777).optimize()
    run2 = HybridGWOPSO(eval_func, lb, ub, pop_size=10, max_iter=10, seed=777).optimize()

    assert run1["best_fitness"] == run2["best_fitness"]
    np.testing.assert_allclose(run1["best_position"], run2["best_position"], atol=1e-10)


def test_results_exported():
    """Verify result persistence and metrics files exist."""
    assert os.path.exists("results/metrics/algorithm_comparison_summary.csv")
    assert os.path.exists("results/metrics/detailed_runs_metrics.csv")
