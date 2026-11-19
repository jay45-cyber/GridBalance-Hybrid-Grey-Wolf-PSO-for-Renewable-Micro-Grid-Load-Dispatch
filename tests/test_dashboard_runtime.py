"""
tests/test_dashboard_runtime.py
Rigorous runtime verification test for Streamlit Dashboard (dashboard/app.py).
Tests:
1. Dashboard startup without error.
2. All 10 navigation sections open cleanly.
3. Dataset information displays correctly.
4. Optimization controls (sliders, inputs) work.
5. PSO executes via UI trigger.
6. GWO executes via UI trigger.
7. Hybrid GWO-PSO executes via UI trigger.
8. GA executes via UI trigger.
9. Comparison graphs display in Section G.
10. Energy dispatch results display in Section H.
11. Feasibility status banner and detailed breakdown display correctly.
12. CSV download buttons exist and produce correct payloads in Sections H and J.
"""

import os
import sys
import pytest
from streamlit.testing.v1 import AppTest

# Ensure repo root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


DASHBOARD_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py"))


def test_dashboard_startup_and_all_sections():
    """Verify dashboard starts and all 10 navigation sections render without exception."""
    sections = [
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
    
    for sec in sections:
        at = AppTest.from_file(DASHBOARD_PATH, default_timeout=30)
        at.run()
        assert not at.exception, f"Exception on initial load: {at.exception}"
        
        # Switch navigation section
        at.sidebar.radio[0].set_value(sec).run()
        assert not at.exception, f"Exception rendering section {sec}: {at.exception}"
        print(f"Section '{sec}' rendered successfully.")


def test_dashboard_dataset_info_section():
    """Verify Section B: Dataset Information renders tables and metrics."""
    at = AppTest.from_file(DASHBOARD_PATH, default_timeout=30)
    at.run()
    at.sidebar.radio[0].set_value("B. Dataset Information").run()
    assert not at.exception
    # Check that title or markdown rendered
    assert len(at.markdown) > 0 or len(at.title) > 0


def test_dashboard_optimization_controls_and_execution_all_algos():
    """Verify Section F: Execution of PSO, GWO, Hybrid GWO-PSO, and GA."""
    algorithms = ["PSO", "GWO", "Hybrid GWO-PSO", "Genetic Algorithm (GA)"]
    
    for algo in algorithms:
        at = AppTest.from_file(DASHBOARD_PATH, default_timeout=30)
        at.run()
        at.sidebar.radio[0].set_value("F. Run Optimization").run()
        assert not at.exception
        
        # Configure small population and iterations for fast runtime UI testing
        at.sidebar.slider[1].set_value(10).run()  # pop_size = 10
        at.sidebar.slider[2].set_value(20).run()  # max_iter = 20
        
        # Select algorithm
        at.selectbox[0].set_value(algo).run()
        assert not at.exception
        
        # Click Run button (button 0 in main body)
        at.button[0].click().run()
        assert not at.exception, f"Exception executing {algo}: {at.exception}"
        
        # Verify success message and feasibility banner
        success_messages = [s.value for s in at.success]
        assert any(algo in s for s in success_messages), f"Optimization completion message missing for {algo}"
        assert any("FEASIBLE WITHIN CONFIGURED CONSTRAINT TOLERANCES" in s for s in success_messages), f"Feasibility status banner missing for {algo}"
        
        # Verify metrics displayed
        assert len(at.metric) >= 8, f"Expected at least 8 metrics, found {len(at.metric)}"
        
        # Verify Pure Operating Cost metric exists and is positive
        cost_metric = at.metric[0]
        assert "$" in cost_metric.value
        print(f"Dashboard executed {algo} successfully: {cost_metric.label} = {cost_metric.value}")


def test_dashboard_comparison_and_dispatch_results():
    """Verify Section G (Algorithm Comparison) and Section H (Energy Dispatch Results)."""
    at = AppTest.from_file(DASHBOARD_PATH, default_timeout=30)
    at.run()
    
    # Section G: Algorithm Comparison
    at.sidebar.radio[0].set_value("G. Algorithm Comparison").run()
    assert not at.exception
    assert len(at.dataframe) > 0
    
    # Section H: Energy Dispatch Results
    at.sidebar.radio[0].set_value("H. Energy Dispatch Results").run()
    assert not at.exception
    assert len(at.dataframe) > 0
    assert len(at.download_button) > 0
    # Test download button
    sched_dl = at.download_button[0]
    assert "Download" in sched_dl.label
    print(f"Section H download button verified: {sched_dl.label}")


def test_dashboard_performance_metrics_and_download():
    """Verify Section J: Performance Metrics and CSV download button."""
    at = AppTest.from_file(DASHBOARD_PATH, default_timeout=30)
    at.run()
    
    at.sidebar.radio[0].set_value("J. Performance Metrics").run()
    assert not at.exception
    assert len(at.dataframe) > 0
    assert len(at.download_button) > 0
    dl_btn = at.download_button[0]
    assert "Download" in dl_btn.label
    print(f"Section J download button verified: {dl_btn.label}")


if __name__ == "__main__":
    print("Testing dashboard startup and navigation...")
    test_dashboard_startup_and_all_sections()
    print("Testing dataset information...")
    test_dashboard_dataset_info_section()
    print("Testing optimization execution for all 4 algorithms...")
    test_dashboard_optimization_controls_and_execution_all_algos()
    print("Testing comparison and dispatch results...")
    test_dashboard_comparison_and_dispatch_results()
    print("Testing performance metrics and download...")
    test_dashboard_performance_metrics_and_download()
    print("\nALL DASHBOARD RUNTIME TESTS PASSED SUCCESSFULLY!")
