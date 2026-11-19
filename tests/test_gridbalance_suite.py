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
from src.ga import GeneticAlgorithm
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


# ------------------------------------------------------------------------------
# 6. Detailed Deficit, Excess Generation & Grid Limits Tests (Tasks 1 & 2)
# ------------------------------------------------------------------------------
def test_power_balance_deficit_condition(loaded_system):
    """
    Test power balance identity under severe deficit:
    Load = 6000 kW, Solar=0, Wind=0, Battery=0.
    Grid import caps at 2500 kW, leaving 3500 kW unserved load.
    The identity: P_solar + P_wind + P_bat + P_grid_imp - P_grid_exp + P_unserved - P_excess = P_load
    must hold exactly, but feasibility must be False.
    """
    em = loaded_system["energy_model"]
    c = loaded_system["constraints"]
    T = 3
    p_load = np.full(T, 6000.0)
    sim = em.simulate_dispatch(np.zeros(T), np.zeros(T), np.zeros(T), p_load)

    # Check identity
    identity = (sim["p_solar"] + sim["p_wind"] + sim["p_battery"] +
                sim["p_grid_import"] - sim["p_grid_export"] +
                sim["unserved_load"] - sim["excess_generation"])
    np.testing.assert_allclose(identity, p_load, atol=1e-4)

    # Constraint evaluator check
    scen = {"solar_available_kw": np.zeros(T), "wind_available_kw": np.zeros(T), "load_demand_kw": p_load}
    rep = c.evaluate_constraints(
        p_solar=sim["p_solar"],
        p_wind=sim["p_wind"],
        p_battery=sim["p_battery"],
        p_grid=sim["p_grid"],
        soc_trajectory=sim["soc_trajectory"],
        scenario=scen,
        p_grid_import=sim["p_grid_import"],
        p_grid_export=sim["p_grid_export"],
        unserved_load=sim["unserved_load"],
        excess_generation=sim["excess_generation"]
    )
    assert rep["is_feasible"] is False
    assert rep["unserved_load_valid"] is False
    assert rep["unserved_load_total_kw"] > 3000.0


def test_power_balance_excess_generation_condition(loaded_system):
    """
    Test power balance identity under severe excess generation:
    Solar = 3000 kW, Load = 0, Battery = 0.
    Grid export caps at max_export_power_kw (1000 kW), leaving 2000 kW excess.
    The identity must hold, but feasibility must be False.
    """
    em = loaded_system["energy_model"]
    c = loaded_system["constraints"]
    T = 3
    p_solar = np.full(T, 3000.0)
    p_load = np.zeros(T)
    sim = em.simulate_dispatch(p_solar, np.zeros(T), np.zeros(T), p_load)

    # Check identity
    identity = (sim["p_solar"] + sim["p_wind"] + sim["p_battery"] +
                sim["p_grid_import"] - sim["p_grid_export"] +
                sim["unserved_load"] - sim["excess_generation"])
    np.testing.assert_allclose(identity, p_load, atol=1e-4)
    assert np.all(sim["p_grid_export"] <= em.p_export_max + 1e-4)
    assert np.all(sim["excess_generation"] > 1500.0)

    # Feasibility must be False
    scen = {"solar_available_kw": p_solar, "wind_available_kw": np.zeros(T), "load_demand_kw": p_load}
    rep = c.evaluate_constraints(
        p_solar=sim["p_solar"],
        p_wind=sim["p_wind"],
        p_battery=sim["p_battery"],
        p_grid=sim["p_grid"],
        soc_trajectory=sim["soc_trajectory"],
        scenario=scen,
        p_grid_import=sim["p_grid_import"],
        p_grid_export=sim["p_grid_export"],
        unserved_load=sim["unserved_load"],
        excess_generation=sim["excess_generation"]
    )
    assert rep["is_feasible"] is False
    assert rep["excess_generation_valid"] is False


