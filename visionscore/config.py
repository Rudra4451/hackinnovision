"""
Configuration and Environment Profiles for ODYSSEY VisionScore (Stage 1).

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Tuple


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


DEFAULT_ENVIRONMENT_PARAMETERS: Dict[EnvironmentProfile, EnvironmentParameters] = {
    EnvironmentProfile.MARS: EnvironmentParameters(
        name="MARS",
        expected_redness_ratio=0.30,
        texture_caution_threshold=12.0,
        texture_hazard_threshold=28.0,
        shadow_luminance_max=22.0,
        saturation_luminance_min=242.0,
        description="Martian surface profile: basaltic rock, ferric oxide dust, high-contrast shadows.",
    ),
    EnvironmentProfile.EARTH: EnvironmentParameters(
        name="EARTH",
        expected_redness_ratio=0.08,
        texture_caution_threshold=18.0,
        texture_hazard_threshold=36.0,
        shadow_luminance_max=15.0,
        saturation_luminance_min=248.0,
        description="Terrestrial surface profile: standard daylight scattering, gravel, dirt, and varied albedo.",
    ),
    EnvironmentProfile.SIMULATION: EnvironmentParameters(
        name="SIMULATION",
        expected_redness_ratio=0.22,
        texture_caution_threshold=14.0,
        texture_hazard_threshold=30.0,
        shadow_luminance_max=20.0,
        saturation_luminance_min=245.0,
        description="Synthetic simulation profile: procedurally generated or rendered virtual landscapes.",
    ),
}


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
    environment_params: Dict[EnvironmentProfile, EnvironmentParameters] = field(
        default_factory=lambda: dict(DEFAULT_ENVIRONMENT_PARAMETERS)
    )

    def get_env_params(self, env: EnvironmentProfile) -> EnvironmentParameters:
        """Retrieve optical parameters for the target environment."""
        return self.environment_params.get(env, self.environment_params[EnvironmentProfile.SIMULATION])

