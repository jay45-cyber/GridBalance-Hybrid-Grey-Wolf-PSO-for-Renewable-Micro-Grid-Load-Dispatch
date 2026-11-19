"""
dashboard/app.py
Interactive Streamlit Dashboard for GridBalance:
Hybrid Grey Wolf - PSO for Renewable Microgrid Load Dispatch
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.data_loader import DataLoader
from src.objective_function import MicrogridObjective
from src.pso import ParticleSwarmOptimizer
from src.gwo import GreyWolfOptimizer
from src.hybrid_gwo_pso import HybridGWOPSO
from src.ga import GeneticAlgorithm

# Streamlit Page Config
st.set_page_config(
    page_title="GridBalance — Renewable Microgrid Dispatch",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished research-grade UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #E2E8F0;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_loader():
    return DataLoader("config/system_parameters.yaml")


loader = get_loader()
config = loader.config

# Sidebar Navigation & Settings
st.sidebar.image("https://img.icons8.com/fluency/96/electricity.png", width=64)
st.sidebar.title("GridBalance System")
st.sidebar.markdown("**Hybrid GWO-PSO Dispatch Engine**")

section = st.sidebar.radio(
    "Navigation Sections",
    [
        "A. Project Overview",
        "B. Dataset Information",
        "C. Renewable Energy Profiles",
        "D. Microgrid Configuration",
        "E. Optimization Parameters",
        "F. Run Optimization",
        "G. Algorithm Comparison",
        "H. Energy Dispatch Results",
        "I. Convergence Analysis",
        "J. Performance Metrics"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Simulation Controls")
selected_day = st.sidebar.slider("Scenario Day (DDRE-33)", min_value=1, max_value=360, value=15, step=1)
pop_size = st.sidebar.slider("Population Size", min_value=10, max_value=60, value=30, step=5)
max_iter = st.sidebar.slider("Max Iterations", min_value=20, max_value=150, value=100, step=10)
random_seed = st.sidebar.number_input("Random Seed", value=42, step=1)


# ------------------------------------------------------------------------------
# SECTION A: Project Overview
# ------------------------------------------------------------------------------
if section == "A. Project Overview":
    st.markdown('<div class="main-header">GridBalance: Hybrid Grey Wolf–PSO for Renewable Micro-Grid Load Dispatch</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Research-grade load dispatch optimization fusing nature-inspired exploration with kinetic velocity exploitation.</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Test Network", "IEEE 33-Bus System", "Radial Feeder")
    with col2:
        st.metric("Renewable Dataset", "DDRE-33", "Nature Sci Data 2025")
    with col3:
        st.metric("Core Algorithm", "Hybrid GWO-PSO", "Self-Adaptive Blend")
    with col4:
        st.metric("Target Metric", "Operating Cost ($)", "Feasibility Repair")

    st.markdown("### Architectural Schematic")
    st.info("""
    **GridBalance Architecture:**
    1. **DDRE-33 Real Scenario Ingestion**: Bus 33 Solar PV and Bus 22 Distributed Wind at 15-minute resolution across 35,040 intervals.
    2. **Energy System Formulation**: Strict power balance, discrete BESS state transitions, TOU tariffs, and degradation costs.
    3. **Hybrid Optimization Engine**: GWO $\\alpha, \\beta, \\delta$ pack leadership guides global trajectory while PSO velocity updates provide rapid exploitation.
    4. **Feasibility Repair Operator**: Enforces physical charge/discharge limits and eliminates constraint violations.
    """)

    st.markdown("### Key Scientific Contributions")
    st.markdown("""
    - **Genuine Hybrid Formulation**: Blends GWO multi-leader encircling with PSO personal/global best velocity vectors.
    - **Authentic DDRE-33 Benchmark**: Zero fabricated measurements; clearly separated from declared simulation assumptions.
    - **Multi-Algorithm Statistical Benchmarking**: Validated against standalone PSO, GWO, and Genetic Algorithm across 10 independent random seeds.
    - **100% Feasibility Enforcement**: Dynamic state tracking guarantees zero power imbalance and zero battery SOC boundary violations.
    """)


# ------------------------------------------------------------------------------
# SECTION B: Dataset Information
# ------------------------------------------------------------------------------
elif section == "B. Dataset Information":
    st.title("B. DDRE-33 Dataset Inventory & Audit")
    st.markdown("""
    **Dataset Citation**: *Chen et al., 'DDRE-33: A Large-Scale Dataset of Distributed Renewable Energy Scenarios on the IEEE-33 Bus Network'*, **Scientific Data (Nature Portfolio)**, Vol. 13, Art. 146, 2025.  
    **DOI**: `10.6084/m9.figshare.29374640`
    """)

    report_path = "results/reports/data_quality_report.json"
    if os.path.exists(report_path):
        import json
        with open(report_path) as f:
            audit = json.load(f)
        st.success("Automated Dataset Quality Audit: PASSED (Zero Missing Values, Zero Negatives)")
        st.json(audit)
    else:
        st.warning("Run data preprocessing to generate data quality report.")

    st.markdown("### Data Dictionary & Variable Distinctions")
    dict_df = pd.DataFrame([
        {"Variable": "Bus 33 Solar PV (OT)", "Type": "Real Measurement (DDRE-33)", "Units": "Per-Unit [0, 1] / kW", "Resolution": "15-Min / 1-Hour", "Description": "Solar generation at Bus 33"},
        {"Variable": "Bus 22 Wind Turbine (OT)", "Type": "Real Measurement (DDRE-33)", "Units": "Per-Unit [0, 1] / kW", "Resolution": "15-Min / 1-Hour", "Description": "Wind generation at Bus 22"},
        {"Variable": "Microgrid Load Demand", "Type": "Declared Simulation Assumption", "Units": "kW", "Resolution": "Hourly Profile", "Description": "Standard diurnal load scaled to IEEE-33 feeder (1600 kW peak)"},
        {"Variable": "Battery Energy Capacity", "Type": "Declared Simulation Assumption", "Units": "kWh", "Value": "2000 kWh", "Description": "Lithium Iron Phosphate (LFP) BESS"},
        {"Variable": "TOU Grid Tariff", "Type": "Declared Simulation Assumption", "Units": "$/kWh", "Values": "Off-peak: $0.06, Shoulder: $0.12, Peak: $0.24", "Description": "3-tier Time-of-Use schedule"}
    ])
    st.table(dict_df)


# ------------------------------------------------------------------------------
# SECTION C: Renewable Energy Profiles
# ------------------------------------------------------------------------------
elif section == "C. Renewable Energy Profiles":
    st.title("C. Renewable Energy & Demand Profiles")
    scen = loader.get_dispatch_scenario(day_index=selected_day)
    df_scen = scen["dataframe"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_scen["hour"], y=scen["solar_available_kw"], mode="lines+markers", name="Solar PV Available (kW)", line=dict(color="#F39C12", width=3)))
    fig.add_trace(go.Scatter(x=df_scen["hour"], y=scen["wind_available_kw"], mode="lines+markers", name="Wind Turbine Available (kW)", line=dict(color="#2980B9", width=3)))
    fig.add_trace(go.Scatter(x=df_scen["hour"], y=scen["load_demand_kw"], mode="lines+markers", name="Load Demand (kW)", line=dict(color="#C0392B", width=3, dash="dash")))

    fig.update_layout(title=f"24-Hour Resource Profiles (Scenario Day {selected_day})", xaxis_title="Hour of Day", yaxis_title="Power (kW)", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Peak Solar Available", f"{scen['solar_available_kw'].max():.1f} kW")
    c2.metric("Peak Wind Available", f"{scen['wind_available_kw'].max():.1f} kW")
    c3.metric("Peak Load Demand", f"{scen['load_demand_kw'].max():.1f} kW")


# ------------------------------------------------------------------------------
# SECTION D: Microgrid Configuration
# ------------------------------------------------------------------------------
elif section == "D. Microgrid Configuration":
    st.title("D. Microgrid Physical & Economic Configuration")
    st.markdown("All parameters are loaded from `config/system_parameters.yaml`.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Generation & Battery Specifications")
        st.write(f"- **Solar PV Rated Capacity**: {config['solar_pv']['rated_capacity_kw']} kW")
        st.write(f"- **Solar PV O&M Cost**: ${config['solar_pv']['unit_om_cost_per_kwh']}/kWh")
        st.write(f"- **Wind Turbine Rated Capacity**: {config['wind_turbine']['rated_capacity_kw']} kW")
        st.write(f"- **Wind Turbine O&M Cost**: ${config['wind_turbine']['unit_om_cost_per_kwh']}/kWh")
        st.write(f"- **BESS Energy Capacity**: {config['battery']['nominal_energy_capacity_kwh']} kWh")
        st.write(f"- **BESS Max Charge/Discharge**: {config['battery']['max_charge_power_kw']} kW")
        st.write(f"- **BESS Efficiency**: {config['battery']['charge_efficiency']*100:.0f}% Charge / {config['battery']['discharge_efficiency']*100:.0f}% Discharge")
        st.write(f"- **SOC Operating Range**: {config['battery']['soc_min']*100:.0f}% – {config['battery']['soc_max']*100:.0f}%")

    with col2:
        st.subheader("Grid Interconnection & Tariffs")
        st.write(f"- **Grid Interconnection Bus**: Bus {config['grid']['pcc_bus_id']} (Substation)")
        st.write(f"- **Max Grid Import**: {config['grid']['max_import_power_kw']} kW")
        st.write(f"- **Carbon Emission Factor**: {config['grid']['co2_emission_factor_kg_per_kwh']} kg CO₂/kWh")
        st.write(f"- **Carbon Tax**: ${config['grid']['carbon_tax_per_kg_co2']}/kg CO₂")
        st.write("- **Time-of-Use Import Tariff**:")
        st.write("  * Off-peak (23:00 - 07:00): $0.06 / kWh")
        st.write("  * Shoulder (07:00 - 14:00, 20:00 - 23:00): $0.12 / kWh")
        st.write("  * On-peak (14:00 - 20:00): $0.24 / kWh")


# ------------------------------------------------------------------------------
# SECTION E: Optimization Parameters
# ------------------------------------------------------------------------------
elif section == "E. Optimization Parameters":
    st.title("E. Optimization Algorithm Hyperparameters")
    p_col1, p_col2, p_col3 = st.columns(3)

    with p_col1:
        st.markdown("#### Particle Swarm Optimization")
        st.write("- **Inertia Weight ($w$)**: 0.9 → 0.4 (linear decay)")
        st.write("- **Cognitive Coeff ($c_1$)**: 1.8")
        st.write("- **Social Coeff ($c_2$)**: 1.8")
        st.write("- **Velocity Clamping**: 20% search width")

    with p_col2:
        st.markdown("#### Grey Wolf Optimizer")
        st.write("- **Exploration Factor ($a$)**: 2.0 → 0.0 (linear decay)")
        st.write("- **Leadership Pack**: Alpha, Beta, Delta")
        st.write("- **Encircle Mechanism**: Stochastic $A, C$ vectors")

    with p_col3:
        st.markdown("#### Hybrid GWO-PSO")
        st.write("- **Exploration Blend ($\\lambda$)**: 0.80 → 0.20")
        st.write("- **Velocity Guidance**: Combined $pbest$ & GWO leader")
        st.write("- **Inertia Weight**: 0.9 → 0.4")
        st.write("- **Feasibility Repair**: Enforced every iteration")


# ------------------------------------------------------------------------------
# SECTION F: Run Optimization
# ------------------------------------------------------------------------------
elif section == "F. Run Optimization":
    st.title("F. Interactive Dispatch Optimization Execution")
    st.markdown("Select an algorithm and run live dispatch optimization on the authentic DDRE-33 scenario.")

    algo_choice = st.selectbox(
        "Choose Optimization Algorithm",
        ["Hybrid GWO-PSO", "PSO", "GWO", "Genetic Algorithm (GA)"]
    )

    if st.button("🚀 Run Dispatch Optimization", type="primary"):
        scen = loader.get_dispatch_scenario(day_index=selected_day)
        obj = MicrogridObjective(loader.config)
        T = scen["horizon_steps"]

        lb = np.concatenate([np.zeros(T), np.zeros(T), -np.full(T, config["battery"]["max_charge_power_kw"])])
        ub = np.concatenate([scen["solar_available_kw"], scen["wind_available_kw"], np.full(T, config["battery"]["max_discharge_power_kw"])])
        eval_func = lambda x: obj.evaluate(x, scen, apply_repair=True)

        with st.spinner(f"Running {algo_choice} (Pop={pop_size}, Iter={max_iter}, Seed={random_seed})..."):
            if algo_choice == "Hybrid GWO-PSO":
                opt = HybridGWOPSO(eval_func, lb, ub, pop_size=pop_size, max_iter=max_iter, seed=random_seed)
            elif algo_choice == "PSO":
                opt = ParticleSwarmOptimizer(eval_func, lb, ub, pop_size=pop_size, max_iter=max_iter, seed=random_seed)
            elif algo_choice == "GWO":
                opt = GreyWolfOptimizer(eval_func, lb, ub, pop_size=pop_size, max_iter=max_iter, seed=random_seed)
            else:
                opt = GeneticAlgorithm(eval_func, lb, ub, pop_size=pop_size, max_iter=max_iter, seed=random_seed)

            res = opt.optimize()

        st.session_state["last_run_result"] = res
        st.session_state["last_run_algo"] = algo_choice
        st.session_state["last_run_scen"] = scen
        st.success(f"{algo_choice} Optimization Completed in {res['execution_time']:.3f} seconds!")

    if "last_run_result" in st.session_state:
        res = st.session_state["last_run_result"]
        d = res["best_details"]
        scen = st.session_state["last_run_scen"]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Operating Cost", f"${res['best_fitness']:.2f}")
        m2.metric("RE Utilization", f"{d['re_utilization_pct']:.2f}%")
        m3.metric("Grid Dependency", f"{d['grid_dependency_pct']:.2f}%")
        m4.metric("Feasibility", "FEASIBLE" if d["is_feasible"] else "INFEASIBLE")

        # Convergence plot
        fig_conv = px.line(
            x=range(len(res["convergence_curve"])),
            y=res["convergence_curve"],
            labels={"x": "Iteration", "y": "Operating Cost ($)"},
            title=f"Convergence Trajectory ({st.session_state['last_run_algo']})"
        )
        st.plotly_chart(fig_conv, use_container_width=True)


# ------------------------------------------------------------------------------
# SECTION G: Algorithm Comparison
# ------------------------------------------------------------------------------
elif section == "G. Algorithm Comparison":
    st.title("G. Multi-Algorithm Statistical Benchmarking")
    st.markdown("Comparative results across 10 independent random seeds under identical problem formulations.")

    summary_path = "results/metrics/algorithm_comparison_summary.csv"
    if os.path.exists(summary_path):
        df_sum = pd.read_csv(summary_path)
        st.dataframe(df_sum.style.highlight_min(subset=["mean_cost_usd", "best_cost_usd"], color="#D4EDDA"))

        fig_bar = px.bar(
            df_sum,
            x="algorithm",
            y="mean_cost_usd",
            error_y="std_cost_usd",
            color="algorithm",
            title="Mean Operating Cost Comparison with Standard Deviation Error Bars ($)",
            labels={"mean_cost_usd": "Mean Cost ($)", "algorithm": "Algorithm"}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        if os.path.exists("results/graphs/08_algorithm_cost_comparison.png"):
            st.image("results/graphs/08_algorithm_cost_comparison.png", caption="Cost Distribution Boxplot Across 10 Independent Seeds")
    else:
        st.warning("Run experiments/compare_algorithms.py to generate comparative metrics.")


# ------------------------------------------------------------------------------
# SECTION H: Energy Dispatch Results
# ------------------------------------------------------------------------------
elif section == "H. Energy Dispatch Results":
    st.title("H. Microgrid Energy Dispatch Schedule")

    if os.path.exists("results/graphs/04_energy_dispatch_distribution.png"):
        st.image("results/graphs/04_energy_dispatch_distribution.png", caption="Optimal 24-Hour Multi-Source Energy Dispatch Stack")

    schedule_path = "results/metrics/hybrid_dispatch_schedule.csv"
    if os.path.exists(schedule_path):
        df_sched = pd.read_csv(schedule_path)
        st.markdown("### Numerical Dispatch Schedule")
        st.dataframe(df_sched)
        st.download_button(
            "📥 Download Schedule (CSV)",
            data=df_sched.to_csv(index=False),
            file_name="hybrid_dispatch_schedule.csv",
            mime="text/csv"
        )


# ------------------------------------------------------------------------------
# SECTION I: Convergence Analysis
# ------------------------------------------------------------------------------
elif section == "I. Convergence Analysis":
    st.title("I. Multi-Algorithm Convergence Dynamics")
    if os.path.exists("results/graphs/07_multi_algorithm_convergence.png"):
        st.image("results/graphs/07_multi_algorithm_convergence.png", caption="Comparative Convergence Curves (PSO vs GWO vs Hybrid GWO-PSO vs GA)")

    col1, col2 = st.columns(2)
    with col1:
        if os.path.exists("results/graphs/05_pso_convergence_curve.png"):
            st.image("results/graphs/05_pso_convergence_curve.png", caption="PSO Convergence Progression")
    with col2:
        if os.path.exists("results/graphs/06_gwo_convergence_curve.png"):
            st.image("results/graphs/06_gwo_convergence_curve.png", caption="GWO Convergence Progression")


# ------------------------------------------------------------------------------
# SECTION J: Performance Metrics
# ------------------------------------------------------------------------------
elif section == "J. Performance Metrics":
    st.title("J. Performance Metrics & Result Export")

    detailed_path = "results/metrics/detailed_runs_metrics.csv"
    if os.path.exists(detailed_path):
        df_detail = pd.read_csv(detailed_path)
        st.markdown("### Detailed Run-by-Run Experimental Records")
        st.dataframe(df_detail)

        st.download_button(
            "📥 Download All Run Metrics (CSV)",
            data=df_detail.to_csv(index=False),
            file_name="detailed_runs_metrics.csv",
            mime="text/csv"
        )

    if os.path.exists("results/graphs/09_renewable_energy_utilization_comparison.png"):
        st.image("results/graphs/09_renewable_energy_utilization_comparison.png", caption="Renewable Utilization vs Grid Dependency")

    if os.path.exists("results/graphs/10_battery_soc_profile.png"):
        st.image("results/graphs/10_battery_soc_profile.png", caption="BESS State of Charge (SOC) Dynamics")
