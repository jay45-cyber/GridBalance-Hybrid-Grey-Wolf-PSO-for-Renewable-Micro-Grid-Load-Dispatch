"""
src/evaluation.py
Calculates comprehensive statistical and operational metrics across
multiple experimental runs and algorithms for renewable microgrid dispatch.
"""

import os
import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ExperimentEvaluator:
    """
    Computes statistical and power engineering metrics across optimization runs.
    """

    def __init__(self, metrics_dir: str = "results/metrics"):
        self.metrics_dir = metrics_dir
        os.makedirs(self.metrics_dir, exist_ok=True)

    @staticmethod
    def compute_run_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes aggregate statistics across multiple independent runs of a single algorithm.
        """
        if not results:
            raise ValueError("Empty results list provided.")

        algorithm_name = results[0]["algorithm"]
        costs = np.array([r["best_fitness"] for r in results])
        times = np.array([r["execution_time"] for r in results])
        
        re_utils = np.array([r["best_details"].get("re_utilization_pct", 0.0) for r in results])
        grid_deps = np.array([r["best_details"].get("grid_dependency_pct", 0.0) for r in results])
        curtailments = np.array([r["best_details"].get("curtailment_kwh", 0.0) for r in results])
        grid_imports = np.array([r["best_details"].get("grid_import_kwh", 0.0) for r in results])
        
        # Battery throughput
        bat_throughputs = []
        for r in results:
            p_bat = r["best_details"].get("p_battery", np.array([]))
            bat_throughputs.append(float(np.sum(np.abs(p_bat))))
        bat_throughputs = np.array(bat_throughputs)

        feasibilities = np.array([1.0 if r["best_details"].get("is_feasible", False) else 0.0 for r in results])

        # Convergence speed: iteration index at which fitness is within 1% of final minimum
        conv_speeds = []
        for r in results:
            curve = r.get("convergence_curve", [])
            final_val = r["best_fitness"]
            threshold = final_val * 1.01  # within 1% of best
            reached_iter = len(curve) - 1
            for it_idx, val in enumerate(curve):
                if val <= threshold:
                    reached_iter = it_idx
                    break
            conv_speeds.append(reached_iter)
        conv_speeds = np.array(conv_speeds)

        summary = {
            "algorithm": algorithm_name,
            "runs_count": len(results),
            "best_cost_usd": float(np.min(costs)),
            "mean_cost_usd": float(np.mean(costs)),
            "median_cost_usd": float(np.median(costs)),
            "worst_cost_usd": float(np.max(costs)),
            "std_cost_usd": float(np.std(costs)),
            "mean_runtime_sec": float(np.mean(times)),
            "std_runtime_sec": float(np.std(times)),
            "mean_conv_iteration": float(np.mean(conv_speeds)),
            "re_utilization_pct": float(np.mean(re_utils)),
            "grid_dependency_pct": float(np.mean(grid_deps)),
            "mean_curtailment_kwh": float(np.mean(curtailments)),
            "mean_grid_import_kwh": float(np.mean(grid_imports)),
            "mean_battery_throughput_kwh": float(np.mean(bat_throughputs)),
            "feasibility_rate_pct": float(np.mean(feasibilities) * 100.0)
        }
        return summary

    def generate_comparison_table(
        self,
        multi_algo_results: Dict[str, List[Dict[str, Any]]],
        save_csv: bool = True
    ) -> pd.DataFrame:
        """
        Creates a clean benchmark comparison DataFrame across all algorithms.
        """
        rows = []
        for algo_name, runs in multi_algo_results.items():
            metrics = self.compute_run_metrics(runs)
            rows.append(metrics)

        df = pd.DataFrame(rows)
        # Sort by mean cost
        df = df.sort_values("mean_cost_usd").reset_index(drop=True)

        if save_csv:
            csv_path = os.path.join(self.metrics_dir, "algorithm_comparison_summary.csv")
            df.to_csv(csv_path, index=False)
            logger.info(f"Comparison table saved to {csv_path}")

        return df

    def export_per_run_data(
        self,
        multi_algo_results: Dict[str, List[Dict[str, Any]]]
    ) -> pd.DataFrame:
        """
        Exports detailed run-by-run metrics for statistical testing.
        """
        records = []
        for algo_name, runs in multi_algo_results.items():
            for run_idx, r in enumerate(runs):
                d = r["best_details"]
                p_bat = d.get("p_battery", np.zeros(1))
                records.append({
                    "algorithm": algo_name,
                    "seed": r.get("seed", run_idx),
                    "best_fitness": r["best_fitness"],
                    "operating_cost": d.get("operating_cost", r["best_fitness"]),
                    "execution_time_sec": r["execution_time"],
                    "is_feasible": d.get("is_feasible", True),
                    "re_utilization_pct": d.get("re_utilization_pct", 0.0),
                    "grid_dependency_pct": d.get("grid_dependency_pct", 0.0),
                    "curtailment_kwh": d.get("curtailment_kwh", 0.0),
                    "grid_import_kwh": d.get("grid_import_kwh", 0.0),
                    "battery_throughput_kwh": float(np.sum(np.abs(p_bat)))
                })

        df_runs = pd.DataFrame(records)
        runs_path = os.path.join(self.metrics_dir, "detailed_runs_metrics.csv")
        df_runs.to_csv(runs_path, index=False)
        logger.info(f"Detailed runs metrics saved to {runs_path}")
        return df_runs
