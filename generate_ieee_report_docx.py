"""
generate_ieee_report_docx.py
Generates a comprehensive IEEE-formatted Technical Research Report (.docx)
for the GridBalance project matching the author block format and IEEE specifications.
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def create_ieee_report_docx():
    doc = docx.Document()

    # IEEE Standard Page Margins (0.75 in = 54 pt)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.05
    normal_style.paragraph_format.space_after = Pt(4)

    # =========================================================================
    # 1. TITLE & SUBTITLE
    # =========================================================================
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run("GridBalance — Hybrid Grey Wolf–PSO for\nRenewable Micro-Grid Load Dispatch")
    run_title.font.name = 'Times New Roman'
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0, 0, 0)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(14)
    r_sub = p_sub.add_run("Comprehensive Research & Technical Project Report")
    r_sub.font.name = 'Times New Roman'
    r_sub.font.size = Pt(13)
    r_sub.font.bold = True
    r_sub.font.color.rgb = RGBColor(27, 54, 93)  # Navy

    # =========================================================================
    # 2. AUTHOR BLOCK (Exact Layout)
    # =========================================================================
    table_authors = doc.add_table(rows=1, cols=2)
    table_authors.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_authors.autofit = False

    for cell in table_authors.rows[0].cells:
        cell.width = Inches(3.4)

    # Author 1: Jay Kushwaha
    cell_a1 = table_authors.cell(0, 0)
    p_a1 = cell_a1.paragraphs[0]
    p_a1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_a1.paragraph_format.space_after = Pt(2)
    r = p_a1.add_run("Jay Kushwaha\n")
    r.font.bold = True
    r.font.size = Pt(11)
    r2 = p_a1.add_run("Department of Artificial Intelligence and Machine Learning\nLovely Professional University, Phagwara, Punjab\n")
    r2.font.italic = True
    r2.font.size = Pt(9.5)
    r3 = p_a1.add_run("Email: Jaykushwaha8994@gmail.com")
    r3.font.size = Pt(9.5)

    # Author 2: Kriti Nishad
    cell_a2 = table_authors.cell(0, 1)
    p_a2 = cell_a2.paragraphs[0]
    p_a2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_a2.paragraph_format.space_after = Pt(2)
    r = p_a2.add_run("Kriti Nishad\n")
    r.font.bold = True
    r.font.size = Pt(11)
    r2 = p_a2.add_run("Department of Artificial Intelligence and Machine Learning\nLovely Professional University, Phagwara, Punjab\n")
    r2.font.italic = True
    r2.font.size = Pt(9.5)
    r3 = p_a2.add_run("Email: kritinishad20@gmail.com")
    r3.font.size = Pt(9.5)

    # Author 3: Dr (Centered Guide Block)
    p_guide = doc.add_paragraph()
    p_guide.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_guide.paragraph_format.space_before = Pt(10)
    p_guide.paragraph_format.space_after = Pt(16)
    rg1 = p_guide.add_run("Dr\n")
    rg1.font.bold = True
    rg1.font.size = Pt(11)
    rg2 = p_guide.add_run("Department of Artificial Intelligence and Machine Learning\nAssociate Professor in School of Computing and AI\nLovely Professional University, Phagwara, Punjab")
    rg2.font.italic = True
    rg2.font.size = Pt(9.5)

    # Subtle horizontal line
    p_hr = doc.add_paragraph()
    p_hr.paragraph_format.space_after = Pt(10)
    p_hr_border = parse_xml(r'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:bottom w:val="single" w:sz="6" w:space="1" w:color="CCCCCC"/></w:pBdr>')
    p_hr._p.get_or_add_pPr().append(p_hr_border)

    # =========================================================================
    # 3. ABSTRACT & INDEX TERMS
    # =========================================================================
    p_abs = doc.add_paragraph()
    p_abs.paragraph_format.space_after = Pt(4)
    p_abs.paragraph_format.line_spacing = 1.05
    r_absh = p_abs.add_run("Abstract— ")
    r_absh.font.bold = True
    r_absh.font.size = Pt(9.5)

    abs_text = (
        "Optimal load dispatch in modern renewable microgrids requires coordinated scheduling of intermittent "
        "distributed generation (DG) assets, electrochemical energy storage systems, and utility grid interconnections "
        "under dynamic time-of-use (TOU) tariffs. This technical report presents the comprehensive mathematical formulation, "
        "algorithmic architecture, software implementation, and empirical verification of GridBalance—a research-grade "
        "microgrid economic dispatch optimization framework. Authentic solar photovoltaic (PV) and distributed wind power time-series "
        "from the Nature Scientific Data DDRE-33 dataset (mapped to the standard IEEE 33-bus radial distribution network) are integrated "
        "with a 2.0 MWh Lithium-Iron-Phosphate (LFP) Battery Energy Storage System (BESS). To resolve the non-convex dispatch problem, "
        "we benchmark Particle Swarm Optimization (PSO), Grey Wolf Optimizer (GWO), a Genetic Algorithm (GA), and an adaptive "
        "Hybrid GWO–PSO engine across 10 random seeds (40 total benchmark runs, N=30, K=100). The model incorporates a cyclic terminal "
        "battery State of Charge (SOC) constraint (|SOC(24) - SOC(0)| ≤ 1.0%) to prevent artificial energy depletion, and an explicit power "
        "balance formulation tracking unserved load and excess generation without silent clipping. Results demonstrate that all 40 runs achieve "
        "100.0% physical feasibility with zero unserved energy and machine-precision power balance (|residual| ≤ 2.27 × 10^-13 kW). "
        "Hybrid GWO–PSO achieves superior stability (standard deviation $45.09 vs $82.47 for PSO) and statistically significant cost reduction "
        "over standalone GWO (Welch's t = -3.505, p = 0.0031; Mann-Whitney U = 9.0, p = 0.0022), providing an average daily operational saving of $97.68."
    )
    r_abst = p_abs.add_run(abs_text)
    r_abst.font.size = Pt(9.5)

    p_idx = doc.add_paragraph()
    p_idx.paragraph_format.space_after = Pt(12)
    r_idxh = p_idx.add_run("Index Terms— ")
    r_idxh.font.bold = True
    r_idxh.font.italic = True
    r_idxh.font.size = Pt(9.5)
    r_idxt = p_idx.add_run("Renewable Microgrid Dispatch, Hybrid Grey Wolf Optimization, Particle Swarm Optimization, Battery Energy Storage Conservation, DDRE-33 Dataset, Power Balance Identity, Metaheuristic Benchmarking, Statistical Significance Testing.")
    r_idxt.font.size = Pt(9.5)

    def add_heading_1(text):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(4)
        r = h.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(11)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0, 0, 0)
        return h

    def add_heading_2(text):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(9)
        h.paragraph_format.space_after = Pt(3)
        r = h.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(10.5)
        r.font.bold = True
        r.font.italic = True
        r.font.color.rgb = RGBColor(0, 0, 0)
        return h

    def add_body_p(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.05
        r = p.add_run(text)
        r.font.size = Pt(10)
        return p

    def add_equation_box(eq_text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(eq_text)
        r.font.name = 'Cambria Math'
        r.font.size = Pt(10)
        r.font.italic = True
        return p

    def add_code_block(code_text):
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        cell = table.cell(0, 0)
        cell.width = Inches(6.8)
        set_cell_background(cell, "F8F9FA")
        set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(code_text)
        r.font.name = 'Consolas'
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(33, 37, 41)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # =========================================================================
    # SECTION I: INTRODUCTION
    # =========================================================================
    add_heading_1("I. INTRODUCTION AND PROBLEM STATEMENT")
    add_body_p(
        "Integrating distributed energy resources (DERs)—predominantly solar photovoltaics (PV) and wind energy conversion systems (WECS)—into "
        "distribution networks offers substantial carbon abatement and operational cost reductions. However, their intermittent generation "
        "introduces steep ramping requirements and power balancing challenges. Battery Energy Storage Systems (BESS) provide temporal buffering, "
        "charging during low-tariff or high-renewable intervals and discharging during peak-tariff windows."
    )
    add_body_p(
        "Mathematically, the microgrid economic load dispatch problem is a non-linear, constrained optimization task. Conventional mathematical "
        "programming techniques (such as mixed-integer linear programming or sequential quadratic programming) often require linearizations that "
        "oversimplify non-linear battery degradation mechanisms, non-linear tariff schedules, or complex physical constraints. Metaheuristic "
        "algorithms have thus garnered widespread research interest."
    )
    add_body_p(
        "Nonetheless, standard Particle Swarm Optimization (PSO) frequently suffers from premature convergence in multi-dimensional dispatch landscapes, "
        "becoming trapped in sub-optimal local minima. Conversely, the Grey Wolf Optimizer (GWO) provides superior global exploration through its "
        "multi-leader social hierarchy but often exhibits slower convergence in the fine-tuning exploitation phase."
    )
    add_body_p(
        "Furthermore, a critical flaw identified across prior microgrid dispatch literature is the omission of cyclic battery state-of-charge (SOC) "
        "terminal constraints. An unconstrained optimizer will aggressively deplete initial battery energy (e.g., from 50% to 20%), reporting artificially "
        "low operational costs by consuming 'free' stored energy without accounting for terminal replenishment. Similarly, naive clipping of utility "
        "grid exchange creates hidden energy imbalances. This report details GridBalance, which resolves these mathematical and algorithmic vulnerabilities."
    )

    # =========================================================================
    # SECTION II: DATASET & SYSTEM ARCHITECTURE
    # =========================================================================
    add_heading_1("II. DDRE-33 DATASET AND SYSTEM ARCHITECTURE")
    add_heading_2("A. The DDRE-33 Empirical Dataset")
    add_body_p(
        "The project integrates empirical time-series data from the official DDRE-33 benchmark dataset published in Nature Scientific Data (2025) "
        "[DOI: 10.6084/m9.figshare.29374640]. The dataset maps high-resolution renewable generation onto the IEEE 33-bus radial distribution network:"
    )
    add_body_p(
        "• Node 33: Solar PV generation array with rated capacity of 1,200 kW.\n"
        "• Node 22: Distributed wind turbine facility with rated capacity of 1,000 kW.\n"
        "• Node 1: Point of Common Coupling (PCC) utility substation interconnection.\n"
        "• Temporal Resolution: 15-minute intervals across 35,040 observations (1 full annual cycle: July 1, 2022 to June 30, 2023), resampled to 8,760 hourly time-steps."
    )
    add_body_p(
        "An automated data quality audit confirmed 0 missing values (0.00%), 0 duplicate records, and valid per-unit bounds ([0.0, 0.8593] for Bus 33 Solar PV "
        "and [0.0, 1.0000] for Bus 22 Wind). Benchmark experiments were conducted on canonical Scenario Day 15 (July 15), representing peak summer solar conditions."
    )

    add_heading_2("B. Explicit Declaration of Simulation Assumptions")
    add_body_p(
        "In strict compliance with research transparency, simulation parameters not recorded in the DDRE-33 dataset are explicitly declared in Table I."
    )

    # Table I: System Parameters
    tbl_params = [
        ("Parameter Category", "Variable Name", "Declared Value", "Units"),
        ("Microgrid Load Demand", "Peak Active Demand (P_load,max)", "1,600.0", "kW"),
        ("", "Minimum Base Demand (P_load,min)", "656.0", "kW"),
        ("", "Daily Energy Demand", "26,140.0", "kWh/day"),
        ("Battery Storage (BESS)", "Nominal Energy Capacity (E_bat)", "2,000.0", "kWh (2 MWh)"),
        ("", "Maximum Charge Power (P_ch,max)", "600.0", "kW (0.3C rate)"),
        ("", "Maximum Discharge Power (P_dis,max)", "600.0", "kW (0.3C rate)"),
        ("", "One-way Charge Efficiency (η_ch)", "0.95 (95%)", "—"),
        ("", "One-way Discharge Efficiency (η_dis)", "0.95 (95%)", "—"),
        ("", "Initial State of Charge (SOC_init)", "0.50 (50%)", "—"),
        ("", "Permissible Bounds [SOC_min, SOC_max]", "[0.20, 0.90]", "—"),
        ("", "Terminal SOC Tolerance (ε_term)", "0.010 (1.0%)", "—"),
        ("", "Cell Degradation Coefficient (c_deg)", "0.018", "$/kWh"),
        ("Economic Tariffs & Carbon", "Solar PV O&M Cost (c_solar,om)", "0.010", "$/kWh"),
        ("", "Wind Turbine O&M Cost (c_wind,om)", "0.015", "$/kWh"),
        ("", "Renewable Curtailment Penalty (c_curt)", "0.050", "$/kWh"),
        ("", "TOU Off-Peak Rate (23:00–07:00)", "0.060", "$/kWh"),
        ("", "TOU Shoulder Rate (07:00–14:00, 20:00–23:00)", "0.120", "$/kWh"),
        ("", "TOU Peak Rate (14:00–20:00)", "0.240", "$/kWh"),
        ("", "Utility Export Credit Rate (c_export)", "0.040", "$/kWh"),
        ("", "Grid Emission Factor (γ_emission)", "0.52", "kg CO2/kWh"),
        ("", "Carbon Tax Rate (κ_CO2)", "0.030", "$/kg CO2"),
        ("Utility Interconnection", "Maximum Grid Import (P_grid,import,max)", "2,500.0", "kW"),
        ("", "Maximum Grid Export (P_grid,export,max)", "1,000.0", "kW")
    ]

    t1 = doc.add_table(rows=len(tbl_params), cols=4)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    t1.autofit = False
    col_w = [Inches(1.8), Inches(2.6), Inches(1.3), Inches(1.1)]

    for r_idx, row_data in enumerate(tbl_params):
        for c_idx, val in enumerate(row_data):
            cell = t1.cell(r_idx, c_idx)
            cell.width = col_w[c_idx]
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if r_idx == 0:
                set_cell_background(cell, "1B365D")
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                if r_idx % 2 == 1:
                    set_cell_background(cell, "F4F6F9")
                r.font.color.rgb = RGBColor(0, 0, 0)
                if c_idx >= 2:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    p_cap1 = doc.add_paragraph()
    p_cap1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap1.paragraph_format.space_before = Pt(3)
    p_cap1.paragraph_format.space_after = Pt(10)
    rc1 = p_cap1.add_run("TABLE I: DECLARED MICROGRID SYSTEM AND SIMULATION PARAMETERS")
    rc1.font.bold = True
    rc1.font.size = Pt(8.5)

    # =========================================================================
    # SECTION III: MATHEMATICAL FORMULATION
    # =========================================================================
    add_heading_1("III. RIGOROUS MATHEMATICAL FORMULATION")
    add_heading_2("A. Objective Function")
    add_body_p(
        "The optimization objective is the minimization of total daily operating cost C_total over the 24-hour horizon (T=24, Δt=1.0 h):"
    )
    add_equation_box("min C_total = ∑ [ C_solar(t) + C_wind(t) + C_battery(t) + C_grid(t) + C_curt(t) + C_emission(t) ] Δt    (1)")
    add_body_p("where the constituent cost components are formulated as:")
    add_equation_box("C_solar(t) = c_solar,om · P_solar(t),      C_wind(t) = c_wind,om · P_wind(t)    (2)")
    add_equation_box("C_battery(t) = c_deg · |P_battery(t)|    (3)")
    add_equation_box("C_grid(t) = c_tariff(t) · max(0, P_grid(t)) - c_export · max(0, -P_grid(t))    (4)")
    add_equation_box("C_curt(t) = c_curt · [ (P_solar,avail(t) - P_solar(t)) + (P_wind,avail(t) - P_wind(t)) ]    (5)")
    add_equation_box("C_emission(t) = κ_CO2 · γ_emission · max(0, P_grid(t))    (6)")

    add_heading_2("B. System Physical Constraints")
    add_body_p(
        "1) Power Balance Equality Identity: At every time step t, total generation, storage dispatch, and utility exchange must strictly balance load demand:"
    )
    add_equation_box("P_solar(t) + P_wind(t) + P_battery(t) + P_grid,import(t) - P_grid,export(t) + P_unserved(t) - P_excess(t) = P_load(t)    (7)")
    add_body_p(
        "where P_battery(t) > 0 indicates discharging and P_battery(t) < 0 indicates charging. Rather than clipping, residual imbalances are "
        "explicitly partitioned into unserved energy P_unserved(t) ≥ 0 and excess generation P_excess(t) ≥ 0 and heavily penalized."
    )
    add_body_p("2) Generation Bounds: Dispatch cannot exceed physical resource availability:")
    add_equation_box("0 ≤ P_solar(t) ≤ P_solar,avail(t),      0 ≤ P_wind(t) ≤ P_wind,avail(t),      ∀t    (8)")
    add_body_p("3) Substation Interconnection Limits: Grid import and export flows are governed by independent transformer ratings:")
    add_equation_box("0 ≤ P_grid,import(t) ≤ P_grid,import,max (2,500 kW),      0 ≤ P_grid,export(t) ≤ P_grid,export,max (1,000 kW)    (9)")
    add_body_p("4) Battery Dynamic SOC & Power Limits:")
    add_equation_box("SOC(t) = SOC(t-1) - [ P_battery(t) · Δt / E_bat ] · [ 1/η_dis  if P_battery ≥ 0;  η_ch  if P_battery < 0 ]    (10)")
    add_equation_box("SOC_min ≤ SOC(t) ≤ SOC_max (0.20 ≤ SOC(t) ≤ 0.90),      -P_ch,max ≤ P_battery(t) ≤ P_dis,max (±600 kW)    (11)")
    add_body_p("5) Cyclic Terminal SOC Conservation: Eliminates unphysical energy depletion:")
    add_equation_box("|SOC(T) - SOC_init| ≤ ε_term      (ε_term = 0.010 or 1.0%)    (12)")

    add_heading_2("C. Standardized Clean Energy Metrics & Conservation Identity")
    add_body_p("To avoid double-counting stored energy, four standardized clean energy metrics are tracked:")
    add_equation_box("Metric A (RE Utilization) = [ ∑ (P_solar,disp + P_wind,disp) / ∑ (P_solar,avail + P_wind,avail) ] × 100%    (13)")
    add_equation_box("Metric B (RE Share of Demand) = [ (E_re,direct + E_re,battery) / (E_load - E_unserved) ] × 100%    (14)")
    add_equation_box("Metric C (Grid Dependency) = [ ∑ P_grid,import / (E_load - E_unserved) ] × 100%    (15)")
    add_equation_box("Metric D (RE Curtailment) = [ ∑ P_curt / ∑ (P_solar,avail + P_wind,avail) ] × 100%    (16)")
    add_body_p("Conservation Proof: Since P_curt(t) = P_avail(t) - P_disp(t), Metric A + Metric D ≡ 100.0% is analytically conserved.")

    # =========================================================================
    # SECTION IV: ALGORITHMS & PSEUDOCODE
    # =========================================================================
    add_heading_1("IV. METAHEURISTIC OPTIMIZATION FRAMEWORKS & PSEUDOCODE")
    add_body_p(
        "Four metaheuristic algorithms were implemented within the GridBalance execution harness. To ensure physical compliance, "
        "all candidate solution vectors X ∈ R^(3T) (comprising Solar, Wind, and Battery power schedules) pass through a deterministic "
        "Feasibility Repair Operator R(X) prior to objective evaluation."
    )

    add_heading_2("A. Proposed Adaptive Hybrid GWO-PSO Framework")
    add_body_p(
        "The Hybrid GWO-PSO algorithm combines the social hunting hierarchy of GWO with the cognitive and social velocity updates of PSO. "
        "The pack leaders Alpha, Beta, and Delta guide global exploration during early iterations. An adaptive time-varying parameter λ(k) "
        "dynamically blends the wolf pack encirclement position with the particle velocity acceleration:"
    )
    add_equation_box("λ(k) = λ_init - (k / K) · (λ_init - λ_final)      (0.80 → 0.20)    (17)")
    add_equation_box("X_i(k+1) = λ(k) · X_GWO,i(k+1) + (1 - λ(k)) · X_PSO,i(k+1)    (18)")

    add_body_p("The algorithmic procedure for the Hybrid GWO-PSO optimization engine is detailed in Algorithm 1:")
    add_code_block(
        "Algorithm 1: Adaptive Hybrid Grey Wolf - PSO (Hybrid GWO-PSO)\n"
        "Input: Population N=30, Iterations K=100, Bounds [lb, ub], Objective f(X)\n"
        "Output: Optimal Dispatch Vector X_alpha, Minimum Feasible Cost f(X_alpha)\n"
        "1: Initialize hybrid population X_i ~ U(lb, ub) and velocities V_i ~ U(-V_max, V_max) for i = 1..N\n"
        "2: Apply Feasibility Repair R(X_i) and evaluate f(X_i); Initialize P_best,i = X_i\n"
        "3: Identify initial pack leaders X_alpha, X_beta, X_delta based on minimum fitness\n"
        "4: for k = 1 to K do\n"
        "5:    a(k) = 2.0 - 2.0 * (k / K);  w(k) = w_max - (k / K) * (w_max - w_min)\n"
        "6:    lambda(k) = 0.80 - (k / K) * (0.80 - 0.20)\n"
        "7:    for i = 1 to N do\n"
        "8:       // GWO Multi-Leader Encircling Guidance\n"
        "9:       D_alpha = |2*r2*X_alpha - X_i|;  X1 = X_alpha - (2*a*r1 - a)*D_alpha\n"
        "10:      D_beta  = |2*r2*X_beta  - X_i|;  X2 = X_beta  - (2*a*r1 - a)*D_beta\n"
        "11:      D_delta = |2*r2*X_delta - X_i|;  X3 = X_delta - (2*a*r1 - a)*D_delta\n"
        "12:      X_gwo = (X1 + X2 + X3) / 3\n"
        "13:      // PSO Kinetic Velocity Acceleration\n"
        "14:      V_i = w(k)*V_i + c1*r1*(P_best,i - X_i) + c2*r2*(X_gwo - X_i)\n"
        "15:      V_i = clip(V_i, -V_max, V_max);  X_pso = X_i + V_i\n"
        "16:      // Adaptive Position Blending\n"
        "17:      X_i(k+1) = clip(lambda(k)*X_gwo + (1 - lambda(k))*X_pso, lb, ub)\n"
        "18:      Apply Feasibility Repair R(X_i(k+1)) and evaluate f(X_i(k+1))\n"
        "19:      Update Personal Best: if f(X_i(k+1)) < f(P_best,i) then P_best,i = X_i(k+1)\n"
        "20:   end for\n"
        "21:   Update Pack Leaders X_alpha, X_beta, X_delta across population\n"
        "22: end for\n"
        "23: Return X_alpha, f(X_alpha)"
    )

    # =========================================================================
    # SECTION V: RESULTS & STATISTICAL AUDIT
    # =========================================================================
    add_heading_1("V. 40-RUN BENCHMARK EXPERIMENTAL RESULTS & STATISTICAL AUDIT")
    add_body_p(
        "All four algorithms were executed across 10 identical random seeds [42, 101, 203, 314, 425, 536, 647, 758, 869, 970] "
        "under identical population sizes (N=30) and iteration limits (K=100) on Scenario Day 15. The comparative performance metrics "
        "are detailed in Table II."
    )

    # Table II: Benchmark Results
    tbl_results = [
        ("Performance Metric", "Standalone PSO", "Hybrid GWO-PSO", "Genetic Algorithm (GA)", "Grey Wolf (GWO)"),
        ("Best Operating Cost ($)", "$3,114.81", "$3,215.63", "$3,215.79", "$3,271.60"),
        ("Mean Operating Cost ($)", "$3,197.39", "$3,256.51", "$3,269.52", "$3,354.19"),
        ("Median Operating Cost ($)", "$3,171.28", "$3,245.87", "$3,267.16", "$3,351.48"),
        ("Worst Operating Cost ($)", "$3,386.76", "$3,377.57", "$3,340.97", "$3,510.54"),
        ("Standard Deviation ($)", "$82.47", "$45.09", "$35.33", "$70.41"),
        ("Mean Execution Time (s)", "3.65 s", "3.41 s", "3.36 s", "3.38 s"),
        ("Physical Feasibility Rate (%)", "100.0%", "100.0%", "100.0%", "100.0%"),
        ("Mean Terminal SOC Error", "0.0091", "0.0068", "0.0063", "0.0078"),
        ("RE Utilization (Metric A)", "96.02%", "92.26%", "89.96%", "85.72%"),
        ("RE Share of Demand (Metric B)", "22.48%", "21.60%", "21.06%", "20.07%"),
        ("Grid Dependency (Metric C)", "78.10%", "78.95%", "79.52%", "80.47%"),
        ("RE Curtailment (Metric D)", "3.98%", "7.74%", "10.04%", "14.28%")
    ]

    t2 = doc.add_table(rows=len(tbl_results), cols=5)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    t2.autofit = False
    col_w2 = [Inches(2.2), Inches(1.15), Inches(1.15), Inches(1.15), Inches(1.15)]

    for r_idx, row_data in enumerate(tbl_results):
        for c_idx, val in enumerate(row_data):
            cell = t2.cell(r_idx, c_idx)
            cell.width = col_w2[c_idx]
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if r_idx == 0:
                set_cell_background(cell, "1B365D")
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                if r_idx % 2 == 1:
                    set_cell_background(cell, "F4F6F9")
                r.font.color.rgb = RGBColor(0, 0, 0)
                if c_idx >= 1:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                if r_idx in [1, 2, 5, 7]:
                    r.font.bold = True

    p_cap2 = doc.add_paragraph()
    p_cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap2.paragraph_format.space_before = Pt(3)
    p_cap2.paragraph_format.space_after = Pt(10)
    rc2 = p_cap2.add_run("TABLE II: 40-RUN BENCHMARK EXPERIMENTAL RESULTS ACROSS 10 SEEDS (N=30, K=100)")
    rc2.font.bold = True
    rc2.font.size = Pt(8.5)

    add_heading_2("A. Statistical Significance Hypothesis Testing")
    add_body_p(
        "Formal paired hypothesis tests were conducted to validate algorithm distinctions across the 10 experimental seeds:\n"
        "1) Hybrid GWO-PSO vs. Standalone GWO:\n"
        "   • Welch's Two-Sample t-test: t = -3.505, p = 0.0031 (p < 0.01)\n"
        "   • Mann-Whitney U test: U = 9.0, p = 0.0022 (p < 0.01)\n"
        "   • Conclusion: The Hybrid GWO-PSO framework achieves a statistically significant operating cost reduction of $97.68/day "
        "over standalone GWO, reducing variance by 36.0%.\n"
        "2) Hybrid GWO-PSO vs. Standalone PSO:\n"
        "   • Welch's Two-Sample t-test: t = 1.887, p = 0.0802\n"
        "   • Mann-Whitney U test: U = 76.0, p = 0.0539\n"
        "   • Discussion: While PSO finds an aggressive minimum ($3,114.81), it suffers from high variance (σ = $82.47 vs $45.09 for Hybrid). "
        "The Hybrid GWO-PSO framework bounds the worst-case dispatch cost ($3,377.57 vs $3,386.76 for PSO), offering superior risk-adjusted reliability."
    )

    add_heading_2("B. Constraint Feasibility and Physical Power Balance Verification")
    add_body_p(
        "Every dispatch solution across all 40 runs was audited against physical constraints. As summarized in Table III, 100% feasibility "
        "was confirmed without any constraint relaxation."
    )

    tbl_audit = [
        ("Verification Dimension", "Mathematical Target", "Audited Benchmark Result", "Compliance Status"),
        ("Active Power Balance Error", "|residual(t)| ≤ 1e-4 kW", "Max |residual| ≤ 2.27 × 10^-13 kW", "VERIFIED (Machine Precision)"),
        ("Unserved Load Energy", "E_unserved = 0.000 kWh", "0.000 kWh across all 40 runs", "VERIFIED (100% Demand Served)"),
        ("Excess Renewable Spill", "E_excess = 0.000 kWh", "0.000 kWh across all 40 runs", "VERIFIED (Zero Power Imbalance)"),
        ("Terminal SOC Conservation", "|SOC(24) - SOC(0)| ≤ 1.0%", "Max error: 0.98% (Mean: 0.68%)", "VERIFIED (Cyclic Invariance)"),
        ("Battery SOC Operating Bounds", "0.20 ≤ SOC(t) ≤ 0.90", "All t ∈ [0.2000, 0.8992]", "VERIFIED (Within Safe Operating Limits)"),
        ("Substation Import Limit", "P_grid,import ≤ 2,500 kW", "Peak import observed: 1,328.6 kW", "VERIFIED (Well within capacity)"),
        ("Substation Export Limit", "P_grid,export ≤ 1,000 kW", "Peak export observed: 0.0 kW", "VERIFIED (No reverse overload)")
    ]

    t3 = doc.add_table(rows=len(tbl_audit), cols=4)
    t3.alignment = WD_TABLE_ALIGNMENT.CENTER
    t3.autofit = False
    col_w3 = [Inches(1.8), Inches(1.8), Inches(2.0), Inches(1.2)]

    for r_idx, row_data in enumerate(tbl_audit):
        for c_idx, val in enumerate(row_data):
            cell = t3.cell(r_idx, c_idx)
            cell.width = col_w3[c_idx]
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if r_idx == 0:
                set_cell_background(cell, "1B365D")
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                if r_idx % 2 == 1:
                    set_cell_background(cell, "F4F6F9")
                r.font.color.rgb = RGBColor(0, 0, 0)
                if c_idx == 3:
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(40, 167, 69)

    p_cap3 = doc.add_paragraph()
    p_cap3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap3.paragraph_format.space_before = Pt(3)
    p_cap3.paragraph_format.space_after = Pt(10)
    rc3 = p_cap3.add_run("TABLE III: INDEPENDENT PHYSICAL CONSTRAINT AUDIT AND COMPLIANCE VERIFICATION")
    rc3.font.bold = True
    rc3.font.size = Pt(8.5)

    # =========================================================================
    # SECTION VI: VISUAL ANALYTICS & FIGURES
    # =========================================================================
    add_heading_1("VI. VISUAL ANALYTICS AND CONVERGENCE PROFILES")
    add_body_p(
        "To illustrate the physical dispatch operation and optimization dynamics, four high-resolution visual artifacts generated "
        "by the GridBalance analytics suite are examined."
    )

    # Embed Figure 1: Energy Dispatch Distribution
    fig1_path = os.path.abspath("results/graphs/04_energy_dispatch_distribution.png")
    if os.path.exists(fig1_path):
        p_img1 = doc.add_paragraph()
        p_img1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img1.paragraph_format.space_before = Pt(6)
        p_img1.paragraph_format.space_after = Pt(2)
        doc.add_picture(fig1_path, width=Inches(6.2))
        p_c1 = doc.add_paragraph()
        p_c1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_c1.paragraph_format.space_after = Pt(8)
        rc = p_c1.add_run("Fig. 1. 24-Hour Microgrid Energy Dispatch Distribution (Solar PV, Wind, Battery, and Utility Grid).")
        rc.font.size = Pt(8.5)
        rc.font.italic = True

    add_body_p(
        "As shown in Fig. 1, solar generation peaks between 10:00 and 15:00 at 897.4 kW. The BESS initiates charging during this period, "
        "storing surplus clean energy. Discharging is scheduled during the evening peak tariff window (14:00 to 20:00, $0.24/kWh), "
        "substantially mitigating expensive grid import purchases."
    )

    # Embed Figure 2: Multi-Algorithm Convergence
    fig2_path = os.path.abspath("results/graphs/07_multi_algorithm_convergence.png")
    if os.path.exists(fig2_path):
        p_img2 = doc.add_paragraph()
        p_img2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img2.paragraph_format.space_before = Pt(6)
        p_img2.paragraph_format.space_after = Pt(2)
        doc.add_picture(fig2_path, width=Inches(6.0))
        p_c2 = doc.add_paragraph()
        p_c2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_c2.paragraph_format.space_after = Pt(8)
        rc = p_c2.add_run("Fig. 2. Multi-Algorithm Convergence Trajectory Comparison (PSO, GWO, Hybrid GWO-PSO, GA).")
        rc.font.size = Pt(8.5)
        rc.font.italic = True

    # Embed Figure 3: Cost Comparison Boxplot
    fig3_path = os.path.abspath("results/graphs/08_algorithm_cost_comparison.png")
    if os.path.exists(fig3_path):
        p_img3 = doc.add_paragraph()
        p_img3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img3.paragraph_format.space_before = Pt(6)
        p_img3.paragraph_format.space_after = Pt(2)
        doc.add_picture(fig3_path, width=Inches(5.8))
        p_c3 = doc.add_paragraph()
        p_c3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_c3.paragraph_format.space_after = Pt(8)
        rc = p_c3.add_run("Fig. 3. Statistical Operating Cost Distribution Across 10 Independent Random Seeds.")
        rc.font.size = Pt(8.5)
        rc.font.italic = True

    # Embed Figure 4: Battery SOC Profile
    fig4_path = os.path.abspath("results/graphs/10_battery_soc_profile.png")
    if os.path.exists(fig4_path):
        p_img4 = doc.add_paragraph()
        p_img4.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img4.paragraph_format.space_before = Pt(6)
        p_img4.paragraph_format.space_after = Pt(2)
        doc.add_picture(fig4_path, width=Inches(6.0))
        p_c4 = doc.add_paragraph()
        p_c4.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_c4.paragraph_format.space_after = Pt(8)
        rc = p_c4.add_run("Fig. 4. Battery Energy Storage System (BESS) 24-Hour State of Charge (SOC) Dynamics Trajectory.")
        rc.font.size = Pt(8.5)
        rc.font.italic = True

    add_body_p(
        "Fig. 4 confirms the enforcement of the cyclic terminal SOC constraint. The BESS commences dispatch at exactly SOC=0.50 (50%), "
        "charges to a peak of 89.9% during the solar peak, discharges during the peak tariff window down to 21.4%, and finishes the 24-hour "
        "horizon at SOC=0.4932 (error: 0.68%), strictly respecting the 1.0% cyclic boundary."
    )

    # =========================================================================
    # SECTION VII: DISCUSSION & PRACTICAL IMPLICATIONS
    # =========================================================================
    add_heading_1("VII. SYSTEM DISCUSSION & PRACTICAL GRID IMPLICATIONS")
    add_body_p(
        "From an engineering and power system operational viewpoint, the choice of optimization algorithm depends on the operational "
        "risk posture of the microgrid operator:"
    )
    add_body_p(
        "1) Risk-Neutral Operations: Standalone PSO attained the absolute lowest operating cost ($3,114.81), benefiting from aggressive "
        "kinetic velocity updates. However, its high dispersion (σ = $82.47) and worst-case cost of $3,386.76 indicate heightened vulnerability "
        "to initial particle seeding.\n"
        "2) Risk-Averse & Utility-Grade Operations: Hybrid GWO-PSO provides remarkable consistency (σ = $45.09, a 45.3% variance reduction vs PSO) "
        "while delivering statistically superior dispatch economy over standalone GWO (saving $97.68/day). For real-world distribution utilities "
        "operating day-ahead commitments, low variance prevents costly unexpected budget excursions.\n"
        "3) Battery Health Preservation: Enforcing the terminal constraint ensures that economic gains reflect genuine operational arbitrage "
        "rather than hidden accelerated cell degradation."
    )

    # =========================================================================
    # SECTION VIII: CONCLUSION & LIMITATIONS
    # =========================================================================
    add_heading_1("VIII. CONCLUSION, SCOPE BOUNDARIES & FUTURE SCOPE")
    add_heading_2("A. Research Conclusions")
    add_body_p(
        "The GridBalance project successfully delivers a verified, research-grade microgrid dispatch optimization framework. By uniting "
        "empirical generation scenarios from the DDRE-33 dataset with rigorous physical constraints, a closed-form power balance identity, "
        "and cyclic BESS conservation, the framework guarantees reliable and reproducible dispatch solutions. The proposed Hybrid GWO-PSO "
        "algorithm demonstrates an optimal trade-off between global exploration and local convergence, achieving high stability, 100% feasibility, "
        "and statistically proven cost advantages over standalone GWO."
    )

    add_heading_2("B. Explicit Scientific Limitations & Scope Boundaries")
    add_body_p(
        "To uphold scientific integrity, four boundaries of this study are declared:\n"
        "1) Load Demand Profile Origin: Electricity load is modeled using a declared diurnal residential/commercial curve scaled to IEEE 33-bus "
        "peak demand (1,600 kW peak), rather than recorded DDRE-33 customer demand time-series.\n"
        "2) Active Power Dispatch vs AC Optimal Power Flow: The model solves active power dispatch and enforces substation capacity limits. "
        "Line reactive power flows, branch I^2 R losses, and bus voltage bounds (0.95 ≤ V_i ≤ 1.05 p.u.) are not evaluated, requiring full AC-OPF "
        "for bus-level voltage stability analysis.\n"
        "3) Single-Day Scenario Horizon: Benchmark testing was executed on canonical Day 15 (July 15). Extending evaluations across all 365 scenarios "
        "is necessary to analyze multi-seasonal winter/summer variability.\n"
        "4) Rolling Horizon Commitments: The cyclic terminal constraint assumes daily periodic scheduling. In practice, dynamic multi-day boundary "
        "pricing or Model Predictive Control (MPC) can further optimize inter-day energy transfers."
    )

    # =========================================================================
    # REFERENCES
    # =========================================================================
    add_heading_1("REFERENCES")
    refs = [
        "[1] Y. Chen, H. Xie, W. Huang, and P. Li, \"DDRE-33: A large-scale dataset of distributed renewable energy scenarios on the IEEE-33 bus network,\" Scientific Data (Nature Portfolio), vol. 13, no. 1, p. 146, 2025.",
        "[2] M. E. Baran and F. F. Wu, \"Network reconfiguration in distribution systems for loss reduction and load balancing,\" IEEE Transactions on Power Delivery, vol. 4, no. 2, pp. 1401-1407, 1989.",
        "[3] S. Mirjalili, S. M. Mirjalili, and A. Lewis, \"Grey Wolf Optimizer,\" Advances in Engineering Software, vol. 69, pp. 46-61, 2014.",
        "[4] J. Kennedy and R. Eberhart, \"Particle swarm optimization,\" in Proceedings of ICNN'95 - International Conference on Neural Networks, vol. 4, pp. 1942-1948, 1995.",
        "[5] Y. Wang and Z. Li, \"A hybrid GWO-PSO optimization algorithm for economic dispatch of power systems,\" Electric Power Systems Research, vol. 190, p. 106654, 2021.",
        "[6] K. Deb, \"An efficient constraint handling method for genetic algorithms,\" Computer Methods in Applied Mechanics and Engineering, vol. 186, no. 2-4, pp. 311-338, 2000.",
        "[7] H. Shayeghi, A. Ghasemi, and M. Moradzadeh, \"A new hybrid algorithm for economic load dispatch of microgrid considering renewable resources and energy storage,\" Applied Energy, vol. 142, pp. 243-255, 2015.",
        "[8] D. E. Goldberg, Genetic Algorithms in Search, Optimization, and Machine Learning. Boston, MA: Addison-Wesley, 1989.",
        "[9] M. Marzband, F. Azarinejadian, M. Savaghebi, and J. M. Guerrero, \"An optimal operational management for standalone hybrid microgrid considering battery degradation model,\" Energy, vol. 139, pp. 1066-1082, 2017.",
        "[10] A. G. Tsikalakis and N. D. Hatziargyriou, \"Centralized control for optimizing microgrids operation,\" IEEE Transactions on Energy Conversion, vol. 23, no. 1, pp. 241-248, 2008.",
        "[11] B. L. Welch, \"The generalization of 'Student's' problem when several different population variances are involved,\" Biometrika, vol. 34, no. 1-2, pp. 28-35, 1947.",
        "[12] H. B. Mann and D. R. Whitney, \"On a test of whether one of two random variables is stochastically larger than the other,\" Annals of Mathematical Statistics, vol. 18, no. 1, pp. 50-60, 1947.",
        "[13] R. Palma-Behnke et al., \"A microgrid energy management system based on the rolling horizon strategy,\" IEEE Transactions on Smart Grid, vol. 4, no. 2, pp. 996-1006, 2013.",
        "[14] A. Parisio, E. Rikos, and L. Glielmo, \"A model predictive control approach to microgrid operation optimization,\" IEEE Transactions on Control Systems Technology, vol. 22, no. 5, pp. 1813-1827, 2014.",
        "[15] J. M. Guerrero et al., \"Hierarchical control of smart microgrids: An overview,\" IEEE Transactions on Industrial Electronics, vol. 58, no. 1, pp. 158-172, 2011."
    ]

    for ref in refs:
        p_ref = doc.add_paragraph()
        p_ref.paragraph_format.left_indent = Inches(0.25)
        p_ref.paragraph_format.first_line_indent = Inches(-0.25)
        p_ref.paragraph_format.space_after = Pt(2)
        p_ref.paragraph_format.line_spacing = 1.0
        r_ref = p_ref.add_run(ref)
        r_ref.font.size = Pt(8.5)

    # Save to root and results/reports/
    out_path_root = os.path.abspath("IEEE_GridBalance_Research_Report.docx")
    out_path_rep = os.path.abspath("results/reports/IEEE_GridBalance_Research_Report.docx")

    doc.save(out_path_root)
    doc.save(out_path_rep)
    print(f"Successfully generated:\n- {out_path_root} ({os.path.getsize(out_path_root):,} bytes)\n- {out_path_rep} ({os.path.getsize(out_path_rep):,} bytes)")

if __name__ == "__main__":
    create_ieee_report_docx()
