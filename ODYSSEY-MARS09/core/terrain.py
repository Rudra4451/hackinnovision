"""
Terrain Generation, Classification, and Traversability Cost Mapping
"""

from typing import Optional, Union, List, Any
try:
    import numpy as np
except ImportError:
    np = None

from core.config import GRID_SIZE, MAX_SLOPE, OBSTACLE_COST


def generate_terrain(
    grid_size: int = GRID_SIZE,
    seed: Optional[int] = 42,
    roughness: float = 0.5
) -> Any:
    """
    Generate a 2D synthetic Martian digital elevation model (DEM).

    Returns:
        np.ndarray (or 2D list if numpy is not installed) of shape (grid_size, grid_size).
    """
    if np is not None:
        rng = np.random.default_rng(seed)
        x = np.linspace(0, 10, grid_size)
        y = np.linspace(0, 10, grid_size)
        xx, yy = np.meshgrid(x, y)
        elevation = np.sin(xx / 2.0) * np.cos(yy / 2.0) * 15.0 + rng.normal(0, 0.5, (grid_size, grid_size))
        return elevation.astype(np.float32)
    
    # Fallback to pure Python list structure
    return [[float((r * c) % 25) for c in range(grid_size)] for r in range(grid_size)]


def classify_terrain(
    elevation_map: Any,
    max_slope: float = MAX_SLOPE
) -> Any:
    """
    Classify terrain into traversability zones based on gradient/slope.
    0 = Smooth, 1 = Rough, 2 = Obstacle.

    Returns:
        np.ndarray (or 2D list) of matching shape.
    """
    if np is not None and isinstance(elevation_map, np.ndarray):
        dy, dx = np.gradient(elevation_map)
        slope_degrees = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
        classified = np.zeros_like(elevation_map, dtype=np.int32)
        classified[slope_degrees > 15.0] = 1
        classified[slope_degrees > max_slope] = 2
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
    Generate a traversal cost grid for pathfinding algorithms.

    Returns:
        np.ndarray (or 2D list) of matching shape.
    """
    if np is not None and isinstance(elevation_map, np.ndarray):
        dy, dx = np.gradient(elevation_map)
        slope_degrees = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
        cost_map = 1.0 + (slope_degrees / 5.0)
        cost_map[slope_degrees > max_slope] = obstacle_cost
        return cost_map.astype(np.float64)

    rows = len(elevation_map)
    cols = len(elevation_map[0]) if rows > 0 else 0
    return [[1.0 for _ in range(cols)] for _ in range(rows)]
