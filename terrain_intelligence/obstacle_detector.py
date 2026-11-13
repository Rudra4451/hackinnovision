"""Obstacle detection and spatial clustering module for planetary rovers.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import ndimage

from terrain_intelligence.config import SIMULATION_NOTICE, TerrainConfig


@dataclass
class ObstacleReport:
    """Detailed results of obstacle detection and cluster analysis.

    Attributes:
        obstacle_mask: 2D boolean array where True indicates an impassable obstacle cell.
        obstacle_density: 2D float array in [0.0, 1.0] representing spatial rock/boulder concentration.
        cluster_labels: 2D integer array where each distinct obstacle group has a unique integer ID (0 = background).
        num_clusters: Total count of distinct contiguous obstacle clusters detected.
        total_obstacle_cells: Total number of impassable obstacle cells in the grid.
        obstacle_fraction: Fraction of grid cells occupied by obstacles.
        cluster_sizes: List containing cell counts for each identified cluster.
        notice: Simulation notice.
    """
    obstacle_mask: np.ndarray
    obstacle_density: np.ndarray
    cluster_labels: np.ndarray
    num_clusters: int
    total_obstacle_cells: int
    obstacle_fraction: float
    cluster_sizes: List[int] = field(default_factory=list)
    notice: str = SIMULATION_NOTICE

    @property
    def shape(self) -> Tuple[int, int]:
        return self.obstacle_mask.shape

    def summary(self) -> Dict[str, float]:
        """Statistical summary of detected obstacles."""
        max_sz = max(self.cluster_sizes) if self.cluster_sizes else 0
        mean_sz = float(np.mean(self.cluster_sizes)) if self.cluster_sizes else 0.0
        return {
            "total_obstacle_cells": float(self.total_obstacle_cells),
            "obstacle_fraction": self.obstacle_fraction,
            "num_clusters": float(self.num_clusters),
            "max_cluster_size": float(max_sz),
            "mean_cluster_size": mean_sz,
        }


class ObstacleDetector:
    """Detects and clusters rocky obstacles, boulders, and impassable terrain features."""

    def __init__(self, config: Optional[TerrainConfig] = None):
        self.config = config or TerrainConfig()

    def generate_obstacles(
        self,
        elevation: np.ndarray,
        seed: Optional[int] = None,
        num_boulder_fields: int = 4,
        base_density_threshold: float = 0.55,
    ) -> ObstacleReport:
        """Generates realistic spatial obstacle clusters on top of terrain topography.

        Martian boulders naturally aggregate in geological cluster fields (e.g. crater ejecta,
        talus slopes, and rock pavement). This method uses a Neyman-Scott style spatial clustering
        process modulated by elevation roughness to position boulders realistically.

        Args:
            elevation: 2D terrain elevation array (100x100).
            seed: RNG seed for reproducible obstacle placement. Defaults to config.seed.
            num_boulder_fields: Number of spatial cluster epicenters (boulder fields).
            base_density_threshold: Probability cutoff above which discrete rocks form.

        Returns:
            ObstacleReport with binary mask, continuous density map, and cluster labels.
        """
        if elevation.ndim != 2:
            raise ValueError(f"Elevation array must be 2D, got shape {elevation.shape}")

        rng_seed = self.config.seed if seed is None else seed
        rng = np.random.default_rng(rng_seed)
        rows, cols = elevation.shape

        # 1. Continuous spatial density map via Gaussian cluster superposition
        density_field = np.zeros((rows, cols), dtype=np.float64)

        # Coordinate grid
        yy, xx = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")

        for _ in range(num_boulder_fields):
            cr = rng.uniform(0.1 * rows, 0.9 * rows)
            cc = rng.uniform(0.1 * cols, 0.9 * cols)
            spread = rng.uniform(4.0, 10.0)
            amplitude = rng.uniform(0.6, 1.0)
            dist_sq = (yy - cr) ** 2 + (xx - cc) ** 2
            density_field += amplitude * np.exp(-dist_sq / (2.0 * (spread ** 2)))

        # Also add background geological roughness from elevation laplacian/high-frequency
        laplacian = np.abs(ndimage.laplace(elevation))
        if np.ptp(laplacian) > 1e-6:
            laplacian_norm = (laplacian - np.min(laplacian)) / np.ptp(laplacian)
        else:
            laplacian_norm = np.zeros_like(laplacian)

        density_field += 0.3 * laplacian_norm

        # Normalize density field to [0.0, 1.0]
        if np.ptp(density_field) > 1e-6:
            density_field = (density_field - np.min(density_field)) / np.ptp(density_field)
        else:
            density_field = np.zeros_like(density_field)

        # 2. Discrete obstacle mask: Stochastic sampling based on local density
        # Rock occurrence probability scales with spatial density
        random_sample = rng.uniform(0.0, 1.0, size=(rows, cols))
        obstacle_mask = (density_field > base_density_threshold) & (random_sample < (density_field ** 1.5))

        # Morphological closing to create contiguous boulder formations / rock slabs
        structuring_element = ndimage.generate_binary_structure(2, 2)  # 8-connectivity
        obstacle_mask = ndimage.binary_closing(obstacle_mask, structure=structuring_element, iterations=1)

        # 3. Connected-component labeling for spatial cluster analysis
        cluster_labels, num_clusters = ndimage.label(obstacle_mask, structure=structuring_element)

        # Compute cluster sizes
        cluster_sizes = []
        if num_clusters > 0:
            sizes = ndimage.sum(obstacle_mask, cluster_labels, range(1, num_clusters + 1))
            cluster_sizes = [int(s) for s in np.atleast_1d(sizes)]

        total_obs = int(np.count_nonzero(obstacle_mask))
        obs_fraction = float(total_obs / (rows * cols))

        return ObstacleReport(
            obstacle_mask=obstacle_mask,
            obstacle_density=density_field,
            cluster_labels=cluster_labels,
            num_clusters=num_clusters,
            total_obstacle_cells=total_obs,
            obstacle_fraction=obs_fraction,
            cluster_sizes=cluster_sizes,
        )


def detect_obstacles(
    elevation: np.ndarray,
    seed: int = 42,
    num_boulder_fields: int = 4,
    base_density_threshold: float = 0.55,
) -> ObstacleReport:
    """Convenience function to generate obstacle fields and spatial clusters."""
    detector = ObstacleDetector(TerrainConfig(seed=seed))
    return detector.generate_obstacles(
        elevation,
        seed=seed,
        num_boulder_fields=num_boulder_fields,
        base_density_threshold=base_density_threshold,
    )
