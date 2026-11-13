"""Unit tests for integrated TerrainPipeline execution."""

import numpy as np
import pytest
from terrain_intelligence import (
    TerrainConfig,
    TerrainPipeline,
)


def test_pipeline_end_to_end():
    """Verify complete sequential pipeline run and output integrity."""
    config = TerrainConfig(grid_shape=(100, 100), seed=42)
    pipeline = TerrainPipeline(config)
    result = pipeline.run()

    # All arrays must strictly adhere to 100x100
    assert result.elevation_array.shape == (100, 100)
    assert result.slope_array_deg.shape == (100, 100)
    assert result.obstacle_mask_array.shape == (100, 100)
    assert result.classification_array.shape == (100, 100)
    assert result.movement_cost_array.shape == (100, 100)
    assert result.uncertainty_array.shape == (100, 100)

    # Verification of summary dictionary export
    summary = result.export_summary()
    assert summary["grid_shape"] == [100, 100]
    assert "elevation" in summary
    assert "slope" in summary
    assert "obstacles" in summary
    assert "classification" in summary
    assert "traversal_costs" in summary
    assert "uncertainty" in summary


def test_pipeline_with_elevation_override():
    """Verify that external elevation data (e.g. from orbital DEM) can be fed into pipeline."""
    external_elev = np.zeros((100, 100))
    external_elev[40:60, 40:60] = 15.0  # Synthetic plateau

    pipeline = TerrainPipeline()
    result = pipeline.run(elevation_override=external_elev)

    np.testing.assert_allclose(result.elevation_array, external_elev)
    assert result.elevation_metrics.max_m == 15.0
    assert result.elevation_metrics.min_m == 0.0
