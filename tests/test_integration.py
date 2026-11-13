"""
Integration Test Suite: Autonomous Navigation Interface Contract
Lead Integration Architect — MARS-09 ODYSSEY
Validates Member 3 core.navigation contract with mock 10x10 cost map.
"""

import numpy as np
import pytest
from core.navigation import compare_routes


@pytest.fixture
def mock_cost_map():
    """
    Generate a 10x10 mock terrain cost map adhering to Member 2/3 contract:
    - 1.0 = SAFE traversable terrain
    - 5.0 = CAUTION high-slope terrain
    - np.inf = IMPASSABLE hazard (crater/boulder)
    """
    cost_map = np.full((10, 10), 1.0, dtype=np.float64)

    # Introduce a caution zone in the central corridor
    cost_map[3:7, 3:7] = 5.0

    # Introduce discrete obstacle hazards
    cost_map[2, 2] = np.inf
    cost_map[7, 8] = np.inf

    return cost_map


def test_compare_routes_contract_reachable(mock_cost_map):
    """
    Validate that compare_routes satisfies all interface contract keys,
    data types, and structure for a reachable route from (0, 0) to (9, 9).
    """
    start = (0, 0)
    goal = (9, 9)

    res = compare_routes(mock_cost_map, start, goal)

    # 1. Verify root contract sections exist
    assert "safest" in res, "Missing 'safest' key in compare_routes response"
    assert "shortest" in res, "Missing 'shortest' key in compare_routes response"
    assert "summary" in res, "Missing 'summary' key in compare_routes response"

    # 2. Verify 'route' payload and types
    route = res["safest"]["route"]
    assert isinstance(route["success"], bool), "'success' must be a boolean"
    assert route["success"] is True, "Expected path finding to succeed for clear map"

    assert isinstance(route["x"], list), "'x' coordinates must be a list"
    assert isinstance(route["y"], list), "'y' coordinates must be a list"
    assert len(route["x"]) == len(route["y"]), "'x' and 'y' coordinate lists must match in length"

    assert isinstance(route["path"], list), "'path' must be a list"
    assert len(route["path"]) > 0, "'path' must contain waypoints"
    for wp in route["path"]:
        assert isinstance(wp, tuple), f"Waypoint {wp} in 'path' must be a tuple"
        assert len(wp) == 2, f"Waypoint {wp} must be a 2-tuple (row, col)"
        assert isinstance(wp[0], int) and isinstance(wp[1], int), "Waypoint coords must be integers"

    # 3. Verify 'metrics' payload and types
    metrics = res["safest"]["metrics"]
    assert "total_cost" in metrics, "Missing 'total_cost' in safest metrics"
    assert isinstance(metrics["total_cost"], (float, int)), "'total_cost' must be a numeric value"
    assert metrics["total_cost"] > 0, "'total_cost' must be positive"

    assert "caution_steps" in metrics, "Missing 'caution_steps' in safest metrics"
    assert isinstance(metrics["caution_steps"], int), "'caution_steps' must be an integer"
    assert metrics["caution_steps"] >= 0, "'caution_steps' cannot be negative"

    # 4. Verify 'summary' payload and types
    summary = res["summary"]
    assert "distance_penalty_pct" in summary, "Missing 'distance_penalty_pct' in summary"
    assert isinstance(summary["distance_penalty_pct"], (float, int)), "'distance_penalty_pct' must be numeric"

    assert "recommendation" in summary, "Missing 'recommendation' in summary"
    assert isinstance(summary["recommendation"], str), "'recommendation' must be a string"
    assert len(summary["recommendation"]) > 0, "'recommendation' string must not be empty"


def test_compare_routes_contract_unreachable(mock_cost_map):
    """
    Validate that compare_routes correctly handles an unreachable goal
    (destination completely surrounded by np.inf hazards).
    """
    start = (0, 0)
    goal = (9, 9)

    # Completely wall off goal (9, 9) with np.inf hazards
    unreachable_map = mock_cost_map.copy()
    unreachable_map[8, 8] = np.inf
    unreachable_map[8, 9] = np.inf
    unreachable_map[9, 8] = np.inf
    unreachable_map[9, 9] = np.inf

    res = compare_routes(unreachable_map, start, goal)

    # Assert route failure status and descriptive reason
    route = res["safest"]["route"]
    assert route["success"] is False, "Expected 'success' to be False for unreachable goal"
    assert isinstance(route["reason"], str), "'reason' must be a string describing failure"
    assert len(route["reason"]) > 0, "'reason' string must not be empty"
    assert len(route["path"]) == 0, "'path' must be empty when goal is unreachable"
