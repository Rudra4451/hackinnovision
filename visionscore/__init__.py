"""
ODYSSEY VisionScore: Visual Terrain Scoring and Explainability Module (Stage 1).

A modular, efficient, and transparent computer vision subsystem for planetary rover autonomy.
Provides unified image input adapters (ImageUploadSource, CameraFrameSource), environmental
profiles (MARS, EARTH, SIMULATION), and a replaceable terrain analysis interface (analyze_terrain).

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from visionscore.config import (
    DEFAULT_ENVIRONMENT_PARAMETERS,
    EnvironmentParameters,
    EnvironmentProfile,
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
from visionscore.results import VisualResults

__version__ = "1.0.0"
__all__ = [
    # Configuration & Profiles
    "EnvironmentProfile",
    "VisualTerrainClass",
    "EnvironmentParameters",
    "VisionConfig",
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
    # Analysis Interface & Models
    "AnalysisResult",
    "TerrainSegment",
    "BaseTerrainModel",
    "DemoVisualTerrainModel",
    "analyze_terrain",
    "get_default_analyzer",
    # Results Interface
    "VisualResults",
]
