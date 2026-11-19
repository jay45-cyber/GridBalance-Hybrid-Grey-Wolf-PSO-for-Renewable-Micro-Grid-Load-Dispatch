"""
main.py
Main Command Line Interface for GridBalance:
Hybrid Grey Wolf–PSO for Renewable Micro-Grid Load Dispatch
"""

import os
import sys
import argparse
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_audit():
    logger.info("Executing DDRE-33 Dataset Quality Audit...")
    from src.data_preprocessing import DDRE33Preprocessor
    pre = DDRE33Preprocessor()
    audit = pre.audit_raw_data()
    print("Audit completed successfully. See results/reports/data_quality_report.json")


def run_preprocess(day_index: int = 15):
    logger.info("Executing Data Preprocessing and Scenario Extraction...")
    from src.data_preprocessing import DDRE33Preprocessor
    from src.data_loader import DataLoader
    loader = DataLoader()
    pre = DDRE33Preprocessor()
    pre.process_and_align()
    pre.extract_scenario_sample(
        day_index=day_index,
        solar_capacity_kw=loader.config["solar_pv"]["rated_capacity_kw"],
        wind_capacity_kw=loader.config["wind_turbine"]["rated_capacity_kw"],
        peak_demand_kw=loader.config["load"]["peak_demand_kw"],
        hourly_load_multipliers=loader.config["load"]["hourly_load_multipliers"]
    )
    print("Data preprocessing and sampling complete.")


def run_optimization(algo: str, day_index: int = 15, seed: int = 42, pop_size: int = 30, max_iter: int = 100):
    if algo == "pso":
        from experiments.run_pso import run
        run(day_index=day_index, seed=seed, pop_size=pop_size, max_iter=max_iter)
    elif algo == "gwo":
        from experiments.run_gwo import run
        run(day_index=day_index, seed=seed, pop_size=pop_size, max_iter=max_iter)
    elif algo == "hybrid":
        from experiments.run_hybrid import run
        run(day_index=day_index, seed=seed, pop_size=pop_size, max_iter=max_iter)
    elif algo == "ga":
        from experiments.run_ga import run
        run(day_index=day_index, seed=seed, pop_size=pop_size, max_iter=max_iter)
    else:
        raise ValueError(f"Unknown algorithm: {algo}")


def run_benchmark(day_index: int = 15, pop_size: int = 30, max_iter: int = 100):
    from experiments.compare_algorithms import run_benchmark
    run_benchmark(day_index=day_index, pop_size=pop_size, max_iter=max_iter)


def run_tests():
    logger.info("Running automated test suite with pytest...")
    ret = subprocess.run([sys.executable, "-m", "pytest", "tests/test_gridbalance_suite.py", "-v"])
    return ret.returncode


def run_dashboard():
    logger.info("Starting GridBalance Streamlit Dashboard...")
    subprocess.run(["streamlit", "run", "dashboard/app.py"])


def main():
    parser = argparse.ArgumentParser(
        description="GridBalance — Hybrid Grey Wolf–PSO for Renewable Micro-Grid Load Dispatch"
    )
    parser.add_argument(
        "--mode",
        choices=["all", "audit", "preprocess", "pso", "gwo", "hybrid", "ga", "benchmark", "test", "dashboard"],
        default="all",
        help="Execution mode (default: all)"
    )
    parser.add_argument("--day-index", type=int, default=15, help="DDRE-33 Scenario Day Index (0-364)")
    parser.add_argument("--pop-size", type=int, default=30, help="Optimization Population Size")
    parser.add_argument("--max-iter", type=int, default=100, help="Maximum Optimization Iterations")
    parser.add_argument("--seed", type=int, default=42, help="Random Seed for Reproducibility")

    args = parser.parse_args()

    if args.mode == "audit":
        run_audit()
    elif args.mode == "preprocess":
        run_preprocess(day_index=args.day_index)
    elif args.mode in ["pso", "gwo", "hybrid", "ga"]:
        run_optimization(args.mode, day_index=args.day_index, seed=args.seed, pop_size=args.pop_size, max_iter=args.max_iter)
    elif args.mode == "benchmark":
        run_benchmark(day_index=args.day_index, pop_size=args.pop_size, max_iter=args.max_iter)
    elif args.mode == "test":
        run_tests()
    elif args.mode == "dashboard":
        run_dashboard()
    elif args.mode == "all":
        print("================================================================================")
        print("GRIDBALANCE: EXECUTING FULL END-TO-END PIPELINE")
        print("================================================================================")
        run_audit()
        run_preprocess(day_index=args.day_index)
        run_benchmark(day_index=args.day_index, pop_size=args.pop_size, max_iter=args.max_iter)
        run_tests()
        print("\nFull end-to-end pipeline completed successfully.")


if __name__ == "__main__":
    main()
