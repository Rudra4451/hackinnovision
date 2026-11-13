"""Terrain traversability classification module for autonomous rover guidance.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import numpy as np

from terrain_intelligence.config import SIMULATION_NOTICE, TerrainClass, TerrainConfig


@dataclass
class ClassificationReport:
    """Summary and 2D arrays of terrain classification.

    Attributes:
        classification_map: 2D integer array where values match TerrainClass enum:
            0 = SAFE
            1 = CAUTION
            2 = HAZARD
        safe_mask: 2D boolean mask for safe cells.
        caution_mask: 2D boolean mask for caution cells.
        hazard_mask: 2D boolean mask for hazard cells.
        safe_fraction: Fraction of total cells classified as SAFE.
        caution_fraction: Fraction of total cells classified as CAUTION.
        hazard_fraction: Fraction of total cells classified as HAZARD.
        total_cells: Total cell count in the grid.
        notice: Simulation notice.
    """
    classification_map: np.ndarray
    safe_mask: np.ndarray
    caution_mask: np.ndarray
    hazard_mask: np.ndarray
    safe_fraction: float
    caution_fraction: float
    hazard_fraction: float
    total_cells: int
    notice: str = SIMULATION_NOTICE

    @property
    def shape(self) -> Tuple[int, int]:
        return self.classification_map.shape

    def summary(self) -> Dict[str, float]:
        """Returns classification percentage and count statistics."""
        return {
            "safe_fraction": self.safe_fraction,
            "caution_fraction": self.caution_fraction,
            "hazard_fraction": self.hazard_fraction,
            "safe_cells": float(np.sum(self.safe_mask)),
            "caution_cells": float(np.sum(self.caution_mask)),
            "hazard_cells": float(np.sum(self.hazard_mask)),
            "total_cells": float(self.total_cells),
        }


class TerrainClassifier:
    """Classifies grid cells into SAFE, CAUTION, or HAZARD based on slope and obstacles."""

    def __init__(self, config: Optional[TerrainConfig] = None):
        self.config = config or TerrainConfig()

    def classify(
        self,
        slope_deg: np.ndarray,
        obstacle_mask: np.ndarray,
        obstacle_density: Optional[np.ndarray] = None,
        slope_caution_thresh_deg: Optional[float] = None,
        slope_hazard_thresh_deg: Optional[float] = None,
        density_caution_thresh: Optional[float] = None,
        density_hazard_thresh: Optional[float] = None,
    ) -> ClassificationReport:
        """Classifies every cell of a 100x100 grid into SAFE, CAUTION, or HAZARD.

        Classification Rules:
        1. HAZARD:
           - Direct obstacle present (obstacle_mask == True), OR
           - Slope >= slope_hazard_thresh_deg (rollover risk), OR
           - Obstacle density >= density_hazard_thresh (impassable boulder field).
        2. CAUTION (if not HAZARD):
           - Slope >= slope_caution_thresh_deg, OR
           - Obstacle density >= density_caution_thresh.
        3. SAFE:
           - All other terrain cells with nominal slope and low obstacle presence.

        Args:
            slope_deg: 2D array of slope in degrees.
            obstacle_mask: 2D boolean array of discrete impassable obstacles.
            obstacle_density: Optional 2D float array of local rock density [0, 1].
            slope_caution_thresh_deg: Override for caution slope threshold.
            slope_hazard_thresh_deg: Override for hazard slope threshold.
            density_caution_thresh: Override for caution rock density threshold.
            density_hazard_thresh: Override for hazard rock density threshold.

        Returns:
            ClassificationReport containing classification map and breakdown metrics.
        """
        if slope_deg.shape != obstacle_mask.shape:
            raise ValueError(
                f"Shape mismatch: slope {slope_deg.shape} vs obstacle {obstacle_mask.shape}"
            )

        s_caution = (
            slope_caution_thresh_deg
            if slope_caution_thresh_deg is not None
            else self.config.slope_caution_thresh_deg
        )
        s_hazard = (
            slope_hazard_thresh_deg
            if slope_hazard_thresh_deg is not None
            else self.config.slope_hazard_thresh_deg
        )
        d_caution = (
            density_caution_thresh
            if density_caution_thresh is not None
            else self.config.obstacle_density_caution
        )
        d_hazard = (
            density_hazard_thresh
            if density_hazard_thresh is not None
            else self.config.obstacle_density_hazard
        )

        rows, cols = slope_deg.shape
        total_cells = rows * cols

        # 1. Compute Hazard condition
        is_hazard = obstacle_mask.copy()
        is_hazard |= (slope_deg >= s_hazard)
        if obstacle_density is not None:
            is_hazard |= (obstacle_density >= d_hazard)

        # 2. Compute Caution condition (excluding existing hazard cells)
        is_caution = (slope_deg >= s_caution)
        if obstacle_density is not None:
            is_caution |= (obstacle_density >= d_caution)
        is_caution &= (~is_hazard)

        # 3. Safe condition
        is_safe = (~is_hazard) & (~is_caution)

        # Construct discrete integer classification map
        # SAFE = 0, CAUTION = 1, HAZARD = 2
        class_map = np.zeros(slope_deg.shape, dtype=np.int8)
        class_map[is_caution] = int(TerrainClass.CAUTION)
        class_map[is_hazard] = int(TerrainClass.HAZARD)

        safe_count = int(np.sum(is_safe))
        caution_count = int(np.sum(is_caution))
        hazard_count = int(np.sum(is_hazard))

        # Integrity assertion: every cell must be partitioned into exactly one class
        assert safe_count + caution_count + hazard_count == total_cells, "Partitioning mismatch!"

        return ClassificationReport(
            classification_map=class_map,
            safe_mask=is_safe,
            caution_mask=is_caution,
            hazard_mask=is_hazard,
            safe_fraction=float(safe_count / total_cells),
            caution_fraction=float(caution_count / total_cells),
            hazard_fraction=float(hazard_count / total_cells),
            total_cells=total_cells,
        )


def classify_terrain(
    slope_deg: np.ndarray,
    obstacle_mask: np.ndarray,
    obstacle_density: Optional[np.ndarray] = None,
    slope_caution_thresh_deg: float = 12.0,
    slope_hazard_thresh_deg: float = 20.0,
) -> ClassificationReport:
    """Convenience function to classify terrain."""
    classifier = TerrainClassifier(TerrainConfig(
        slope_caution_thresh_deg=slope_caution_thresh_deg,
        slope_hazard_thresh_deg=slope_hazard_thresh_deg,
    ))
    return classifier.classify(
        slope_deg=slope_deg,
        obstacle_mask=obstacle_mask,
        obstacle_density=obstacle_density,
    )
