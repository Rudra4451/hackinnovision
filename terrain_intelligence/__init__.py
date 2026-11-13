"""Odyssey Terrain Intelligence Package.

Autonomous Mars Rover Hackathon Project - Member 2 Module.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from terrain_intelligence.config import (
    SIMULATION_NOTICE,
    TerrainClass,
    TerrainConfig,
)
from terrain_intelligence.cost_map_generator import (
    CostMapGenerator,
    CostMapReport,
    generate_cost_map,
)
from terrain_intelligence.elevation_analyzer import (
    ElevationAnalyzer,
    ElevationMetrics,
    analyze_elevation,
)
from terrain_intelligence.obstacle_detector import (
    ObstacleDetector,
    ObstacleReport,
    detect_obstacles,
)
from terrain_intelligence.pipeline import (
    TerrainIntelligenceResult,
    TerrainPipeline,
)
from terrain_intelligence.slope_analyzer import (
    SlopeAnalyzer,
    SlopeReport,
    analyze_slope,
)
from terrain_intelligence.terrain_classifier import (
    ClassificationReport,
    TerrainClassifier,
    classify_terrain,
)
from terrain_intelligence.terrain_generator import (
    TerrainData,
    TerrainGenerator,
    generate_terrain,
)
from terrain_intelligence.uncertainty_estimator import (
    UncertaintyEstimator,
    UncertaintyReport,
    estimate_uncertainty,
)
from terrain_intelligence.visualizer import TerrainVisualizer

__version__ = "1.0.0"
__author__ = "Odyssey Terrain Intelligence Engineer (Member 2)"

__all__ = [
    # Config
    "SIMULATION_NOTICE",
    "TerrainClass",
    "TerrainConfig",
    # Generator
    "TerrainData",
    "TerrainGenerator",
    "generate_terrain",
    # Elevation
    "ElevationMetrics",
    "ElevationAnalyzer",
    "analyze_elevation",
    # Slope
    "SlopeReport",
    "SlopeAnalyzer",
    "analyze_slope",
    # Obstacles
    "ObstacleReport",
    "ObstacleDetector",
    "detect_obstacles",
    # Classification
    "ClassificationReport",
    "TerrainClassifier",
    "classify_terrain",
    # Cost Map
    "CostMapReport",
    "CostMapGenerator",
    "generate_cost_map",
    # Uncertainty
    "UncertaintyReport",
    "UncertaintyEstimator",
    "estimate_uncertainty",
    # Visualizer
    "TerrainVisualizer",
    # Integrated Pipeline
    "TerrainIntelligenceResult",
    "TerrainPipeline",
]
