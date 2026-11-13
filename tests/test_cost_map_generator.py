"""Unit tests for movement cost map generation component."""

import numpy as np
import pytest
from terrain_intelligence import (
    TerrainClass,
    TerrainConfig,
    generate_cost_map,
)


def test_cost_map_impassable_infinity():
    """Verify that hazard and obstacle cells are strictly assigned np.inf."""
    slope = np.zeros((10, 10))
    cls_map = np.zeros((10, 10), dtype=np.int8)
    obstacles = np.zeros((10, 10), dtype=bool)

    # Set cell (2, 2) as HAZARD
    cls_map[2, 2] = int(TerrainClass.HAZARD)
    # Set cell (5, 5) with obstacle
    obstacles[5, 5] = True

    report = generate_cost_map(slope, cls_map, obstacles)
    cost = report.cost_map

    assert np.isinf(cost[2, 2])
    assert np.isinf(cost[5, 5])
    assert cost[2, 2] > 0
    assert cost[5, 5] > 0


def test_cost_map_traversable_costs():
    """Verify relative traversal costs: safe < caution < hazard."""
    slope = np.zeros((10, 10))
    cls_map = np.zeros((10, 10), dtype=np.int8)
    obstacles = np.zeros((10, 10), dtype=bool)

    cls_map[0, 0] = int(TerrainClass.SAFE)
    cls_map[0, 1] = int(TerrainClass.CAUTION)
    cls_map[0, 2] = int(TerrainClass.HAZARD)

    report = generate_cost_map(slope, cls_map, obstacles)
    cost = report.cost_map

    assert np.isfinite(cost[0, 0])
    assert np.isfinite(cost[0, 1])
    assert np.isinf(cost[0, 2])

    # Safe should be strictly lower cost than caution
    assert cost[0, 0] < cost[0, 1]
    assert cost[0, 0] == 1.0  # Safe must be exactly 1.0 per contract
    assert cost[0, 1] > 2.0   # Caution must be > 2.0 per contract


def test_cost_map_finite_fill_method():
    """Verify method that substitutes infinity with a finite surrogate for specific algorithms."""
    slope = np.zeros((10, 10))
    cls_map = np.zeros((10, 10), dtype=np.int8)
    cls_map[3, 3] = int(TerrainClass.HAZARD)
    obstacles = np.zeros((10, 10), dtype=bool)

    report = generate_cost_map(slope, cls_map, obstacles)
    finite_arr = report.get_finite_cost_array(impassable_fill_value=9999.0)

    assert np.all(np.isfinite(finite_arr))
    assert finite_arr[3, 3] == 9999.0


def test_cost_map_no_negative_or_nan():
    """Verify cost map never produces negative values or NaNs."""
    slope = np.random.uniform(0.0, 30.0, (100, 100))
    cls_map = np.random.choice([0, 1, 2], size=(100, 100))
    obstacles = np.random.uniform(0.0, 1.0, (100, 100)) > 0.90
    density = np.random.uniform(0.0, 1.0, (100, 100))
    uncertainty = np.random.uniform(0.0, 1.0, (100, 100))

    report = generate_cost_map(
        slope,
        cls_map,
        obstacles,
        obstacle_density=density,
        uncertainty_map=uncertainty,
    )

    cost = report.cost_map
    assert not np.any(np.isnan(cost))
    assert np.all(cost > 0.0)
