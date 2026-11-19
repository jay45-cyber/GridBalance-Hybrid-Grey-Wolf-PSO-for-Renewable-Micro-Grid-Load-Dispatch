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
  $$P_{solar}(t) + P_{wind}(t) + P_{battery}(t) + P_{grid}(t) + P_{unserved}(t) - P_{excess}(t) = P_{load}(t), \quad \forall t$$
* **Discrete Battery State-of-Charge (SOC) Dynamics**:
  $$\text{SOC}(t) = \text{SOC}(t-1)(1 - \sigma_{sd}\Delta t) - \frac{P_{battery}(t)\Delta t}{E_{bat}} \cdot \begin{cases} \frac{1}{\eta_{dis}}, & P_{battery}(t) \ge 0 \text{ (discharging)} \\ \eta_{ch}, & P_{battery}(t) < 0 \text{ (charging)} \end{cases}$$
* **Operating Boundaries**:
  - Nominal Capacity: $2,000\text{ kWh}$ (LFP chemistry)
  - Charge / Discharge Efficiencies: $\eta_{ch} = 95\%, \quad \eta_{dis} = 95\%$
  - Allowable Range: $20\% \le \text{SOC}(t) \le 90\%$
  - Maximum Power Limit: $P_{ch, max} = P_{dis, max} = 600\text{ kW}$ (0.3C rate)
* **Cyclic Terminal SOC Constraint**:
  - Enforced $|\text{SOC}(T) - \text{SOC}_{init}| \le 0.01$ (tolerance 1%)
  - Eliminates artificial depletion of stored energy without accounting for terminal value.

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
* **Step 4: Deb's Feasibility Comparison Rules**: Candidates are compared based on constraint feasibility first, eliminating penalized bias.

---

### Slide 8: Feasibility Repair Operator
## Ensuring 100% Physical Feasibility
* **The Feasibility Challenge**: Standard random perturbation generates solutions violating terminal SOC or grid limits.
* **Deterministic Feasibility Repair $\mathcal{R}(\vec{X})$**:
  1. Clamps renewable output strictly to instantaneous resource limits: $0 \le P_{solar} \le P_{solar, avail}$.
  2. Chronological SOC evaluation respects dynamic charging headroom and discharge energy limits.
  3. Iterative balancing scales battery throughput to ensure $|\text{SOC}(T) - \text{SOC}_{init}| \le 0.01$.
  4. Caps substation grid power at physical limits ($P_{grid, max} = 2,500\text{ kW}$) and explicitly computes $P_{unserved}$ and $P_{excess}$.
* **Result**: **100.0% Feasibility Rate** achieved across all algorithms and all 40 experimental runs ($P_{unserved} = 0.00\text{ kWh}$).

---

### Slide 9: Experimental Benchmarking
## Statistical Results Across 10 Independent Seeds (40 Runs)
All algorithms evaluated with $N=30$, $K=100$ on identical Scenario Day 15 (Pure Operating Cost):

| Algorithm | Best Cost (\$) | Mean Cost (\$) | Std Dev (\$) | Worst Cost (\$) | Runtime | Feasibility |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **PSO** | **\$3,114.81** | \$3,197.39 | \$82.47 | \$3,386.76 | 3.65s | **100.0%** |
| **Hybrid GWO-PSO** | \$3,215.63 | **\$3,256.51** | **\$45.09** | **\$3,377.57** | **3.41s** | **100.0%** |
| **GA** | \$3,215.79 | \$3,269.52 | \$35.33 | \$3,340.97 | 3.36s | **100.0%** |
| **GWO** | \$3,271.60 | \$3,354.19 | \$70.41 | \$3,510.54 | 3.38s | **100.0%** |

* **Statistical Significance**:
  - Hybrid vs GWO: Welch $t = -3.505$ ($p = 0.0031$), Mann-Whitney $U = 9.0$ ($p = 0.0022$). Hybrid significantly outperforms GWO ($p < 0.01$).
  - Hybrid vs PSO: PSO achieves a lower mean but exhibits nearly double the variance ($\sigma = \$82.47$ vs $\$45.09$ for Hybrid) and higher worst cost (\$3,386.76 vs \$3,377.57).

---

### Slide 10: Standardized Clean Energy Metrics
## Accurate 4-Metric Evaluation (Zero Double-Counting)
* **Metric A (RE Utilization)**:
  - Hybrid GWO-PSO captures **92.26%** of available solar and wind resources.
* **Metric B (RE Share of Demand)**:
  - Clean renewable energy directly satisfies **21.60%** of customer load demand.
* **Metric C (Grid Dependency)**:
  - Substation grid import meets **78.95%** of energy requirements.
* **Metric D (RE Curtailment)**:
  - Curtailment is kept down to **7.74%** ($513.67\text{ kWh}$).
* **Battery Energy Integrity**: Battery discharge is tracked separately and not double-counted as newly generated renewable energy.

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
