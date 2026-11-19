================================================================================
DDRE-33 Dataset for Distributed Renewable Energy Scenarios
================================================================================

1. Dataset Citation & Metadata
------------------------------
Title: DDRE-33: A Large-Scale Dataset of Distributed Renewable Energy Scenarios on the IEEE-33 Bus Network
Authors: Yuxuan Chen, Haipeng Xie, Wenqi Huang, Peng Li
Journal: Scientific Data (Nature Portfolio), Vol. 13, Article 146 (2025)
DOI: 10.6084/m9.figshare.29374640
Repository URL: https://figshare.com/articles/dataset/DDRE-33_Dataset_for_Distributed_Renewable_Energy_Scenarios/29374640
Official GitHub: https://github.com/YuxuanCEE/DDRE-33-CHIME

2. Dataset Purpose & Description
--------------------------------
The DDRE-33 dataset provides comprehensive, high-resolution scenarios of distributed 
solar photovoltaic (PV) and wind power generation mapped to the standard IEEE 33-bus 
radial distribution network.

Unlike centralized generation datasets, DDRE-33 provides localized, spatiotemporally 
correlated renewable energy outputs at specific distribution network nodes:
- Solar PV Generation: Bus 18 and Bus 33
- Distributed Wind Generation: Bus 22 and Bus 25

3. Temporal Structure & Resolution
----------------------------------
- Sampling Frequency: 15-minute intervals (4 steps per hour)
- Daily Horizon: 96 intervals per day (24 hours * 4 quarters)
- Full Dataset Span: 35,040 observations per series = 365 days (1 full year)
- Start Timestamp: 2022-07-01 00:00:00
- End Timestamp: 2023-06-30 23:45:00

4. Units and Variables
----------------------
- Per-unit files (e.g. node_33_solar_1.csv, node_22_wind_1.csv):
  Normalized values in [0.0, 1.0] representing instantaneous power output divided 
  by installed rated generator capacity (p.u.).
- Actual generation files (e.g. node_33_PV_actual.csv): 
  Active power generation in Megawatts (MW).
- Synthesized diffusion scenarios (ddpm_syn_solar.csv, ddpm_syn_wind.csv):
  Generated via Denoising Diffusion Probabilistic Models (DDPM/CHIME) calibrated 
  against real measurements.

5. Distinguishing Measured Data from Simulation Assumptions
-----------------------------------------------------------
- REAL MEASUREMENTS (DDRE-33):
  * Solar PV generation time series at Bus 33 (15-min, 35,040 samples).
  * Wind power generation time series at Bus 22 (15-min, 35,040 samples).
  * Real normalized output profiles (p.u.) and diffusion scenarios.

- SIMULATION ASSUMPTIONS (declared in config/system_parameters.yaml):
  * IEEE-33 bus feeder load demand: 1600 kW peak load with standard diurnal profile.
  * Battery Energy Storage System (BESS): 2000 kWh capacity, 600 kW max rate, 95% eff.
  * Utility Grid Tariffs: Time-of-Use (TOU) 3-tier tariff ($0.06, $0.12, $0.24 / kWh).
  * Operating & Maintenance Costs: Solar ($0.010/kWh), Wind ($0.015/kWh), BESS ($0.018/kWh).
================================================================================
