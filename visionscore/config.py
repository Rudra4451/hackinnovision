"""
Configuration and Environment Profiles for ODYSSEY VisionScore (Stage 1).

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class EnvironmentProfile(str, Enum):
    """
    Environmental profiles for vision-based terrain analysis.

    Different planetary environments exhibit distinct atmospheric scattering,
    illumination spectra, and surface geology. Earth-trained models cannot be
    assumed to transfer directly to Martian surfaces without calibration.
    """
    MARS = "MARS"
    EARTH = "EARTH"
    SIMULATION = "SIMULATION"


class VisualTerrainClass(str, Enum):
    """Visual traversability categories defined for VisionScore."""
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    HAZARD = "HAZARD"
    UNKNOWN = "UNKNOWN"


class SemanticClass(str, Enum):
    """
    Pixel-level geological and surface semantic categories for VisionScore 2.0.
    Kept strictly distinct from physical traversability classifications.
    """
    ROCK = "ROCK"
    SAND = "SAND"
    SOIL = "SOIL"
    VEGETATION = "VEGETATION"
    WATER = "WATER"
    OBSTACLE = "OBSTACLE"
    UNKNOWN = "UNKNOWN"


# Consistent, publication-grade RGB color palette for semantic visualization
SEMANTIC_COLOR_PALETTE: Dict[SemanticClass, Tuple[int, int, int]] = {
    SemanticClass.ROCK: (128, 128, 128),       # Slate Gray (geological outcrops / boulders)
    SemanticClass.SAND: (237, 201, 137),       # Ochre / Golden Sand (smooth Martian drifts)
    SemanticClass.SOIL: (184, 80, 50),         # Martian Rust Red / Regolith
    SemanticClass.VEGETATION: (46, 204, 113),  # Emerald Green (terrestrial / synthetic)
    SemanticClass.WATER: (52, 152, 219),       # Cyan / Blue (terrestrial / synthetic)
    SemanticClass.OBSTACLE: (231, 76, 60),     # Crimson Red (impassable crags, drop-offs, sharp rocks)
    SemanticClass.UNKNOWN: (108, 52, 131),     # Deep Amethyst Violet (shadows, glare, unclassified)
}

# Mapping from semantic surface classes to candidate traversability tiers
SEMANTIC_TRAVERSABILITY_MAP: Dict[SemanticClass, VisualTerrainClass] = {
    SemanticClass.SAND: VisualTerrainClass.SAFE,
    SemanticClass.SOIL: VisualTerrainClass.SAFE,
    SemanticClass.ROCK: VisualTerrainClass.CAUTION,
    SemanticClass.VEGETATION: VisualTerrainClass.CAUTION,
    SemanticClass.WATER: VisualTerrainClass.HAZARD,
    SemanticClass.OBSTACLE: VisualTerrainClass.HAZARD,
    SemanticClass.UNKNOWN: VisualTerrainClass.UNKNOWN,
}


@dataclass(frozen=True)
class EnvironmentParameters:
    """Optical and geological thresholds specific to an operational environment."""
    name: str
    expected_redness_ratio: float  # (R - B) / (R + B)
    texture_caution_threshold: float
    texture_hazard_threshold: float
    shadow_luminance_max: float    # Pixel luminance below which terrain is shadowed (UNKNOWN)
    saturation_luminance_min: float # Pixel luminance above which terrain is glare-saturated (UNKNOWN)
    description: str
    supported_classes: Tuple[SemanticClass, ...] = (
        SemanticClass.ROCK,
        SemanticClass.SAND,
        SemanticClass.SOIL,
        SemanticClass.OBSTACLE,
        SemanticClass.UNKNOWN,
    )


DEFAULT_ENVIRONMENT_PARAMETERS: Dict[EnvironmentProfile, EnvironmentParameters] = {
    EnvironmentProfile.MARS: EnvironmentParameters(
        name="MARS",
        expected_redness_ratio=0.30,
        texture_caution_threshold=12.0,
        texture_hazard_threshold=28.0,
        shadow_luminance_max=22.0,
        saturation_luminance_min=242.0,
        description="Martian surface profile: basaltic rock, ferric oxide dust, high-contrast shadows.",
        supported_classes=(
            SemanticClass.ROCK,
            SemanticClass.SAND,
            SemanticClass.SOIL,
            SemanticClass.OBSTACLE,
            SemanticClass.UNKNOWN,
        ),
    ),
    EnvironmentProfile.EARTH: EnvironmentParameters(
        name="EARTH",
        expected_redness_ratio=0.08,
        texture_caution_threshold=18.0,
        texture_hazard_threshold=36.0,
        shadow_luminance_max=15.0,
        saturation_luminance_min=248.0,
        description="Terrestrial surface profile: standard daylight scattering, gravel, dirt, and varied albedo.",
        supported_classes=(
            SemanticClass.ROCK,
            SemanticClass.SAND,
            SemanticClass.SOIL,
            SemanticClass.VEGETATION,
            SemanticClass.WATER,
            SemanticClass.OBSTACLE,
            SemanticClass.UNKNOWN,
        ),
    ),
    EnvironmentProfile.SIMULATION: EnvironmentParameters(
        name="SIMULATION",
        expected_redness_ratio=0.22,
        texture_caution_threshold=14.0,
        texture_hazard_threshold=30.0,
        shadow_luminance_max=20.0,
        saturation_luminance_min=245.0,
        description="Synthetic simulation profile: procedurally generated or rendered virtual landscapes.",
        supported_classes=(
            SemanticClass.ROCK,
            SemanticClass.SAND,
            SemanticClass.SOIL,
            SemanticClass.VEGETATION,
            SemanticClass.WATER,
            SemanticClass.OBSTACLE,
            SemanticClass.UNKNOWN,
        ),
    ),
}


@dataclass
class AlertConfig:
    """
    Configuration parameters for automatic obstacle image capture and alerts.

    Attributes:
        min_confidence: Minimum detection confidence to trigger an event alert [0.0 - 1.0].
        min_obstacle_area_pct: Minimum percentage of image pixels occupied by obstacle to trigger.
        cooldown_seconds: Minimum duration (seconds) before emitting another alert for a persistent obstacle.
        dedup_similarity_threshold: Feature similarity threshold (0.0 - 1.0) for identifying identical obstacles.
        storage_dir: Local filesystem directory where captured alert images are persisted.
        max_stored_events: Maximum number of captured events to keep on disk before circular eviction.
        auto_capture_enabled: Master switch for automatic capture on incoming frames.
    """
    min_confidence: float = 0.65
    min_obstacle_area_pct: float = 2.5
    cooldown_seconds: float = 5.0
    dedup_similarity_threshold: float = 0.80
    storage_dir: str = "outputs/obstacle_alerts"
    max_stored_events: int = 50
    auto_capture_enabled: bool = True


@dataclass
class VisionConfig:
    """
    Global configuration for VisionScore Stage 1 image processing.

    Attributes:
        default_environment: Default environment profile.
        max_input_dimension: Maximum image resolution dimension (resizes if exceeded).
        min_input_dimension: Minimum supported image resolution dimension.
        analysis_grid_shape: Subdivision grid (rows, cols) for regional patch segmentation.
        overlay_alpha: Transparency blending factor for annotated overlay masks [0.0 - 1.0].
        environment_params: Environment-specific parameter mappings.
    """
    default_environment: EnvironmentProfile = EnvironmentProfile.MARS
    max_input_dimension: int = 1920
    min_input_dimension: int = 16
    analysis_grid_shape: Tuple[int, int] = (16, 16)
    overlay_alpha: float = 0.40
    alert_config: AlertConfig = field(default_factory=AlertConfig)
    environment_params: Dict[EnvironmentProfile, EnvironmentParameters] = field(
        default_factory=lambda: dict(DEFAULT_ENVIRONMENT_PARAMETERS)
    )

    def get_env_params(self, env: EnvironmentProfile) -> EnvironmentParameters:
        """Retrieve optical parameters for the target environment."""
        return self.environment_params.get(env, self.environment_params[EnvironmentProfile.SIMULATION])

