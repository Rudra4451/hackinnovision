"""
Replaceable Terrain Analysis Engine for ODYSSEY VisionScore (Stage 1).

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
    The primary classifier below is a deterministic optical feature segmenter.
    It is explicitly labeled as a demo algorithmic model and NEVER claimed as
    a pre-trained deep neural network.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

from visionscore.config import (
    EnvironmentParameters,
    EnvironmentProfile,
    VisionConfig,
    VisualTerrainClass,
)
from visionscore.image_input import UnifiedImage


@dataclass
class TerrainSegment:
    """Individual segmented region or spatial patch of analyzed terrain."""
    region_id: int
    bounding_box: Tuple[int, int, int, int]  # (min_row, min_col, max_row, max_col)
    terrain_class: VisualTerrainClass
    confidence: float
    texture_energy: float
    mean_luminance: float
    chromaticity: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "bounding_box": list(self.bounding_box),
            "terrain_class": self.terrain_class.value,
            "confidence": round(self.confidence, 4),
            "texture_energy": round(self.texture_energy, 2),
            "mean_luminance": round(self.mean_luminance, 2),
            "chromaticity": round(self.chromaticity, 4),
        }


@dataclass
class AnalysisResult:
    """
    Standardized result contract returned by the VisionScore terrain analysis interface.

    Attributes:
        terrain_regions: List of identified sub-regions and their classifications.
        terrain_class: Dominant visual traversability class across the frame.
        confidence: Aggregate confidence score in [0.0, 1.0].
        classification: Breakdown of fractional coverage across categories.
        annotated_image: RGB uint8 array with semi-transparent diagnostic overlays.
        overall_status: High-level operational status string.
        model_status: Full provenance metadata documenting the active vision model.
    """
    terrain_regions: List[TerrainSegment]
    terrain_class: VisualTerrainClass
    confidence: float
    classification: Dict[str, float]
    annotated_image: np.ndarray
    overall_status: str
    model_status: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "terrain_class": self.terrain_class.value,
            "confidence": round(self.confidence, 4),
            "classification": {k: round(v, 4) for k, v in self.classification.items()},
            "overall_status": self.overall_status,
            "num_regions": len(self.terrain_regions),
            "model_status": self.model_status,
            "sample_regions": [r.to_dict() for r in self.terrain_regions[:5]],
        }


# Overlay color mappings: (R, G, B)
CLASS_COLORS: Dict[VisualTerrainClass, Tuple[int, int, int]] = {
    VisualTerrainClass.SAFE: (46, 204, 113),       # Emerald Green
    VisualTerrainClass.CAUTION: (243, 156, 18),    # Amber Orange
    VisualTerrainClass.HAZARD: (231, 76, 60),      # Crimson Red
    VisualTerrainClass.UNKNOWN: (155, 89, 182),    # Amethyst Purple
}


class BaseTerrainModel(ABC):
    """Abstract interface contract for pluggable terrain segmentation models."""

    @abstractmethod
    def analyze(
        self,
        image: UnifiedImage,
        environment: Optional[EnvironmentProfile] = None,
    ) -> AnalysisResult:
        """Executes optical terrain classification over the provided unified image."""
        pass


class DemoVisualTerrainModel(BaseTerrainModel):
    """
    Planetary Multi-Band Texture & Chromaticity Segmentation (PMTCS) Model.

    A fully transparent, deterministic, and documented computer-vision model
    inspired by planetary rover optical classification principles (e.g. OASIS/SPOC):
    1. Multi-band chromaticity: Ratio of ferric red absorption vs blue scattering.
    2. Spatial frequency texture energy: Local Laplacian filter magnitude capturing
       fine dust smoothness vs coarse boulder fractures.
    3. Illumination bounds: Identifies underexposed shadow crevices or optical glare as UNKNOWN.

    Notice:
        This is an algorithmic heuristic model engineered for Stage 1 validation.
        It is explicitly marked as 'is_real_ai_model': False.
    """

    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or VisionConfig()

    def analyze(
        self,
        image: UnifiedImage,
        environment: Optional[EnvironmentProfile] = None,
    ) -> AnalysisResult:
        arr = image.image
        h, w = arr.shape[:2]
        env = environment or image.environment
        env_params: EnvironmentParameters = self.config.get_env_params(env)

        # Convert to float for vectorized optical algebra
        img_float = arr.astype(np.float64)
        if img_float.ndim == 3:
            r = img_float[:, :, 0]
            g = img_float[:, :, 1]
            b = img_float[:, :, 2]
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            chromaticity = np.divide(r - b, r + b + 1e-5)
        else:
            luminance = img_float
            chromaticity = np.zeros_like(luminance)

        # High-performance spatial texture energy via Laplacian filter
        texture_field = np.abs(ndimage.laplace(luminance))

        # Subdivision into regional patches for spatial explainability
        grid_r, grid_c = self.config.analysis_grid_shape
        cell_h = max(1, h // grid_r)
        cell_w = max(1, w // grid_c)

        regions: List[TerrainSegment] = []
        class_counts = {cls: 0 for cls in VisualTerrainClass}
        region_confidences: List[float] = []

        # Create overlay canvas for visualization
        overlay = arr.copy().astype(np.float64)

        reg_idx = 0
        for gr in range(grid_r):
            for gc in range(grid_c):
                r0 = gr * cell_h
                r1 = h if gr == grid_r - 1 else (gr + 1) * cell_h
                c0 = gc * cell_w
                c1 = w if gc == grid_c - 1 else (gc + 1) * cell_w

                patch_lum = float(np.mean(luminance[r0:r1, c0:c1]))
                patch_tex = float(np.mean(texture_field[r0:r1, c0:c1]))
                patch_chroma = float(np.mean(chromaticity[r0:r1, c0:c1]))

                # 1. Shadow / Saturation check -> UNKNOWN
                if (
                    patch_lum < env_params.shadow_luminance_max
                    or patch_lum > env_params.saturation_luminance_min
                ):
                    assigned_class = VisualTerrainClass.UNKNOWN
                    conf = 0.50 + 0.30 * min(1.0, abs(patch_lum - 128.0) / 128.0)

                # 2. High texture roughness / dark angular contrast -> HAZARD
                elif patch_tex >= env_params.texture_hazard_threshold:
                    assigned_class = VisualTerrainClass.HAZARD
                    conf = np.clip(0.65 + 0.35 * (patch_tex / (env_params.texture_hazard_threshold * 1.5)), 0.65, 0.98)

                # 3. Moderate texture roughness / transitional slope -> CAUTION
                elif patch_tex >= env_params.texture_caution_threshold:
                    assigned_class = VisualTerrainClass.CAUTION
                    span = max(env_params.texture_hazard_threshold - env_params.texture_caution_threshold, 1e-3)
                    ratio = (patch_tex - env_params.texture_caution_threshold) / span
                    conf = np.clip(0.60 + 0.30 * ratio, 0.60, 0.95)

                # 4. Low texture energy / smooth uniform regolith -> SAFE
                else:
                    assigned_class = VisualTerrainClass.SAFE
                    conf = np.clip(0.70 + 0.28 * (1.0 - (patch_tex / max(env_params.texture_caution_threshold, 1e-3))), 0.70, 0.98)

                region = TerrainSegment(
                    region_id=reg_idx,
                    bounding_box=(r0, c0, r1, c1),
                    terrain_class=assigned_class,
                    confidence=float(conf),
                    texture_energy=patch_tex,
                    mean_luminance=patch_lum,
                    chromaticity=patch_chroma,
                )
                regions.append(region)
                class_counts[assigned_class] += 1
                region_confidences.append(float(conf))

                # Blend patch color onto overlay canvas
                c_color = np.array(CLASS_COLORS[assigned_class], dtype=np.float64)
                overlay[r0:r1, c0:c1] = (
                    (1.0 - self.config.overlay_alpha) * overlay[r0:r1, c0:c1]
                    + self.config.overlay_alpha * c_color
                )
                reg_idx += 1

        total_regions = float(len(regions))
        class_fractions = {
            cls.value: float(class_counts[cls] / total_regions)
            for cls in VisualTerrainClass
        }

        # Determine dominant classification
        dominant_class = max(class_counts, key=class_counts.get)
        mean_confidence = float(np.mean(region_confidences)) if region_confidences else 0.50

        # Burn-in diagnostic grid lines and HUD banner
        annotated_arr = np.clip(overlay, 0, 255).astype(np.uint8)
        annotated_pil = Image.fromarray(annotated_arr)
        draw = ImageDraw.Draw(annotated_pil)

        # Draw grid wireframe outlines
        for reg in regions:
            r0, c0, r1, c1 = reg.bounding_box
            if reg.terrain_class == VisualTerrainClass.HAZARD:
                # Highlight hazard boundaries in bold red
                draw.rectangle([c0, r0, c1, r1], outline=(255, 30, 30), width=2)

        # Top diagnostic telemetry banner
        banner_text = (
            f"ODYSSEY VisionScore (Stage 1 Demo) | Env: {env.value} | "
            f"Class: {dominant_class.value} ({class_fractions[dominant_class.value]*100:.1f}%) | "
            f"Conf: {mean_confidence:.2f}"
        )
        draw.rectangle([0, 0, w, 24], fill=(20, 24, 30))
        draw.text((8, 4), banner_text, fill=(230, 235, 240))

        annotated_final = np.asarray(annotated_pil, dtype=np.uint8)

        status_map = {
            VisualTerrainClass.SAFE: "OPERATIONAL_SAFE",
            VisualTerrainClass.CAUTION: "OPERATIONAL_CAUTION",
            VisualTerrainClass.HAZARD: "OPERATIONAL_HAZARD",
            VisualTerrainClass.UNKNOWN: "OPERATIONAL_UNKNOWN",
        }

        model_status_info = {
            "model_name": "Planetary Multi-Band Texture & Chromaticity Segmenter (PMTCS)",
            "is_real_ai_model": False,
            "architecture_type": "Deterministic Optical Texture Energy & Chromatic Feature Segmenter",
            "model_version": "1.0.0-demo",
            "environment_calibrated": env.value,
            "model_transparency_notice": (
                "DEMO IMPLEMENTATION: This analysis uses deterministic spatial filters (Laplacian "
                "texture energy and chromaticity bands) for Stage 1 interface validation. "
                "It is NOT a pre-trained deep convolutional neural network and does NOT replace "
                "physical elevation/slope cost maps."
            ),
        }

        return AnalysisResult(
            terrain_regions=regions,
            terrain_class=dominant_class,
            confidence=mean_confidence,
            classification=class_fractions,
            annotated_image=annotated_final,
            overall_status=status_map[dominant_class],
            model_status=model_status_info,
        )


# Singleton model cache to avoid repeated object initialization
_DEFAULT_ANALYZER_MODEL: Optional[BaseTerrainModel] = None


def get_default_analyzer() -> BaseTerrainModel:
    """Returns cached default analyzer model instance."""
    global _DEFAULT_ANALYZER_MODEL
    if _DEFAULT_ANALYZER_MODEL is None:
        _DEFAULT_ANALYZER_MODEL = DemoVisualTerrainModel()
    return _DEFAULT_ANALYZER_MODEL


def analyze_terrain(
    image: UnifiedImage,
    environment: Optional[EnvironmentProfile] = None,
    model: Optional[BaseTerrainModel] = None,
) -> AnalysisResult:
    """
    Standard entrypoint interface for VisionScore optical terrain analysis.

    Parameters:
        image: Standardized UnifiedImage container.
        environment: Optional environmental profile override.
        model: Optional custom BaseTerrainModel implementation.

    Returns:
        AnalysisResult containing regions, dominant class, confidence, overlays, and status.
    """
    analyzer = model or get_default_analyzer()
    return analyzer.analyze(image, environment=environment)

