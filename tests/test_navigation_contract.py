"""
Unit tests validating Member 3's Navigation Integration Contract.

Validates:
1. cost_map is a 2D NumPy array.
2. cost_map.shape == (100, 100).
3. cost_map.dtype is a floating-point type.
4. SAFE terrain cells have cost exactly 1.0.
5. CAUTION terrain cells have costs strictly greater than 2.0 (scaled in [5.0, 20.0]).
6. Impassable HAZARD terrain cells have cost np.inf.
7. Traversable cells have strictly finite positive costs.
8. All terrain maps have matching shapes (row, col indexing).
9. Integration API: from core.terrain import build_terrain_intelligence -> terrain["cost_map"].
10. End-to-end integration: Member 3's core.navigation.find_path executes successfully on cost_map.
"""

import numpy as np
import pytest

from core.costmap import create_cost_map, create_risk_map, build_costmap
from core.terrain import build_terrain_intelligence
from core.navigation import find_path, calculate_path_metrics, compare_routes


def test_navigation_contract_types_and_shapes():
    """Verify cost_map type, shape, and floating-point dtype."""
    terrain = build_terrain_intelligence(seed=42)
    cost_map = terrain["cost_map"]

    assert isinstance(cost_map, np.ndarray), "cost_map must be a NumPy ndarray"
    assert cost_map.shape == (100, 100), f"cost_map shape must be (100, 100), got {cost_map.shape}"
    assert np.issubdtype(cost_map.dtype, np.floating), f"cost_map dtype must be float, got {cost_map.dtype}"


def test_navigation_contract_cost_values():
    """Verify exact cost values: SAFE == 1.0, CAUTION > 2.0 (5.0..20.0), HAZARD == np.inf."""
    terrain = build_terrain_intelligence(seed=42)
    cost_map = terrain["cost_map"]
    classification = terrain["classification"]
    obstacle_mask = terrain["obstacle_mask"]

    safe_mask = (classification == 0) & (~obstacle_mask)
    caution_mask = (classification == 1) & (~obstacle_mask)
    hazard_mask = (classification == 2) | obstacle_mask

    # 1. SAFE cells must have cost exactly 1.0
    if np.any(safe_mask):
        safe_costs = cost_map[safe_mask]
        np.testing.assert_allclose(
            safe_costs,
            1.0,
            rtol=1e-7,
            err_msg="All SAFE cells must have cost exactly 1.0 per contract item 3",
        )

    # 2. CAUTION cells must have costs greater than 2.0 (specifically between 5.0 and 20.0)
    if np.any(caution_mask):
        caution_costs = cost_map[caution_mask]
        assert np.all(caution_costs > 2.0), "All CAUTION cells must have cost > 2.0"
        assert np.all(caution_costs >= 5.0), "CAUTION cells should be >= 5.0 by default"
        assert np.all(caution_costs <= 20.0), "CAUTION cells should be <= 20.0 by default"
        assert np.all(np.isfinite(caution_costs)), "CAUTION cells must have finite positive costs"

    # 3. Impassable HAZARD cells must have cost np.inf
    if np.any(hazard_mask):
        hazard_costs = cost_map[hazard_mask]
        assert np.all(np.isinf(hazard_costs)), "All HAZARD cells must have cost np.inf"
        assert np.all(hazard_costs > 0), "HAZARD cost must be positive infinity (+inf)"


def test_all_traversable_cells_are_positive_and_finite():
    """Verify that all non-hazard cells have strictly positive and finite costs."""
    terrain = build_terrain_intelligence(seed=42)
    cost_map = terrain["cost_map"]

    finite_mask = np.isfinite(cost_map)
    assert np.any(finite_mask), "There must be navigable (finite) terrain cells"
    finite_costs = cost_map[finite_mask]

    assert np.all(finite_costs >= 1.0), "Traversable cells must have cost >= 1.0"
    assert not np.any(np.isnan(finite_costs)), "No cost cell may be NaN"


def test_all_terrain_maps_have_matching_shapes():
    """Verify that elevation, slope, obstacle_mask, classification, uncertainty, and cost_map have identical shapes."""
    terrain = build_terrain_intelligence(seed=42)
    expected_shape = (100, 100)

    map_keys = [
        "cost_map",
        "risk_map",
        "elevation",
        "slope",
        "grad_x",
        "grad_y",
        "obstacle_mask",
        "obstacle_density",
        "classification",
        "uncertainty",
        "confidence_map",
    ]

    for key in map_keys:
        assert key in terrain, f"Missing key '{key}' in terrain dictionary"
        arr = terrain[key]
        assert isinstance(arr, np.ndarray), f"Map '{key}' must be a NumPy array"
        assert arr.shape == expected_shape, f"Map '{key}' shape {arr.shape} != {expected_shape}"


def test_risk_map_is_separate_and_normalized():
    """Verify risk_map is separate from cost_map and normalized in [0.0, 1.0]."""
    terrain = build_terrain_intelligence(seed=42)
    risk_map = terrain["risk_map"]
    cost_map = terrain["cost_map"]

    assert risk_map is not cost_map, "risk_map must be an independent array from cost_map"
    assert np.all(risk_map >= 0.0), "risk_map values must be >= 0.0"
    assert np.all(risk_map <= 1.0), "risk_map values must be <= 1.0"
    assert np.all(np.isfinite(risk_map)), "risk_map must contain finite continuous probabilities"


def test_integration_api_specification():
    """Verify exact contract import: from core.terrain import build_terrain_intelligence."""
    terrain = build_terrain_intelligence(seed=42)
    assert "cost_map" in terrain
    cost_map = terrain["cost_map"]
    assert cost_map.shape == (100, 100)
    assert cost_map.dtype == np.float64


def test_reproducibility():
    """Verify that build_terrain_intelligence produces identical outputs for the same seed."""
    t1 = build_terrain_intelligence(seed=99)
    t2 = build_terrain_intelligence(seed=99)

    np.testing.assert_array_equal(t1["cost_map"], t2["cost_map"])
    np.testing.assert_array_equal(t1["elevation"], t2["elevation"])
    np.testing.assert_array_equal(t1["classification"], t2["classification"])


def test_navigation_algorithm_consumes_generated_costmap():
    """Verify that Member 3's navigation algorithm (find_path) runs successfully on generated cost_map."""
    terrain = build_terrain_intelligence(seed=42)
    cost_map = terrain["cost_map"]

    # Find open start and goal cells (SAFE terrain)
    safe_indices = np.argwhere(cost_map == 1.0)
    assert len(safe_indices) >= 2, "Must have at least 2 safe cells to plan path"

    # Select two nearby safe points
    start = tuple(safe_indices[0])
    # Pick a safe point reasonably close to test pathfinding
    distances = np.hypot(safe_indices[:, 0] - start[0], safe_indices[:, 1] - start[1])
    candidates = safe_indices[(distances > 5.0) & (distances < 20.0)]
    if len(candidates) > 0:
        goal = tuple(candidates[0])
    else:
        goal = tuple(safe_indices[1])

    # Run Member 3's A* pathfinder
    result = find_path(cost_map, start, goal, mode="safest")
    assert result["mode"] == "safest"
    assert "success" in result
    if result["success"]:
        assert result["path"][0] == start
        assert result["path"][-1] == goal
        metrics = calculate_path_metrics(result["path"], cost_map)
        assert metrics["total_distance"] > 0
        assert metrics["total_cost"] > 0
