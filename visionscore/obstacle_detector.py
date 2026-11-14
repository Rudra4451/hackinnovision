"""
Automatic Obstacle Detection & Event-Based Image Alert Engine for ODYSSEY VisionScore 2.0.

Provides:
1. Automated obstacle event detection from live or simulated camera frames.
2. Deduplication and temporal cooldown to prevent alert flooding on persistent hazards.
3. Ephemeral frame handling with managed local storage for verified obstacle alerts.
4. Rich alert telemetry payload with verification workflows (UNVERIFIED, CONFIRMED, FALSE_POSITIVE).

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from visionscore.config import AlertConfig, EnvironmentProfile, SemanticClass, VisualTerrainClass
from visionscore.image_input import UnifiedImage
from visionscore.semantic import SemanticSegmentationResult, segment_terrain

logger = logging.getLogger(__name__)


@dataclass
class ObstacleAlert:
    """
    Standardized Obstacle Alert event record conforming to ODYSSEY specifications.

    Attributes:
        event_id: Unique RFC 4122 event identifier (e.g. 'EVT-20261114-123456-abc123').
        timestamp: ISO 8601 UTC timestamp when the obstacle was detected.
        source: Origin modality ('CAMERA' or 'UPLOAD').
        environment: Operational environment profile ('MARS', 'EARTH', 'SIMULATION').
        detection_category: Classification category (e.g. 'HAZARD_OBSTACLE', 'BOULDER_CLUSTER').
        confidence: Detection confidence score in [0.0, 1.0].
        obstacle_area_pct: Percentage of image frame occupied by the detected obstacle.
        explanation: Detailed rationale explaining why this region triggers a hazard alert.
        verification_status: Verification state ('UNVERIFIED', 'CONFIRMED', 'FALSE_POSITIVE', 'BYPASSED').
        captured_image: Clean RGB frame at the moment of detection (H, W, 3) uint8.
        annotated_image: Diagnostic overlay highlighting bounding box and hazard overlay (H, W, 3) uint8.
        bounding_box: Optional coordinates (min_row, min_col, max_row, max_col).
        image_path: Relative filesystem path to saved original frame.
        annotated_path: Relative filesystem path to saved annotated frame.
        grid_mapping: Optional spatial projection to rover DEM grid or 'UNMAPPED_VISUAL_OBSTACLE'.
        metadata: Additional diagnostic telemetry.
    """
    event_id: str
    timestamp: str
    source: str
    environment: str
    detection_category: str
    confidence: float
    obstacle_area_pct: float
    explanation: str
    verification_status: str
    captured_image: np.ndarray
    annotated_image: np.ndarray
    bounding_box: Optional[Tuple[int, int, int, int]] = None
    image_path: Optional[str] = None
    annotated_path: Optional[str] = None
    grid_mapping: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_images: bool = False) -> Dict[str, Any]:
        """Serializes alert record to JSON-compatible dictionary."""
        payload: Dict[str, Any] = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "environment": self.environment,
            "detection_category": self.detection_category,
            "confidence": round(self.confidence, 4),
            "obstacle_area_pct": round(self.obstacle_area_pct, 2),
            "explanation": self.explanation,
            "verification_status": self.verification_status,
            "bounding_box": list(self.bounding_box) if self.bounding_box else None,
            "image_path": self.image_path,
            "annotated_path": self.annotated_path,
            "grid_mapping": self.grid_mapping,
            "metadata": self.metadata,
        }
        if include_images:
            payload["image_shape"] = list(self.captured_image.shape)
        return payload


class ObstacleEventDetector:
    """
    Automated Obstacle Detection & Event Capture Engine.

    Features:
    - Processes incoming camera frames or uploads.
    - Evaluates obstacle region coverage against configurable thresholds.
    - Deduplicates persistent obstacles in the camera field-of-view using spatial IoU
      and perceptual feature signatures.
    - Applies a temporal cooldown period to prevent alert spam.
    - Manages circular storage of captured event frames on disk.
    - Gracefully handles missing cameras, invalid inputs, and storage failures.
    """

    def __init__(self, config: Optional[AlertConfig] = None):
        self.config = config or AlertConfig()
        self._alerts: List[ObstacleAlert] = []
        self._last_alert_time: float = 0.0
        self._last_obstacle_centroid: Optional[Tuple[float, float]] = None
        self._last_obstacle_signature: Optional[str] = None
        self._storage_dir = Path(self.config.storage_dir)

        # Initialize storage directory gracefully
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create alert storage directory {self._storage_dir}: {e}")

    @property
    def alert_count(self) -> int:
        return len(self._alerts)

    def get_alerts(
        self,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> List[ObstacleAlert]:
        """Retrieve recent obstacle alerts, optionally filtered by verification status."""
        alerts = self._alerts
        if status:
            alerts = [a for a in alerts if a.verification_status.upper() == status.upper()]
        return alerts[-limit:][::-1]  # Return newest first

    def get_alert_by_id(self, event_id: str) -> Optional[ObstacleAlert]:
        """Fetch a specific alert record by its unique ID."""
        for a in self._alerts:
            if a.event_id == event_id:
                return a
        return None

    def verify_alert(self, event_id: str, status: str, notes: str = "") -> bool:
        """
        Update the verification status of an existing alert.
        Valid statuses: 'CONFIRMED', 'FALSE_POSITIVE', 'BYPASSED', 'UNVERIFIED'.
        """
        valid_statuses = {"CONFIRMED", "FALSE_POSITIVE", "BYPASSED", "UNVERIFIED"}
        clean_status = status.strip().upper()
        if clean_status not in valid_statuses:
            raise ValueError(f"Invalid verification status '{status}'. Must be one of {valid_statuses}")

        alert = self.get_alert_by_id(event_id)
        if alert is None:
            return False

        alert.verification_status = clean_status
        if notes:
            alert.metadata["verification_notes"] = notes
        alert.metadata["verified_at"] = datetime.now(timezone.utc).isoformat()
        return True

    def clear_alerts(self) -> None:
        """Clears all in-memory alerts and resets tracker state."""
        self._alerts.clear()
        self._last_alert_time = 0.0
        self._last_obstacle_centroid = None
        self._last_obstacle_signature = None

    def process_frame(
        self,
        image: UnifiedImage,
        segmentation: Optional[SemanticSegmentationResult] = None,
    ) -> Optional[ObstacleAlert]:
        """
        Process an incoming camera frame or uploaded image, identify obstacles,
        and trigger an event alert if detection criteria are met.

        Args:
            image: Ingested UnifiedImage.
            segmentation: Optional precomputed SemanticSegmentationResult.

        Returns:
            ObstacleAlert if a new event was triggered; None if suppressed or no obstacle.
        """
        if not self.config.auto_capture_enabled:
            return None

        # 1. Obtain Semantic Segmentation
        if segmentation is None:
            try:
                segmentation = segment_terrain(image, environment=image.environment)
            except Exception as e:
                logger.error(f"Failed to segment frame {image.image_id}: {e}")
                return None

        # 2. Check for Obstacle Presence
        # Calculate obstacle coverage (SemanticClass.OBSTACLE)
        obstacle_pct = segmentation.class_pixel_percentages.get(SemanticClass.OBSTACLE.value, 0.0)
        overall_confidence = segmentation.confidence_information.get("overall_confidence", 0.0)

        # Check if thresholds are met
        meets_area = obstacle_pct >= self.config.min_obstacle_area_pct
        meets_conf = overall_confidence >= self.config.min_confidence

        if not (meets_area and meets_conf):
            return None

        # 3. Locate Major Obstacle Region
        # Find the largest obstacle region among region segments
        obstacle_regions = [
            r for r in segmentation.region_segments
            if r.get("semantic_class") == SemanticClass.OBSTACLE.value
        ]
        if not obstacle_regions:
            # Fallback if region segmenter grouped it differently
            dominant_region = {
                "bounding_box": [0, 0, image.image.shape[0], image.image.shape[1]],
                "centroid": [image.image.shape[0] / 2.0, image.image.shape[1] / 2.0],
                "area_pixels": int((obstacle_pct / 100.0) * image.image.shape[0] * image.image.shape[1]),
                "area_percentage": obstacle_pct,
            }
        else:
            dominant_region = max(obstacle_regions, key=lambda r: r.get("area_pixels", 0))

        bbox = tuple(dominant_region["bounding_box"])  # (min_r, min_c, max_r, max_c)
        centroid = tuple(dominant_region["centroid"])  # (r, c)

        # 4. Deduplication & Temporal Cooldown Check
        current_time = time.time()
        elapsed_since_last = current_time - self._last_alert_time

        # Compute spatial perceptual fingerprint
        # Quantize centroid coordinates to 20px bins and hash with area
        grid_bin_r = int(centroid[0] // 25)
        grid_bin_c = int(centroid[1] // 25)
        area_bin = int(dominant_region["area_pixels"] // 100)
        obstacle_sig = f"{grid_bin_r}_{grid_bin_c}_{area_bin}_{image.environment.value}"

        is_duplicate = False
        if elapsed_since_last < self.config.cooldown_seconds:
            # Within cooldown window: check similarity
            if self._last_obstacle_signature == obstacle_sig:
                is_duplicate = True
            elif self._last_obstacle_centroid is not None:
                # Euclidean distance between obstacle centroids in pixels
                dist = np.hypot(centroid[0] - self._last_obstacle_centroid[0], centroid[1] - self._last_obstacle_centroid[1])
                diag = np.hypot(image.image.shape[0], image.image.shape[1])
                norm_dist = dist / max(diag, 1.0)
                if norm_dist < (1.0 - self.config.dedup_similarity_threshold):
                    is_duplicate = True

        if is_duplicate:
            # Suppress redundant alert for persistent hazard
            return None

        # 5. Build New Obstacle Alert Record
        event_uuid = uuid.uuid4().hex[:8]
        timestamp_str = datetime.now(timezone.utc).isoformat()
        date_tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        event_id = f"EVT-{date_tag}-{event_uuid}"

        # Generate diagnostic annotated image with prominent alert HUD
        annotated_img = self._create_alert_annotated_image(
            original_rgb=image.image,
            overlay_rgb=segmentation.overlay_image,
            bbox=bbox,
            event_id=event_id,
            confidence=overall_confidence,
            area_pct=obstacle_pct,
        )

        explanation = (
            f"Automatic visual alert triggered: High-contrast morphological hazard detected in camera field. "
            f"Obstacle surface coverage: {obstacle_pct:.1f}% (threshold {self.config.min_obstacle_area_pct}%). "
            f"Confidence: {overall_confidence:.2f}. Potential rover chassis rollover or wheel-entrapment hazard."
        )

        source_type = "CAMERA" if "camera" in image.source.lower() else "UPLOAD"

        # 6. Persist Images to Managed Storage
        image_rel_path, annotated_rel_path = self._persist_event_images(
            event_id=event_id,
            original_img=image.image,
            annotated_img=annotated_img,
        )

        alert = ObstacleAlert(
            event_id=event_id,
            timestamp=timestamp_str,
            source=source_type,
            environment=image.environment.value,
            detection_category="HAZARD_OBSTACLE",
            confidence=float(overall_confidence),
            obstacle_area_pct=float(obstacle_pct),
            explanation=explanation,
            verification_status="UNVERIFIED",
            captured_image=image.image.copy(),
            annotated_image=annotated_img,
            bounding_box=bbox,
            image_path=image_rel_path,
            annotated_path=annotated_rel_path,
            grid_mapping={
                "mapping_status": "UNMAPPED_VISUAL_OBSTACLE",
                "notes": "Visual obstacle detected without certified extrinsic camera-to-grid calibration.",
            },
            metadata={
                "image_id": image.image_id,
                "input_source": image.source,
                "dominant_class": segmentation.dominant_class,
                "camera_model": image.metadata.get("camera_model") if isinstance(image.metadata, dict) else getattr(image.metadata, "camera_model", "Generic_Rover_Camera"),
            },
        )

        # 7. Update Tracker State & Append
        self._last_alert_time = current_time
        self._last_obstacle_centroid = centroid
        self._last_obstacle_signature = obstacle_sig
        self._alerts.append(alert)

        # Enforce maximum stored events circular buffer
        if len(self._alerts) > self.config.max_stored_events:
            self._alerts.pop(0)

        return alert

    def _create_alert_annotated_image(
        self,
        original_rgb: np.ndarray,
        overlay_rgb: np.ndarray,
        bbox: Tuple[int, int, int, int],
        event_id: str,
        confidence: float,
        area_pct: float,
    ) -> np.ndarray:
        """Draws bounding box, target crosshairs, and diagnostic alert banner on the frame."""
        pil_img = Image.fromarray(overlay_rgb.copy())
        draw = ImageDraw.Draw(pil_img)

        min_r, min_c, max_r, max_c = bbox
        h, w = original_rgb.shape[:2]

        # Draw Crimson Red Alert Bounding Box (3px thick)
        red_box = (231, 76, 60)
        draw.rectangle([(min_c, min_r), (max_c, max_r)], outline=red_box, width=3)

        # Draw Top Warning Banner
        banner_h = 28
        draw.rectangle([(0, 0), (w, banner_h)], fill=(20, 20, 25))
        draw.rectangle([(0, banner_h - 2), (w, banner_h)], fill=red_box)

        banner_text = f"🔴 ALERT [{event_id}] OBSTACLE DETECTED | CONF: {confidence:.2f} | COVERAGE: {area_pct:.1f}%"
        draw.text((8, 6), banner_text, fill=(255, 255, 255))

        return np.array(pil_img)

    def _persist_event_images(
        self,
        event_id: str,
        original_img: np.ndarray,
        annotated_img: np.ndarray,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Saves original and annotated images to local disk, returning relative paths."""
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            orig_filename = f"{event_id}_orig.png"
            ann_filename = f"{event_id}_annotated.png"

            orig_path = self._storage_dir / orig_filename
            ann_path = self._storage_dir / ann_filename

            Image.fromarray(original_img).save(orig_path)
            Image.fromarray(annotated_img).save(ann_path)

            return str(orig_path).replace("\\", "/"), str(ann_path).replace("\\", "/")
        except Exception as e:
            logger.warning(f"Failed to persist alert images for {event_id}: {e}")
            return None, None


# Global singleton detector instance for app-wide lifecycle management
_DEFAULT_OBSTACLE_DETECTOR = ObstacleEventDetector()


def get_obstacle_detector() -> ObstacleEventDetector:
    """Access the application-wide singleton obstacle event detector."""
    return _DEFAULT_OBSTACLE_DETECTOR
