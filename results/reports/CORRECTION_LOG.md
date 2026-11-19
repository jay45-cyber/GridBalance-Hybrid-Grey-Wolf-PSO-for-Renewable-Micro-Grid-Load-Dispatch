# GridBalance: Comprehensive Bug Fix & Optimization Correction Log

**Project**: GridBalance — Hybrid Grey Wolf–PSO for Renewable Micro-Grid Load Dispatch  
**Dataset**: Official DDRE-33 Renewable Energy Scenarios (Nature Scientific Data 2025, DOI: 10.6084/m9.figshare.29374640)  
**System Configuration**: IEEE 33-Bus Radial Feeder (Node 33 Solar PV, Node 22 Wind Turbine, Node 1 Substation Grid)  
**Environment**: Python 3.11.9, NumPy 2.4.6, Pandas 3.1.1, SciPy 1.17.1, PyYAML 6.0.3, Streamlit 1.67.0, Pytest 9.0.2  
**Date**: November 2026  

---

## Executive Summary of Corrections

This document records the systematic identification, root-cause diagnosis, mathematical reformulation, implementation, and automated test verification for all mathematical, logical, algorithmic, and evaluation components within the **GridBalance** microgrid load dispatch framework.

Eight major domains of correction were performed:
1. **Battery Terminal State of Charge (SOC) Conservation**
2. **Power Balance Equality, Unserved Load, and Grid Capacity Constraints**
3. **Independent Multi-Constraint Feasibility Validation & Reporting**
4. **Objective Function Restructuring & Penalty Separation**
5. **Standardized 4-Metric Renewable Energy Accounting (Zero Double-Counting)**
6. **Fair Multi-Algorithm Benchmarking with Statistical Significance Testing**
7. **Refined Hybrid GWO-PSO Algorithm Architecture (Deb's Rules & Adaptive Blending)**
8. **Interactive Streamlit Dashboard & Publication-Grade Visualizations**

---

## 1. Battery Terminal State of Charge (SOC)

### Original Problem Description
In the initial model, the battery could start at an initial state of charge of 50% ($SOC_{init} = 0.50$) and finish at the minimum allowable boundary ($SOC_{final} = 0.20$). Because no terminal state condition was enforced, the optimization algorithms artificially minimized operational costs by consuming 30% of the battery's stored energy capacity (600 kWh) as "free energy," creating an unphysical economic bias across 24-hour dispatch horizons.

### Root Cause
1. `src/energy_model.py` and `src/constraints.py` evaluated instantaneous SOC limits ($SOC_{min} \le SOC(t) \le SOC_{max}$) chronologically, but omitted any boundary condition on $SOC(T)$.
2. `src/objective_function.py` lacked a terminal SOC deviation penalty.
3. Candidate solutions were allowed to violate cyclic net-zero energy conservation without receiving any fitness penalization or repair.

### Files Modified
- `src/energy_model.py`
- `src/constraints.py`
- `src/objective_function.py`
- `tests/test_gridbalance_suite.py`

### Specific Correction Implemented
1. **Cyclic Terminal SOC Constraint**: For cyclic 24-hour daily scheduling, enforced the boundary condition:
   $$\text{SOC}(T) = \text{SOC}_{init} \pm \epsilon_{term}$$
   where $\epsilon_{term} = 0.01$ (1.0% tolerance).
2. **Dynamic Terminal Tracking**: Modified `simulate_dispatch()` in `MicrogridEnergyModel` to calculate and report `soc_final`, `soc_initial`, and `terminal_soc_error = |soc_final - soc_initial|` at every evaluation.
3. **Iterative Feasibility Repair**: Implemented an iterative energy balancing operator in `MicrogridConstraints.repair_candidate()`. If net battery energy throughput leaves the battery depleted ($\text{SOC}(T) < \text{SOC}_{init}$), candidate discharging commands are proportionally scaled down; conversely, if excess energy remains, charging commands are scaled down, ensuring candidate solutions enter the feasible basin.
4. **Terminal SOC Penalization**: Implemented both quadratic and linear penalties in `MicrogridObjective`:
   $$C_{pen, term} = \mu_{term} \cdot (\Delta \text{SOC})^2 + \mu_{term, lin} \cdot \Delta \text{SOC}$$
   with $\mu_{term} = \$10,000$ and $\mu_{term, lin} = \$500/\text{p.u.}$, preventing unfeasible terminal solutions from appearing attractive to the optimizers.
5. **Non-Simultaneous Charging and Discharging**: Explicitly separated $P_{ch}(t) \ge 0$ and $P_{dis}(t) \ge 0$ such that $P_{ch}(t) \cdot P_{dis}(t) = 0$ for all $t$.

### Mathematical Formulation
**Before Correction:**
$$\text{SOC}(t) = \text{SOC}(t-1) - \frac{P_{bat}(t) \Delta t}{E_{bat}}, \quad \text{SOC}(T) \text{ unconstrained}$$

**After Correction:**
$$\text{SOC}(t) = \text{SOC}(t-1)(1 - \sigma_{sd} \Delta t) - \frac{P_{bat}(t) \Delta t}{E_{bat}} \cdot \begin{cases} \frac{1}{\eta_{dis}}, & P_{bat}(t) \ge 0 \text{ (discharging)} \\ \eta_{ch}, & P_{bat}(t) < 0 \text{ (charging)} \end{cases}$$
$$\text{Subject to: } |\text{SOC}(T) - \text{SOC}_{init}| \le 0.01$$

### Test Performed
Executed `test_battery_terminal_soc` and `test_battery_energy_conservation` in `tests/test_gridbalance_suite.py`.

### Test Result
**PASSED**. Terminal SOC error on balanced test cycles is $< 0.001$. Optimizers achieve $\text{SOC}(T) \approx 0.5000 \pm 0.008$.

### Remaining Limitations
If the scheduling horizon is non-cyclic (e.g., rolling 6-hour or 12-hour intraday redispatch), the terminal condition should be set to a dynamic target from day-ahead planning rather than fixed cyclic equality.

---

## 2. Power Balance Equality and Grid Constraints

### Original Problem Description
The previous energy model clipped utility grid power directly to its maximum import and export limits ($[-P_{grid, export, max}, P_{grid, import, max}]$). If load demand exceeded the combined capacity of solar, wind, battery, and maximum grid import, the shortfall was silently clipped, concealing unserved electricity demand and violating the fundamental power balance equation.

### Root Cause
In `src/energy_model.py`, grid power was assigned as:
`p_grid = np.clip(p_load - p_solar - p_wind - p_battery, -p_grid_max, p_grid_max)`
without tracking or penalizing the residual difference `p_load - (p_solar + p_wind + p_battery + p_grid)`.

### Files Modified
- `src/energy_model.py`
- `src/constraints.py`
- `src/objective_function.py`
- `tests/test_gridbalance_suite.py`

### Specific Correction Implemented
1. **Explicit Power Residual Tracking**: Residual power imbalance is partitioned into physical deficits (`unserved_load`) and surpluses (`excess_generation`):
   $$P_{raw}(t) = P_{load}(t) - P_{solar}(t) - P_{wind}(t) - P_{battery}(t)$$
   - If $P_{raw}(t) > P_{grid, import, max}$:
     $$P_{grid}(t) = P_{grid, import, max}, \quad P_{unserved}(t) = P_{raw}(t) - P_{grid, import, max}, \quad P_{excess}(t) = 0$$
   - If $P_{raw}(t) < -P_{grid, export, max}$:
     $$P_{grid}(t) = -P_{grid, export, max}, \quad P_{excess}(t) = -P_{raw}(t) - P_{grid, export, max}, \quad P_{unserved}(t) = 0$$
   - Otherwise:
     $$P_{grid}(t) = P_{raw}(t), \quad P_{unserved}(t) = 0, \quad P_{excess}(t) = 0$$
2. **Rigorous Power Balance Identity**: Enforced the exact equality at every time step:
   $$P_{solar}(t) + P_{wind}(t) + P_{battery}(t) + P_{grid}(t) + P_{unserved}(t) - P_{excess}(t) = P_{load}(t)$$
   within numerical tolerance ($\delta \le 10^{-5}\text{ kW}$).
3. **Severe Economic Penalties**: Applied Value of Lost Load ($VOLL = \$2.00/\text{kWh}$) to unserved demand and $\$0.50/\text{kWh}$ to unmarketable excess generation.

### Mathematical Formulation
**Before Correction:**
$$P_{grid}(t) = \text{clip}\left(P_{load}(t) - P_{solar}(t) - P_{wind}(t) - P_{bat}(t), -P_{grid, max}, P_{grid, max}\right)$$
$$(\text{Residual imbalance unrecorded})$$

**After Correction:**
$$P_{deficit}(t) = \max\left(0, P_{load}(t) - P_{solar}(t) - P_{wind}(t) - P_{bat}(t) - P_{grid, max}\right)$$
$$P_{excess}(t) = \max\left(0, P_{solar}(t) + P_{wind}(t) + P_{bat}(t) - P_{load}(t) - P_{export, max}\right)$$
$$\text{Residual Imbalance: } |P_{solar} + P_{wind} + P_{bat} + P_{grid} + P_{deficit} - P_{excess} - P_{load}| < 10^{-4}\text{ kW}$$

### Test Performed
Executed `test_grid_limits_and_power_balance` in `tests/test_gridbalance_suite.py` with an artificially inflated load profile of 5,000 kW (exceeding the 2,500 kW grid substation limit).

### Test Result
**PASSED**. Grid power remained strictly capped at 2,500 kW, unserved load registered 2,500 kW, and power balance was satisfied with $0.0000$ error.

### Remaining Limitations
Distribution branch flow congestion and node bus voltages are not evaluated in active power dispatch; requires AC-OPF integration.

---

## 3. Constraint Validation and Reporting

### Original Problem Description
The constraint module previously aggregated all constraint violations into a single scalar fitness penalty. It was impossible to determine which specific constraint (solar limits, wind limits, battery rate, hourly SOC, terminal SOC, grid import, or grid export) was violated, or by what magnitude.

### Root Cause
`src/constraints.py` lacked an independent metric evaluation pipeline and returned only combined penalties.

### Files Modified
- `src/constraints.py`
- `tests/test_gridbalance_suite.py`

### Specific Correction Implemented
1. Developed `MicrogridConstraints.evaluate_feasibility()`, which computes independent numerical metrics:
   - `solar_upper_violation` (kW)
   - `solar_lower_violation` (kW)
   - `wind_upper_violation` (kW)
   - `wind_lower_violation` (kW)
   - `battery_charge_violation` (kW)
   - `battery_discharge_violation` (kW)
   - `soc_bounds_violation` (p.u.)
   - `terminal_soc_error` (p.u.)
   - `grid_import_violation` (kW)
   - `grid_export_violation` (kW)
   - `power_balance_residual` (kW)
   - `unserved_load_kwh` (kWh)
   - `excess_generation_kwh` (kWh)
2. Implemented independent boolean flags for every constraint alongside the overall `is_feasible` flag.
3. Provided complete structured dictionary outputs for downstream reporting and dashboard display.

### Test Performed
Executed `test_solar_generation_limits`, `test_wind_generation_limits`, `test_battery_charging_limits`, and `test_battery_discharging_limits` in `tests/test_gridbalance_suite.py`.

### Test Result
**PASSED**. All constraints are evaluated independently and report 0.0 violations on feasible solutions.

---

## 4. Objective Function and Cost Restructuring

### Original Problem Description
Constraint penalties were previously conflated with pure operational expenses ($C_{oper}$). This led to ambiguous optimization reporting where an infeasible candidate with high penalties could not be transparently distinguished from a feasible candidate with naturally higher operating expenses. In addition, kW-to-kWh energy conversions and battery degradation required rigorous verification.

### Root Cause
In `src/objective_function.py`, penalty values were added into intermediate cost variables rather than strictly isolated.

### Files Modified
- `src/objective_function.py`
- `src/evaluation.py`
- `tests/test_gridbalance_suite.py`

### Specific Correction Implemented
1. **Strict Cost Separation**: Divided the evaluation output into two strictly separate categories:
   - **Pure Operating Cost ($C_{oper}$)**:
     $$C_{oper} = \sum_{t=1}^{T} \Big( c_{solar, om} P_{solar}(t) + c_{wind, om} P_{wind}(t) + c_{deg} |P_{bat}(t)| + C_{grid}(t) + c_{curt} P_{curt}(t) + C_{CO2}(t) \Big) \Delta t$$
   - **Constraint Penalties ($C_{penalties}$)**:
     $$C_{penalties} = \mu_{unserved} E_{unserved} + \mu_{excess} E_{excess} + C_{pen, term} + \mu_{soc} \sum \text{Viol}_{soc}$$
   - **Total Fitness**:
     $$\text{Fitness} = C_{oper} + C_{penalties}$$
2. **Accurate Unit Conversions**: Guaranteed that all power values (kW) are multiplied by time step duration ($\Delta t = 1.0\text{ h}$) to yield energy in kWh before tariff and cost multiplication.
3. **Throughput-Based Degradation**: Battery degradation is evaluated strictly as $c_{deg} \times |P_{battery}(t)| \Delta t$ (\$0.018/kWh throughput).
4. **Carbon Abatement Modeling**: Carbon tax is assessed strictly on net utility grid imports:
   $$C_{CO2}(t) = \kappa_{CO2} \times \gamma_{emission} \times \max(0, P_{grid}(t)) \Delta t$$
   ($0.52\text{ kg CO}_2/\text{kWh}$ at $\$0.030/\text{kg CO}_2 = \$0.0156/\text{kWh}$).

### Test Performed
Executed `test_objective_function_components` in `tests/test_gridbalance_suite.py`.

### Test Result
**PASSED**. `operating_cost + total_penalty == fitness` verified to machine precision ($10^{-12}$). Pure operating costs and penalty terms are exported into separate CSV columns.

---

## 5. Standardized Renewable Energy Metrics

### Original Problem Description
The previous renewable utilization metric computed $\sum (P_{solar} + P_{wind}) / \sum P_{load} \times 100$. This formulation conflated renewable availability with load penetration, could exceed 100% during periods of high generation, and failed to account for battery charging/discharging energy paths.

### Root Cause
A single ambiguous "utilization" ratio was used without distinguishing resource absorption from grid dependency and curtailment.

### Files Modified
- `src/objective_function.py`
- `src/evaluation.py`
- `src/visualization.py`
- `dashboard/app.py`
- `tests/test_gridbalance_suite.py`

### Specific Correction Implemented
Implemented four standardized, non-overlapping renewable energy metrics:

1. **Metric A: Renewable Energy Utilization (%)**:
   $$\text{RE Utilization} = \frac{\sum_{t=1}^T \left( P_{solar, disp}(t) + P_{wind, disp}(t) \right) \Delta t}{\sum_{t=1}^T \left( P_{solar, avail}(t) + P_{wind, avail}(t) \right) \Delta t} \times 100$$
   *Measures the proportion of available clean natural resource successfully captured.*

2. **Metric B: Renewable Share of Served Demand (%)**:
   $$\text{RE Share} = \frac{\sum_{t=1}^T \min\left( P_{load}(t), P_{solar, disp}(t) + P_{wind, disp}(t) \right) \Delta t}{\sum_{t=1}^T P_{load}(t) \Delta t} \times 100$$
   *Measures the fraction of customer load directly satisfied by instantaneous clean renewables.*

3. **Metric C: Utility Grid Dependency (%)**:
   $$\text{Grid Dependency} = \frac{\sum_{t=1}^T \max\left(0, P_{grid}(t)\right) \Delta t}{\sum_{t=1}^T P_{load}(t) \Delta t} \times 100$$
   *Measures reliance on external fossil-dominated grid imports.*

4. **Metric D: Renewable Energy Curtailment (%)**:
   $$\text{RE Curtailment} = \frac{\sum_{t=1}^T P_{curt}(t) \Delta t}{\sum_{t=1}^T \left( P_{solar, avail}(t) + P_{wind, avail}(t) \right) \Delta t} \times 100$$
   *Measures clean energy wasted due to system limits. By identity: $\text{Metric A} + \text{Metric D} \equiv 100.0\%$.*

### Battery Discharge Origin Tracking
Battery discharge is not counted as newly generated renewable energy to prevent double counting. Energy stored in the BESS is accounted for at the time of generation.

### Test Performed
Executed `test_renewable_utilization_metric` and `test_curtailment_metric` in `tests/test_gridbalance_suite.py`.

### Test Result
**PASSED**. Metric A + Metric D equals $100.00\%$ exactly across all test cases.

---

## 6. Fair Algorithm Comparison and Statistical Verification

### Original Problem Description
Previously, algorithm comparisons ranked solutions on raw fitness without isolating penalty terms, lacked hypothesis testing, and did not guarantee identical evaluation conditions across multiple random seeds.

### Root Cause
`experiments/compare_algorithms.py` and `src/evaluation.py` lacked statistical hypothesis tests and ranked candidates on combined fitness rather than pure feasible operating cost.

### Files Modified
- `experiments/compare_algorithms.py`
- `src/evaluation.py`
- `src/pso.py`
- `src/gwo.py`
- `src/hybrid_gwo_pso.py`
- `src/ga.py`

### Specific Correction Implemented
1. **Rigorous Experimental Parity**:
   - Identical Scenario: Day 15 (July 15) from authentic DDRE-33 data.
   - Identical Search Space: $D = 72$ decision variables ($24\text{ solar} + 24\text{ wind} + 24\text{ battery}$).
   - Identical Population Size: $N = 30$ agents.
   - Identical Iteration Budget: $K = 100$ generations ($3,000$ function evaluations per run).
   - Identical 10 Random Seeds: `[42, 101, 203, 314, 425, 536, 647, 758, 869, 970]`.
2. **Deb's Feasibility Comparison Rules**:
   - Between two feasible solutions: select the one with lower operating cost.
   - Between a feasible and infeasible solution: select the feasible solution.
   - Between two infeasible solutions: select the one with smaller constraint violation.
3. **Statistical Hypothesis Testing**:
   - Computed mean, median, standard deviation, interquartile range (IQR), and best/worst costs across all 10 seeds.
   - Executed **Welch's Two-Sample t-Test** (parametric) to test for differences in mean operating cost.
   - Executed **Mann-Whitney U Rank-Sum Test** (non-parametric) to test distribution stochastics.
4. **Transparent Ranking**:
   - All algorithms ranked strictly on pure feasible operating cost ($C_{oper}$).
   - Feasibility rate, unserved load, and terminal SOC error are reported explicitly.

---

## 7. Refined Hybrid GWO-PSO Algorithm Architecture

### Original Problem Description
The initial hybrid implementation was a basic linear combination of wolf position and particle position without proper velocity bounds, inertia decay, or Deb's constraint-domination logic.

### Root Cause
`src/hybrid_gwo_pso.py` lacked adaptive time-varying blending parameters and did not properly maintain the pack hierarchy when encountering infeasible solutions.

### Files Modified
- `src/hybrid_gwo_pso.py`
- `tests/test_gridbalance_suite.py`

### Specific Correction Implemented
1. **GWO Multi-Leader Hunting Vector**:
   Candidate wolves encircle prey under the guidance of the three fittest wolves:
   $$\vec{X}_{1} = \vec{X}_{\alpha} - \vec{A}_1 \odot |\vec{C}_1 \odot \vec{X}_{\alpha} - \vec{X}_i|$$
   $$\vec{X}_{2} = \vec{X}_{\beta} - \vec{A}_2 \odot |\vec{C}_2 \odot \vec{X}_{\beta} - \vec{X}_i|$$
   $$\vec{X}_{3} = \vec{X}_{\delta} - \vec{A}_3 \odot |\vec{C}_3 \odot \vec{X}_{\delta} - \vec{X}_i|$$
   $$\vec{X}_{GWO, i} = \frac{\vec{X}_1 + \vec{X}_2 + \vec{X}_3}{3}$$
2. **PSO Velocity Update with Dual Guidance**:
   $$\vec{V}_i(k+1) = w(k) \vec{V}_i(k) + c_1 \vec{r}_1 \odot (\vec{P}_{best, i} - \vec{X}_i) + c_2 \vec{r}_2 \odot (\vec{X}_{GWO, i} - \vec{X}_i)$$
   where inertia weight decays linearly: $w(k) = 0.90 - 0.50 \times (k/K)$.
3. **Adaptive Time-Varying Exploration-Exploitation Blend**:
   $$\vec{X}_i(k+1) = \lambda(k) \vec{X}_{GWO, i} + (1 - \lambda(k)) \left( \vec{X}_i(k) + \vec{V}_i(k+1) \right)$$
   where $\lambda(k)$ linearly decreases from $0.80 \to 0.20$.
4. **Deb's Rules for Pack Hierarchy & Personal Best Updates**: Feasibility is checked before updating $\vec{P}_{best, i}$, $\vec{X}_{\alpha}$, $\vec{X}_{\beta}$, and $\vec{X}_{\delta}$.

### Test Performed
Executed `test_hybrid_gwo_pso_optimization` and `test_seed_reproducibility` in `tests/test_gridbalance_suite.py`.

### Test Result
**PASSED**. Identical random seeds produce bitwise identical results. 100% feasibility achieved.

---

## 8. Dashboard and Interactive Visualizations

### Original Problem Description
The Streamlit dashboard lacked visibility into individual constraint violations, did not distinguish pure operating cost from penalties, and displayed the outdated renewable utilization formula.

### Root Cause
`dashboard/app.py` and `src/visualization.py` had not incorporated the new constraint metrics and cost breakdown.

### Files Modified
- `dashboard/app.py`
- `src/visualization.py`

### Specific Correction Implemented
1. **Feasibility Alert Banner**: Real-time visual status banner displaying either:
   - Green Alert: "FEASIBLE SOLUTION — All microgrid operational and physical constraints satisfied."
   - Red Alert: Detailed table of specific constraint violations (terminal SOC, unserved load, bounds).
2. **Separate Cost & Penalty KPIs**: Added distinct metric cards for Pure Operating Cost (\$), Constraint Penalties (\$), Terminal SOC Error, Unserved Load (kWh), and Excess Generation (kWh).
3. **Standardized Metrics Dashboard**: Prominently displayed Metrics A, B, C, and D with interactive tooltips and stacked energy charts.
4. **Enhanced Visualizations**:
   - Plot 8: Pure Operating Cost boxplot across seeds.
   - Plot 9: Standardized 4-metric renewable comparison.
   - Plot 10: Battery SOC trajectory with initial and terminal equality reference lines.

---

## Verification Test Matrix

| Verification ID | Test Description | Target Module | Pytest Function | Result |
| :---: | :--- | :--- | :--- | :---: |
| **V-01** | Raw DDRE-33 CSV files exist and are non-empty | `data_loader.py` | `test_dataset_files_exist` | **PASS** |
| **V-02** | Zero missing values, zero negatives, valid p.u. | `data_preprocessing.py` | `test_preprocessing_audit` | **PASS** |
| **V-03** | Battery terminal SOC equals initial SOC ($\le 0.01$) | `energy_model.py` | `test_battery_terminal_soc` | **PASS** |
| **V-04** | Discrete BESS equations conserve energy & efficiencies | `energy_model.py` | `test_battery_energy_conservation`| **PASS** |
| **V-05** | Battery charging limits strictly bounded ($\le P_{ch, max}$) | `energy_model.py` | `test_battery_charging_limits` | **PASS** |
| **V-06** | Battery discharge limits strictly bounded ($\ge SOC_{min}$) | `energy_model.py` | `test_battery_discharging_limits`| **PASS** |
| **V-07** | Solar dispatch bounded by instantaneous availability | `constraints.py` | `test_solar_generation_limits` | **PASS** |
| **V-08** | Wind dispatch bounded by instantaneous availability | `constraints.py` | `test_wind_generation_limits` | **PASS** |
| **V-09** | Grid import/export capped; power balance identity holds | `energy_model.py` | `test_grid_limits_and_power_balance`| **PASS** |
| **V-10** | Standardized RE Utilization Metric A calculated accurately | `objective_function.py` | `test_renewable_utilization_metric`| **PASS** |
| **V-11** | Metric D (Curtailment) satisfies Metric A + D == 100% | `objective_function.py` | `test_curtailment_metric` | **PASS** |
| **V-12** | Pure operating cost separated from constraint penalties | `objective_function.py` | `test_objective_function_components`| **PASS** |
| **V-13** | Standalone PSO executes and achieves feasible dispatch | `pso.py` | `test_pso_optimization` | **PASS** |
| **V-14** | Standalone GWO executes and achieves feasible dispatch | `gwo.py` | `test_gwo_optimization` | **PASS** |
| **V-15** | Hybrid GWO-PSO executes and achieves feasible dispatch | `hybrid_gwo_pso.py` | `test_hybrid_gwo_pso_optimization`| **PASS** |
| **V-16** | Deterministic seed reproducibility verified bitwise | `hybrid_gwo_pso.py` | `test_seed_reproducibility` | **PASS** |
| **V-17** | Benchmark metrics CSV files exported properly | `evaluation.py` | `test_results_exported` | **PASS** |

---

## Conclusion & System Status

All 8 problem areas have been addressed directly in the codebase. The GridBalance framework now operates with complete mathematical rigor, enforces true cyclic battery energy conservation, guarantees physical power balance without silent clipping, evaluates all constraints independently, reports pure operating costs separated from penalties, tracks standardized renewable energy metrics without double counting, and benchmarks all algorithms fairly under identical conditions.
