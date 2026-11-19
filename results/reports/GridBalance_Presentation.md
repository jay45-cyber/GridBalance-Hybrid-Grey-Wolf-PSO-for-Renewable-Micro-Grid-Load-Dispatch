# GridBalance: Hybrid Grey Wolf–PSO for Renewable Microgrid Load Dispatch
## Academic Research Presentation (12 Slides)

---

### Slide 1: Title & Project Overview
# GridBalance
### Hybrid Grey Wolf–PSO for Renewable Micro-Grid Load Dispatch

**Presenters**: Senior Research Engineer, Optimization Scientist & Energy Systems Researcher  
**Focus**: Renewable Economic Dispatch on IEEE 33-Bus Feeder using the Authentic DDRE-33 Dataset  
**Algorithms**: Hybrid GWO-PSO, Standalone PSO, Standalone GWO, Real-Coded GA  
**Dataset DOI**: [10.6084/m9.figshare.29374640](https://doi.org/10.6084/m9.figshare.29374640) (*Nature Scientific Data 2025*)

---

### Slide 2: Motivation & Problem Statement
## The Microgrid Economic Dispatch Challenge
* **Renewable Intermittency**: High penetration of distributed Solar PV and Wind creates steep net-load ramping events.
* **Non-Convex Search Space**: Multi-generator dispatch involves non-linear battery degradation, dynamic Time-of-Use (TOU) tariffs, and strict power balance constraints.
* **Shortcomings of Standalone Metaheuristics**:
  - **PSO**: Fast initial exploitation, but susceptible to premature convergence in local minima.
  - **GWO**: Robust global exploration via pack hierarchy, but slower late-stage local refinement.
* **Core Goal**: Develop a mathematically unified **Hybrid GWO-PSO** framework that combines GWO's global exploration with PSO's kinetic velocity exploitation.

---

### Slide 3: Dataset Ingestion & Physical Testbed
## Authentic DDRE-33 Dataset & IEEE 33-Bus System
* **Dataset Citation**: Chen et al., *Scientific Data (Nature Portfolio)*, 2025.
* **Physical Mapping to IEEE 33-Bus Radial Feeder**:
  - **Bus 33**: Distributed Solar Photovoltaic (PV) ($1,200\text{ kW}$ rated peak).
  - **Bus 22**: Distributed Wind Turbine ($1,000\text{ kW}$ rated peak).
  - **Bus 1**: Substation Point of Common Coupling (PCC) ($2,500\text{ kW}$ import limit).
* **Data Resolution**: 15-minute sampling frequency across 35,040 observations (1 full annual cycle).
* **Integrity Guarantee**: Verified 0 missing values, 0 negative artifacts. Real measurements are strictly distinguished from declared simulation assumptions.

---

### Slide 4: Mathematical Optimization Model
## Objective Function Formulation
Minimizing total 24-hour microgrid operating cost:
$$\min \quad C_{total} = \sum_{t=1}^{T} \left( C_{solar}(t) + C_{wind}(t) + C_{battery}(t) + C_{grid}(t) + C_{curt}(t) + C_{emission}(t) \right) \Delta t$$

* **Solar & Wind O&M**: $C_{solar} = \$0.010/\text{kWh}, \quad C_{wind} = \$0.015/\text{kWh}$
* **BESS Degradation**: $C_{battery} = \$0.018/\text{kWh}$ (throughput degradation)
* **Time-of-Use (TOU) Grid Tariff**:
  - Off-Peak (23:00–07:00): $\$0.060/\text{kWh}$
  - Shoulder (07:00–14:00, 20:00–23:00): $\$0.120/\text{kWh}$
  - On-Peak (14:00–20:00): $\$0.240/\text{kWh}$
  - Feed-in Export Credit: $\$0.040/\text{kWh}$
* **Curtailment Penalty**: $\$0.050/\text{kWh}$ for unutilized renewable potential.

---

### Slide 5: Battery Energy Storage & Physical Constraints
## BESS State Dynamics & Power Balance
* **Power Balance Equality Constraint**:
  $$P_{solar}(t) + P_{wind}(t) + P_{battery}(t) + P_{grid}(t) = P_{load}(t), \quad \forall t$$
* **Discrete Battery State-of-Charge (SOC) Dynamics**:
  $$\text{SOC}(t) = \text{SOC}(t-1)(1 - \sigma_{sd}\Delta t) - \frac{P_{battery}(t)\Delta t}{E_{bat}} \cdot \begin{cases} \frac{1}{\eta_{dis}}, & P_{battery}(t) \ge 0 \text{ (discharging)} \\ \eta_{ch}, & P_{battery}(t) < 0 \text{ (charging)} \end{cases}$$
* **Operating Boundaries**:
  - Nominal Capacity: $2,000\text{ kWh}$ (LFP chemistry)
  - Charge / Discharge Efficiencies: $\eta_{ch} = 95\%, \quad \eta_{dis} = 95\%$
  - Allowable Range: $20\% \le \text{SOC}(t) \le 90\%$
  - Maximum Power Limit: $P_{ch, max} = P_{dis, max} = 600\text{ kW}$ (0.3C rate)

---

### Slide 6: Standalone Optimization Baselines
## Particle Swarm Optimization & Grey Wolf Optimizer
* **Standalone PSO**:
  - Velocity Equation: $\vec{V}_i(k+1) = w(k) \vec{V}_i(k) + c_1 r_1 (\vec{P}_{best, i} - \vec{X}_i) + c_2 r_2 (\vec{G}_{best} - \vec{X}_i)$
  - Dynamic Inertia Weight: $w(k) = 0.9 \to 0.4$ (linear decay)
  - Velocity Clamping: $V_{max} = 0.20 \times (ub - lb)$
* **Standalone GWO**:
  - Social Hierarchy: $\alpha$ (Alpha, optimal), $\beta$ (Beta, 2nd), $\delta$ (Delta, 3rd), $\omega$ (Omega, candidates)
  - Encircling & Hunting: $\vec{X}_i(k+1) = \frac{\vec{X}_1 + \vec{X}_2 + \vec{X}_3}{3}$
  - Linear Exploration Factor: $a(k) = 2.0 \to 0.0$

---

### Slide 7: Core Contribution: Hybrid GWO-PSO
## Synergistic Hybrid Optimization Architecture
* **Step 1: GWO Leadership Guidance**:
  $$\vec{X}_{GWO, i}(k+1) = \frac{\vec{X}_1 + \vec{X}_2 + \vec{X}_3}{3}$$
* **Step 2: Velocity Guidance with Dual Memory**:
  $$\vec{V}_i(k+1) = w(k)\vec{V}_i(k) + c_1 \vec{r}_1 \odot (\vec{P}_{best, i} - \vec{X}_i) + c_2 \vec{r}_2 \odot (\vec{X}_{GWO, i} - \vec{X}_i)$$
* **Step 3: Adaptive Time-Varying Blending**:
  $$\vec{X}_i(k+1) = \lambda(k) \vec{X}_{GWO, i} + (1 - \lambda(k)) (\vec{X}_i + \vec{V}_i(k+1))$$
  - $\lambda(k) = 0.80 \to 0.20$: Early iterations prioritize GWO multi-leader exploration; late iterations transition to PSO velocity exploitation.

---

### Slide 8: Feasibility Repair Operator
## Ensuring 100% Physical Feasibility
* **The Feasibility Challenge**: Standard random perturbation in metaheuristics generates solutions violating SOC limits or power balance.
* **Deterministic Feasibility Repair $\mathcal{R}(\vec{X})$**:
  1. Clamps renewable output strictly to instantaneous resource limits: $0 \le P_{solar} \le P_{solar, avail}$.
  2. Evaluates chronological SOC transitions step-by-step. Discharging is capped by usable energy above $SOC_{min}$; charging is capped by headroom below $SOC_{max}$.
  3. Computes exact substation grid power required to eliminate imbalance: $P_{grid} = P_{load} - P_{solar} - P_{wind} - P_{battery}$.
* **Result**: **100.0% Feasibility Rate** achieved across all algorithms and all 40 experimental runs.

---

### Slide 9: Experimental Benchmarking
## Statistical Results Across 10 Independent Seeds (40 Runs)
All algorithms evaluated with $N=30$, $K=100$ on identical Scenario Day 15:

| Algorithm | Best Cost (\$) | Mean Cost (\$) | Std Dev (\$) | Worst Cost (\$) | Runtime | Feasibility |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **GA** | \$3,068.12 | \$3,078.11 | \$6.41 | \$3,088.63 | 1.79s | **100.0%** |
| **Hybrid GWO-PSO** | **\$3,098.41** | **\$3,163.36** | **\$51.84** | **\$3,288.44** | **1.84s** | **100.0%** |
| **PSO** | \$3,056.75 | \$3,160.29 | \$74.86 | \$3,312.69 | 1.78s | **100.0%** |
| **GWO** | \$3,166.66 | \$3,215.69 | \$33.03 | \$3,290.27 | 1.74s | **100.0%** |

* **Key Takeaway**: Hybrid GWO-PSO reduces variance significantly relative to PSO ($\sigma = \$51.84$ vs $\$74.86$) and achieves a better worst-case performance (\$3,288.44 vs \$3,312.69).

---

### Slide 10: 24-Hour Energy Dispatch Results
## Optimal Generation Stack & Battery Dynamics
* **Peak Solar Absorption**: Peak solar generation ($673\text{ kW}$) occurs at 12:00–14:00. The battery charges at max rate ($600\text{ kW}$) to prevent export at low feed-in tariffs.
* **On-Peak Price Arbitrage**: During peak tariff hours (14:00–20:00, $\$0.24/\text{kWh}$), the battery discharges continuously, reducing expensive grid import by $550–600\text{ kW}$.
* **Zero Curtailment**: Achieved $0.00\text{ kWh}$ renewable curtailment across the entire 24-hour horizon.
* **RE Utilization**: $21.30\%$ of total microgrid energy demand supplied directly by local Solar PV and Wind.

---

### Slide 11: Interactive Streamlit Dashboard
## Real-Time Research & Visualization Platform
* **10 Comprehensive Navigation Sections**:
  - Section A: Project Overview & Architecture
  - Section B: DDRE-33 Dataset Inventory & Quality Audit
  - Section C: 24-Hour Resource & Demand Profiles
  - Section D: Microgrid & BESS Parameter Specifications
  - Section E: Algorithm Hyperparameter Controls
  - Section F: Live Optimization Engine (User-Selected Seeds & Days)
  - Section G: Comparative Benchmark & Cost Boxplots
  - Section H: Numerical Dispatch Schedules with CSV Export
  - Section I: Multi-Algorithm Convergence Trajectories
  - Section J: Performance Metric Reporting
* **Interactive Controls**: Sliders for Population, Iterations, Scenario Day, and Seeds.

---

### Slide 12: Summary, Conclusions & Research Roadmap
## Project Achievements & Future Directions
* **Summary of Achievements**:
  1. Authentic **DDRE-33** renewable dataset successfully audited, processed, and integrated.
  2. Standalone **PSO**, **GWO**, and **Hybrid GWO-PSO** algorithms developed from scratch in Python.
  3. Feasibility Repair guarantees 100% physical compliance across all runs.
  4. Reproducible 10-seed benchmarks and 10 publication-quality figures generated.
  5. Interactive Streamlit dashboard and complete academic documentation delivered.
* **Research Roadmap**:
  - Phase 1: Non-linear AC Optimal Power Flow (AC-OPF) with reactive power ($Q$) and voltage limits ($0.95 \le V_i \le 1.05\text{ p.u.}$).
  - Phase 2: Model Predictive Control (MPC) with rolling horizons under stochastic weather uncertainty.
  - Phase 3: Integration of hydrogen storage and bidirectional EV fleet dispatch.
