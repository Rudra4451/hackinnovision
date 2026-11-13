"""Terrain uncertainty estimation module for planetary rover perception systems.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import numpy as np
from scipy import ndimage

from terrain_intelligence.config import SIMULATION_NOTICE, TerrainConfig


@dataclass
class UncertaintyReport:
    """Detailed terrain uncertainty assessment.

    Attributes:
        uncertainty_map: 2D array of simulated terrain uncertainty in [0.0, 1.0].
            0.0 = absolute sensor confidence (e.g. nearby verified ground).
            1.0 = total epistemic uncertainty (e.g. occluded, far-range, or shadow).
        confidence_map: 2D array of perceptual confidence (1.0 - uncertainty).
        mean_uncertainty: Average uncertainty value across all grid cells.
        min_uncertainty: Minimum uncertainty observed.
        max_uncertainty: Maximum uncertainty observed.
        high_uncertainty_fraction: Fraction of cells where uncertainty exceeds 0.70.
        sensor_origin: (row, col) coordinates of simulated sensor/rover vantage point.
        notice: Simulation notice.
    """
    uncertainty_map: np.ndarray
    confidence_map: np.ndarray
    mean_uncertainty: float
    min_uncertainty: float
    max_uncertainty: float
    high_uncertainty_fraction: float
    sensor_origin: Tuple[int, int]
    notice: str = SIMULATION_NOTICE

    @property
    def shape(self) -> Tuple[int, int]:
        return self.uncertainty_map.shape

    def summary(self) -> Dict[str, float]:
        """Summary metrics of terrain uncertainty."""
        return {
            "mean_uncertainty": self.mean_uncertainty,
            "min_uncertainty": self.min_uncertainty,
            "max_uncertainty": self.max_uncertainty,
            "high_uncertainty_fraction": self.high_uncertainty_fraction,
            "sensor_r": float(self.sensor_origin[0]),
            "sensor_c": float(self.sensor_origin[1]),
        }


class UncertaintyEstimator:
    """Simulates realistic epistemic and perceptual uncertainty in terrain maps."""

    def __init__(self, config: Optional[TerrainConfig] = None):
        self.config = config or TerrainConfig()

    def estimate(
        self,
        elevation: np.ndarray,
        sensor_origin: Optional[Tuple[int, int]] = None,
        max_range_cells: float = 50.0,
        baseline_orbital_uncertainty: float = 0.20,
        roughness_influence: float = 0.35,
        seed: Optional[int] = None,
    ) -> UncertaintyReport:
        """Simulates spatial uncertainty of terrain knowledge.

        Planetary rover terrain knowledge degrades due to three physical factors:
        1. Range Attenuation: Stereo vision/LiDAR disparity errors grow quadratically with distance.
        2. Topographical Occlusion / Shadow: Crater interior slopes and reverse hill faces
           create grazing angle degradation and shadows.
        3. Local Surface Roughness: High micro-roughness creates stereo mismatch artifacts.

        Args:
            elevation: 2D array of terrain elevation (100x100).
            sensor_origin: (row, col) location of rover/sensor. Default is grid center (50, 50).
            max_range_cells: Distance beyond which in-situ sensor uncertainty saturates to 1.0.
            baseline_orbital_uncertainty: Prior uncertainty from coarse orbital imagery.
            roughness_influence: Sensitivity to local micro-relief roughness.
            seed: RNG seed for stochastic sensor noise.

        Returns:
            UncertaintyReport containing 2D uncertainty and confidence arrays.
        """
        if elevation.ndim != 2:
            raise ValueError(f"Elevation array must be 2D, got shape {elevation.shape}")

        rng_seed = self.config.seed if seed is None else seed
        rng = np.random.default_rng(rng_seed)
        rows, cols = elevation.shape

        origin = sensor_origin or (rows // 2, cols // 2)
        r0, c0 = origin

        # 1. Range attenuation component: quadratic error increase
        yy, xx = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
        distance = np.hypot(yy - r0, xx - c0)
        norm_distance = np.clip(distance / max_range_cells, 0.0, 1.0)
        range_uncertainty = (norm_distance ** 1.8)

        # 2. Topographical occlusion / Grazing angle shadow
        # Approximate line-of-sight slope differential from sensor origin
        dz = elevation - elevation[r0, c0]
        # Distant cells that are lower than intermediate ridges create shadowing
        grad_y, grad_x = np.gradient(elevation, self.config.resolution_m)
        slope_rad = np.arctan(np.hypot(grad_x, grad_y))
        occlusion_risk = np.clip(np.sin(slope_rad) * (norm_distance ** 0.5), 0.0, 1.0)

        # 3. Local surface roughness component (Laplacian magnitude)
        laplacian = np.abs(ndimage.laplace(elevation))
        span_lap = np.ptp(laplacian)
        norm_roughness = (laplacian - np.min(laplacian)) / (span_lap if span_lap > 1e-6 else 1.0)

        # 4. Sensor measurement noise (Gaussian random field)
        noise = rng.normal(0.0, 0.05, size=(rows, cols))

        # Composite uncertainty model
        total_uncertainty = (
            baseline_orbital_uncertainty
            + (1.0 - baseline_orbital_uncertainty) * (
                0.60 * range_uncertainty
                + 0.25 * occlusion_risk
                + roughness_influence * norm_roughness
            )
            + noise
        )

        # Strictly clamp uncertainty between [0.0, 1.0]
        uncertainty_map = np.clip(total_uncertainty, 0.0, 1.0)
        confidence_map = 1.0 - uncertainty_map

        mean_u = float(np.mean(uncertainty_map))
        min_u = float(np.min(uncertainty_map))
        max_u = float(np.max(uncertainty_map))
        high_u_frac = float(np.count_nonzero(uncertainty_map > 0.70) / (rows * cols))

        return UncertaintyReport(
            uncertainty_map=uncertainty_map,
            confidence_map=confidence_map,
            mean_uncertainty=mean_u,
            min_uncertainty=min_u,
            max_uncertainty=max_u,
            high_uncertainty_fraction=high_u_frac,
            sensor_origin=origin,
        )


def estimate_uncertainty(
    elevation: np.ndarray,
    sensor_origin: Optional[Tuple[int, int]] = None,
    seed: int = 42,
) -> UncertaintyReport:
    """Convenience function to generate a terrain uncertainty map."""
    estimator = UncertaintyEstimator(TerrainConfig(seed=seed))
    return estimator.estimate(elevation, sensor_origin=sensor_origin, seed=seed)
