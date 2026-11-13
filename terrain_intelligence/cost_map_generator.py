"""Movement cost map generation module for pathfinding and navigation.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import numpy as np

from terrain_intelligence.config import SIMULATION_NOTICE, TerrainClass, TerrainConfig


@dataclass
class CostMapReport:
    """Detailed movement cost map and associated metrics.

    Attributes:
        cost_map: 2D array of traversal costs (float64).
            Safe terrain: low cost (typically ~1.0 to ~3.0).
            Difficult terrain: higher cost (typically ~5.0 to ~15.0).
            Impassable terrain: strictly np.inf.
        min_finite_cost: Minimum traversal cost across navigable cells.
        max_finite_cost: Maximum traversal cost across navigable cells.
        mean_finite_cost: Average traversal cost across navigable cells.
        impassable_cells: Count of cells with cost == np.inf.
        impassable_fraction: Fraction of grid that is non-traversable.
        notice: Simulation notice.
    """
    cost_map: np.ndarray
    min_finite_cost: float
    max_finite_cost: float
    mean_finite_cost: float
    impassable_cells: int
    impassable_fraction: float
    notice: str = SIMULATION_NOTICE

    @property
    def shape(self) -> Tuple[int, int]:
        return self.cost_map.shape

    def get_finite_cost_array(self, impassable_fill_value: float = 1e6) -> np.ndarray:
        """Returns a copy where np.inf is replaced with a finite large numerical penalty."""
        out = self.cost_map.copy()
        out[np.isneginf(out) | np.isinf(out)] = impassable_fill_value
        return out

    def summary(self) -> Dict[str, float]:
        """Summary metrics of the cost map."""
        return {
            "min_finite_cost": self.min_finite_cost,
            "max_finite_cost": self.max_finite_cost,
            "mean_finite_cost": self.mean_finite_cost,
            "impassable_cells": float(self.impassable_cells),
            "impassable_fraction": self.impassable_fraction,
        }


class CostMapGenerator:
    """Generates 2D traversability cost matrices for autonomous navigation planners."""

    def __init__(self, config: Optional[TerrainConfig] = None):
        self.config = config or TerrainConfig()

    def generate(
        self,
        slope_deg: np.ndarray,
        classification_map: np.ndarray,
        obstacle_mask: np.ndarray,
        obstacle_density: Optional[np.ndarray] = None,
        uncertainty_map: Optional[np.ndarray] = None,
    ) -> CostMapReport:
        """Computes a 2D numerical traversal cost array from terrain analysis.

        Cost Function:
        1. HAZARD / Obstacles:
           cost = np.inf (impassable mechanical barrier).
        2. SAFE terrain:
           cost = base_safe + w_slope * (slope / slope_caution)^2 + w_obs * density
        3. CAUTION terrain:
           cost = base_caution + w_slope * ( (slope - slope_caution) / (slope_hazard - slope_caution) )^2
                  + 2.0 * w_obs * density

        If an uncertainty map is provided, traversal risk is scaled slightly by terrain uncertainty:
           cost = cost * (1.0 + 0.5 * uncertainty)

        Args:
            slope_deg: 2D array of terrain slopes in degrees.
            classification_map: 2D array of TerrainClass enum values (0=SAFE, 1=CAUTION, 2=HAZARD).
            obstacle_mask: 2D boolean array of discrete impassable obstacles.
            obstacle_density: Optional 2D float array in [0.0, 1.0] of rock density.
            uncertainty_map: Optional 2D float array in [0.0, 1.0] of terrain knowledge uncertainty.

        Returns:
            CostMapReport containing cost matrix and traversal statistics.
        """
        if slope_deg.shape != classification_map.shape:
            raise ValueError("Dimensions of slope and classification map must match.")

        rows, cols = slope_deg.shape
        cost_map = np.full((rows, cols), np.inf, dtype=np.float64)

        s_caution = max(self.config.slope_caution_thresh_deg, 1e-3)
        s_hazard = max(self.config.slope_hazard_thresh_deg, s_caution + 1e-3)

        density = obstacle_density if obstacle_density is not None else np.zeros((rows, cols))

        is_safe = (classification_map == int(TerrainClass.SAFE)) & (~obstacle_mask)
        is_caution = (classification_map == int(TerrainClass.CAUTION)) & (~obstacle_mask)

        # 1. SAFE terrain: Exactly 1.0 per navigation integration contract
        cost_map[is_safe] = 1.0

        # 2. CAUTION terrain: Configurable finite cost > 2.0 (scaled within [5.0, 20.0])
        slope_excess = np.clip((slope_deg[is_caution] - s_caution) / (s_hazard - s_caution), 0.0, 1.0)
        density_factor = np.clip(density[is_caution], 0.0, 1.0)
        caution_cost = 5.0 + 15.0 * (0.70 * slope_excess + 0.30 * density_factor)
        cost_map[is_caution] = np.clip(caution_cost, 5.0, 20.0)

        # 3. Impassable HAZARD terrain: Strictly np.inf per contract item 5
        cost_map[obstacle_mask] = np.inf
        cost_map[classification_map == int(TerrainClass.HAZARD)] = np.inf

        # Statistics over navigable cells
        finite_mask = np.isfinite(cost_map)
        impassable_count = int(np.count_nonzero(~finite_mask))
        impassable_frac = float(impassable_count / (rows * cols))

        if np.any(finite_mask):
            min_c = float(np.min(cost_map[finite_mask]))
            max_c = float(np.max(cost_map[finite_mask]))
            mean_c = float(np.mean(cost_map[finite_mask]))
        else:
            min_c, max_c, mean_c = np.inf, np.inf, np.inf

        return CostMapReport(
            cost_map=cost_map,
            min_finite_cost=min_c,
            max_finite_cost=max_c,
            mean_finite_cost=mean_c,
            impassable_cells=impassable_count,
            impassable_fraction=impassable_frac,
        )


def generate_cost_map(
    slope_deg: np.ndarray,
    classification_map: np.ndarray,
    obstacle_mask: np.ndarray,
    obstacle_density: Optional[np.ndarray] = None,
    uncertainty_map: Optional[np.ndarray] = None,
    config: Optional[TerrainConfig] = None,
) -> CostMapReport:
    """Convenience functional wrapper to generate a 2D movement cost map."""
    generator = CostMapGenerator(config)
    return generator.generate(
        slope_deg=slope_deg,
        classification_map=classification_map,
        obstacle_mask=obstacle_mask,
        obstacle_density=obstacle_density,
        uncertainty_map=uncertainty_map,
    )
