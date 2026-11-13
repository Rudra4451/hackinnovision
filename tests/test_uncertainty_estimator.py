"""Unit tests for terrain uncertainty estimation component."""

import numpy as np
import pytest
from terrain_intelligence import (
    UncertaintyEstimator,
    estimate_uncertainty,
    generate_terrain,
)


def test_uncertainty_bounds_and_shape():
    """Verify uncertainty map is strictly clamped within [0.0, 1.0] and has shape (100, 100)."""
    terrain = generate_terrain(seed=42)
    report = estimate_uncertainty(terrain.elevation, seed=42)

    assert report.shape == (100, 100)
    assert np.all(report.uncertainty_map >= 0.0)
    assert np.all(report.uncertainty_map <= 1.0)
    assert np.all(report.confidence_map >= 0.0)
    assert np.all(report.confidence_map <= 1.0)


def test_confidence_complementarity():
    """Verify confidence is the exact mathematical complement of uncertainty."""
    terrain = generate_terrain(seed=42)
    report = estimate_uncertainty(terrain.elevation, seed=42)

    sum_map = report.uncertainty_map + report.confidence_map
    np.testing.assert_allclose(sum_map, 1.0, atol=1e-7)


def test_uncertainty_distance_growth():
    """Verify uncertainty is lower near the sensor origin and increases radially outward."""
    flat = np.zeros((100, 100))
    origin = (50, 50)
    report = estimate_uncertainty(flat, sensor_origin=origin, seed=42)

    near_origin = report.uncertainty_map[48:52, 48:52]
    far_corner = report.uncertainty_map[0:5, 0:5]

    assert np.mean(near_origin) < np.mean(far_corner)


def test_uncertainty_reproducibility():
    """Verify reproducible uncertainty generation with identical random seed."""
    terrain = generate_terrain(seed=42)
    u1 = estimate_uncertainty(terrain.elevation, seed=99)
    u2 = estimate_uncertainty(terrain.elevation, seed=99)

    np.testing.assert_allclose(u1.uncertainty_map, u2.uncertainty_map)
