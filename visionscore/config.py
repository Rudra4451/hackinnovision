"""
Configuration and Environment Profiles for ODYSSEY VisionScore (Stage 1).

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union


class EnvironmentProfile(str, Enum):
    """
    Environmental profiles for vision-based terrain analysis.

    MARS is the primary and only operational flight environment for ODYSSEY.
    SIMULATION_MARS provides high-fidelity synthetic simulations for Mars operations.
    EARTH and SIMULATION are preserved strictly for backward-compatible testing.
    """
    MARS = "MARS"
    SIMULATION_MARS = "SIMULATION_MARS"

    # Backward compatibility aliases
    SIMULATION = "SIMULATION"
    EARTH = "EARTH"


# Active operational profiles permitted in production and mission control UI
ACTIVE_ENVIRONMENT_PROFILES: Tuple[EnvironmentProfile, ...] = (
    EnvironmentProfile.MARS,
    EnvironmentProfile.SIMULATION_MARS,
)
OPERATIONAL_ENVIRONMENTS: Tuple[EnvironmentProfile, ...] = ACTIVE_ENVIRONMENT_PROFILES


class VisualTerrainClass(str, Enum):
    """Visual traversability categories defined for VisionScore."""
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    HAZARD = "HAZARD"
    UNKNOWN = "UNKNOWN"


class SemanticClass(str, Enum):
    """
    Pixel-level geological and surface semantic categories for ODYSSEY VisionScore.
    Kept strictly distinct from physical traversability classifications.

    Mars Operational Taxonomy:
    - ROCK: Exposed bedrock outcrops, scree, small stones, and gravel.
    - BOULDER: Large isolated rock masses and morphological hazards.
    - SAND: Aeolian sand sheets, dune fields, and fine rippled deposits.
    - REGOLITH: Unconsolidated loose rocky substrate and weathered debris.
    - SOIL: Oxidized Martian surface plains and cohesive ground.
    - BEDROCK: Exposed solid rock pavement and consolidated basement strata.
    - DUST: Fine-grained atmospheric fallout mantling surface features.
    - CRATER: Impact depression structures, rim escarpments, and bowl walls.
    - UNKNOWN: Degraded visibility, high-contrast shadows, glare, or unclassified regions.

    Legacy / Terrestrial Aliases:
    - OBSTACLE: Legacy alias for severe geometric hazards (mapped to BOULDER / HAZARD).
    - VEGETATION: Terrestrial biological biomass (unsupported on Mars).
    - WATER: Terrestrial liquid bodies (unsupported on Mars).
    """
    # Mars Target Taxonomy
    ROCK = "ROCK"
    BOULDER = "BOULDER"
    SAND = "SAND"
    REGOLITH = "REGOLITH"
    SOIL = "SOIL"
    BEDROCK = "BEDROCK"
    DUST = "DUST"
    CRATER = "CRATER"
    UNKNOWN = "UNKNOWN"

    # Legacy / Terrestrial Aliases
    OBSTACLE = "OBSTACLE"
    VEGETATION = "VEGETATION"
    WATER = "WATER"


# Full Mars Target Semantic Taxonomy
MARS_TARGET_TAXONOMY: Tuple[SemanticClass, ...] = (
    SemanticClass.ROCK,
    SemanticClass.BOULDER,
    SemanticClass.SAND,
    SemanticClass.REGOLITH,
    SemanticClass.SOIL,
    SemanticClass.BEDROCK,
    SemanticClass.DUST,
    SemanticClass.CRATER,
    SemanticClass.UNKNOWN,
)

# Classes recognized by the baseline optical heuristic model (PSM-TCS v2.0)
HEURISTIC_RECOGNIZED_CLASSES: Tuple[SemanticClass, ...] = (
    SemanticClass.ROCK,
    SemanticClass.BOULDER,
    SemanticClass.SAND,
    SemanticClass.SOIL,
    SemanticClass.OBSTACLE,
    SemanticClass.UNKNOWN,
)

# Extended classes defined in taxonomy for AI4Mars deep-learning integration
EXTENDED_PLANNED_CLASSES: Tuple[SemanticClass, ...] = (
    SemanticClass.REGOLITH,
    SemanticClass.BEDROCK,
    SemanticClass.DUST,
    SemanticClass.CRATER,
)


# Consistent, publication-grade RGB color palette for semantic visualization
SEMANTIC_COLOR_PALETTE: Dict[SemanticClass, Tuple[int, int, int]] = {
    # Mars Taxonomy
    SemanticClass.ROCK: (128, 128, 128),       # Slate Gray (geological outcrops / scree)
    SemanticClass.BOULDER: (75, 85, 99),       # Dark Slate / Charcoal (large rock hazards)
    SemanticClass.SAND: (237, 201, 137),       # Ochre / Golden Sand (smooth Martian drifts)
    SemanticClass.REGOLITH: (194, 65, 12),     # Terracotta / Rust (weathered mantle)
    SemanticClass.SOIL: (184, 80, 50),         # Martian Rust Red / Oxidized surface
    SemanticClass.BEDROCK: (107, 114, 128),    # Stone Gray Pavement (firm basement rock)
    SemanticClass.DUST: (245, 158, 11),        # Pale Ochre / Dust Yellow (fine atmospheric mantling)
    SemanticClass.CRATER: (67, 20, 7),         # Deep Umber / Crater Shadow (impact rims & depressions)
    SemanticClass.UNKNOWN: (108, 52, 131),     # Deep Amethyst Violet (shadows, glare, unclassified)

    # Legacy Aliases
    SemanticClass.OBSTACLE: (231, 76, 60),     # Crimson Red (impassable crags, drop-offs, sharp rocks)
    SemanticClass.VEGETATION: (46, 204, 113),  # Emerald Green (terrestrial / synthetic)
    SemanticClass.WATER: (52, 152, 219),       # Cyan / Blue (terrestrial / synthetic)
}

# Mapping from semantic surface classes to candidate traversability tiers
SEMANTIC_TRAVERSABILITY_MAP: Dict[SemanticClass, VisualTerrainClass] = {
    # SAFE: Flat, trafficable surfaces
    SemanticClass.SAND: VisualTerrainClass.SAFE,
    SemanticClass.SOIL: VisualTerrainClass.SAFE,
    SemanticClass.REGOLITH: VisualTerrainClass.SAFE,
    SemanticClass.BEDROCK: VisualTerrainClass.SAFE,

    # CAUTION: Moderate roughness or mobility penalty
    SemanticClass.ROCK: VisualTerrainClass.CAUTION,
    SemanticClass.DUST: VisualTerrainClass.CAUTION,

    # HAZARD: Impassable or dangerous morphology
    SemanticClass.BOULDER: VisualTerrainClass.HAZARD,
    SemanticClass.CRATER: VisualTerrainClass.HAZARD,
    SemanticClass.OBSTACLE: VisualTerrainClass.HAZARD,
    SemanticClass.WATER: VisualTerrainClass.HAZARD,

    # UNKNOWN: Degraded observation or unclassified
    SemanticClass.UNKNOWN: VisualTerrainClass.UNKNOWN,

    # Legacy
    SemanticClass.VEGETATION: VisualTerrainClass.CAUTION,
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
        supported_classes=HEURISTIC_RECOGNIZED_CLASSES,
    ),
    EnvironmentProfile.SIMULATION_MARS: EnvironmentParameters(
        name="SIMULATION_MARS",
        expected_redness_ratio=0.28,
        texture_caution_threshold=12.0,
        texture_hazard_threshold=28.0,
        shadow_luminance_max=22.0,
        saturation_luminance_min=242.0,
        description="High-fidelity Martian simulation: synthetic Mars surface, ferric regolith, boulder scatter.",
        supported_classes=HEURISTIC_RECOGNIZED_CLASSES,
    ),
    EnvironmentProfile.SIMULATION: EnvironmentParameters(
        name="SIMULATION",
        expected_redness_ratio=0.22,
        texture_caution_threshold=14.0,
        texture_hazard_threshold=30.0,
        shadow_luminance_max=20.0,
        saturation_luminance_min=245.0,
        description="Legacy synthetic simulation profile (alias for SIMULATION_MARS).",
        supported_classes=HEURISTIC_RECOGNIZED_CLASSES,
    ),
    EnvironmentProfile.EARTH: EnvironmentParameters(
        name="EARTH",
        expected_redness_ratio=0.08,
        texture_caution_threshold=18.0,
        texture_hazard_threshold=36.0,
        shadow_luminance_max=15.0,
        saturation_luminance_min=248.0,
        description="Deprecated terrestrial profile (preserved solely for backward compatibility testing).",
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
        default_environment: Default environment profile (MARS).
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

    def get_env_params(self, env: Union[EnvironmentProfile, str]) -> EnvironmentParameters:
        """Retrieve optical parameters for the target environment, defaulting safely to MARS."""
        if isinstance(env, str):
            try:
                env = EnvironmentProfile(env.upper())
            except ValueError:
                env = EnvironmentProfile.MARS

        if env in self.environment_params:
            return self.environment_params[env]
        if env == EnvironmentProfile.SIMULATION:
            return self.environment_params.get(
                EnvironmentProfile.SIMULATION_MARS,
                self.environment_params[EnvironmentProfile.MARS]
            )
        return self.environment_params.get(
            EnvironmentProfile.MARS,
            next(iter(self.environment_params.values()))
        )


def resolve_environment(env_input: Union[str, EnvironmentProfile]) -> EnvironmentProfile:
    """
    Safely resolves an environment string or enum to an active Mars operational profile or legacy alias.
    Guarantees strict fallback to MARS for any invalid or missing input.
    """
    if isinstance(env_input, EnvironmentProfile):
        return env_input
    if not isinstance(env_input, str):
        return EnvironmentProfile.MARS

    clean = env_input.strip().upper()
    if clean in ("SIMULATION", "SIM", "SIM_MARS", "SIMULATION_MARS"):
        return EnvironmentProfile.SIMULATION_MARS
    if clean == "EARTH":
        return EnvironmentProfile.EARTH
    try:
        return EnvironmentProfile(clean)
    except ValueError:
        return EnvironmentProfile.MARS

