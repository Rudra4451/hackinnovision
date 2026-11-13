"""Unit tests for terrain generation component."""

import numpy as np
import pytest
from terrain_intelligence import (
    SIMULATION_NOTICE,
    TerrainConfig,
    TerrainGenerator,
    generate_terrain,
)


def test_terrain_generator_shape():
    """Verify that generated terrain strictly complies with 100x100 shape specification."""
    data = generate_terrain(shape=(100, 100), seed=42)
    assert data.elevation.shape == (100, 100)
    assert data.elevation.dtype == np.float64
    assert data.shape == (100, 100)


def test_terrain_generator_reproducibility():
    """Verify that identical random seeds produce identical terrain elevation matrices."""
    t1 = generate_terrain(shape=(100, 100), seed=123)
    t2 = generate_terrain(shape=(100, 100), seed=123)
    np.testing.assert_allclose(t1.elevation, t2.elevation, rtol=1e-12)


def test_terrain_generator_seed_divergence():
    """Verify that different random seeds produce different terrains."""
    t1 = generate_terrain(shape=(100, 100), seed=10)
    t2 = generate_terrain(shape=(100, 100), seed=99)
    assert not np.allclose(t1.elevation, t2.elevation)


def test_terrain_generator_morphological_features():
    """Verify presence of crater depressions, hills, and relief dynamic range."""
    data = generate_terrain(shape=(100, 100), seed=42, num_hills=5, num_craters=4)
    elev = data.elevation

    # Dynamic relief range should be positive and realistic (10m - 50m)
    span = np.ptp(elev)
    assert span > 10.0
    assert span < 100.0

    # Verify metadata and simulation notice
    assert data.notice == SIMULATION_NOTICE
    assert "features" in data.metadata
    assert len(data.metadata["features"].hills) == 5
    assert len(data.metadata["features"].craters) == 4


def test_terrain_generator_custom_resolution():
    """Verify generation respects configurable ground sampling resolution."""
    cfg = TerrainConfig(grid_shape=(100, 100), resolution_m=2.5, seed=7)
    gen = TerrainGenerator(cfg)
    data = gen.generate()
    assert data.resolution_m == 2.5
    assert data.elevation.shape == (100, 100)
