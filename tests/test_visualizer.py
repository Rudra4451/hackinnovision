"""Unit tests for visualization component."""

from pathlib import Path
import numpy as np
import pytest
from terrain_intelligence import (
    TerrainPipeline,
    TerrainVisualizer,
)


def test_visualizer_generates_files(tmp_path):
    """Verify all visualizer methods successfully generate output image and HTML files."""
    viz = TerrainVisualizer(output_dir=tmp_path)

    # Synthetic arrays
    elev = np.ones((50, 50)) * 10.0
    slope = np.zeros((50, 50))
    obs = np.zeros((50, 50), dtype=bool)
    obs[10, 10] = True
    density = np.zeros((50, 50))
    cls_map = np.zeros((50, 50), dtype=np.int8)
    cost = np.ones((50, 50))
    cost[10, 10] = np.inf
    unc = np.zeros((50, 50))

    p_elev = viz.plot_elevation(elev)
    p_slope = viz.plot_slope(slope)
    p_obs = viz.plot_obstacles(obs, density)
    p_cls = viz.plot_classification(cls_map)
    p_cost = viz.plot_cost_map(cost)
    p_unc = viz.plot_uncertainty(unc)
    p_dash = viz.plot_dashboard(elev, slope, obs, density, cls_map, cost, unc)
    p_static3d = viz.plot_3d_static(elev)
    p_plotly = viz.create_3d_interactive(elev)

    for p in [p_elev, p_slope, p_obs, p_cls, p_cost, p_unc, p_dash, p_static3d, p_plotly]:
        assert p.exists()
        assert p.stat().st_size > 0
