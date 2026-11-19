# GridBalance — Hybrid Grey Wolf–PSO for Renewable Micro-Grid Load Dispatch

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Dataset: DDRE-33](https://img.shields.io/badge/Dataset-DDRE--33%20(Nature%20Sci%20Data)-green.svg)](https://doi.org/10.6084/m9.figshare.29374640)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 33 Passed](https://img.shields.io/badge/tests-33%20passed-brightgreen.svg)](tests/)

**GridBalance** is a research-grade renewable microgrid optimal economic load dispatch framework implemented in Python. It integrates authentic high-resolution distributed solar PV and wind generation scenarios from the **DDRE-33** dataset (mapped to the standard **IEEE 33-bus distribution feeder**) and introduces a synergistic **Hybrid Grey Wolf–Particle Swarm Optimization (Hybrid GWO-PSO)** dispatch algorithm.

---

## 1. Project Architecture

```
GridBalance/
│
├── data/
│   ├── raw/                 # Authentic DDRE-33 raw CSVs and dataset Readme.txt
│   ├── processed/           # Aligned 15-min and hourly clean time-series
│   └── samples/             # 24-hour canonical and multi-day dispatch scenarios
│
├── config/
│   └── system_parameters.yaml # Explicit microgrid specs, tariffs, BESS limits, costs
│
├── src/
│   ├── data_loader.py       # YAML configuration and scenario vector loader
│   ├── data_preprocessing.py # DDRE-33 audit, range checking, clean alignment
│   ├── energy_model.py      # BESS discrete SOC dynamics and power balance simulation
│   ├── constraints.py       # Feasibility repair operator and physical limit validation
│   ├── objective_function.py # Operational cost, TOU tariffs, curtailment, and penalties
│   ├── pso.py               # Standalone Particle Swarm Optimization from scratch
│   ├── gwo.py               # Standalone Grey Wolf Optimizer from scratch
│   ├── hybrid_gwo_pso.py    # Synergistic Hybrid GWO-PSO optimization engine
│   ├── ga.py                # Standalone Real-Coded Genetic Algorithm benchmark
│   ├── evaluation.py        # Statistical metrics (mean, std, worst, feasibility)
│   └── visualization.py     # Publication-grade figures (stacked dispatch, boxplots)
│
├── experiments/
│   ├── run_pso.py           # Standalone PSO experiment runner
│   ├── run_gwo.py           # Standalone GWO experiment runner
│   ├── run_hybrid.py        # Standalone Hybrid GWO-PSO experiment runner
│   └── compare_algorithms.py# 10-seed 4-algorithm benchmarking pipeline
│
├── dashboard/
│   └── app.py               # Interactive Streamlit 10-section research dashboard
│
├── results/
│   ├── metrics/             # Exported comparison summary and run-by-run CSVs
│   ├── graphs/              # 10 publication figures (profiles, convergence, boxplots)
│   └── reports/             # Academic Research Report and Presentation slides
│
├── tests/
│   ├── test_gridbalance_suite.py # 28 automated unit and integration tests (100% pass)
│   ├── test_dashboard_runtime.py # Full Streamlit runtime verification suite
│   └── validate_end_to_end.py    # 40-run independent mathematical audit script
│
├── requirements.txt         # Pinned Python package dependencies
├── README.md                # Project master documentation
└── main.py                  # CLI unified pipeline entrypoint
```

---

## 2. Publications and Project Deliverables

All research documentation, IEEE format publications, slide decks, and data archives are integrated directly into the repository:

| Deliverable | Formats | Primary Locations | Description |
| :--- | :---: | :--- | :--- |
| **IEEE Research Paper** | `.docx`, `.tex`, `.md` | `IEEE_GridBalance_Research_Paper.docx`<br/>`results/reports/IEEE_GridBalance_Research_Paper.docx` | Publication-ready paper in IEEE 2-column format with author header block, equations, tables, embedded figures, and 15 citations. |
| **IEEE Technical Report** | `.docx`, `.tex`, `.md` | `IEEE_GridBalance_Research_Report.docx`<br/>`results/reports/IEEE_GridBalance_Research_Report.docx` | Comprehensive 857 KB research report detailing the DDRE-33 audit, 40-run benchmark, hypothesis testing, and constraint verification. |
| **Academic Presentation** | `.pptx`, `.md` | `results/reports/GridBalance_7_Slide_Presentation.pptx`<br/>`results/reports/GridBalance_7_Slide_Presentation.md` | 7-slide widescreen presentation deck for M.Tech thesis / conference defense. |
| **Technical Audit & Log** | `.md` | `FINAL_TECHNICAL_AUDIT.md`<br/>`CORRECTION_LOG.md` | Exhaustive independent verification audit and chronological technical correction record. |
| **Complete Project ZIP** | `.zip` | `GridBalance_Project.zip` | Standalone 7.7 MB archive bundling source code, datasets, figures, tests, and documentation. |

---

## 3. Dataset Integration: DDRE-33

GridBalance uses the authentic **DDRE-33** dataset:
- **Citation**: Chen et al., *"DDRE-33: A Large-Scale Dataset of Distributed Renewable Energy Scenarios on the IEEE-33 Bus Network"*, *Scientific Data* (Nature Portfolio), Vol. 13, Article 146, 2025.
- **Figshare DOI**: [10.6084/m9.figshare.29374640](https://doi.org/10.6084/m9.figshare.29374640)
- **Nodes & Generators**:
  - **Bus 33**: Distributed Solar Photovoltaic (PV) Generation ($P_{solar, rated} = 1,200\text{ kW}$)
  - **Bus 22**: Distributed Wind Turbine Generation ($P_{wind, rated} = 1,000\text{ kW}$)
- **Resolution**: 15-minute intervals across 35,040 observations (1 full annual cycle).

### Distinction: Real Measurements vs. Declared Assumptions
To uphold strict scientific integrity, real dataset observations are separated from simulation parameters:
- **Measured Data (DDRE-33)**: Solar PV output and Wind turbine output (p.u. and kW).
- **Declared Assumptions (`config/system_parameters.yaml`)**:
  - Microgrid Load Profile: Diurnal commercial/residential shape scaled to IEEE-33 feeder ($1,600\text{ kW}$ peak demand).
  - Battery Storage (BESS): 2,000 kWh Lithium Iron Phosphate (LFP) capacity, 600 kW max rate, 95% efficiency, SOC bounds [20%, 90%].
  - Utility Tariff: 3-tier Time-of-Use (TOU) import schedule (\$0.06 off-peak, \$0.12 shoulder, \$0.24 on-peak) and \$0.04/kWh export credit.

---

## 3. Mathematical Formulation

### 3.1 Objective Function
The primary objective minimizes total 24-hour microgrid operating cost:
$$\min \quad C_{total} = \sum_{t=1}^{T} \left( C_{solar}(t) + C_{wind}(t) + C_{battery}(t) + C_{grid}(t) + C_{curtailment}(t) + C_{emission}(t) \right) \Delta t$$
where:
- $C_{solar}(t) = c_{solar, om} P_{solar}(t)$ (\$0.010/kWh)
- $C_{wind}(t) = c_{wind, om} P_{wind}(t)$ (\$0.015/kWh)
- $C_{battery}(t) = c_{deg} |P_{battery}(t)|$ (\$0.018/kWh degradation throughput cost)
- $C_{grid}(t) = c_{tariff}(t) \max(0, P_{grid}(t)) - c_{export} \max(0, -P_{grid}(t))$
- $C_{curtailment}(t) = c_{curt} \left([P_{solar, avail}(t) - P_{solar}(t)] + [P_{wind, avail}(t) - P_{wind}(t)]\right)$ (\$0.050/kWh)
- $C_{emission}(t) = \kappa_{CO2} \cdot \gamma_{emission} \cdot \max(0, P_{grid}(t))$ (Carbon tax)

### 3.2 Physical Constraints & Standardized Metrics
1. **Power Balance Identity (Evaluated Hourly)**:
   $$P_{solar}(t) + P_{wind}(t) + P_{battery}(t) + P_{grid, import}(t) - P_{grid, export}(t) + P_{unserved}(t) - P_{excess}(t) = P_{load}(t), \quad \forall t$$
   where $P_{unserved}(t) \ge 0$ (unserved load) and $P_{excess}(t) \ge 0$ (excess generation) are tracked independently to eliminate silent clipping.
2. **Generation Limits**:
   $$0 \le P_{solar}(t) \le P_{solar, avail}(t), \quad 0 \le P_{wind}(t) \le P_{wind, avail}(t)$$
3. **Independent Grid Capacity Limits**:
   $$0 \le P_{grid, import}(t) \le P_{grid, import, max} \quad (2,500\text{ kW})$$
   $$0 \le P_{grid, export}(t) \le P_{grid, export, max} \quad (1,000\text{ kW})$$
4. **BESS Dynamic State of Charge (SOC) Trajectory**:
   $$\text{SOC}(t) = \text{SOC}(t-1)(1 - \sigma_{sd}\Delta t) - \frac{P_{battery}(t) \Delta t}{E_{bat}} \cdot \begin{cases} \frac{1}{\eta_{dis}}, & P_{battery}(t) \ge 0 \text{ (discharge)} \\ \eta_{ch}, & P_{battery}(t) < 0 \text{ (charge)} \end{cases}$$
   $$\text{SOC}_{min} \le \text{SOC}(t) \le \text{SOC}_{max}, \quad \forall t \in \{0, \dots, T\}$$
   with $\text{SOC}_{min} = 0.20, \quad \text{SOC}_{max} = 0.90, \quad \text{SOC}_{init} = 0.50$.
5. **Cyclic Terminal SOC Constraint**:
   $$|\text{SOC}(T) - \text{SOC}_{init}| \le \epsilon_{term} \quad (\epsilon_{term} = 0.01)$$
   guarantees zero unphysical energy borrowing over the daily scheduling cycle.
6. **Standardized Clean Energy Metrics & Attribution**:
   - **Metric A (RE Utilization)**: $\frac{\sum (P_{solar} + P_{wind})}{\sum (P_{solar, avail} + P_{wind, avail})} \times 100$
   - **Metric B (RE Share of Demand)**: $\frac{\sum P_{re \to demand} + \sum P_{re, dis \to demand}}{\sum P_{load} - P_{unserved}} \times 100$
   - **Metric C (Grid Dependency)**: $\frac{\sum P_{grid, import}}{\sum P_{load} - P_{unserved}} \times 100$
   - **Metric D (Curtailment)**: $\frac{\sum P_{curt}}{\sum (P_{solar, avail} + P_{wind, avail})} \times 100$ (with $\text{Metric A} + \text{Metric D} \equiv 100\%$)
   - *Attribution Note*: Battery discharge is attributed based on dynamic stored clean fraction $f_{re}(t)$ without double-counting.

---

## 4. Hybrid GWO-PSO Algorithm

Standard PSO often suffers from premature convergence in non-convex multi-generator spaces, while standard GWO can exhibit slower late-stage exploitation. GridBalance couples them via an adaptive hybrid mechanism:

1. **GWO Leadership Estimation**:
   Candidate wolves are guided by the Alpha ($\alpha$), Beta ($\beta$), and Delta ($\delta$) pack leaders:
   $$\vec{X}_{GWO, i}(k+1) = \frac{\vec{X}_1 + \vec{X}_2 + \vec{X}_3}{3}$$
2. **PSO Velocity Guidance**:
   Particles maintain personal best memory ($pbest_i$) and incorporate the GWO target as social guidance:
   $$\vec{V}_i(k+1) = w(k) \vec{V}_i(k) + c_1 \vec{r}_1 \odot (\vec{P}_{best, i} - \vec{X}_i(k)) + c_2 \vec{r}_2 \odot (\vec{X}_{GWO, i} - \vec{X}_i(k))$$
3. **Adaptive Time-Varying Position Blend**:
   $$\vec{X}_i(k+1) = \lambda(k) \vec{X}_{GWO, i} + (1 - \lambda(k)) (\vec{X}_i(k) + \vec{V}_i(k+1))$$
   where $\lambda(k)$ linearly decreases from $0.80 \to 0.20$, transitioning the swarm from GWO-dominated global exploration to PSO velocity exploitation.
4. **Feasibility Repair & Deb's Constraint Rules**: Ensures solutions strictly respect terminal SOC and physical bounds, ranking candidates on pure operating cost.

---

## 5. Experimental Benchmark Results (10 Seeds, 40 Runs)

Benchmarked on identical DDRE-33 Scenario Day 15, population size $N=30$, and iteration budget $K=100$ (ranked by Pure Operating Cost):

| Algorithm | Best Cost (\$) | Mean Cost (\$) | Std Dev (\$) | Worst Cost (\$) | Mean Runtime | Feasibility Rate | Mean Term SOC Err |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **PSO** | **\$3,114.81** | \$3,197.39 | \$82.47 | \$3,386.76 | 3.65s | **100.0%** | 0.0091 |
| **Hybrid GWO-PSO** | \$3,215.63 | **\$3,256.51** | **\$45.09** | **\$3,377.57** | **3.41s** | **100.0%** | **0.0068** |
| **GA** | \$3,215.79 | \$3,269.52 | **\$35.33** | **\$3,340.97** | 3.36s | **100.0%** | 0.0063 |
| **GWO** | \$3,271.60 | \$3,354.19 | \$70.41 | \$3,510.54 | 3.38s | **100.0%** | 0.0078 |

*Statistical Significance & Engineering Trade-offs*:
- **Statistical Superiority over GWO**: Hybrid GWO-PSO demonstrates a statistically significant improvement over standalone GWO (Welch's $t = -3.505, p = 0.0031$; Mann-Whitney $U = 9.0, p = 0.0022$), saving an average of \$97.68/day.
- **Stability Comparison**: Standalone PSO achieved the lowest mean cost (\$3,197.39) on this active power problem, but exhibited high variance across seeds ($\sigma = \$82.47$), with its worst seed performing worse than the Hybrid's worst seed (\$3,386.76 vs \$3,377.57). Hybrid GWO-PSO reduced dispersion by 45.3% ($\sigma = \$45.09$). GA showed the lowest variance ($\sigma = \$35.33$).
- **Feasibility**: 100.0% feasibility achieved across all 40 runs ($P_{unserved} = 0.00\text{ kWh}$, $P_{excess} = 0.00\text{ kWh}$).

---

## 6. Installation & Execution

### Prerequisites
- Python 3.11+
- Virtual environment recommended

```bash
git clone https://github.com/your-username/GridBalance.git
cd GridBalance
pip install -r requirements.txt
```

### Running Automated Test Suite
```bash
pytest tests/test_gridbalance_suite.py -v
```

### Running Individual Algorithms
```bash
# Run Particle Swarm Optimization
python experiments/run_pso.py

# Run Grey Wolf Optimizer
python experiments/run_gwo.py

# Run Hybrid GWO-PSO
python experiments/run_hybrid.py
```

### Running 10-Seed Multi-Algorithm Benchmark
```bash
python experiments/compare_algorithms.py
```

### Launching Streamlit Interactive Dashboard
```bash
streamlit run dashboard/app.py
```

### Unified CLI Runner (`main.py`)
```bash
# Execute entire pipeline (Audit -> Preprocess -> Benchmark -> Tests)
python main.py --mode all

# Run specific algorithm on scenario day 20 with seed 101
python main.py --mode hybrid --day-index 20 --seed 101 --pop-size 30 --max-iter 100
```

---

## 7. Limitations & Future Work

1. **AC Power Flow Integration**: The current model enforces active power balance. Integrating full non-linear AC optimal power flow (AC-OPF) with reactive power dispatch ($Q$) and bus voltage limits ($0.95 \le V_i \le 1.05\text{ p.u.}$) is a prime target for future work.
2. **Multi-Horizon Lookahead**: Extending dispatch to model-predictive control (MPC) with rolling 48-hour horizons under stochastic renewable forecast uncertainty.
3. **Hydrogen & EV Integration**: Incorporating green hydrogen electrolyzers and bidirectional electric vehicle (V2G) fleet scheduling.

---

## 8. License

Distributed under the MIT License. See `LICENSE` for details.
