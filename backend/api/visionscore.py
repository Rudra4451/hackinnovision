"""
VisionScore 2.0 REST API Endpoints for MARS-09 Odyssey Mission Control.

Provides:
- Semantic terrain segmentation analysis (/api/visionscore/segment).
- Automatic obstacle alerts feed and verification (/api/visionscore/alerts).
- Live/simulated camera stream frames (/api/visionscore/camera/frame).
- Obstacle trigger simulation (/api/visionscore/camera/trigger).
- Path safety evaluation against visual alerts (/api/visionscore/evaluate-path).
"""

import base64
import io
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

from backend.integrations.terrain_adapter import get_default_terrain
from visionscore.config import EnvironmentProfile, SemanticClass
from visionscore.image_input import (
    CameraUnavailableError,
    ImageInputHandler,
    SimulatedCameraFeed,
    UnifiedImage,
)
from visionscore.obstacle_detector import ObstacleAlert, get_obstacle_detector
from visionscore.semantic import segment_terrain
from visionscore.terrain_integration import (
    evaluate_candidate_path_safety,
    integrate_visual_obstacle,
)

router = APIRouter(prefix="/api/visionscore", tags=["VisionScore 2.0"])

# Global simulated camera stream for API feed
_STREAM_SIMULATOR = SimulatedCameraFeed(environment=EnvironmentProfile.MARS)
_INPUT_HANDLER = ImageInputHandler(camera_stream=_STREAM_SIMULATOR)


def _to_base64_data_uri(img_arr: np.ndarray, format: str = "PNG") -> str:
    """Helper to convert NumPy RGB array to base64 Data URI string."""
    pil_img = Image.fromarray(img_arr)
    buf = io.BytesIO()
    pil_img.save(buf, format=format)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    mime = "image/png" if format.upper() == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


class PathEvaluationPayload(BaseModel):
    path: List[Tuple[int, int]] = Field(description="Sequence of (row, col) coordinates")
    rover_position: Optional[Tuple[int, int]] = None
    rover_heading_deg: Optional[float] = None


class VerificationPayload(BaseModel):
    status: str = Field(description="CONFIRMED, FALSE_POSITIVE, BYPASSED, UNVERIFIED")
    notes: Optional[str] = Field(default="")


@router.get("/status")
def get_visionscore_status() -> Dict[str, Any]:
    """Returns VisionScore operational status and feature inventory."""
    detector = get_obstacle_detector()
    return {
        "subsystem": "ODYSSEY VisionScore 2.0",
        "status": "OPERATIONAL",
        "version": "2.0.0",
        "active_environment": _STREAM_SIMULATOR.environment.value,
        "obstacle_injection_active": _STREAM_SIMULATOR.inject_obstacle,
        "total_alerts_recorded": detector.alert_count,
        "capabilities": [
            "Pixel-Level Semantic Segmentation",
            "Automatic Obstacle Event Detection",
            "Temporal Cooldown & Spatial Deduplication",
            "Managed Event Storage",
            "Verification Lifecycle Workflow",
            "DEM & Navigation Path Safety Scoring",
        ],
    }


@router.post("/segment")
async def segment_uploaded_image(
    file: Optional[UploadFile] = File(default=None),
    environment: str = Form(default="MARS"),
    include_preview: bool = Form(default=True),
) -> Dict[str, Any]:
    """
    Executes semantic terrain segmentation on an uploaded image or current camera frame.
    Returns pixel percentages, dominant class, traversability summary, and base64 overlays.
    """
    try:
        env_profile = EnvironmentProfile(environment.upper())
    except ValueError:
        env_profile = EnvironmentProfile.MARS

    if file is not None and file.filename:
        content = await file.read()
        unified_img = _INPUT_HANDLER.load_from_bytes(
            content,
            filename=file.filename,
            environment=env_profile,
        )
    else:
        # Fall back to live/simulated camera frame
        unified_img = _INPUT_HANDLER.capture_frame(environment_override=env_profile)

    res = segment_terrain(unified_img, environment=env_profile)

    # Check for automatic obstacle alert trigger
    detector = get_obstacle_detector()
    alert = detector.process_frame(unified_img, segmentation=res)

    payload = res.to_dict(include_arrays=False)
    if include_preview:
        payload["color_map_data_uri"] = _to_base64_data_uri(res.color_map)
        payload["overlay_data_uri"] = _to_base64_data_uri(res.overlay_image)
        payload["original_data_uri"] = _to_base64_data_uri(unified_img.image)

    payload["alert_triggered"] = alert is not None
    if alert is not None:
        payload["triggered_event_id"] = alert.event_id

    return payload