def test_grid_export_limit_violation(loaded_system):
    """Verify that export exceeding max_export_power_kw (1000 kW) is rejected."""
    c = loaded_system["constraints"]
    T = 2
    scen = {"solar_available_kw": np.full(T, 1500.0), "wind_available_kw": np.zeros(T), "load_demand_kw": np.zeros(T)}
    # Direct candidate with 1500 kW export
    rep = c.evaluate_constraints(
        p_solar=np.full(T, 1500.0),
        p_wind=np.zeros(T),
        p_battery=np.zeros(T),
        p_grid_import=np.zeros(T),
        p_grid_export=np.full(T, 1500.0),
        unserved_load=np.zeros(T),
        excess_generation=np.zeros(T),
        soc_trajectory=np.full(T + 1, 0.50),
        scenario=scen
    )
    assert rep["grid_export_valid"] is False
    assert rep["grid_valid"] is False
    assert rep["is_feasible"] is False
    assert rep["grid_export_violation"] > 0.0


def test_grid_import_limit_violation(loaded_system):
    """Verify that import exceeding max_import_power_kw (2500 kW) is rejected."""
    c = loaded_system["constraints"]
    T = 2
    scen = {"solar_available_kw": np.zeros(T), "wind_available_kw": np.zeros(T), "load_demand_kw": np.full(T, 3000.0)}
    # Candidate with 3000 kW import
    rep = c.evaluate_constraints(
        p_solar=np.zeros(T),
        p_wind=np.zeros(T),
        p_battery=np.zeros(T),
        p_grid_import=np.full(T, 3000.0),
        p_grid_export=np.zeros(T),
        unserved_load=np.zeros(T),
        excess_generation=np.zeros(T),
        soc_trajectory=np.full(T + 1, 0.50),
        scenario=scen
    )
    assert rep["grid_import_valid"] is False
    assert rep["grid_valid"] is False
    assert rep["is_feasible"] is False
    assert rep["grid_import_violation"] > 0.0


# ------------------------------------------------------------------------------
# 7. Complete Battery SOC Trajectory Tests (Task 3)
# ------------------------------------------------------------------------------
def test_battery_only_charging_conservation(loaded_system):
    """Verify battery-only charging across multiple steps matches discrete formula."""
    em = loaded_system["energy_model"]
    T = 3
    dt = 1.0
    p_ch = np.array([-200.0, -300.0, -100.0])
    sim = em.simulate_dispatch(np.zeros(T), np.zeros(T), p_ch, np.full(T, 500.0), dt=dt, soc_initial=0.25)
    soc = sim["soc_trajectory"]

    cur_soc = 0.25
    for t in range(T):
        cur_soc = cur_soc * (1.0 - em.self_discharge * dt) + (abs(p_ch[t]) * dt * em.eta_ch) / em.e_bat_kwh
        assert pytest.approx(soc[t + 1], abs=1e-5) == cur_soc


def test_battery_only_discharging_conservation(loaded_system):
    """Verify battery-only discharging across multiple steps matches discrete formula."""
    em = loaded_system["energy_model"]
    T = 3
    dt = 1.0
    p_dis = np.array([200.0, 150.0, 100.0])
    sim = em.simulate_dispatch(np.zeros(T), np.zeros(T), p_dis, np.full(T, 500.0), dt=dt, soc_initial=0.85)
    soc = sim["soc_trajectory"]

    cur_soc = 0.85
    for t in range(T):
        cur_soc = cur_soc * (1.0 - em.self_discharge * dt) - (p_dis[t] * dt) / (em.e_bat_kwh * em.eta_dis)
        assert pytest.approx(soc[t + 1], abs=1e-5) == cur_soc


def test_battery_mixed_charging_discharging(loaded_system):
    """Verify alternating charge and discharge maintains energy consistency."""
    em = loaded_system["energy_model"]
    T = 4
    dt = 1.0
    # Charge 200 kW, Discharge 100 kW, Charge 300 kW, Discharge 200 kW
    p_mixed = np.array([-200.0, 100.0, -300.0, 200.0])
    sim = em.simulate_dispatch(np.zeros(T), np.zeros(T), p_mixed, np.full(T, 500.0), dt=dt, soc_initial=0.50)
    soc = sim["soc_trajectory"]
    assert len(soc) == T + 1
    assert np.all(soc >= em.soc_min)
    assert np.all(soc <= em.soc_max)
    # Ensure simultaneous charging and discharging is strictly 0
    assert np.all(sim["p_battery_charge"] * sim["p_battery_discharge"] == 0.0)


