"""Terrain generation module for synthetic Martian topography.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy import ndimage

from terrain_intelligence.config import SIMULATION_NOTICE, TerrainConfig


@dataclass
class TerrainFeatureMetadata:
    """Metadata describing geological features seeded in the synthetic landscape."""
    hills: List[Dict[str, float]] = field(default_factory=list)
    craters: List[Dict[str, float]] = field(default_factory=list)
    flat_center: Tuple[int, int] = (0, 0)
    rocky_center: Tuple[int, int] = (0, 0)


@dataclass
class TerrainData:
    """Container for generated terrain elevation and associated metadata."""
    elevation: np.ndarray  # 2D array of elevation in meters
    resolution_m: float
    seed: Optional[int]
    metadata: Dict[str, Any]
    notice: str = SIMULATION_NOTICE

    @property
    def shape(self) -> Tuple[int, int]:
        return self.elevation.shape


class TerrainGenerator:
    """Generates synthetic, physically plausible Martian landscapes."""

    def __init__(self, config: Optional[TerrainConfig] = None):
        self.config = config or TerrainConfig()

    def generate(
        self,
        shape: Optional[Tuple[int, int]] = None,
        seed: Optional[int] = None,
        resolution_m: Optional[float] = None,
        num_hills: int = 5,
        num_craters: int = 4,
    ) -> TerrainData:
        """Generates a reproducible 2D synthetic Martian elevation grid.

        The terrain combines:
        1. Base undulation (multi-octave filtered noise representing regional topography).
        2. Prominent Martian hills (Gaussian positive elevation mounds).
        3. Impact craters (spherical depressions with raised ejecta rims).
        4. Smooth flat plains (damped variance region).
        5. Rocky chaotic regions (high-frequency roughness).

        Args:
            shape: Grid dimensions (rows, cols). Defaults to config.grid_shape (100, 100).
            seed: RNG seed for reproducible generation. Defaults to config.seed.
            resolution_m: Ground sampling distance in meters. Defaults to config.resolution_m.
            num_hills: Number of distinct hills to synthesize.
            num_craters: Number of impact craters with raised rims to place.

        Returns:
            TerrainData instance containing the 100x100 elevation array and metadata.
        """
        grid_shape = shape or self.config.grid_shape
        rng_seed = self.config.seed if seed is None else seed
        res = resolution_m or self.config.resolution_m

        rng = np.random.default_rng(rng_seed)
        rows, cols = grid_shape

        # Coordinate meshgrid in meters
        y_coords = np.arange(rows, dtype=np.float64) * res
        x_coords = np.arange(cols, dtype=np.float64) * res
        xx, yy = np.meshgrid(x_coords, y_coords)

        # 1. Base topography: Multi-octave synthetic smoothed crustal noise
        elevation = np.zeros(grid_shape, dtype=np.float64)
        octaves = [(25.0, 3.5), (12.0, 1.5), (5.0, 0.5)]  # (sigma_cells, amplitude_m)
        for sigma, amp in octaves:
            white_noise = rng.standard_normal(grid_shape)
            filtered = ndimage.gaussian_filter(white_noise, sigma=sigma, mode="reflect")
            # Normalize filtered noise to standard deviation 1 then scale
            if np.std(filtered) > 1e-6:
                filtered = (filtered - np.mean(filtered)) / np.std(filtered)
            elevation += filtered * amp

        feature_meta = TerrainFeatureMetadata()

        # 2. Prominent Martian Hills (Mounds)
        for _ in range(num_hills):
            hr = rng.uniform(0.15 * rows, 0.85 * rows) * res
            hc = rng.uniform(0.15 * cols, 0.85 * cols) * res
            h_amp = rng.uniform(3.5, 7.5)  # height in meters
            h_sigma = rng.uniform(10.0, 22.0) * res  # spread in meters
            dist_sq = (xx - hc) ** 2 + (yy - hr) ** 2
            elevation += h_amp * np.exp(-dist_sq / (2.0 * (h_sigma ** 2)))
            feature_meta.hills.append({
                "center_m": (float(hr), float(hc)),
                "height_m": float(h_amp),
                "radius_m": float(h_sigma)
            })

        # 3. Impact Craters (Bowl depression + raised rim)
        for _ in range(num_craters):
            cr = rng.uniform(0.2 * rows, 0.8 * rows) * res
            cc = rng.uniform(0.2 * cols, 0.8 * cols) * res
            c_radius = rng.uniform(8.0, 18.0) * res  # meters
            c_depth = rng.uniform(2.5, 6.0)  # meters
            c_rim_height = c_depth * 0.28  # raised rim height

            dist = np.sqrt((xx - cc) ** 2 + (yy - cr) ** 2)

            # Central cavity depression
            depression = -c_depth * np.exp(-((dist / (0.75 * c_radius)) ** 2))

            # Raised circular ejecta rim
            rim_width = 0.25 * c_radius
            rim = c_rim_height * np.exp(-(((dist - c_radius) / rim_width) ** 2))

            elevation += (depression + rim)
            feature_meta.craters.append({
                "center_m": (float(cr), float(cc)),
                "radius_m": float(c_radius),
                "depth_m": float(c_depth),
                "rim_height_m": float(c_rim_height)
            })

        # 4. Flat Region: Smooth plains (e.g. landing basin)
        flat_r = rng.integers(int(0.2 * rows), int(0.5 * rows))
        flat_c = rng.integers(int(0.2 * cols), int(0.5 * cols))
        flat_radius = 20.0 * res
        dist_flat = np.sqrt((xx - flat_c * res) ** 2 + (yy - flat_r * res) ** 2)
        flat_mask = np.clip(1.0 - (dist_flat / flat_radius), 0.0, 1.0)
        flat_weight = flat_mask ** 2

        # Flatten elevation inside the flat plain towards local mean
        local_mean = float(np.mean(elevation[dist_flat < flat_radius])) if np.any(dist_flat < flat_radius) else 0.0
        elevation = (1.0 - 0.85 * flat_weight) * elevation + (0.85 * flat_weight) * local_mean
        feature_meta.flat_center = (int(flat_r), int(flat_c))

        # 5. Rocky Region: High-frequency roughness zone
        rocky_r = rng.integers(int(0.5 * rows), int(0.85 * rows))
        rocky_c = rng.integers(int(0.5 * cols), int(0.85 * cols))
        rocky_radius = 22.0 * res
        dist_rocky = np.sqrt((xx - rocky_c * res) ** 2 + (yy - rocky_r * res) ** 2)
        rocky_weight = np.clip(1.0 - (dist_rocky / rocky_radius), 0.0, 1.0)

        high_freq_noise = rng.standard_normal(grid_shape) * 0.4
        elevation += high_freq_noise * rocky_weight
        feature_meta.rocky_center = (int(rocky_r), int(rocky_c))

        # Baseline offset from config
        elevation += self.config.base_elevation_m

        meta = {
            "simulation_notice": SIMULATION_NOTICE,
            "seed": rng_seed,
            "grid_shape": grid_shape,
            "resolution_m": res,
            "num_hills": num_hills,
            "num_craters": num_craters,
            "elevation_min_m": float(np.min(elevation)),
            "elevation_max_m": float(np.max(elevation)),
            "elevation_mean_m": float(np.mean(elevation)),
            "elevation_std_m": float(np.std(elevation)),
            "features": feature_meta,
        }

        return TerrainData(
            elevation=elevation,
            resolution_m=res,
            seed=rng_seed,
            metadata=meta,
        )


def generate_terrain(
    shape: Tuple[int, int] = (100, 100),
    seed: int = 42,
    resolution_m: float = 1.0,
    **kwargs,
) -> TerrainData:
    """Convenience functional wrapper to generate a 100x100 synthetic Mars landscape."""
    gen = TerrainGenerator(TerrainConfig(grid_shape=shape, seed=seed, resolution_m=resolution_m))
    return gen.generate(shape=shape, seed=seed, resolution_m=resolution_m, **kwargs)
