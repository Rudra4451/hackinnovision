"""
Semantic Terrain Segmentation Module for ODYSSEY VisionScore 2.0.

Provides modular, pixel-level surface classification, semantic color mapping,
and diagnostic overlay generation conforming to planetary autonomy standards.

Initial visual semantic categories:
- ROCK: Weathered boulders, scree, gravel, and outcrop formations.
- SAND: Fine-grained aeolian sand dunes and ripples.
- SOIL: Martian oxidized regolith, ferric dust, and flat plains.
- VEGETATION: Terrestrial/synthetic photosynthetic biomass (unsupported on Mars).
- WATER: Terrestrial/synthetic liquid bodies (unsupported on Mars).
- OBSTACLE: Severe morphological hazards, impassable crags, drop-offs, deep trenches.
- UNKNOWN: Degraded visibility, high-contrast shadow, saturation glare, anomalous features.

Traversability classifications (SAFE, CAUTION, HAZARD, UNKNOWN) remain separate
from visual semantics and are derived via formal mapping contracts.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
    The primary classifier below is a deterministic optical/texture feature segmenter.
    It is explicitly labeled as a demo algorithmic model and NEVER claimed as
    a pre-trained deep neural network.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

from visionscore.config import (
    EnvironmentParameters,
    EnvironmentProfile,
    SEMANTIC_COLOR_PALETTE,
    SEMANTIC_TRAVERSABILITY_MAP,
    SemanticClass,
    VisionConfig,
    VisualTerrainClass,
)
from visionscore.image_input import ImageInputHandler, UnifiedImage


@dataclass
class SemanticSegmentationResult:
    """
    Standardized result contract for VisionScore semantic terrain segmentation.

    Attributes:
        segmentation_mask: 2D integer NumPy array (H, W) where each pixel represents a SemanticClass index.
        color_map: 3D uint8 NumPy array (H, W, 3) with standardized RGB color assignments.
        overlay_image: 3D uint8 NumPy array (H, W, 3) blending original frame with color_map.
        class_names: Mapping of integer class IDs to string names.
        class_pixel_percentages: Breakdown of image area percentage occupied by each class (0.0 to 100.0).
        dominant_class: SemanticClass with the largest surface area.
        traversability_summary: Breakdown of pixels mapped to SAFE, CAUTION, HAZARD, UNKNOWN.
        region_segments: List of identified contiguous morphological clusters with bounding boxes and area.
        confidence_information: Mean confidence, per-class confidence, and uncertainty distribution.
        environment: Operational environment profile ('MARS', 'EARTH', 'SIMULATION').
        model_status: Provenance metadata documenting the active segmentation model and its limitations.
    """
    segmentation_mask: np.ndarray
    color_map: np.ndarray
    overlay_image: np.ndarray
    class_names: Dict[int, str]
    class_pixel_percentages: Dict[str, float]
    dominant_class: str
    traversability_summary: Dict[str, float]
    region_segments: List[Dict[str, Any]]
    confidence_information: Dict[str, Any]
    environment: str
    model_status: Dict[str, Any]

    def to_dict(self, include_arrays: bool = False) -> Dict[str, Any]:
        """Serializes segmentation results into a clean dictionary for APIs and telemetry."""
        payload: Dict[str, Any] = {
            "environment": self.environment,
            "dominant_class": self.dominant_class,
            "class_pixel_percentages": {k: round(v, 2) for k, v in self.class_pixel_percentages.items()},
            "traversability_summary": {k: round(v, 2) for k, v in self.traversability_summary.items()},
            "confidence_information": self.confidence_information,
            "num_regions": len(self.region_segments),
            "region_segments": self.region_segments[:10],  # Sample top 10 regions
            "model_status": self.model_status,
            "mask_shape": list(self.segmentation_mask.shape),
        }
        if include_arrays:
            payload["segmentation_mask"] = self.segmentation_mask.tolist()
        return payload

    def save_color_map(self, path: Union[str, Path]) -> Path:
        """Persists the color-coded semantic segmentation map to disk."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(self.color_map).save(target)
        return target

    def save_overlay(self, path: Union[str, Path]) -> Path:
        """Persists the alpha-blended diagnostic overlay to disk."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(self.overlay_image).save(target)
        return target

    def save_mask(self, path: Union[str, Path]) -> Path:
        """Persists the raw integer segmentation mask as a grayscale PNG."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(self.segmentation_mask.astype(np.uint8)).save(target)
        return target


