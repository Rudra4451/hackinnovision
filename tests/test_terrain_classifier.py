"""Unit tests for terrain traversability classification component."""

import numpy as np
import pytest
from terrain_intelligence import (
    TerrainClass,
    TerrainClassifier,
    classify_terrain,
)


def test_classifier_partition_integrity():
    """Verify that every cell in the 100x100 grid is classified into exactly one class."""
    slope = np.random.uniform(0.0, 30.0, (100, 100))
    obstacles = np.random.uniform(0.0, 1.0, (100, 100)) > 0.90
    density = np.random.uniform(0.0, 1.0, (100, 100))

    report = classify_terrain(slope, obstacles, obstacle_density=density)

    assert report.shape == (100, 100)
    assert report.total_cells == 10000

    # Every cell must have an integer value in {0, 1, 2}
    unique_vals = set(np.unique(report.classification_map))
    assert unique_vals.issubset({0, 1, 2})

    # Mutually exclusive and collectively exhaustive masks
    safe_count = int(np.sum(report.safe_mask))
    caution_count = int(np.sum(report.caution_mask))
    hazard_count = int(np.sum(report.hazard_mask))
    assert safe_count + caution_count + hazard_count == 10000

    # Fractions sum to 1.0
    assert report.safe_fraction + report.caution_fraction + report.hazard_fraction == pytest.approx(1.0, abs=1e-7)


def test_classifier_rules_determinism():
    """Verify that classification rules trigger predictably for synthetic edge cases."""
    shape = (10, 10)
    # Cell (0,0): flat and clear -> SAFE
    # Cell (0,1): caution slope (15°) -> CAUTION
    # Cell (0,2): hazard slope (25°) -> HAZARD
    # Cell (0,3): flat but has direct obstacle -> HAZARD
    # Cell (0,4): flat but extreme obstacle density -> HAZARD

    slope = np.zeros(shape)
    slope[0, 1] = 15.0
    slope[0, 2] = 25.0

    obstacles = np.zeros(shape, dtype=bool)
    obstacles[0, 3] = True

    density = np.zeros(shape)
    density[0, 4] = 0.85  # Exceeds default hazard density threshold of 0.60

    report = classify_terrain(
        slope_deg=slope,
        obstacle_mask=obstacles,
        obstacle_density=density,
        slope_caution_thresh_deg=12.0,
        slope_hazard_thresh_deg=20.0,
    )

    c_map = report.classification_map
    assert c_map[0, 0] == int(TerrainClass.SAFE)
    assert c_map[0, 1] == int(TerrainClass.CAUTION)
    assert c_map[0, 2] == int(TerrainClass.HAZARD)
    assert c_map[0, 3] == int(TerrainClass.HAZARD)
    assert c_map[0, 4] == int(TerrainClass.HAZARD)


def test_classifier_dimension_mismatch_raises():
    """Verify error raised on mismatched array shapes."""
    slope = np.zeros((100, 100))
    obstacles = np.zeros((50, 50), dtype=bool)
    with pytest.raises(ValueError):
        classify_terrain(slope, obstacles)
