"""Unit tests for obstacle detection and clustering component."""

import numpy as np
import pytest
from terrain_intelligence import (
    ObstacleDetector,
    detect_obstacles,
    generate_terrain,
)


def test_obstacle_detector_shape_and_dtype():
    """Verify output shape and types of obstacle mask and density maps."""
    terrain = generate_terrain(seed=42)
    report = detect_obstacles(terrain.elevation, seed=42)

    assert report.shape == (100, 100)
    assert report.obstacle_mask.dtype == bool
    assert report.obstacle_density.dtype == np.float64
    assert np.all(report.obstacle_density >= 0.0)
    assert np.all(report.obstacle_density <= 1.0)


def test_obstacle_reproducibility():
    """Verify obstacle detection produces identical results with the same random seed."""
    terrain = generate_terrain(seed=42)
    r1 = detect_obstacles(terrain.elevation, seed=101)
    r2 = detect_obstacles(terrain.elevation, seed=101)

    np.testing.assert_array_equal(r1.obstacle_mask, r2.obstacle_mask)
    np.testing.assert_allclose(r1.obstacle_density, r2.obstacle_density)
    assert r1.num_clusters == r2.num_clusters


def test_obstacle_clustering():
    """Verify spatial cluster identification and connectivity."""
    terrain = generate_terrain(seed=42)
    report = detect_obstacles(terrain.elevation, seed=42, num_boulder_fields=5)

    assert report.num_clusters >= 1
    assert len(report.cluster_sizes) == report.num_clusters
    assert sum(report.cluster_sizes) == report.total_obstacle_cells
    assert np.max(report.cluster_labels) == report.num_clusters


def test_obstacle_summary():
    """Verify obstacle statistical summary output."""
    terrain = generate_terrain(seed=42)
    report = detect_obstacles(terrain.elevation, seed=42)
    summary = report.summary()

    assert "total_obstacle_cells" in summary
    assert "num_clusters" in summary
    assert 0.0 <= summary["obstacle_fraction"] <= 1.0
