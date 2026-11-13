"""
Terrain Intelligence integration module for MARS-09 autonomous rover.

Exposes the standardized Member 2 / Member 3 integration API:
    from core.terrain import build_terrain_intelligence
    terrain = build_terrain_intelligence(seed=42)
    cost_map = terrain["cost_map"]

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from typing import Any, Dict, Optional, Tuple
import numpy as np

from core.costmap import create_cost_map, create_risk_map
from terrain_intelligence.config import SIMULATION_NOTICE, TerrainConfig
from terrain_intelligence.elevation_analyzer import ElevationAnalyzer
from terrain_intelligence.obstacle_detector import ObstacleDetector
from terrain_intelligence.slope_analyzer import SlopeAnalyzer
from terrain_intelligence.terrain_classifier import TerrainClassifier
from terrain_intelligence.terrain_generator import TerrainGenerator
from terrain_intelligence.uncertainty_estimator import UncertaintyEstimator


def build_terrain_intelligence(
    seed: int = 42,
    shape: Tuple[int, int] = (100, 100),
    resolution_m: float = 1.0,
    slope_caution_thresh_deg: float = 12.0,
    slope_hazard_thresh_deg: float = 20.0,
    caution_min_cost: float = 5.0,
    caution_max_cost: float = 20.0,
    elevation_override: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Build and execute the complete Terrain Intelligence module.

    Produces all topographical layers and the Member 3 compliant cost_map.

    Parameters:
        seed: Random seed for deterministic reproducibility.
        shape: Grid dimensions (row, col). Nominally (100, 100).
        resolution_m: Ground sampling resolution in meters per cell (default 1.0 m).
        slope_caution_thresh_deg: Slope defining caution threshold (default 12.0°).
        slope_hazard_thresh_deg: Slope defining rollover hazard (default 20.0°).
        caution_min_cost: Minimum cost for caution cells (> 2.0, default 5.0).
        caution_max_cost: Maximum cost for caution cells (default 20.0).
        elevation_override: Optional external 2D elevation grid.

    Returns:
        terrain: Dictionary containing all terrain maps and metrics:
            - "cost_map": 2D float ndarray (SAFE=1.0, CAUTION=5.0-20.0, HAZARD=np.inf)
            - "risk_map": 2D float ndarray in [0.0, 1.0]
            - "elevation": 2D float ndarray in meters
            - "elevation_map": alias for "elevation"
            - "slope": 2D float ndarray in degrees
            - "slope_map": alias for "slope"
            - "grad_x": 2D float ndarray of elevation gradient dZ/dX
            - "grad_y": 2D float ndarray of elevation gradient dZ/dY
            - "obstacle_mask": 2D boolean ndarray (True=impassable obstacle)
            - "obstacle_density": 2D float ndarray in [0.0, 1.0]
            - "classification": 2D integer ndarray (0=SAFE, 1=CAUTION, 2=HAZARD)
            - "classification_map": alias for "classification"
            - "uncertainty": 2D float ndarray in [0.0, 1.0]
            - "uncertainty_map": alias for "uncertainty"
            - "confidence_map": 2D float ndarray in [0.0, 1.0]
            - "seed": int
            - "shape": Tuple[int, int]
            - "resolution_m": float
            - "metadata": Dict summary of geomorphological features
            - "notice": SIMULATION_NOTICE
    """
    config = TerrainConfig(
        grid_shape=shape,
        resolution_m=resolution_m,
        seed=seed,
        slope_caution_thresh_deg=slope_caution_thresh_deg,
        slope_hazard_thresh_deg=slope_hazard_thresh_deg,
    )

    # 1. Terrain Generation
    if elevation_override is not None:
        if elevation_override.shape != shape:
            raise ValueError(f"Elevation override shape {elevation_override.shape} != requested {shape}")
        elevation = elevation_override.copy().astype(np.float64)
        terrain_meta = {"source": "elevation_override"}
    else:
        gen = TerrainGenerator(config)
        terrain_data = gen.generate(shape=shape, seed=seed, resolution_m=resolution_m)
        elevation = terrain_data.elevation
        terrain_meta = terrain_data.metadata

    # 2. Elevation Analysis
    elev_metrics = ElevationAnalyzer.analyze(elevation)

    # 3. Slope Analysis
    slope_analyzer = SlopeAnalyzer(config)
    slope_report = slope_analyzer.analyze(elevation)
    slope_deg = slope_report.slope_deg

    # 4. Obstacle Detection & Clustering
    obstacle_detector = ObstacleDetector(config)
    obstacle_report = obstacle_detector.generate_obstacles(elevation, seed=seed)
    obstacle_mask = obstacle_report.obstacle_mask
    obstacle_density = obstacle_report.obstacle_density

    # 5. Terrain Classification (0=SAFE, 1=CAUTION, 2=HAZARD)
    classifier = TerrainClassifier(config)
    cls_report = classifier.classify(
        slope_deg=slope_deg,
        obstacle_mask=obstacle_mask,
        obstacle_density=obstacle_density,
    )
    classification_map = cls_report.classification_map

    # 6. Uncertainty Estimation
    unc_estimator = UncertaintyEstimator(config)
    unc_report = unc_estimator.estimate(
        elevation,
        sensor_origin=(shape[0] // 2, shape[1] // 2),
        seed=seed,
    )
    uncertainty_map = unc_report.uncertainty_map

    # 7. Member 3 Navigation Cost Map & Separate Risk Map
    cost_map = create_cost_map(
        classification_map=classification_map,
        slope_deg=slope_deg,
        obstacle_mask=obstacle_mask,
        obstacle_density=obstacle_density,
        caution_min_cost=caution_min_cost,
        caution_max_cost=caution_max_cost,
        slope_caution_thresh_deg=slope_caution_thresh_deg,
        slope_hazard_thresh_deg=slope_hazard_thresh_deg,
    )
    risk_map = create_risk_map(
        slope_deg=slope_deg,
        obstacle_density=obstacle_density,
        uncertainty_map=uncertainty_map,
        obstacle_mask=obstacle_mask,
    )

    return {
        "cost_map": cost_map,
        "risk_map": risk_map,
        "elevation": elevation,
        "elevation_map": elevation,
        "slope": slope_deg,
        "slope_map": slope_deg,
        "grad_x": slope_report.grad_x,
        "grad_y": slope_report.grad_y,
        "aspect_deg": slope_report.aspect_deg,
        "obstacle_mask": obstacle_mask,
        "obstacle_density": obstacle_density,
        "classification": classification_map,
        "classification_map": classification_map,
        "uncertainty": uncertainty_map,
        "uncertainty_map": uncertainty_map,
        "confidence_map": unc_report.confidence_map,
        "seed": seed,
        "shape": shape,
        "resolution_m": resolution_m,
        "metadata": {
            "elevation": elev_metrics.to_dict(),
            "slope": slope_report.summary(),
            "obstacles": obstacle_report.summary(),
            "classification": cls_report.summary(),
            "terrain_features": terrain_meta,
        },
        "notice": SIMULATION_NOTICE,
    }
