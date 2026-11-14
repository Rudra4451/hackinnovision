"""
ODYSSEY VisionScore 2.0: Semantic Terrain Segmentation & Automatic Obstacle Image Alerts.

A modular, efficient, and transparent computer vision subsystem for planetary rover autonomy.
Provides:
- Unified image input adapters (ImageUploadSource, CameraFrameSource).
- Multi-environment profiles (MARS, EARTH, SIMULATION).
- Regional terrain analysis (analyze_terrain).
- Pixel-level semantic terrain segmentation (segment_terrain).
- Automatic obstacle event detection, cooldown deduplication, and image alerts (ObstacleEventDetector).
- Integration with Member 2 DEM/cost_map and Member 1/3 candidate path safety scoring.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from visionscore.config import (
    AlertConfig,
    DEFAULT_ENVIRONMENT_PARAMETERS,
    EnvironmentParameters,
    EnvironmentProfile,
    SEMANTIC_COLOR_PALETTE,
    SEMANTIC_TRAVERSABILITY_MAP,
    SemanticClass,
    VisionConfig,
    VisualTerrainClass,
)
from visionscore.image_input import (
    BaseCameraStream,
    CameraFrameSource,
    CameraPermissionError,
    CameraUnavailableError,
    EmptyImageError,
    ImageInputHandler,
    ImageMetadata,
    ImageUploadSource,
    InvalidImageError,
    SimulatedCameraFeed,
    UnifiedImage,
    UnsupportedResolutionError,
    VisionInputError,
)
from visionscore.analyzer import (
    AnalysisResult,
    BaseTerrainModel,
    DemoVisualTerrainModel,
    TerrainSegment,
    analyze_terrain,
    get_default_analyzer,
)
from visionscore.semantic import (
    BaseSegmentationModel,
    DemoSemanticSegmentationModel,
    SemanticSegmentationResult,
    segment_terrain,
)
from visionscore.obstacle_detector import (
    ObstacleAlert,
    ObstacleEventDetector,
    get_obstacle_detector,
)
from visionscore.terrain_integration import (
    evaluate_candidate_path_safety,
    integrate_visual_obstacle,
)
from visionscore.results import VisualResults

__version__ = "2.0.0"
__all__ = [
    # Configuration & Profiles
    "EnvironmentProfile",
    "VisualTerrainClass",
    "SemanticClass",
    "SEMANTIC_COLOR_PALETTE",
    "SEMANTIC_TRAVERSABILITY_MAP",
    "EnvironmentParameters",
    "VisionConfig",
    "AlertConfig",
    "DEFAULT_ENVIRONMENT_PARAMETERS",
    # Input Exceptions
    "VisionInputError",
    "InvalidImageError",
    "EmptyImageError",
    "UnsupportedResolutionError",
    "CameraUnavailableError",
    "CameraPermissionError",
    # Unified Image Data Model
    "UnifiedImage",
    "ImageMetadata",
    # Input Adapters
    "ImageUploadSource",
    "CameraFrameSource",
    "BaseCameraStream",
    "SimulatedCameraFeed",
    "ImageInputHandler",
    # Analysis Interface & Models
    "AnalysisResult",
    "TerrainSegment",
    "BaseTerrainModel",
    "DemoVisualTerrainModel",
    "analyze_terrain",
    "get_default_analyzer",
    # Semantic Segmentation
    "BaseSegmentationModel",
    "DemoSemanticSegmentationModel",
    "SemanticSegmentationResult",
    "segment_terrain",
    # Obstacle Detection & Alerts
    "ObstacleAlert",
    "ObstacleEventDetector",
    "get_obstacle_detector",
    # Terrain Intelligence Integration
    "integrate_visual_obstacle",
    "evaluate_candidate_path_safety",
    # Results Interface
    "VisualResults",
]
