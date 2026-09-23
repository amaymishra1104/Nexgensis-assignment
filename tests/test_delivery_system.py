"""
Comprehensive test suite for the Nexgensis FastBox Delivery System.
Covers core calculation, models, parser variations, validation, simulation,
zero-delivery edge cases, reporting, bonus features, and all supplied test cases.
"""

import json
import math
import subprocess
import sys
from pathlib import Path
import pytest

from delivery_system.models import (
    Location,
    Warehouse,
    Agent,
    Package,
    ValidationError,
    ParserError,
    SimulationError,
)
from delivery_system.distance import calculate_distance
from delivery_system.parser import (
    parse_location,
    parse_input_data,
    load_input_data,
)
from delivery_system.assignment import assign_packages
from delivery_system.simulation import simulate_deliveries
from delivery_system.report import format_report, save_report, generate_summary_text
from delivery_system.bonus import (
    render_ascii_map,
    export_performance_to_csv,
)


# ==============================================================================
# 1. Distance Calculation Tests
# ==============================================================================

def test_distance_calculation_known_triangles():
    # 3-4-5 right triangle
    loc1 = Location(0.0, 0.0)
    loc2 = Location(3.0, 4.0)
    assert calculate_distance(loc1, loc2) == pytest.approx(5.0)

    # 5-12-13 right triangle
    loc3 = Location(1.0, 2.0)
    loc4 = Location(6.0, 14.0)
    assert calculate_distance(loc3, loc4) == pytest.approx(13.0)


def test_distance_calculation_zero_distance():
    loc = Location(42.5, 99.1)
    assert calculate_distance(loc, loc) == 0.0


def test_distance_calculation_negative_coordinates():
    loc1 = Location(-10.0, -20.0)
    loc2 = Location(-13.0, -24.0)
    assert calculate_distance(loc1, loc2) == pytest.approx(5.0)


def test_distance_floating_precision_no_intermediate_rounding():
    loc1 = Location(1.123456789, 2.987654321)
    loc2 = Location(4.123456789, 6.987654321)
    # dx=3.0, dy=4.0 -> exact 5.0
    assert calculate_distance(loc1, loc2) == pytest.approx(5.0)


# ==============================================================================
# 2. Nearest-Agent Assignment & 3. Tie-breaking Tests
# ==============================================================================

def test_nearest_agent_assignment():
    whs = {"W1": Warehouse(id="W1", location=Location(0.0, 0.0))}
    agents = {
        "A1": Agent(id="A1", initial_location=Location(10.0, 10.0)),
        "A2": Agent(id="A2", initial_location=Location(2.0, 2.0)),  # Closer to W1
    }
    pkgs = [Package(id="P1", warehouse_id="W1", destination=Location(5.0, 5.0))]

    assignments = assign_packages(agents, whs, pkgs)
    assert len(assignments["A2"]) == 1
    assert assignments["A2"][0].id == "P1"
    assert len(assignments["A1"]) == 0


def test_tie_breaking_deterministic_lexicographical():
    # Both A1 and A2 are at equal distance from W1
    whs = {"W1": Warehouse(id="W1", location=Location(0.0, 0.0))}
    agents = {
        "A2": Agent(id="A2", initial_location=Location(5.0, 0.0)),
        "A1": Agent(id="A1", initial_location=Location(0.0, 5.0)),
        "A3": Agent(id="A3", initial_location=Location(5.0, 0.0)),
    }
    # Distance is 5.0 for all three. Lexicographical winner must be A1.
    pkgs = [Package(id="P1", warehouse_id="W1", destination=Location(10.0, 10.0))]

    assignments = assign_packages(agents, whs, pkgs)
    assert len(assignments["A1"]) == 1
    assert assignments["A1"][0].id == "P1"
    assert len(assignments["A2"]) == 0
    assert len(assignments["A3"]) == 0


# ==============================================================================
# 4. Multiple Packages & 5. Agent Movement Tests
# ==============================================================================

