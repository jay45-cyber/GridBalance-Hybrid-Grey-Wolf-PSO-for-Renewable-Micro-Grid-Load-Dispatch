"""
src/data_loader.py
Loads system configuration and renewable microgrid scenarios.
Provides clean structured access to dispatch inputs.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DataLoader:
    """
    Manages loading of YAML configurations, DDRE-33 time-series,
    and dispatch scenario vectors.
    """

    def __init__(self, config_path: str = "config/system_parameters.yaml"):
        self.config_path = config_path
        self.config = self.load_config(config_path)

    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """Loads and validates the system YAML configuration."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config

    def get_dispatch_scenario(
        self,
        day_index: Optional[int] = None,
        use_hourly: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieves the complete input scenario vectors for optimization.
        Returns a dictionary with arrays for solar, wind, load, tariffs, and timestamps.
        """
        if day_index is None:
            day_index = self.config["dataset"].get("default_scenario_day", 15)

        solar_cap = self.config["solar_pv"]["rated_capacity_kw"]
        wind_cap = self.config["wind_turbine"]["rated_capacity_kw"]
        peak_load = self.config["load"]["peak_demand_kw"]
        hourly_multipliers = self.config["load"]["hourly_load_multipliers"]

        # Check if preprocessed sample already exists
        sample_path = os.path.join(
            self.config["dataset"]["samples_dir"],
            f"sample_dispatch_day_{day_index}.csv" if use_hourly else f"sample_dispatch_day_{day_index}_15min.csv"
        )

        if not os.path.exists(sample_path):
            from src.data_preprocessing import DDRE33Preprocessor
            pre = DDRE33Preprocessor(
                solar_path=os.path.join(self.config["dataset"]["raw_dir"], self.config["dataset"]["solar_raw_file"]),
                wind_path=os.path.join(self.config["dataset"]["raw_dir"], self.config["dataset"]["wind_raw_file"]),
                processed_dir=self.config["dataset"]["processed_dir"],
                samples_dir=self.config["dataset"]["samples_dir"],
            )
            pre.audit_raw_data()
            pre.process_and_align()
            pre.extract_scenario_sample(
                day_index=day_index,
                solar_capacity_kw=solar_cap,
                wind_capacity_kw=wind_cap,
                peak_demand_kw=peak_load,
                hourly_load_multipliers=hourly_multipliers
            )

        df = pd.read_csv(sample_path)

        # Build tariff array
        base_tariffs = self.config["grid"]["tou_tariff"]["hourly_import_rates"]
        if use_hourly:
            tariffs = np.array(base_tariffs, dtype=np.float64)
            dt = 1.0
        else:
            # 15-minute resolution: 4 repeat entries per hour
            tariffs = np.repeat(np.array(base_tariffs, dtype=np.float64), 4)
            dt = 0.25

        scenario = {
            "day_index": day_index,
            "horizon_steps": len(df),
            "dt_hours": dt,
            "timestamps": df["timestamp"].values,
            "solar_available_kw": df["solar_available_kw"].values.astype(np.float64),
            "wind_available_kw": df["wind_available_kw"].values.astype(np.float64),
            "load_demand_kw": df["load_demand_kw"].values.astype(np.float64),
            "grid_tariff_per_kwh": tariffs,
            "dataframe": df
        }
        return scenario


if __name__ == "__main__":
    loader = DataLoader()
    scen = loader.get_dispatch_scenario(day_index=15)
    print("Scenario loaded successfully.")
    print("Steps:", scen["horizon_steps"])
    print("Solar peak available (kW):", scen["solar_available_kw"].max())
    print("Wind peak available (kW):", scen["wind_available_kw"].max())
    print("Load peak demand (kW):", scen["load_demand_kw"].max())