class BaseSegmentationModel(ABC):
    """
    Abstract base interface for replaceable semantic terrain segmentation models.
    Supports future hot-swapping with deep learning architectures (e.g. SegFormer, Mask2Former).
    """

    @abstractmethod
    def segment(
        self,
        image: UnifiedImage,
        config: VisionConfig,
    ) -> SemanticSegmentationResult:
        """
        Segment the given UnifiedImage into pixel-level semantic terrain categories.

        Args:
            image: Ingested image frame.
            config: Operational configuration containing environmental thresholds.

        Returns:
            SemanticSegmentationResult containing masks, percentages, and telemetry.
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable name of the model."""
        pass

    @property
    @abstractmethod
    def is_real_ai_model(self) -> bool:
        """Flag denoting whether weights originate from a trained neural network."""
        pass


class DemoSemanticSegmentationModel(BaseSegmentationModel):
    """
    Planetary Semantic Multi-Band Texture & Chromaticity Segmenter (PSM-TCS).

    A deterministic, highly optimized optical feature segmenter operating across:
    1. Multi-band chromaticity (Redness ratio, Green excess, Blue albedo).
    2. Localized gradient magnitude & texture entropy (Sobel spatial energy).
    3. Illuminance boundaries (epistemic UNKNOWN tagging for shadows & optical saturation).
    4. Environmental profile rules (strictly preventing biological/liquid hallucination on Mars).

    TRANSPARENCY NOTICE:
    This is an algorithmic heuristic baseline designed for embedded edge hardware.
    It does not claim to use pre-trained deep neural network weights.
    """

    def __init__(self, name: str = "PSM-TCS v2.0 (Planetary Heuristic Baseline)"):
        self._name = name

    @property
    def model_name(self) -> str:
        return self._name

    @property
    def is_real_ai_model(self) -> bool:
        return False

    def segment(
        self,
        image: UnifiedImage,
        config: VisionConfig,
    ) -> SemanticSegmentationResult:
        rgb = image.image
        if rgb.ndim == 2:
            rgb = np.stack([rgb, rgb, rgb], axis=-1)
        elif rgb.ndim == 3 and rgb.shape[2] == 4:
            rgb = rgb[:, :, :3]

        h, w = rgb.shape[:2]
        env_params = config.get_env_params(image.environment)

        # 1. Luminance & Extreme Illumination Filtering
        # Rec. 601 Luma formula: Y = 0.299R + 0.587G + 0.114B
        r_channel = rgb[:, :, 0].astype(np.float32)
        g_channel = rgb[:, :, 1].astype(np.float32)
        b_channel = rgb[:, :, 2].astype(np.float32)
        luminance = 0.299 * r_channel + 0.587 * g_channel + 0.114 * b_channel

        # 2. Chromaticity & Spectral Indices
        total_rb = r_channel + b_channel + 1e-5
        redness_ratio = (r_channel - b_channel) / total_rb
        green_excess = 2.0 * g_channel - r_channel - b_channel
        blue_excess = b_channel - (r_channel + g_channel) * 0.5

        # 3. Spatial Gradient & Texture Energy (Vectorized 3x3 Sobel)
        # Fast Sobel filtering on luminance channel
        sobel_x = ndimage.sobel(luminance, axis=1)
        sobel_y = ndimage.sobel(luminance, axis=0)
        grad_mag = np.hypot(sobel_x, sobel_y) / 8.0  # Normalized gradient energy

        # Local texture variance over 5x5 window
        local_mean = ndimage.uniform_filter(luminance, size=5)
        local_sqr_mean = ndimage.uniform_filter(luminance**2, size=5)
        local_variance = np.maximum(0.0, local_sqr_mean - local_mean**2)
        local_std = np.sqrt(local_variance)
        texture_energy = 0.5 * grad_mag + 0.5 * local_std

        # 4. Pixel-Level Classification Assignment
        # Mapping enum indices:
        # 0: ROCK, 1: SAND, 2: SOIL, 3: VEGETATION, 4: WATER, 5: OBSTACLE, 6: UNKNOWN
        class_to_id: Dict[SemanticClass, int] = {
            SemanticClass.ROCK: 0,
            SemanticClass.SAND: 1,
            SemanticClass.SOIL: 2,
            SemanticClass.VEGETATION: 3,
            SemanticClass.WATER: 4,
            SemanticClass.OBSTACLE: 5,
            SemanticClass.UNKNOWN: 6,
        }
        id_to_class: Dict[int, str] = {idx: cls.value for cls, idx in class_to_id.items()}

        # Initialize default surface mask to SAND
        mask = np.full((h, w), class_to_id[SemanticClass.SAND], dtype=np.uint8)

        # Apply Soil (higher oxidized redness, low-medium texture)
        soil_mask = (redness_ratio >= env_params.expected_redness_ratio * 0.9) & (texture_energy < env_params.texture_caution_threshold)
        mask[soil_mask] = class_to_id[SemanticClass.SOIL]

        # Apply Rock (elevated texture energy)
        rock_mask = (texture_energy >= env_params.texture_caution_threshold) & (texture_energy < env_params.texture_hazard_threshold)
        mask[rock_mask] = class_to_id[SemanticClass.ROCK]

        # Apply Obstacle (severe texture energy / sharp boundary)
        obstacle_mask = (texture_energy >= env_params.texture_hazard_threshold)
        mask[obstacle_mask] = class_to_id[SemanticClass.OBSTACLE]

        # Environmental Adaptation Logic:
        # On Earth/Simulation: Support Vegetation and Water
        if image.environment in (EnvironmentProfile.EARTH, EnvironmentProfile.SIMULATION):
            veg_mask = (green_excess > 20.0) & (g_channel > r_channel) & (g_channel > b_channel) & (texture_energy < env_params.texture_hazard_threshold)
            mask[veg_mask] = class_to_id[SemanticClass.VEGETATION]

            water_mask = (blue_excess > 15.0) & (b_channel > r_channel) & (texture_energy < 8.0) & (luminance > 25.0)
            mask[water_mask] = class_to_id[SemanticClass.WATER]
        else:
            # On Mars: Biological vegetation and surface liquid water are climatologically invalid.
            # If high green/blue excess appears, flag as UNKNOWN (anomalous feature/sensor glare).
            mars_anomaly = ((green_excess > 25.0) | (blue_excess > 25.0)) & ~obstacle_mask
            mask[mars_anomaly] = class_to_id[SemanticClass.UNKNOWN]

        # Apply UNKNOWN to extreme illumination (pitch shadows or glare saturation)
        unknown_illumination = (luminance <= env_params.shadow_luminance_max) | (luminance >= env_params.saturation_luminance_min)
        mask[unknown_illumination] = class_to_id[SemanticClass.UNKNOWN]

        # 5. Morphological Spatial Smoothing (3x3 median filter to eliminate salt-and-pepper noise)
        mask = ndimage.median_filter(mask, size=3)

        # 6. Generate Color-Coded Map (RGB)
        color_map = np.zeros((h, w, 3), dtype=np.uint8)
        for cls_enum, cls_idx in class_to_id.items():
            color_rgb = SEMANTIC_COLOR_PALETTE[cls_enum]
            color_map[mask == cls_idx] = color_rgb

        # 7. Generate Alpha-Blended Overlay Image
        alpha = float(np.clip(config.overlay_alpha, 0.05, 0.95))
        overlay = (1.0 - alpha) * rgb.astype(np.float32) + alpha * color_map.astype(np.float32)
        overlay_image = np.clip(overlay, 0, 255).astype(np.uint8)

        # 8. Compute Per-Class Pixel Percentages
        total_pixels = h * w
        class_percentages: Dict[str, float] = {}
        for cls_enum, cls_idx in class_to_id.items():
            count = int(np.count_nonzero(mask == cls_idx))
            class_percentages[cls_enum.value] = (count / total_pixels) * 100.0

        # Dominant class
        dominant_class = max(class_percentages.items(), key=lambda item: item[1])[0]

        # 9. Compute Traversability Summary (Strict separation between semantics and traversability)
        traversability_summary: Dict[str, float] = {
            VisualTerrainClass.SAFE.value: 0.0,
            VisualTerrainClass.CAUTION.value: 0.0,
            VisualTerrainClass.HAZARD.value: 0.0,
            VisualTerrainClass.UNKNOWN.value: 0.0,
        }
        for cls_enum, pct in class_percentages.items():
            trav_class = SEMANTIC_TRAVERSABILITY_MAP[SemanticClass(cls_enum)]
            traversability_summary[trav_class.value] += pct

        # 10. Extract Morphological Region Segments for Obstacles and Rocks
        region_segments: List[Dict[str, Any]] = []
        hazard_pixels = (mask == class_to_id[SemanticClass.OBSTACLE]) | (mask == class_to_id[SemanticClass.ROCK])
        labeled_regions, num_features = ndimage.label(hazard_pixels)
        if num_features > 0:
            objects = ndimage.find_objects(labeled_regions)
            for idx, loc in enumerate(objects[:15]):  # Process top 15 clusters
                if loc is None:
                    continue
                region_slice = (labeled_regions[loc] == (idx + 1))
                area_px = int(np.count_nonzero(region_slice))
                if area_px < 16:  # Ignore microscopic noise
                    continue
                min_r, max_r = loc[0].start, loc[0].stop
                min_c, max_c = loc[1].start, loc[1].stop
                centroid_r = float(min_r + (max_r - min_r) / 2.0)
                centroid_c = float(min_c + (max_c - min_c) / 2.0)

                sub_mask = mask[loc]
                is_obstacle = np.any(sub_mask == class_to_id[SemanticClass.OBSTACLE])
                reg_class = SemanticClass.OBSTACLE.value if is_obstacle else SemanticClass.ROCK.value

                region_segments.append({
                    "region_id": idx + 1,
                    "semantic_class": reg_class,
                    "bounding_box": [min_r, min_c, max_r, max_c],
                    "centroid": [round(centroid_r, 1), round(centroid_c, 1)],
                    "area_pixels": area_px,
                    "area_percentage": round((area_px / total_pixels) * 100.0, 3),
                })

        # 11. Confidence Information
        # Higher confidence when texture energy is cleanly outside the ambiguous transition zones
        ambiguity_zone = np.abs(texture_energy - env_params.texture_caution_threshold) < 3.0
        known_fraction = 1.0 - (class_percentages[SemanticClass.UNKNOWN.value] / 100.0)
        mean_confidence = float(np.clip(known_fraction * (1.0 - np.mean(ambiguity_zone) * 0.4), 0.25, 0.98))

        confidence_info: Dict[str, Any] = {
            "overall_confidence": round(mean_confidence, 4),
            "known_surface_fraction": round(known_fraction, 4),
            "shadow_or_glare_fraction": round(class_percentages[SemanticClass.UNKNOWN.value] / 100.0, 4),
            "model_transparency": "Demo heuristic - not neural network inference",
        }

        # 12. Model Status Metadata
        model_status: Dict[str, Any] = {
            "model_name": self.model_name,
            "is_real_ai_model": self.is_real_ai_model,
            "model_type": "HEURISTIC_SPECTRAL_TEXTURE_SEGMENTER",
            "version": "2.0.0",
            "environment_profile": image.environment.value,
            "supported_classes": [c.value for c in env_params.supported_classes],
            "input_resolution": f"{w}x{h}",
            "limitations": (
                "Algorithmic optical baseline. Evaluates multi-band chromaticity and spatial gradient texture. "
                "Does not use trained deep-learning neural network weights. Pluggable via BaseSegmentationModel."
            ),
        }

        return SemanticSegmentationResult(
            segmentation_mask=mask,
            color_map=color_map,
            overlay_image=overlay_image,
            class_names=id_to_class,
            class_pixel_percentages=class_percentages,
            dominant_class=dominant_class,
            traversability_summary=traversability_summary,
            region_segments=region_segments,
            confidence_information=confidence_info,
            environment=image.environment.value,
            model_status=model_status,
        )


