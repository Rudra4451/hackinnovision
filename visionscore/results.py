"""
Visual Results Presentation Interface for ODYSSEY VisionScore (Stage 1).

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
from PIL import Image

from visionscore.analyzer import AnalysisResult
from visionscore.image_input import UnifiedImage


@dataclass
class VisualResults:
    """
    Standard presentation and reporting container for VisionScore outputs.

    Attributes:
        original_image: Clean, unmodified RGB input array (H, W, 3) uint8.
        annotated_image: Diagnostic RGB array (H, W, 3) uint8 with overlaid segmentation masks.
        detected_terrain_classes: List of unique terrain classes detected in the scene.
        confidence_values: Quantitative confidence breakdown (overall, per-class, entropy).
        environment: Environmental profile under which analysis was conducted ('MARS', 'EARTH', 'SIMULATION').
        image_source: Provenance of the image ('upload', 'camera_frame', 'simulated_camera').
        processing_status: Execution duration, operational status, and transparency flags.
    """
    original_image: np.ndarray
    annotated_image: np.ndarray
    detected_terrain_classes: List[str]
    confidence_values: Dict[str, float]
    environment: str
    image_source: str
    processing_status: Dict[str, Any]

    @classmethod
    def from_analysis(
        cls,
        image: UnifiedImage,
        analysis: AnalysisResult,
        duration_ms: float = 0.0,
    ) -> "VisualResults":
        """Factory constructor instantiating VisualResults from an input UnifiedImage and AnalysisResult."""
        detected_classes = sorted(list({reg.terrain_class.value for reg in analysis.terrain_regions}))

        confidence_info = {
            "overall_confidence": round(analysis.confidence, 4),
        }
        for cls_name, fraction in analysis.classification.items():
            confidence_info[f"class_coverage_{cls_name.lower()}"] = round(fraction, 4)

        status_info = {
            "overall_status": analysis.overall_status,
            "duration_ms": round(duration_ms, 2),
            "model_status": analysis.model_status,
            "timestamp": image.timestamp,
            "image_id": image.image_id,
        }

        return cls(
            original_image=image.image,
            annotated_image=analysis.annotated_image,
            detected_terrain_classes=detected_classes,
            confidence_values=confidence_info,
            environment=image.environment.value,
            image_source=image.source,
            processing_status=status_info,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes results metadata into a clean JSON-serializable dictionary."""
        return {
            "environment": self.environment,
            "image_source": self.image_source,
            "detected_terrain_classes": self.detected_terrain_classes,
            "confidence_values": self.confidence_values,
            "processing_status": self.processing_status,
            "image_dimensions": {
                "height": self.original_image.shape[0],
                "width": self.original_image.shape[1],
                "channels": self.original_image.shape[2] if self.original_image.ndim == 3 else 1,
            },
        }

    def save_annotated_image(self, path: Union[str, Path]) -> Path:
        """Persists the diagnostic annotated image array to disk."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        pil_img = Image.fromarray(self.annotated_image)
        pil_img.save(target)
        return target

    def save_side_by_side(self, path: Union[str, Path]) -> Path:
        """Creates and saves a side-by-side comparison of original and annotated images."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        orig_pil = Image.fromarray(self.original_image)
        annot_pil = Image.fromarray(self.annotated_image)

        # Match dimensions
        w, h = orig_pil.size
        combined = Image.new("RGB", (w * 2, h))
        combined.paste(orig_pil, (0, 0))
        combined.paste(annot_pil, (w, 0))
        combined.save(target)
        return target

    def get_summary(self) -> str:
        """Generates an executive ASCII summary of visual terrain findings."""
        conf = self.confidence_values.get("overall_confidence", 0.0)
        dur = self.processing_status.get("duration_ms", 0.0)
        status = self.processing_status.get("overall_status", "UNKNOWN")
        classes_str = ", ".join(self.detected_terrain_classes)

        return (
            f"[VisionScore Results]\n"
            f"  Environment : {self.environment}\n"
            f"  Source      : {self.image_source}\n"
            f"  Status      : {status}\n"
            f"  Confidence  : {conf:.2%}\n"
            f"  Detected    : [{classes_str}]\n"
            f"  Latency     : {dur:.1f} ms"
        )