def test_multiple_packages_and_continuous_movement():
    """
    Verifies that:
    1. Multiple packages are assigned to one agent in input order.
    2. Agent moves continuously:
       start -> W1 -> dest1 -> W2 -> dest2
       (Does NOT reset to start between deliveries).
    """
    whs = {
        "W1": Warehouse(id="W1", location=Location(0.0, 0.0)),
        "W2": Warehouse(id="W2", location=Location(10.0, 0.0)),
    }
    # Single agent
    agents = {"A1": Agent(id="A1", initial_location=Location(0.0, 5.0))}

    pkgs = [
        Package(id="P1", warehouse_id="W1", destination=Location(0.0, 10.0)),
        Package(id="P2", warehouse_id="W2", destination=Location(10.0, 10.0)),
    ]

    assignments = assign_packages(agents, whs, pkgs)
    assert len(assignments["A1"]) == 2

    res = simulate_deliveries(agents, whs, assignments)
    rep = res.agent_reports["A1"]

    # Manual path calculation:
    # Start: (0, 5)
    # Leg 1: (0, 5) -> W1(0, 0) = 5.0
    # Leg 2: W1(0, 0) -> dest1(0, 10) = 10.0
    # After P1, agent is at (0, 10)
    # Leg 3: (0, 10) -> W2(10, 0) = sqrt(10^2 + (-10)^2) = sqrt(200) ~ 14.1421356
    # Leg 4: W2(10, 0) -> dest2(10, 10) = 10.0
    # Total expected: 5 + 10 + sqrt(200) + 10 = 25 + 14.1421356 ~ 39.1421356
    expected_dist = 5.0 + 10.0 + math.hypot(10.0 - 0.0, 0.0 - 10.0) + 10.0
    assert rep.total_distance == pytest.approx(expected_dist)
    assert rep.packages_delivered == 2
    assert rep.efficiency == pytest.approx(expected_dist / 2.0)
    assert agents["A1"].current_location == Location(10.0, 10.0)


# ==============================================================================
# 6. Zero-Delivery Agent & Best Agent Selection
# ==============================================================================

def test_zero_delivery_agent_handling():
    whs = {"W1": Warehouse(id="W1", location=Location(0.0, 0.0))}
    agents = {
        "A1": Agent(id="A1", initial_location=Location(1.0, 1.0)),
        "A2": Agent(id="A2", initial_location=Location(100.0, 100.0)),  # Gets 0 packages
    }
    pkgs = [Package(id="P1", warehouse_id="W1", destination=Location(2.0, 2.0))]

    assignments = assign_packages(agents, whs, pkgs)
    res = simulate_deliveries(agents, whs, assignments)

    rep_a2 = res.agent_reports["A2"]
    assert rep_a2.packages_delivered == 0
    assert rep_a2.total_distance == 0.0
    assert rep_a2.efficiency == 0.0

    # Best agent must be A1 (active), NOT A2 (inactive with 0 distance)
    assert res.best_agent == "A1"

    report_dict = format_report(res)
    assert report_dict["A2"]["packages_delivered"] == 0
    assert report_dict["A2"]["total_distance"] == 0.0
    assert report_dict["A2"]["efficiency"] == 0.0
    assert report_dict["best_agent"] == "A1"


# ==============================================================================
# 7. Duplicate & Missing Package Detection / Validation
# ==============================================================================

def test_duplicate_package_id_detection():
    data = {
        "warehouses": {"W1": [0, 0]},
        "agents": {"A1": [1, 1]},
        "packages": [
            {"id": "P1", "warehouse": "W1", "destination": [2, 2]},
            {"id": "P1", "warehouse": "W1", "destination": [3, 3]},
        ],
    }
    with pytest.raises(ValidationError, match="Duplicate package id detected: 'P1'"):
        parse_input_data(data)


def test_unknown_warehouse_reference_validation():
    data = {
        "warehouses": {"W1": [0, 0]},
        "agents": {"A1": [1, 1]},
        "packages": [
            {"id": "P1", "warehouse": "W_NONEXISTENT", "destination": [2, 2]},
        ],
    }
    with pytest.raises(ValidationError, match="references unknown warehouse 'W_NONEXISTENT'"):
        parse_input_data(data)


