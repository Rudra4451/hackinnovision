"""Integrated end-to-end processing pipeline for Odyssey Terrain Intelligence.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np

from terrain_intelligence.config import SIMULATION_NOTICE, TerrainConfig
from terrain_intelligence.cost_map_generator import CostMapGenerator, CostMapReport
from terrain_intelligence.elevation_analyzer import ElevationAnalyzer, ElevationMetrics
from terrain_intelligence.obstacle_detector import ObstacleDetector, ObstacleReport
from terrain_intelligence.slope_analyzer import SlopeAnalyzer, SlopeReport
from terrain_intelligence.terrain_classifier import ClassificationReport, TerrainClassifier
from terrain_intelligence.terrain_generator import TerrainData, TerrainGenerator
from terrain_intelligence.uncertainty_estimator import UncertaintyEstimator, UncertaintyReport
from terrain_intelligence.visualizer import TerrainVisualizer


@dataclass
class TerrainIntelligenceResult:
    """Unified container encapsulating all computed terrain intelligence layers.

    This is the primary object returned to downstream navigation and autonomy modules.
    """
    config: TerrainConfig
    terrain: TerrainData
    elevation_metrics: ElevationMetrics
    slope: SlopeReport
    obstacles: ObstacleReport
    classification: ClassificationReport
    cost_map: CostMapReport
    uncertainty: UncertaintyReport
    notice: str = SIMULATION_NOTICE

    # Direct convenient array accessors
    @property
    def elevation_array(self) -> np.ndarray:
        """100x100 elevation array in meters."""
        return self.terrain.elevation

    @property
    def slope_array_deg(self) -> np.ndarray:
        """100x100 slope angle array in degrees."""
        return self.slope.slope_deg

    @property
    def obstacle_mask_array(self) -> np.ndarray:
        """100x100 boolean obstacle mask."""
        return self.obstacles.obstacle_mask

    @property
    def classification_array(self) -> np.ndarray:
        """100x100 integer traversability array (0=SAFE, 1=CAUTION, 2=HAZARD)."""
        return self.classification.classification_map

    @property
    def movement_cost_array(self) -> np.ndarray:
        """100x100 movement cost array (SAFE=low, CAUTION=higher, HAZARD=inf)."""
        return self.cost_map.cost_map

    @property
    def uncertainty_array(self) -> np.ndarray:
        """100x100 uncertainty array in [0.0, 1.0]."""
        return self.uncertainty.uncertainty_map

    def export_summary(self) -> Dict[str, Any]:
        """Exports an executive summary of terrain analysis for rover mission telemetry."""
        return {
            "notice": self.notice,
            "seed": self.config.seed,
            "grid_shape": list(self.config.grid_shape),
            "resolution_m": self.config.resolution_m,
            "elevation": self.elevation_metrics.to_dict(),
            "slope": self.slope.summary(),
            "obstacles": self.obstacles.summary(),
            "classification": self.classification.summary(),
            "traversal_costs": self.cost_map.summary(),
            "uncertainty": self.uncertainty.summary(),
        }

    def save_all_visualizations(self, output_dir: Union[str, Path] = "outputs") -> Dict[str, Path]:
        """Renders and saves all individual maps, dashboard, and 3D visualizers."""
        viz = TerrainVisualizer(output_dir=output_dir)
        paths = {}
        paths["elevation"] = viz.plot_elevation(self.elevation_array, self.config.resolution_m)
        paths["slope"] = viz.plot_slope(
            self.slope_array_deg,
            self.config.slope_caution_thresh_deg,
            self.config.slope_hazard_thresh_deg,
        )
        paths["obstacles"] = viz.plot_obstacles(
            self.obstacle_mask_array,
            self.obstacles.obstacle_density,
        )
        paths["classification"] = viz.plot_classification(self.classification_array)
        paths["cost_map"] = viz.plot_cost_map(self.movement_cost_array)
        paths["uncertainty"] = viz.plot_uncertainty(
            self.uncertainty_array,
            self.uncertainty.sensor_origin,
        )
        paths["dashboard"] = viz.plot_dashboard(
            self.elevation_array,
            self.slope_array_deg,
            self.obstacle_mask_array,
            self.obstacles.obstacle_density,
            self.classification_array,
            self.movement_cost_array,
            self.uncertainty_array,
        )
        paths["static_3d"] = viz.plot_3d_static(self.elevation_array)
        paths["interactive_3d"] = viz.create_3d_interactive(self.elevation_array)
        return paths


class TerrainPipeline:
    """Full operational pipeline executing all terrain intelligence components."""

    def __init__(self, config: Optional[TerrainConfig] = None):
        self.config = config or TerrainConfig()
        self.generator = TerrainGenerator(self.config)
        self.elevation_analyzer = ElevationAnalyzer()
        self.slope_analyzer = SlopeAnalyzer(self.config)
        self.obstacle_detector = ObstacleDetector(self.config)
        self.classifier = TerrainClassifier(self.config)
        self.cost_generator = CostMapGenerator(self.config)
        self.uncertainty_estimator = UncertaintyEstimator(self.config)

    def run(
        self,
        seed: Optional[int] = None,
        shape: Optional[Tuple[int, int]] = None,
        elevation_override: Optional[np.ndarray] = None,
    ) -> TerrainIntelligenceResult:
        """Executes the full pipeline sequentially.

        Can generate new synthetic terrain or process an externally provided elevation array.

        Args:
            seed: RNG seed for reproducible generation.
            shape: Grid dimensions (rows, cols).
            elevation_override: Optional external elevation array (e.g. from orbit or simulation).

        Returns:
            TerrainIntelligenceResult container.
        """
        active_seed = seed if seed is not None else self.config.seed
        active_shape = shape or self.config.grid_shape

        # Step 1: Terrain Generation
        if elevation_override is not None:
            terrain_data = TerrainData(
                elevation=elevation_override,
                resolution_m=self.config.resolution_m,
                seed=active_seed,
                metadata={"source": "external_override", "notice": SIMULATION_NOTICE},
            )
        else:
            terrain_data = self.generator.generate(shape=active_shape, seed=active_seed)

        elevation = terrain_data.elevation

        # Step 2: Elevation Analysis
        elev_metrics = self.elevation_analyzer.analyze(elevation)

        # Step 3: Slope & Gradient Analysis
        slope_report = self.slope_analyzer.analyze(elevation)

        # Step 4: Obstacle Detection & Spatial Clustering
        obstacle_report = self.obstacle_detector.generate_obstacles(
            elevation,
            seed=active_seed,
        )

        # Step 5: Terrain Classification (SAFE, CAUTION, HAZARD)
        classification_report = self.classifier.classify(
            slope_deg=slope_report.slope_deg,
            obstacle_mask=obstacle_report.obstacle_mask,
            obstacle_density=obstacle_report.obstacle_density,
        )

        # Step 7 (computed before cost so cost can optionally factor it): Uncertainty Estimation
        uncertainty_report = self.uncertainty_estimator.estimate(
            elevation,
            sensor_origin=(active_shape[0] // 2, active_shape[1] // 2),
            seed=active_seed,
        )

        # Step 6: Movement Cost Map (Low, Higher, Infinity)
        cost_report = self.cost_generator.generate(
            slope_deg=slope_report.slope_deg,
            classification_map=classification_report.classification_map,
            obstacle_mask=obstacle_report.obstacle_mask,
            obstacle_density=obstacle_report.obstacle_density,
            uncertainty_map=uncertainty_report.uncertainty_map,
        )

        return TerrainIntelligenceResult(
            config=self.config,
            terrain=terrain_data,
            elevation_metrics=elev_metrics,
            slope=slope_report,
            obstacles=obstacle_report,
            classification=classification_report,
            cost_map=cost_report,
            uncertainty=uncertainty_report,
        )
