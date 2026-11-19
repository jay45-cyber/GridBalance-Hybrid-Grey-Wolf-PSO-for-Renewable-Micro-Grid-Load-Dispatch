"""
src/visualization.py
Generates publication-quality figures and plots for GridBalance:
- Renewable generation profiles (Solar & Wind)
- Load demand vs generation
- Multi-source energy dispatch distribution (stacked area)
- Battery SOC trajectory
- Algorithm convergence curves (individual & combined)
- Cost and performance boxplots
"""

import os
import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Apply publication style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "lines.linewidth": 2.0,
    "figure.dpi": 300
})


class MicrogridVisualizer:
    """
    Renders and saves all required research-grade visual plots for GridBalance.
    """

    def __init__(self, output_dir: str = "results/graphs"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def plot_solar_profile(self, scenario: Dict[str, Any], save_name: str = "01_solar_generation_profile.png"):
        """Plot 1: Solar generation profile across the 24-hour horizon."""
        fig, ax = plt.subplots(figsize=(9, 4.5))
        hours = np.arange(scenario["horizon_steps"])
        solar_kw = scenario["solar_available_kw"]

        ax.plot(hours, solar_kw, color="#F39C12", marker="o", label="Bus 33 Solar PV Available")
        ax.fill_between(hours, solar_kw, color="#F39C12", alpha=0.25)
        ax.set_title("Solar PV Generation Profile (DDRE-33 Bus 33)")
        ax.set_xlabel("Time Horizon (Hours)")
        ax.set_ylabel("Solar Power (kW)")
        ax.set_xticks(hours[::2])
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(loc="upper right")
        plt.tight_layout()

        path = os.path.join(self.output_dir, save_name)
        fig.savefig(path, dpi=300)
        plt.close(fig)
        logger.info(f"Saved {path}")
        return path

    def plot_wind_profile(self, scenario: Dict[str, Any], save_name: str = "02_wind_generation_profile.png"):
        """Plot 2: Wind generation profile across the 24-hour horizon."""
        fig, ax = plt.subplots(figsize=(9, 4.5))
        hours = np.arange(scenario["horizon_steps"])
        wind_kw = scenario["wind_available_kw"]

        ax.plot(hours, wind_kw, color="#2980B9", marker="s", label="Bus 22 Wind Turbine Available")
        ax.fill_between(hours, wind_kw, color="#2980B9", alpha=0.25)
        ax.set_title("Wind Turbine Generation Profile (DDRE-33 Bus 22)")
        ax.set_xlabel("Time Horizon (Hours)")
        ax.set_ylabel("Wind Power (kW)")
        ax.set_xticks(hours[::2])
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(loc="upper right")
        plt.tight_layout()

        path = os.path.join(self.output_dir, save_name)
        fig.savefig(path, dpi=300)
        plt.close(fig)
        logger.info(f"Saved {path}")
        return path

    def plot_load_demand(self, scenario: Dict[str, Any], save_name: str = "03_load_demand_profile.png"):
        """Plot 3: Microgrid load demand profile vs total renewable generation."""
        fig, ax = plt.subplots(figsize=(9, 4.5))
        hours = np.arange(scenario["horizon_steps"])
        load_kw = scenario["load_demand_kw"]
        total_re_kw = scenario["solar_available_kw"] + scenario["wind_available_kw"]

        ax.plot(hours, load_kw, color="#C0392B", marker="d", label="Microgrid Load Demand")
        ax.plot(hours, total_re_kw, color="#27AE60", linestyle="--", marker="^", label="Total Renewable Available (Solar + Wind)")
        ax.fill_between(hours, total_re_kw, color="#27AE60", alpha=0.15)
        ax.set_title("Microgrid Load Demand vs Total Available Renewable Power")
        ax.set_xlabel("Time Horizon (Hours)")
        ax.set_ylabel("Power (kW)")
        ax.set_xticks(hours[::2])
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(loc="upper right")
        plt.tight_layout()

        path = os.path.join(self.output_dir, save_name)
        fig.savefig(path, dpi=300)
        plt.close(fig)
        logger.info(f"Saved {path}")
        return path

    def plot_energy_dispatch_distribution(
        self,
        dispatch_result: Dict[str, Any],
        scenario: Dict[str, Any],
        algorithm_name: str = "Hybrid GWO-PSO",
        save_name: str = "04_energy_dispatch_distribution.png"
    ):
        """Plot 4: Stacked area energy dispatch distribution vs load demand."""
        fig, ax = plt.subplots(figsize=(10, 5.5))
        hours = np.arange(scenario["horizon_steps"])
        d = dispatch_result["best_details"]

        p_solar = d["p_solar"]
        p_wind = d["p_wind"]
        p_bat = d["p_battery"]
        p_grid = d["p_grid"]
        load = scenario["load_demand_kw"]

        # Decompose battery into discharge (generation) and charge (load)
        p_bat_dis = np.maximum(0.0, p_bat)
        p_bat_ch = np.maximum(0.0, -p_bat)
        p_grid_import = np.maximum(0.0, p_grid)

        # Stacked generation components
        y_solar = p_solar
        y_wind = y_solar + p_wind
        y_bat = y_wind + p_bat_dis
        y_grid = y_bat + p_grid_import

        ax.fill_between(hours, 0, y_solar, color="#F39C12", alpha=0.8, label="Solar PV Dispatch")
        ax.fill_between(hours, y_solar, y_wind, color="#2980B9", alpha=0.8, label="Wind Turbine Dispatch")
        ax.fill_between(hours, y_wind, y_bat, color="#8E44AD", alpha=0.8, label="Battery Discharge")
        ax.fill_between(hours, y_bat, y_grid, color="#E67E22", alpha=0.8, label="Main Grid Import")

        # Demand line
        ax.plot(hours, load, color="#C0392B", linewidth=2.5, linestyle="-", label="Microgrid Demand")
        # Battery charging line
        if np.any(p_bat_ch > 0):
            ax.plot(hours, load + p_bat_ch, color="#2C3E50", linewidth=1.5, linestyle=":", label="Demand + Battery Charging")

        ax.set_title(f"Optimal 24-Hour Energy Dispatch Schedule ({algorithm_name})")
        ax.set_xlabel("Hour of Day")
        ax.set_ylabel("Power (kW)")
        ax.set_xticks(hours[::2])
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(loc="upper right", framealpha=0.9)
        plt.tight_layout()

        path = os.path.join(self.output_dir, save_name)
        fig.savefig(path, dpi=300)
        plt.close(fig)
        logger.info(f"Saved {path}")
        return path

    def plot_battery_soc(
        self,
        dispatch_result: Dict[str, Any],
        config: Dict[str, Any],
        algorithm_name: str = "Hybrid GWO-PSO",
        save_name: str = "10_battery_soc_profile.png"
    ):
        """Plot 10: Battery State of Charge (SOC) profile across the dispatch horizon."""
        fig, ax = plt.subplots(figsize=(9, 4.5))
        d = dispatch_result["best_details"]
        soc = d["soc_trajectory"] * 100.0  # Percentage
        time_steps = np.arange(len(soc))

        soc_min = config["battery"]["soc_min"] * 100.0
        soc_max = config["battery"]["soc_max"] * 100.0

        ax.plot(time_steps, soc, color="#16A085", marker="o", linewidth=2.2, label=f"Battery SOC ({algorithm_name})")
        ax.axhline(soc_max, color="#E74C3C", linestyle="--", label=f"SOC Max ({soc_max:.0f}%)")
        ax.axhline(soc_min, color="#E67E22", linestyle="--", label=f"SOC Min ({soc_min:.0f}%)")
        ax.fill_between(time_steps, soc_min, soc_max, color="#2ECC71", alpha=0.1, label="Allowable Operating Region")

        ax.set_title(f"BESS State-of-Charge (SOC) Dynamics ({algorithm_name})")
        ax.set_xlabel("Dispatch Step (Hour)")
        ax.set_ylabel("State of Charge (%)")
        ax.set_ylim([0, 100])
        ax.set_xticks(time_steps[::2])
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(loc="lower right")
        plt.tight_layout()

        path = os.path.join(self.output_dir, save_name)
        fig.savefig(path, dpi=300)
        plt.close(fig)
        logger.info(f"Saved {path}")
        return path

    def plot_single_convergence(
        self,
        curve: List[float],
        algorithm_name: str,
        color: str = "#2980B9",
        save_name: str = "convergence_curve.png"
    ):
        """Plots convergence history for a single algorithm."""
        fig, ax = plt.subplots(figsize=(8, 4.5))
        iters = np.arange(len(curve))

        ax.plot(iters, curve, color=color, linewidth=2.2, label=f"{algorithm_name} Best Fitness")
        ax.set_title(f"Convergence Progression: {algorithm_name}")
        ax.set_xlabel("Iteration")
        ax.set_ylabel("Total Operating Cost ($)")
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(loc="upper right")
        plt.tight_layout()

        path = os.path.join(self.output_dir, save_name)
        fig.savefig(path, dpi=300)
        plt.close(fig)
        logger.info(f"Saved {path}")
        return path

    def plot_multi_convergence(
        self,
        algo_curves: Dict[str, List[float]],
        save_name: str = "07_multi_algorithm_convergence.png"
    ):
        """Plot 5, 6, 7: Combined convergence curve comparing all algorithms."""
        fig, ax = plt.subplots(figsize=(9, 5))
        colors = {
            "Hybrid GWO-PSO": "#E74C3C",
            "PSO": "#2980B9",
            "GWO": "#27AE60",
            "GA": "#8E44AD"
        }

        for algo_name, curve in algo_curves.items():
            color = colors.get(algo_name, "#34495E")
            linestyle = "-" if "Hybrid" in algo_name else "--"
            linewidth = 2.5 if "Hybrid" in algo_name else 1.8
            ax.plot(curve, label=algo_name, color=color, linestyle=linestyle, linewidth=linewidth)

        ax.set_title("Comparative Convergence Analysis: Cost Minimization")
        ax.set_xlabel("Iteration Count")
        ax.set_ylabel("Best Operating Cost ($)")
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(loc="upper right", framealpha=0.95)
        plt.tight_layout()

        path = os.path.join(self.output_dir, save_name)
        fig.savefig(path, dpi=300)
        plt.close(fig)
        logger.info(f"Saved {path}")
        return path

    def plot_cost_comparison(
        self,
        multi_algo_results: Dict[str, List[Dict[str, Any]]],
        save_name: str = "08_algorithm_cost_comparison.png"
    ):
        """Plot 8: Boxplot comparison of pure operating costs across runs."""
        fig, ax = plt.subplots(figsize=(9, 5))
        data = []
        labels = []
        colors = ["#2980B9", "#27AE60", "#E74C3C", "#8E44AD"]

        for algo_name, runs in multi_algo_results.items():
            labels.append(algo_name)
            data.append([r["best_details"].get("operating_cost", r["best_fitness"]) for r in runs])

        bplot = ax.boxplot(data, tick_labels=labels, patch_artist=True, medianprops=dict(color="black", linewidth=1.5))
        for patch, color in zip(bplot["boxes"], colors[:len(labels)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax.set_title("Operating Cost Distribution Across 10 Independent Seeds (Pure Cost)")
        ax.set_ylabel("Total Operating Cost ($)")
        ax.grid(True, linestyle="--", alpha=0.6, axis="y")
        plt.tight_layout()

        path = os.path.join(self.output_dir, save_name)
        fig.savefig(path, dpi=300)
        plt.close(fig)
        logger.info(f"Saved {path}")
        return path

    def plot_renewable_utilization_comparison(
        self,
        summary_df: pd.DataFrame,
        save_name: str = "09_renewable_energy_utilization_comparison.png"
    ):
        """Plot 9: Standardized 4-metric renewable & grid comparison bar chart."""
        fig, ax = plt.subplots(figsize=(10, 5))
        algos = summary_df["algorithm"].tolist()
        re_util = summary_df["re_utilization_pct"].tolist()
        re_share = summary_df.get("re_share_pct", summary_df["re_utilization_pct"]).tolist()
        grid_deps = summary_df["grid_dependency_pct"].tolist()
        curt_vals = summary_df.get("re_curtailment_pct", pd.Series(np.zeros(len(algos)))).tolist()

        x = np.arange(len(algos))
        width = 0.20

        r1 = ax.bar(x - 1.5*width, re_util, width, label="A. RE Utilization (%)", color="#27AE60", alpha=0.85)
        r2 = ax.bar(x - 0.5*width, re_share, width, label="B. RE Share of Demand (%)", color="#2ECC71", alpha=0.85)
        r3 = ax.bar(x + 0.5*width, grid_deps, width, label="C. Grid Dependency (%)", color="#E67E22", alpha=0.85)
        r4 = ax.bar(x + 1.5*width, curt_vals, width, label="D. Curtailment (%)", color="#E74C3C", alpha=0.85)

        ax.set_title("Standardized Renewable & Grid Integration Metrics Comparison")
        ax.set_ylabel("Percentage (%)")
        ax.set_xticks(x)
        ax.set_xticklabels(algos)
        ax.set_ylim([0, 105])
        ax.grid(True, linestyle="--", alpha=0.6, axis="y")
        ax.legend(loc="upper right", framealpha=0.95)

        for rect in r1:
            h = rect.get_height()
            ax.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width()/2, h),
                        xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=8)
        for rect in r2:
            h = rect.get_height()
            ax.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width()/2, h),
                        xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=8)
        for rect in r3:
            h = rect.get_height()
            ax.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width()/2, h),
                        xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=8)

        plt.tight_layout()
        path = os.path.join(self.output_dir, save_name)
        fig.savefig(path, dpi=300)
        plt.close(fig)
        logger.info(f"Saved {path}")
        return path