# ==============================================================================
# 8. Heterogeneous JSON Structures Normalization
# ==============================================================================

def test_different_json_input_structures():
    # Format A: warehouses and agents as lists, package with 'warehouse_id'
    data_a = {
        "warehouses": [{"id": "W1", "location": [0, 0]}],
        "agents": [{"id": "A1", "location": [5, 5]}],
        "packages": [{"id": "P1", "warehouse_id": "W1", "destination": [10, 10]}],
    }
    wh_a, ag_a, pkgs_a = parse_input_data(data_a)
    assert "W1" in wh_a and wh_a["W1"].location == Location(0, 0)
    assert "A1" in ag_a and ag_a["A1"].initial_location == Location(5, 5)
    assert pkgs_a[0].warehouse_id == "W1"

    # Format B: warehouses and agents as dicts, package with 'warehouse'
    data_b = {
        "warehouses": {"W1": [0, 0]},
        "agents": {"A1": [5, 5]},
        "packages": [{"id": "P1", "warehouse": "W1", "destination": [10, 10]}],
    }
    wh_b, ag_b, pkgs_b = parse_input_data(data_b)
    assert "W1" in wh_b and wh_b["W1"].location == Location(0, 0)
    assert "A1" in ag_b and ag_b["A1"].initial_location == Location(5, 5)
    assert pkgs_b[0].warehouse_id == "W1"


# ==============================================================================
# 9. Empty & Edge Case Inputs
# ==============================================================================

def test_empty_packages_list():
    data = {
        "warehouses": {"W1": [0, 0]},
        "agents": {"A1": [5, 5]},
        "packages": [],
    }
    whs, ags, pkgs = parse_input_data(data)
    assignments = assign_packages(ags, whs, pkgs)
    res = simulate_deliveries(ags, whs, assignments)
    rep = format_report(res)

    assert rep["best_agent"] is None
    assert rep["A1"]["packages_delivered"] == 0
    assert rep["A1"]["total_distance"] == 0.0


def test_invalid_coordinates_validation():
    # String coordinates
    with pytest.raises(ValidationError, match="coordinates must be numeric"):
        parse_location(["10", "20"])

    # Boolean coordinates (bool is a subclass of int in Python and must be explicitly rejected)
    with pytest.raises(ValidationError, match="coordinates must be numeric"):
        parse_location([True, False])

    with pytest.raises(ValidationError, match="coordinates must be numeric"):
        parse_location([10.0, True])

    with pytest.raises(ValidationError, match="Coordinates must be numbers"):
        Location(True, 10.0)

    with pytest.raises(ValidationError, match="Coordinates must be numbers"):
        Location(10.0, False)

    # Wrong length
    with pytest.raises(ValidationError, match="expected exactly 2 coordinates"):
        parse_location([10, 20, 30])

    # NaN / Inf coordinates
    with pytest.raises(ValidationError, match="cannot be NaN or infinite"):
        parse_location([float("nan"), 10])


def test_packages_with_zero_agents():
    data = {
        "warehouses": {"W1": [0, 0]},
        "agents": {},
        "packages": [{"id": "P1", "warehouse": "W1", "destination": [1, 1]}],
    }
    with pytest.raises(ValidationError, match="no delivery agents are available"):
        parse_input_data(data)


# ==============================================================================
# 10. Full Base Case Pipeline Verification
# ==============================================================================

