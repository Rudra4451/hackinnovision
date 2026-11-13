"""
Global configuration constants for MARS-09 autonomous rover system.
"""

from typing import Tuple

GRID_SIZE: Tuple[int, int] = (100, 100)
START_POSITION: Tuple[int, int] = (0, 0)
GOAL_POSITION: Tuple[int, int] = (99, 99)
OBSTACLE_COST: float = float("inf")

# Terrain slope thresholds (degrees)
SLOPE_CAUTION_THRESHOLD_DEG: float = 12.0
SLOPE_HAZARD_THRESHOLD_DEG: float = 20.0

# Cost mapping parameters
COST_SAFE: float = 1.0
COST_CAUTION_MIN: float = 5.0
COST_CAUTION_MAX: float = 20.0
COST_HAZARD: float = float("inf")
