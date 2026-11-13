"""Slope and gradient analysis module for planetary surface navigation.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import numpy as np

from terrain_intelligence.config import SIMULATION_NOTICE, TerrainConfig


@dataclass
class SlopeReport:
    """Detailed results of terrain slope analysis.

    Attributes:
        slope_deg: 2D array of slope angles in degrees (0 to 90).
        grad_x: 2D array of spatial elevation gradient along columns (X-axis, m/m).
        grad_y: 2D array of spatial elevation gradient along rows (Y-axis, m/m).
        aspect_deg: 2D array of terrain downhill aspect in degrees (0-360 clockwise from North).
        min_slope_deg: Minimum slope angle across the grid.
        max_slope_deg: Maximum slope angle across the grid.
        mean_slope_deg: Mean slope angle across the grid.
        median_slope_deg: Median slope angle across the grid.
        std_slope_deg: Standard deviation of slope angles.
        caution_fraction: Fraction of cells exceeding caution threshold but below hazard.
        hazard_fraction: Fraction of cells exceeding hazard rollover threshold.
        resolution_m: Ground sampling resolution in meters.
        notice: Simulation notice.
    """
    slope_deg: np.ndarray
    grad_x: np.ndarray
    grad_y: np.ndarray
    aspect_deg: np.ndarray
    min_slope_deg: float
    max_slope_deg: float
    mean_slope_deg: float
    median_slope_deg: float
    std_slope_deg: float
    caution_fraction: float
    hazard_fraction: float
    resolution_m: float
    notice: str = SIMULATION_NOTICE

    @property
    def shape(self) -> Tuple[int, int]:
        return self.slope_deg.shape

    def summary(self) -> Dict[str, float]:
        """Returns statistical summary of slope metrics."""
        return {
            "min_slope_deg": self.min_slope_deg,
            "max_slope_deg": self.max_slope_deg,
            "mean_slope_deg": self.mean_slope_deg,
            "median_slope_deg": self.median_slope_deg,
            "std_slope_deg": self.std_slope_deg,
            "caution_fraction": self.caution_fraction,
            "hazard_fraction": self.hazard_fraction,
        }


class SlopeAnalyzer:
    """Computes spatial derivatives, gradient vectors, and slope angles."""

    def __init__(self, config: Optional[TerrainConfig] = None):
        self.config = config or TerrainConfig()

    def analyze(
        self,
        elevation: np.ndarray,
        resolution_m: Optional[float] = None,
        caution_thresh_deg: Optional[float] = None,
        hazard_thresh_deg: Optional[float] = None,
    ) -> SlopeReport:
        """Calculates gradients in X and Y directions, slope angles, and aspect.

        The slope at point (x, y) is calculated using central difference numerical differentiation:
            grad_x = d(elevation)/dx
            grad_y = d(elevation)/dy
            gradient_magnitude = sqrt(grad_x^2 + grad_y^2)
            slope_deg = arctan(gradient_magnitude) * (180 / pi)

        Args:
            elevation: 2D array of elevation values in meters.
            resolution_m: Distance between adjacent cells in meters.
            caution_thresh_deg: Threshold in degrees defining caution zone.
            hazard_thresh_deg: Threshold in degrees defining hazardous rollover zone.

        Returns:
            SlopeReport containing gradients, slope array, aspect, and summary statistics.
        """
        if elevation.ndim != 2:
            raise ValueError(f"Elevation array must be 2D, got shape {elevation.shape}")

        res = resolution_m if resolution_m is not None else self.config.resolution_m
        c_thresh = caution_thresh_deg if caution_thresh_deg is not None else self.config.slope_caution_thresh_deg
        h_thresh = hazard_thresh_deg if hazard_thresh_deg is not None else self.config.slope_hazard_thresh_deg

        # Gradient along rows (axis 0 -> Y) and cols (axis 1 -> X)
        # Note: np.gradient returns [d_axis0, d_axis1]
        grad_y, grad_x = np.gradient(elevation, res)

        # Gradient magnitude (rise over run)
        grad_mag = np.hypot(grad_x, grad_y)

        # Slope in degrees (0 to 90 degrees)
        slope_rad = np.arctan(grad_mag)
        slope_deg = np.rad2deg(slope_rad)

        # Aspect: Compass direction of steepest descent (0 = North, 90 = East, etc.)
        # Downslope vector points in direction of negative gradient (-grad_x, -grad_y)
        aspect_rad = np.arctan2(-grad_x, -grad_y)
        aspect_deg = (np.rad2deg(aspect_rad) + 360.0) % 360.0

        min_s = float(np.min(slope_deg))
        max_s = float(np.max(slope_deg))
        mean_s = float(np.mean(slope_deg))
        median_s = float(np.median(slope_deg))
        std_s = float(np.std(slope_deg))

        total_cells = float(elevation.size)
        caution_cells = np.count_nonzero((slope_deg >= c_thresh) & (slope_deg < h_thresh))
        hazard_cells = np.count_nonzero(slope_deg >= h_thresh)

        return SlopeReport(
            slope_deg=slope_deg,
            grad_x=grad_x,
            grad_y=grad_y,
            aspect_deg=aspect_deg,
            min_slope_deg=min_s,
            max_slope_deg=max_s,
            mean_slope_deg=mean_s,
            median_slope_deg=median_s,
            std_slope_deg=std_s,
            caution_fraction=float(caution_cells / total_cells),
            hazard_fraction=float(hazard_cells / total_cells),
            resolution_m=res,
        )


def analyze_slope(
    elevation: np.ndarray,
    resolution_m: float = 1.0,
    caution_thresh_deg: float = 12.0,
    hazard_thresh_deg: float = 20.0,
) -> SlopeReport:
    """Convenience function to compute slope and gradients."""
    analyzer = SlopeAnalyzer(TerrainConfig(
        resolution_m=resolution_m,
        slope_caution_thresh_deg=caution_thresh_deg,
        slope_hazard_thresh_deg=hazard_thresh_deg,
    ))
    return analyzer.analyze(elevation)
