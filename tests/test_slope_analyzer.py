"""Unit tests for slope and gradient analysis component."""

import numpy as np
import pytest
from terrain_intelligence import (
    SlopeAnalyzer,
    analyze_slope,
    generate_terrain,
)


def test_slope_flat_terrain():
    """Verify that flat horizontal terrain produces zero gradients and 0° slope."""
    flat = np.ones((100, 100), dtype=np.float64) * 42.0
    report = analyze_slope(flat, resolution_m=1.0)

    assert report.shape == (100, 100)
    assert report.min_slope_deg == pytest.approx(0.0, abs=1e-6)
    assert report.max_slope_deg == pytest.approx(0.0, abs=1e-6)
    assert report.mean_slope_deg == pytest.approx(0.0, abs=1e-6)
    np.testing.assert_allclose(report.grad_x, 0.0, atol=1e-6)
    np.testing.assert_allclose(report.grad_y, 0.0, atol=1e-6)


def test_slope_analytical_45_degree_ramp():
    """Verify slope math on a synthetic 45-degree ramp where dz/dx = 1.0 (rise = run)."""
    # X ramp: elevation rises 1 meter per column index
    _, cols = 100, 100
    ramp = np.tile(np.arange(cols, dtype=np.float64), (100, 1))
    report = analyze_slope(ramp, resolution_m=1.0)

    # In the interior (away from boundary effects), grad_x should be 1.0 and slope 45 degrees
    interior_slope = report.slope_deg[5:95, 5:95]
    np.testing.assert_allclose(interior_slope, 45.0, atol=1e-5)
    np.testing.assert_allclose(report.grad_x[5:95, 5:95], 1.0, atol=1e-5)
    np.testing.assert_allclose(report.grad_y[5:95, 5:95], 0.0, atol=1e-5)


def test_slope_threshold_fractions():
    """Verify caution and hazard fraction calculations."""
    terrain = generate_terrain(seed=42)
    report = analyze_slope(terrain.elevation, caution_thresh_deg=12.0, hazard_thresh_deg=20.0)

    assert 0.0 <= report.caution_fraction <= 1.0
    assert 0.0 <= report.hazard_fraction <= 1.0
    assert report.caution_fraction + report.hazard_fraction <= 1.0
    assert report.min_slope_deg >= 0.0
    assert report.max_slope_deg <= 90.0


def test_slope_aspect_range():
    """Verify terrain downhill aspect angles are within [0, 360) degrees."""
    terrain = generate_terrain(seed=42)
    report = analyze_slope(terrain.elevation)

    assert np.all(report.aspect_deg >= 0.0)
    assert np.all(report.aspect_deg < 360.0)