@router.get("/alerts")
def list_obstacle_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Lists captured obstacle alerts, sorted newest first."""
    detector = get_obstacle_detector()
    alerts = detector.get_alerts(limit=limit, status=status)
    return {
        "count": len(alerts),
        "total_recorded": detector.alert_count,
        "alerts": [a.to_dict(include_images=False) for a in alerts],
    }


@router.get("/alerts/{event_id}")
def get_alert_detail(event_id: str) -> Dict[str, Any]:
    """Retrieves detailed record for a specific obstacle alert with base64 image data."""
    detector = get_obstacle_detector()
    alert = detector.get_alert_by_id(event_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {event_id} not found")

    payload = alert.to_dict(include_images=True)
    payload["captured_image_data_uri"] = _to_base64_data_uri(alert.captured_image)
    payload["annotated_image_data_uri"] = _to_base64_data_uri(alert.annotated_image)
    return payload


@router.post("/alerts/{event_id}/verify")
def verify_alert_record(
    event_id: str,
    body: VerificationPayload,
) -> Dict[str, Any]:
    """Updates the verification status of an obstacle alert."""
    detector = get_obstacle_detector()
    try:
        success = detector.verify_alert(event_id, body.status, notes=body.notes or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not success:
        raise HTTPException(status_code=404, detail=f"Alert {event_id} not found")

    return {
        "event_id": event_id,
        "verification_status": body.status.upper(),
        "notes": body.notes,
        "updated": True,
    }


@router.get("/camera/frame")
def get_camera_frame(
    environment: str = Query(default="MARS"),
    include_segmentation: bool = Query(default=True),
) -> Dict[str, Any]:
    """
    Fetches the latest camera frame, performs obstacle detection,
    and returns image data URI and telemetry.
    """
    try:
        env_profile = EnvironmentProfile(environment.upper())
    except ValueError:
        env_profile = EnvironmentProfile.MARS

    unified_img = _INPUT_HANDLER.capture_frame(environment_override=env_profile)

    detector = get_obstacle_detector()
    seg_result = None
    if include_segmentation:
        seg_result = segment_terrain(unified_img, environment=env_profile)

    alert = detector.process_frame(unified_img, segmentation=seg_result)

    payload: Dict[str, Any] = {
        "image_id": unified_img.image_id,
        "timestamp": unified_img.timestamp,
        "environment": env_profile.value,
        "obstacle_injected": _STREAM_SIMULATOR.inject_obstacle,
        "alert_active": alert is not None,
        "frame_data_uri": _to_base64_data_uri(unified_img.image),
    }

    if alert is not None:
        payload["alert"] = alert.to_dict(include_images=False)
        payload["annotated_data_uri"] = _to_base64_data_uri(alert.annotated_image)

    if seg_result is not None:
        payload["dominant_class"] = seg_result.dominant_class
        payload["class_percentages"] = seg_result.class_pixel_percentages
        payload["overlay_data_uri"] = _to_base64_data_uri(seg_result.overlay_image)

    return payload


@router.post("/camera/trigger")
def trigger_simulated_obstacle(
    enable: bool = Query(default=True),
) -> Dict[str, Any]:
    """Toggles simulated prominent obstacle injection in the camera feed."""
    _STREAM_SIMULATOR.set_obstacle_injection(enable)
    return {
        "simulated_obstacle_enabled": enable,
        "message": "Simulated obstacle field enabled" if enable else "Simulated obstacle field disabled",
    }


@router.post("/evaluate-path")
def evaluate_path_safety(payload: PathEvaluationPayload) -> Dict[str, Any]:
    """
    Evaluates a candidate path against the current terrain cost map and visual alerts.
    Rejects paths intersecting impassable hazard cells (np.inf).
    """
    cost_map, _ = get_default_terrain()
    detector = get_obstacle_detector()
    active_alerts = detector.get_alerts(limit=10)

    result = evaluate_candidate_path_safety(
        path=payload.path,
        cost_map=cost_map,
        visual_alerts=active_alerts,
    )
    return result

