"""Coordinate conversions, file loaders, and formatting helpers."""
from typing import Tuple


def grid_to_world_coords(grid_pos: Tuple[int, int], resolution_m: float = 1.0) -> Tuple[float, float]:
    return (grid_pos[0] * resolution_m, grid_pos[1] * resolution_m)
