"""Configuration parameters and constants for Odyssey Terrain Intelligence.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED FOR
    PLANETARY ROVER SYSTEM VALIDATION. IT DOES NOT REPRESENT ACTUAL
    IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Tuple


class TerrainClass(IntEnum):
    """Terrain traversability classification levels."""
    SAFE = 0
    CAUTION = 1
    HAZARD = 2


SIMULATION_NOTICE: str = (
    "SIMULATED SYNTHETIC MARTIAN TERRAIN DATA. "
    "Designed for autonomous rover navigation algorithm validation. "
    "Not actual planetary mission measurements."
)


@dataclass(frozen=True)
class TerrainConfig:
    """Configuration settings for terrain generation, analysis, and classification.

    Attributes:
        grid_shape: Dimensions of the terrain grid (rows, cols). Default (100, 100).
        resolution_m: Ground sampling distance in meters per grid cell. Default 1.0 m.
        seed: Random seed for deterministic and reproducible generation. Default 42.
        
        # Elevation profile parameters
        base_elevation_m: Nominal datum baseline elevation in meters.
        elevation_range_m: Peak-to-valley variance scale in meters.
        
        # Slope thresholds (Curiosity/Perseverance rover flight engineering guidelines)
        slope_caution_thresh_deg: Slope in degrees where rover must reduce speed and steer cautiously.
        slope_hazard_thresh_deg: Slope in degrees exceeding rover mechanical rollover limit.
        
        # Obstacle thresholds
        obstacle_density_caution: Local rock density threshold for CAUTION classification.
        obstacle_density_hazard: Local rock density threshold for HAZARD classification.
        
        # Cost map weight coefficients
        cost_base_safe: Nominal cost for flat, hazard-free ground traversal.
        cost_base_caution: Base penalty cost for caution zones.
        cost_slope_weight: Quadratic friction penalty multiplier for slope.
        cost_obstacle_weight: Density scaling penalty multiplier for rocky ground.
    """
    grid_shape: Tuple[int, int] = (100, 100)
    resolution_m: float = 1.0
    seed: int = 42

    # Elevation parameters
    base_elevation_m: float = 0.0
    elevation_range_m: float = 25.0

    # Slope thresholds (degrees)
    slope_caution_thresh_deg: float = 12.0
    slope_hazard_thresh_deg: float = 20.0

    # Obstacle density thresholds (fraction [0.0, 1.0])
    obstacle_density_caution: float = 0.30
    obstacle_density_hazard: float = 0.60

    # Cost map parameters
    cost_base_safe: float = 1.0
    cost_base_caution: float = 5.0
    cost_slope_weight: float = 2.5
    cost_obstacle_weight: float = 4.0
