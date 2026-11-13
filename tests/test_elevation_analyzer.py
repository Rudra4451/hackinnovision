"""Unit tests for elevation analysis component."""

import numpy as np
import pytest
from terrain_intelligence import (
    ElevationAnalyzer,
    analyze_elevation,
    generate_terrain,
)


def test_elevation_metrics_computation():
    """Verify statistical metrics on a known synthetic matrix."""
    # Create simple 100x100 ramp
    grid = np.arange(10000, dtype=np.float64).reshape(100, 100)
    metrics = analyze_elevation(grid)

    assert metrics.min_m == 0.0
    assert metrics.max_m == 9999.0
    assert metrics.mean_m == pytest.approx(4999.5, abs=0.1)
    assert metrics.span_m == 9999.0
    assert metrics.hypsometric_integral == pytest.approx(0.5, abs=0.01)
    assert metrics.percentiles["p50"] == pytest.approx(metrics.median_m, abs=1.0)


def test_elevation_analyzer_dataframe_export():
    """Verify conversion of elevation metrics to Pandas DataFrame."""
    terrain = generate_terrain(seed=42)
    metrics = analyze_elevation(terrain.elevation)
    df = metrics.to_dataframe()

    assert not df.empty
    assert "min_m" in df.columns
    assert "max_m" in df.columns
    assert "hypsometric_integral" in df.columns
    assert len(df) == 1


def test_elevation_normalization():
    """Verify min-max and z-score elevation normalization methods."""
    terrain = generate_terrain(seed=42)
    elev = terrain.elevation

    norm_minmax = ElevationAnalyzer.normalize(elev, mode="minmax")
    assert np.min(norm_minmax) == pytest.approx(0.0, abs=1e-7)
    assert np.max(norm_minmax) == pytest.approx(1.0, abs=1e-7)

    norm_zscore = ElevationAnalyzer.normalize(elev, mode="zscore")
    assert np.mean(norm_zscore) == pytest.approx(0.0, abs=1e-7)
    assert np.std(norm_zscore) == pytest.approx(1.0, abs=1e-7)


def test_elevation_profile_extraction():
    """Verify 1D transect profile extraction across the terrain."""
    terrain = generate_terrain(seed=42)
    dist, profile = ElevationAnalyzer.extract_profile(
        terrain.elevation,
        start_cell=(0, 0),
        end_cell=(99, 99),
        num_points=100,
        resolution_m=1.0,
    )

    assert len(dist) == 100
    assert len(profile) == 100
    assert dist[0] == 0.0
    assert dist[-1] > 100.0  # hypot(99, 99) ≈ 140 m
    assert np.all(np.diff(dist) > 0)  # monotonically increasing distance
