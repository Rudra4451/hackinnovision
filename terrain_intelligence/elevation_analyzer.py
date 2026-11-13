"""Elevation analysis module for planetary topography.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple
import numpy as np

from terrain_intelligence.config import SIMULATION_NOTICE


@dataclass
class ElevationMetrics:
    """Statistical summary of terrain elevation.

    Attributes:
        min_m: Minimum elevation in meters.
        max_m: Maximum elevation in meters.
        mean_m: Mean elevation in meters.
        median_m: Median elevation in meters.
        std_m: Standard deviation of elevation in meters.
        variance_m2: Variance of elevation in square meters.
        span_m: Total elevation relief / dynamic range (max - min).
        iqr_m: Interquartile range (75th percentile - 25th percentile).
        hypsometric_integral: Dimensionless geomorphic index (mean - min) / (max - min).
        percentiles: Selected percentiles (p10, p25, p50, p75, p90).
        notice: Simulation notice.
    """
    min_m: float
    max_m: float
    mean_m: float
    median_m: float
    std_m: float
    variance_m2: float
    span_m: float
    iqr_m: float
    hypsometric_integral: float
    percentiles: Dict[str, float]
    notice: str = SIMULATION_NOTICE

    def to_dict(self) -> Dict[str, float]:
        """Convert metrics to a flat dictionary for reporting or logging."""
        d = {
            "min_m": self.min_m,
            "max_m": self.max_m,
            "mean_m": self.mean_m,
            "median_m": self.median_m,
            "std_m": self.std_m,
            "variance_m2": self.variance_m2,
            "span_m": self.span_m,
            "iqr_m": self.iqr_m,
            "hypsometric_integral": self.hypsometric_integral,
        }
        for k, v in self.percentiles.items():
            d[f"percentile_{k}"] = v
        return d

    def to_dataframe(self) -> Any:
        """Convert metrics into a Pandas DataFrame if available, else dict."""
        try:
            import pandas as pd
            return pd.DataFrame([self.to_dict()])
        except Exception:
            return self.to_dict()


class ElevationAnalyzer:
    """Analyzes 2D elevation grids for geomorphic characteristics."""

    @staticmethod
    def analyze(elevation: np.ndarray) -> ElevationMetrics:
        """Computes comprehensive statistical metrics on the elevation field.

        Args:
            elevation: 2D numpy array of elevation values.

        Returns:
            ElevationMetrics dataclass.
        """
        if elevation.ndim != 2:
            raise ValueError(f"Elevation array must be 2D, got shape {elevation.shape}")

        min_val = float(np.min(elevation))
        max_val = float(np.max(elevation))
        mean_val = float(np.mean(elevation))
        median_val = float(np.median(elevation))
        std_val = float(np.std(elevation))
        var_val = float(np.var(elevation))
        span_val = max_val - min_val

        p10, p25, p50, p75, p90 = [
            float(p) for p in np.percentile(elevation, [10, 25, 50, 75, 90])
        ]
        iqr_val = p75 - p25

        # Hypsometric integral: HI = (mean - min) / (max - min)
        hi = (mean_val - min_val) / span_val if span_val > 1e-8 else 0.5

        percentiles_dict = {
            "p10": p10,
            "p25": p25,
            "p50": p50,
            "p75": p75,
            "p90": p90,
        }

        return ElevationMetrics(
            min_m=min_val,
            max_m=max_val,
            mean_m=mean_val,
            median_m=median_val,
            std_m=std_val,
            variance_m2=var_val,
            span_m=span_val,
            iqr_m=iqr_val,
            hypsometric_integral=float(hi),
            percentiles=percentiles_dict,
        )

    @staticmethod
    def extract_profile(
        elevation: np.ndarray,
        start_cell: Tuple[int, int],
        end_cell: Tuple[int, int],
        num_points: int = 100,
        resolution_m: float = 1.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Extracts a continuous 1D elevation profile along a transect between two cells.

        Args:
            elevation: 2D elevation grid.
            start_cell: (row, col) start index.
            end_cell: (row, col) end index.
            num_points: Number of sampling points along the transect line.
            resolution_m: Ground sampling resolution in meters.

        Returns:
            Tuple of (distance_along_line_m, sampled_elevation_m).
        """
        r0, c0 = start_cell
        r1, c1 = end_cell

        rows = np.linspace(r0, r1, num_points)
        cols = np.linspace(c0, c1, num_points)

        # Bilinear interpolation or nearest neighbor sampling
        r_idx = np.clip(np.round(rows).astype(int), 0, elevation.shape[0] - 1)
        c_idx = np.clip(np.round(cols).astype(int), 0, elevation.shape[1] - 1)
        sampled_elev = elevation[r_idx, c_idx]

        step_dist = np.sqrt(((rows - r0) * resolution_m) ** 2 + ((cols - c0) * resolution_m) ** 2)
        return step_dist, sampled_elev

    @staticmethod
    def normalize(elevation: np.ndarray, mode: str = "minmax") -> np.ndarray:
        """Normalizes elevation data into standard numerical ranges.

        Args:
            elevation: 2D numpy array.
            mode: 'minmax' scales to [0, 1]; 'zscore' centers to mean 0, std 1.

        Returns:
            Normalized 2D array.
        """
        if mode == "minmax":
            span = np.ptp(elevation)
            return (elevation - np.min(elevation)) / (span if span > 1e-8 else 1.0)
        elif mode == "zscore":
            std = np.std(elevation)
            return (elevation - np.mean(elevation)) / (std if std > 1e-8 else 1.0)
        else:
            raise ValueError(f"Unknown normalization mode: '{mode}'. Supported: 'minmax', 'zscore'")


def analyze_elevation(elevation: np.ndarray) -> ElevationMetrics:
    """Convenience function to compute elevation metrics."""
    return ElevationAnalyzer.analyze(elevation)