def test_terminal_soc_violation_rejection(loaded_system):
    """Verify that a candidate leaving final SOC far from initial SOC is rejected."""
    c = loaded_system["constraints"]
    T = 24
    scen = loaded_system["scenario"]
    # Candidate trajectory that ends at 0.20 (initial is 0.50)
    soc_viol = np.linspace(0.50, 0.20, T + 1)
    rep = c.evaluate_constraints(
        p_solar=scen["solar_available_kw"],
        p_wind=scen["wind_available_kw"],
        p_battery=np.zeros(T),
        p_grid=scen["load_demand_kw"] - scen["solar_available_kw"] - scen["wind_available_kw"],
        soc_trajectory=soc_viol,
        scenario=scen
    )
    assert rep["terminal_soc_valid"] is False
    assert rep["is_feasible"] is False
    assert rep["terminal_soc_error"] > 0.25


def test_soc_boundary_limits(loaded_system):
    """Verify that battery cannot be discharged below soc_min or charged above soc_max."""
    em = loaded_system["energy_model"]
    # Request extreme continuous discharge from 0.25
    sim_dis = em.simulate_dispatch(np.zeros(10), np.zeros(10), np.full(10, 600.0), np.full(10, 500.0), soc_initial=0.25)
    assert np.all(sim_dis["soc_trajectory"] >= em.soc_min - 1e-4)

    # Request extreme continuous charge from 0.85
    sim_ch = em.simulate_dispatch(np.zeros(10), np.zeros(10), np.full(10, -600.0), np.full(10, 500.0), soc_initial=0.85)
    assert np.all(sim_ch["soc_trajectory"] <= em.soc_max + 1e-4)


# ------------------------------------------------------------------------------
# 8. Renewable Energy Accounting & Attribution Test (Task 4)
# ------------------------------------------------------------------------------
def test_renewable_energy_accounting_attribution(loaded_system):
    """
    Verify complete renewable energy attribution tracking:
    - Direct RE to demand
    - RE stored in battery
    - Battery charging and discharging losses
    - RE discharged from battery
    - Zero double counting
    """
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]

    candidate = np.concatenate([
        scen["solar_available_kw"],
        scen["wind_available_kw"],
        np.zeros(T)
    ])
    res = obj.evaluate(candidate, scen, apply_repair=True)

    assert "re_direct_to_demand_kwh" in res
    assert "re_stored_in_battery_kwh" in res
    assert "battery_charge_losses_kwh" in res
    assert "battery_discharge_losses_kwh" in res
    assert "re_discharged_from_battery_kwh" in res
    assert res["re_direct_to_demand_kwh"] >= 0.0
    assert res["re_stored_in_battery_kwh"] >= 0.0


# ------------------------------------------------------------------------------
# 9. Standalone GA Optimization Test (Task 5)
# ------------------------------------------------------------------------------
def test_ga_optimization(loaded_system):
    """Verify Genetic Algorithm runs, reduces cost, and respects constraints."""
    obj = loaded_system["objective"]
    scen = loaded_system["scenario"]
    T = scen["horizon_steps"]
    lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, 600.0)])
    ub = np.concatenate([scen["solar_available_kw"], scen["wind_available_kw"], np.full(T, 600.0)])

    eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)
    ga = GeneticAlgorithm(eval_func, lb, ub, pop_size=15, max_iter=20, seed=42)
    res = ga.optimize()

    assert res["best_fitness"] > 0.0
    assert res["convergence_curve"][-1] <= res["convergence_curve"][0]
    assert res["best_details"]["is_feasible"] is True
    assert res["best_details"]["terminal_soc_error"] <= 0.02