def test_base_case_full_simulation():
    input_file = Path("data/base_case.json")
    assert input_file.exists()

    whs, ags, pkgs = load_input_data(input_file)
    assignments = assign_packages(ags, whs, pkgs)
    res = simulate_deliveries(ags, whs, assignments)
    rep = format_report(res)

    # Base case expectations:
    # 5 packages, 3 agents
    assert res.total_packages_delivered == 5
    assert len(res.agent_reports) == 3
    assert set(res.agent_reports.keys()) == {"A1", "A2", "A3"}

    # All packages accounted for:
    # A1 gets P1, P4 (from W1)
    # A2 gets P2, P5 (from W2)
    # A3 gets P3 (from W3)
    assert res.agent_reports["A1"].packages_delivered == 2
    assert res.agent_reports["A2"].packages_delivered == 2
    assert res.agent_reports["A3"].packages_delivered == 1

    # Exact expected rounded values:
    assert rep["A1"]["total_distance"] == 121.21
    assert rep["A1"]["efficiency"] == 60.61
    assert rep["A2"]["total_distance"] == 79.21
    assert rep["A2"]["efficiency"] == 39.60
    assert rep["A3"]["total_distance"] == 14.14
    assert rep["A3"]["efficiency"] == 14.14
    assert rep["best_agent"] == "A3"


# ==============================================================================
# 11. All Supplied Test Cases (Parametrized)
# ==============================================================================

@pytest.mark.parametrize("case_num", list(range(1, 11)))
def test_all_supplied_test_cases(case_num):
    case_path = Path(f"data/test_cases/test_case_{case_num}.json")
    assert case_path.exists(), f"Test case file not found: {case_path}"

    whs, ags, pkgs = load_input_data(case_path)
    assignments = assign_packages(ags, whs, pkgs)
    res = simulate_deliveries(ags, whs, assignments)
    rep = format_report(res)

    # Invariants verification:
    # 1. Every package delivered exactly once
    assert res.total_packages_delivered == len(pkgs)

    # 2. Every agent represented in the report
    for ag_id in ags:
        assert ag_id in rep
        assert "packages_delivered" in rep[ag_id]
        assert "total_distance" in rep[ag_id]
        assert "efficiency" in rep[ag_id]

    # 3. Sum of packages delivered equals total packages
    total_delivered = sum(rep[ag_id]["packages_delivered"] for ag_id in ags)
    assert total_delivered == len(pkgs)

    # 4. Best agent is valid and has minimum efficiency among active agents
    active_reps = [v for k, v in rep.items() if k != "best_agent" and v["packages_delivered"] > 0]
    if active_reps:
        min_eff = min(v["efficiency"] for v in active_reps)
        best_id = rep["best_agent"]
        assert best_id in ags
        assert rep[best_id]["efficiency"] == min_eff


# ==============================================================================
# 12. CLI Execution & End-to-End Subprocess Tests
# ==============================================================================

def test_cli_execution_base_case(tmp_path):
    report_file = tmp_path / "cli_report.json"
    cmd = [
        sys.executable,
        "main.py",
        "--input",
        "data/base_case.json",
        "--output",
        str(report_file),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert report_file.exists()

    with open(report_file, "r") as f:
        data = json.load(f)
    assert data["best_agent"] == "A3"
    assert "A1" in data and "A2" in data and "A3" in data


def test_cli_execution_invalid_file(tmp_path):
    cmd = [
        sys.executable,
        "main.py",
        "--input",
        "non_existent_file_xyz.json",
        "--output",
        str(tmp_path / "out.json"),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode != 0
    assert "File Not Found" in proc.stderr or "Error" in proc.stderr or "Failure" in proc.stderr


# ==============================================================================
# 13. Bonus Features Tests
# ==============================================================================

def test_bonus_features(tmp_path):
    whs = {"W1": Warehouse("W1", Location(0, 0))}
    ags = {"A1": Agent("A1", Location(10, 10))}
    pkgs = [Package("P1", "W1", Location(20, 20))]

    assignments = assign_packages(ags, whs, pkgs)
    res = simulate_deliveries(ags, whs, assignments)

    # 1. ASCII map rendering
    ascii_map = render_ascii_map(whs, ags, pkgs)
    assert "ASCII Map" in ascii_map
    assert "Legend" in ascii_map

    # 2. CSV export
    csv_file = tmp_path / "perf.csv"
    export_performance_to_csv(res, csv_file)
    assert csv_file.exists()
    content = csv_file.read_text(encoding="utf-8")
    assert "agent_id,packages_delivered" in content
    assert "A1,1" in content
