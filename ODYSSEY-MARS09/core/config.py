"""
ODYSSEY MARS-09: Mission Configuration and Environment Constants
Lead Software Architect Specification
"""

from typing import Tuple

# Environment & Grid Boundaries
GRID_SIZE: int = 100
START_POSITION: Tuple[int, int] = (5, 5)
GOAL_POSITION: Tuple[int, int] = (90, 90)

# Hazard & Navigation Constraints
MAX_SLOPE: float = 30.0  # Maximum traversable slope in degrees
OBSTACLE_COST: float = float("inf")  # Non-traversable cost penalty

# Rover Vehicle Dynamics
ROVER_MASS_KG: float = 185.0
MAX_SPEED_MPS: float = 0.05  # Meters per second
BATTERY_CAPACITY_WH: float = 1200.0  # Watt-hours
ENERGY_PER_STEP_BASE_WH: float = 1.2
SOL_DURATION_SECONDS: int = 300
