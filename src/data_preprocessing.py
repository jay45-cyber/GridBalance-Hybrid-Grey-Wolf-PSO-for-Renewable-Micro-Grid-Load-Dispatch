"""
src/data_preprocessing.py
Preprocesses authentic DDRE-33 renewable energy time-series and generates
clean, validated datasets for microgrid dispatch optimization.
"""

import os
import json
import logging
from typing import Dict, Tuple, Optional
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DDRE33Preprocessor:
    """
    Handles data quality checks, validation, aggregation, and scenario extraction
    for the DDRE-33 dataset (Bus 33 Solar PV and Bus 22 Wind).
    """

    def __init__(
        self,
        solar_path: str = "data/raw/node_33_solar_1.csv",
        wind_path: str = "data/raw/node_22_wind_1.csv",
        processed_dir: str = "data/processed",
        samples_dir: str = "data/samples",
        reports_dir: str = "results/reports",
    ):
        self.solar_path = solar_path
        self.wind_path = wind_path
        self.processed_dir = processed_dir
        self.samples_dir = samples_dir
        self.reports_dir = reports_dir

        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.samples_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

        self.audit_results: Dict = {}

    def audit_raw_data(self) -> Dict:
        """
        Conducts a rigorous data audit on raw DDRE-33 CSV files:
        checks missing values, duplicates, outliers, boundaries, and types.
        """
        logger.info("Starting audit of DDRE-33 raw data files...")
        audit = {
            "dataset_name": "DDRE-33 (Distributed Renewable Energy Scenarios)",
            "doi": "10.6084/m9.figshare.29374640",
            "files": {},
        }

        for name, path in [("solar_pv_bus33", self.solar_path), ("wind_bus22", self.wind_path)]:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Required raw data file not found: {path}")

            df = pd.read_csv(path)
            col_target = "OT" if "OT" in df.columns else df.columns[1]

            missing_count = int(df.isnull().sum().sum())
            duplicate_count = int(df.duplicated(subset=["timestamp"]).sum()) if "timestamp" in df.columns else 0
            
            # Numeric conversion check
            numeric_vals = pd.to_numeric(df[col_target], errors="coerce")
            invalid_numeric = int(numeric_vals.isnull().sum()) - int(df[col_target].isnull().sum())

            # Range checks for per-unit data [0.0, 1.0]
            val_min = float(numeric_vals.min())
            val_max = float(numeric_vals.max())
            val_mean = float(numeric_vals.mean())
            val_std = float(numeric_vals.std())
            negative_count = int((numeric_vals < 0).sum())
            greater_than_one = int((numeric_vals > 1.0001).sum())

            audit["files"][name] = {
                "file_path": path,
                "total_rows": int(len(df)),
                "columns": list(df.columns),
                "target_column": col_target,
                "missing_values": missing_count,
                "duplicate_timestamps": duplicate_count,
                "invalid_numeric_values": invalid_numeric,
                "min_value_pu": val_min,
                "max_value_pu": val_max,
                "mean_value_pu": round(val_mean, 6),
                "std_value_pu": round(val_std, 6),
                "negative_count": negative_count,
                "greater_than_one_count": greater_than_one,
                "status": "VALID" if (missing_count == 0 and negative_count == 0 and greater_than_one == 0) else "ISSUES_DETECTED"
            }

        self.audit_results = audit
        audit_path = os.path.join(self.reports_dir, "data_quality_report.json")
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit, f, indent=2)
        logger.info(f"Data audit completed and saved to {audit_path}")
        return audit

    def process_and_align(self) -> pd.DataFrame:
        """
        Loads, cleans, validates, and aligns Solar PV and Wind time series.
        Preserves original values without altering genuine zero measurements.
        """
        logger.info("Processing and aligning renewable energy time series...")
        df_solar = pd.read_csv(self.solar_path)
        df_wind = pd.read_csv(self.wind_path)

        # Standardize column names
        solar_val_col = "OT" if "OT" in df_solar.columns else df_solar.columns[1]
        wind_val_col = "OT" if "OT" in df_wind.columns else df_wind.columns[1]

        df_solar["timestamp"] = pd.to_datetime(df_solar["timestamp"])
        df_wind["timestamp"] = pd.to_datetime(df_wind["timestamp"])

        # Validate monotonic timestamps
        df_solar = df_solar.sort_values("timestamp").reset_index(drop=True)
        df_wind = df_wind.sort_values("timestamp").reset_index(drop=True)

        # Merge on timestamp
        merged = pd.merge(
            df_solar[["timestamp", solar_val_col]].rename(columns={solar_val_col: "solar_pu"}),
            df_wind[["timestamp", wind_val_col]].rename(columns={wind_val_col: "wind_pu"}),
            on="timestamp",
            how="inner"
        )

        # Clip minimal numerical precision artifacts strictly to [0.0, 1.0]
        merged["solar_pu"] = merged["solar_pu"].clip(lower=0.0, upper=1.0)
        merged["wind_pu"] = merged["wind_pu"].clip(lower=0.0, upper=1.0)

        # Save complete processed 15-minute dataset
        clean_path = os.path.join(self.processed_dir, "clean_renewable_timeseries_15min.csv")
        merged.to_csv(clean_path, index=False)
        logger.info(f"Saved 15-min cleaned dataset: {clean_path} (shape: {merged.shape})")

        # Create hourly aggregated dataset for standard 24-step dispatch
        merged_hourly = merged.set_index("timestamp").resample("1h").mean().reset_index()
        hourly_path = os.path.join(self.processed_dir, "clean_renewable_timeseries_hourly.csv")
        merged_hourly.to_csv(hourly_path, index=False)
        logger.info(f"Saved hourly aggregated dataset: {hourly_path} (shape: {merged_hourly.shape})")

        return merged

    def extract_scenario_sample(
        self,
        day_index: int = 15,
        solar_capacity_kw: float = 1200.0,
        wind_capacity_kw: float = 1000.0,
        peak_demand_kw: float = 1600.0,
        hourly_load_multipliers: Optional[list] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extracts a clean 24-hour daily scenario (both 15-min and hourly)
        with physically consistent kW units based on rated capacities.
        """
        if hourly_load_multipliers is None:
            hourly_load_multipliers = [
                0.48, 0.44, 0.42, 0.41, 0.43, 0.49, 0.62,
                0.75, 0.84, 0.89, 0.92, 0.94, 0.91, 0.88,
                0.93, 0.98, 1.00, 0.97, 0.94, 0.86,
                0.78, 0.70, 0.61, 0.52
            ]

        hourly_df = pd.read_csv(os.path.join(self.processed_dir, "clean_renewable_timeseries_hourly.csv"))
        hourly_df["timestamp"] = pd.to_datetime(hourly_df["timestamp"])

        # Slice 24 hours corresponding to day_index
        start_idx = day_index * 24
        end_idx = start_idx + 24
        if end_idx > len(hourly_df):
            start_idx = 0
            end_idx = 24

        sample_24h = hourly_df.iloc[start_idx:end_idx].copy().reset_index(drop=True)
        sample_24h["hour"] = range(24)
        sample_24h["solar_available_kw"] = sample_24h["solar_pu"] * solar_capacity_kw
        sample_24h["wind_available_kw"] = sample_24h["wind_pu"] * wind_capacity_kw
        
        # Load demand (kW)
        sample_24h["load_demand_kw"] = [m * peak_demand_kw for m in hourly_load_multipliers]

        sample_path = os.path.join(self.samples_dir, f"sample_dispatch_day_{day_index}.csv")
        sample_24h.to_csv(sample_path, index=False)
        # Default canonical sample
        canonical_path = os.path.join(self.samples_dir, "sample_dispatch_day.csv")
        sample_24h.to_csv(canonical_path, index=False)
        logger.info(f"Saved canonical 24-hour scenario to {canonical_path}")

        # Also extract 96-step 15-min sample
        df_15 = pd.read_csv(os.path.join(self.processed_dir, "clean_renewable_timeseries_15min.csv"))
        df_15["timestamp"] = pd.to_datetime(df_15["timestamp"])
        start_15 = day_index * 96
        end_15 = start_15 + 96
        sample_96 = df_15.iloc[start_15:end_15].copy().reset_index(drop=True)
        sample_96["step"] = range(96)
        sample_96["solar_available_kw"] = sample_96["solar_pu"] * solar_capacity_kw
        sample_96["wind_available_kw"] = sample_96["wind_pu"] * wind_capacity_kw
        # Interpolate load multipliers to 96 steps
        load_96 = np.interp(np.linspace(0, 23, 96), np.arange(24), hourly_load_multipliers) * peak_demand_kw
        sample_96["load_demand_kw"] = load_96

        sample_96_path = os.path.join(self.samples_dir, f"sample_dispatch_day_{day_index}_15min.csv")
        sample_96.to_csv(sample_96_path, index=False)

        return sample_24h, sample_96


if __name__ == "__main__":
    preprocessor = DDRE33Preprocessor()
    preprocessor.audit_raw_data()
    preprocessor.process_and_align()
    preprocessor.extract_scenario_sample(day_index=15)
    print("Preprocessing pipeline executed successfully.")