# Global default segmentation model instance (cached to avoid redundant instantiation)
_DEFAULT_SEGMENTATION_MODEL = DemoSemanticSegmentationModel()


def segment_terrain(
    image: Union[UnifiedImage, np.ndarray, bytes, str, Path],
    environment: Union[EnvironmentProfile, str] = EnvironmentProfile.MARS,
    config: Optional[VisionConfig] = None,
    model: Optional[BaseSegmentationModel] = None,
) -> SemanticSegmentationResult:
    """
    High-level, production-grade semantic terrain segmentation entrypoint for ODYSSEY VisionScore 2.0.

    Accepts any image input (UnifiedImage, raw NumPy array, raw bytes, or file path),
    normalizes it via the input foundation, and executes semantic segmentation.

    Args:
        image: Ingested image representation.
        environment: Operational environment profile (MARS, EARTH, SIMULATION).
        config: Optional custom VisionConfig.
        model: Optional custom BaseSegmentationModel instance (hot-swappable).

    Returns:
        SemanticSegmentationResult with mask, color map, overlay, percentages, and telemetry.
    """
    if isinstance(environment, str):
        try:
            env_enum = EnvironmentProfile(environment.upper())
        except ValueError:
            env_enum = EnvironmentProfile.MARS
    else:
        env_enum = environment

    active_config = config or VisionConfig(default_environment=env_enum)
    active_model = model or _DEFAULT_SEGMENTATION_MODEL

    # Normalize image into UnifiedImage if needed
    if isinstance(image, UnifiedImage):
        unified_img = image
        # Update environment if explicitly overridden
        if unified_img.environment != env_enum:
            unified_img = UnifiedImage(
                image_id=unified_img.image_id,
                image=unified_img.image,
                source=unified_img.source,
                environment=env_enum,
                timestamp=unified_img.timestamp,
                metadata=unified_img.metadata,
            )
    else:
        handler = ImageInputHandler(config=active_config)
        unified_img = handler.ingest(image, environment=env_enum)

    return active_model.segment(unified_img, active_config)

