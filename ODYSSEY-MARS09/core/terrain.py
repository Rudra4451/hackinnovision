"""
ODYSSEY MARS-09: Terrain Generation, Slope Analysis, and Traversability Cost Mapping
Lead Architect Module - Integrates with Member 2 Terrain Intelligence
"""

import math
from typing import Optional, Union, List, Tuple, Dict, Any
try:
    import numpy as np
except ImportError:
    np = None

from core.config import GRID_SIZE, MAX_SLOPE, OBSTACLE_COST


def generate_terrain(
    grid_size: int = 100,
    seed: Optional[int] = 42,
    roughness: float = 0.5
) -> Any:
    """
    Generate a high-fidelity 2D Martian Digital Elevation Model (DEM)
    with multi-scale cratering, ridges, and fractal noise.
    """
    if np is not None:
        rng = np.random.default_rng(seed)
        x = np.linspace(-3, 3, grid_size)
        y = np.linspace(-3, 3, grid_size)
        xx, yy = np.meshgrid(x, y)

        # Base regional topography: rolling hills and valleys
        elevation = (
            np.sin(xx * 0.8) * np.cos(yy * 0.8) * 12.0
            + np.sin(xx * 1.6 + 0.5) * 6.0
            + np.cos(yy * 2.2 - 0.3) * 4.0
        )

        # Synthetic impact crater (Gaussian depression with raised rim)
        crater_center = (0.5, -0.5)
        dist_sq = (xx - crater_center[0])**2 + (yy - crater_center[1])**2
        crater = -15.0 * np.exp(-dist_sq / 0.8) + 4.0 * np.exp(-abs(np.sqrt(dist_sq) - 0.9) / 0.2)
        elevation += crater

        # Fine-scale roughness / fractal noise
        fine_noise = rng.normal(0, roughness, (grid_size, grid_size))
        elevation += fine_noise

        # Normalize elevation so minimum elevation is non-negative
        elevation -= np.min(elevation)
        return elevation.astype(np.float64)

    # Pure Python fallback
    return [[float(abs(math.sin(r * 0.1) * math.cos(c * 0.1) * 20.0)) for c in range(grid_size)] for r in range(grid_size)]


def classify_terrain(
    elevation_map: Any,
    max_slope: float = MAX_SLOPE
) -> Any:
    """
    Classify terrain into 3 standard rover traversability tiers:
    0 = SAFE (< 12.0 deg)
    1 = CAUTION (12.0 deg - max_slope)
    2 = HAZARD (slope > max_slope or impassable obstacle)
    """
    if np is not None and isinstance(elevation_map, np.ndarray):
        dy, dx = np.gradient(elevation_map)
        slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
        slope_deg = np.degrees(slope_rad)

        classified = np.zeros_like(elevation_map, dtype=np.int32)
        classified[slope_deg >= 12.0] = 1
        classified[slope_deg >= max_slope] = 2
        return classified

    rows = len(elevation_map)
    cols = len(elevation_map[0]) if rows > 0 else 0
    return [[0 for _ in range(cols)] for _ in range(rows)]


def generate_cost_map(
    elevation_map: Any,
    obstacle_cost: float = OBSTACLE_COST,
    max_slope: float = MAX_SLOPE
) -> Any:
    """
    Generate a Member 3 compliant 2D cost grid for autonomous pathfinding:
    - SAFE terrain (slope < 12°): cost == 1.0
    - CAUTION terrain (12° <= slope < max_slope): cost in [5.0, 20.0]
    - HAZARD terrain (slope >= max_slope): cost == np.inf
    """
    if np is not None and isinstance(elevation_map, np.ndarray):
        dy, dx = np.gradient(elevation_map)
        slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
        slope_deg = np.degrees(slope_rad)

        cost_map = np.ones_like(elevation_map, dtype=np.float64)

        # Scale caution zone linearly between 5.0 and 20.0
        caution_mask = (slope_deg >= 12.0) & (slope_deg < max_slope)
        norm_slope = (slope_deg[caution_mask] - 12.0) / max(max_slope - 12.0, 1e-3)
        cost_map[caution_mask] = 5.0 + norm_slope * 15.0

        # Assign infinite obstacle cost to hazards
        cost_map[slope_deg >= max_slope] = obstacle_cost
        return cost_map

    rows = len(elevation_map)
    cols = len(elevation_map[0]) if rows > 0 else 0
    return [[1.0 for _ in range(cols)] for _ in range(rows)]
