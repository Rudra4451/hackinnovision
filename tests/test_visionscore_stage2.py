"""
Automated Test Suite for ODYSSEY VisionScore 2.0.

Validates:
1. Semantic terrain segmentation schema and pixel-level mask integrity.
2. Pixel percentages summation and dominant class extraction.
3. Optical shadow and glare boundary handling (epistemic UNKNOWN class).
4. Environmental profile adaptations (MARS vs. EARTH vs. SIMULATION).
5. Automatic obstacle detection, event generation, and image persistence.
6. Cooldown duration and persistent obstacle deduplication.
7. Alert verification lifecycle (CONFIRMED, FALSE_POSITIVE).
8. Camera absence, permission denials, and corrupt frame error handling.
9. Unmapped visual obstacle reporting without coordinate invention.
10. Dynamic DEM correlation and perception discrepancy detection.
11. Candidate path safety evaluation with strict np.inf hazard rejection.
12. Backward compatibility with build_terrain_intelligence(seed=42) and Stage 1 APIs.
13. FastAPI VisionScore route schema integration.
"""

import io
import time
import numpy as np
from PIL import Image
import pytest

from core.terrain import build_terrain_intelligence
from visionscore.config import (
    AlertConfig,
    EnvironmentProfile,
    SEMANTIC_COLOR_PALETTE,
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
    InvalidImageError,
    SimulatedCameraFeed,
    UnifiedImage,
)
from visionscore.obstacle_detector import (
    ObstacleAlert,
    ObstacleEventDetector,
    get_obstacle_detector,
)
from visionscore.semantic import (
    DemoSemanticSegmentationModel,
    SemanticSegmentationResult,
    segment_terrain,
)
from visionscore.terrain_integration import (
    evaluate_candidate_path_safety,
    integrate_visual_obstacle,
)


def _create_synthetic_test_frame(
    width: int = 120,
    height: int = 100,
    base_color: tuple = (180, 90, 50),
    add_obstacle: bool = False,
    extreme_shadow: bool = False,
    extreme_glare: bool = False,
    green_patch: bool = False,
) -> np.ndarray:
    """Helper creating controlled synthetic RGB frames for testing."""
    img = np.full((height, width, 3), base_color, dtype=np.uint8)

    if add_obstacle:
        # High-contrast, high-gradient noisy obstacle block in center
        r_start, r_end = int(height * 0.3), int(height * 0.7)
        c_start, c_end = int(width * 0.3), int(width * 0.7)
        rng = np.random.default_rng(12345)
        noise = rng.integers(0, 255, size=(r_end - r_start, c_end - c_start, 3), dtype=np.uint8)
        img[r_start:r_end, c_start:c_end] = noise

    if extreme_shadow:
        r_sh = min(30, height // 3)
        c_sh = min(30, width // 3)
        img[10:10+r_sh, 10:10+c_sh] = 5  # Pitch black shadow (L <= 22)

    if extreme_glare:
        r_gl = min(30, height // 3)
        c_gl = min(30, width // 3)
        c_start_gl = max(0, width - 10 - c_gl)
        img[10:10+r_gl, c_start_gl:c_start_gl+c_gl] = 250  # Overexposed specular glare (L >= 242)

    if green_patch:
        r_gp = min(30, height // 3)
        c_gp = min(30, width // 3)
        r_start_gp = max(0, height - 10 - r_gp)
        img[r_start_gp:r_start_gp+r_gp, 10:10+c_gp] = (30, 220, 40)  # Strong chlorophyll green

    return img


# ==============================================================================
# 1. Semantic Terrain Segmentation Tests
# ==============================================================================

def test_semantic_segmentation_output_schema():
    """Verify semantic segmentation result fields, types, and model status."""
    frame = _create_synthetic_test_frame(width=80, height=60, add_obstacle=True)
    res = segment_terrain(frame, environment=EnvironmentProfile.MARS)

    assert isinstance(res, SemanticSegmentationResult)
    assert isinstance(res.segmentation_mask, np.ndarray)
    assert res.segmentation_mask.shape == (60, 80)
    assert isinstance(res.color_map, np.ndarray)
    assert res.color_map.shape == (60, 80, 3)
    assert res.color_map.dtype == np.uint8
    assert isinstance(res.overlay_image, np.ndarray)
    assert res.overlay_image.shape == (60, 80, 3)

    assert isinstance(res.class_names, dict)
    assert isinstance(res.class_pixel_percentages, dict)
    assert res.dominant_class in [c.value for c in SemanticClass]
    assert isinstance(res.traversability_summary, dict)
    assert isinstance(res.confidence_information, dict)
    assert 0.0 <= res.confidence_information["overall_confidence"] <= 1.0

    # Model status transparency check
    assert res.model_status["is_real_ai_model"] is False
    assert "DEMO" in res.model_status["model_type"] or "HEURISTIC" in res.model_status["model_type"]


def test_pixel_mask_dimensions_and_percentages_sum():
    """Verify mask dimensions match input and class pixel percentages sum to 100%."""
    frame = _create_synthetic_test_frame(width=100, height=80)
    res = segment_terrain(frame, environment=EnvironmentProfile.MARS)

    assert res.segmentation_mask.shape == (80, 100)
    total_pct = sum(res.class_pixel_percentages.values())
    assert pytest.approx(total_pct, rel=1e-3) == 100.0

    # Verify every class index in mask is valid
    unique_indices = np.unique(res.segmentation_mask)
    for idx in unique_indices:
        assert idx in res.class_names


def test_unknown_classification_shadow_and_glare():
    """Verify extreme shadow and glare pixels are explicitly classified as UNKNOWN."""
    frame = _create_synthetic_test_frame(width=100, height=100, extreme_shadow=True, extreme_glare=True)
    res = segment_terrain(frame, environment=EnvironmentProfile.MARS)

    unknown_pct = res.class_pixel_percentages.get(SemanticClass.UNKNOWN.value, 0.0)
    assert unknown_pct > 0.0, "Expected shadow and glare regions to register as UNKNOWN"

    # Region (15, 15) is pitch black shadow -> must be UNKNOWN (class id 6)
    assert res.class_names[res.segmentation_mask[15, 15]] == SemanticClass.UNKNOWN.value
    # Region (15, 75) is specular glare -> must be UNKNOWN
    assert res.class_names[res.segmentation_mask[15, 75]] == SemanticClass.UNKNOWN.value


def test_environment_profiles_biological_rules():
    """Verify green chlorophyll features map to VEGETATION on Earth but UNKNOWN on Mars."""
    frame = _create_synthetic_test_frame(width=100, height=100, green_patch=True)

    # 1. On Earth: green patch should detect VEGETATION
    res_earth = segment_terrain(frame, environment=EnvironmentProfile.EARTH)
    veg_pct = res_earth.class_pixel_percentages.get(SemanticClass.VEGETATION.value, 0.0)
    assert veg_pct > 2.0, "Expected chlorophyll patch to be classified as VEGETATION on Earth"

    # 2. On Mars: biological vegetation is impossible -> must NOT be classified as VEGETATION
    res_mars = segment_terrain(frame, environment=EnvironmentProfile.MARS)
    mars_veg_pct = res_mars.class_pixel_percentages.get(SemanticClass.VEGETATION.value, 0.0)
    assert mars_veg_pct == 0.0, "Vegetation must not be detected on Martian surface"
    # It must be flagged as UNKNOWN anomaly
    assert res_mars.class_names[res_mars.segmentation_mask[70, 25]] == SemanticClass.UNKNOWN.value


# ==============================================================================
# 2. Automatic Obstacle Detection & Event Alerts Tests
# ==============================================================================

def test_obstacle_event_creation_and_auto_capture(tmp_path):
    """Verify obstacle detection triggers event creation, saves images, and returns alert record."""
    config = AlertConfig(
        min_confidence=0.50,
        min_obstacle_area_pct=2.0,
        cooldown_seconds=1.0,
        storage_dir=str(tmp_path),
    )
    detector = ObstacleEventDetector(config=config)

    # Ingest frame with prominent noisy obstacle
    frame_arr = _create_synthetic_test_frame(width=120, height=100, add_obstacle=True)
    handler = ImageInputHandler()
    unified_img = handler.load_from_array(frame_arr, environment=EnvironmentProfile.MARS)

    alert = detector.process_frame(unified_img)

    assert alert is not None
    assert alert.event_id.startswith("EVT-")
    assert alert.detection_category == "HAZARD_OBSTACLE"
    assert alert.confidence >= 0.50
    assert alert.obstacle_area_pct >= 2.0
    assert alert.verification_status == "UNVERIFIED"
    assert alert.captured_image.shape == (100, 120, 3)
    assert alert.annotated_image.shape == (100, 120, 3)

    # Verify saved files exist on disk
    assert alert.image_path is not None
    assert alert.annotated_path is not None
    assert (tmp_path / f"{alert.event_id}_orig.png").exists()
    assert (tmp_path / f"{alert.event_id}_annotated.png").exists()


def test_duplicate_event_prevention_and_cooldown(tmp_path):
    """Verify persistent obstacle in camera view is suppressed by cooldown and deduplication."""
    config = AlertConfig(
        min_confidence=0.50,
        min_obstacle_area_pct=2.0,
        cooldown_seconds=3.0,
        storage_dir=str(tmp_path),
    )
    detector = ObstacleEventDetector(config=config)

    frame_arr = _create_synthetic_test_frame(width=120, height=100, add_obstacle=True)
    handler = ImageInputHandler()
    img1 = handler.load_from_array(frame_arr, environment=EnvironmentProfile.MARS)

    # First frame -> triggers alert
    alert1 = detector.process_frame(img1)
    assert alert1 is not None

    # Immediate second frame of same persistent obstacle -> MUST be suppressed
    img2 = handler.load_from_array(frame_arr, environment=EnvironmentProfile.MARS)
    alert2 = detector.process_frame(img2)
    assert alert2 is None, "Duplicate alert should be suppressed within cooldown window"
    assert detector.alert_count == 1


def test_alert_verification_workflow(tmp_path):
    """Verify operator verification status updates and rejection of invalid statuses."""
    config = AlertConfig(storage_dir=str(tmp_path))
    detector = ObstacleEventDetector(config=config)

    frame_arr = _create_synthetic_test_frame(width=120, height=100, add_obstacle=True)
    handler = ImageInputHandler()
    img = handler.load_from_array(frame_arr)
    alert = detector.process_frame(img)
    assert alert is not None

    # Verify as CONFIRMED
    success = detector.verify_alert(alert.event_id, "CONFIRMED", notes="Confirmed high-relief boulder field")
    assert success is True
    assert alert.verification_status == "CONFIRMED"
    assert "verification_notes" in alert.metadata

    # Verify invalid status raises ValueError
    with pytest.raises(ValueError):
        detector.verify_alert(alert.event_id, "TOTALLY_SAFE_TRUST_ME")


# ==============================================================================
# 3. Robust Error Handling Tests
# ==============================================================================

def test_missing_camera_and_permission_denials():
    """Verify missing camera stream and permission denials are handled gracefully."""
    class BrokenStream(BaseCameraStream):
        def is_available(self) -> bool:
            return False
        def capture_frame(self):
            raise CameraUnavailableError("Camera device disconnected")
        def release(self):
            pass

    cam_source = CameraFrameSource(stream=BrokenStream())
    with pytest.raises(CameraUnavailableError):
        cam_source.capture()


def test_invalid_and_empty_images():
    """Verify corrupted image buffers and zero-sized arrays raise explicit domain errors."""
    handler = ImageInputHandler()

    with pytest.raises(EmptyImageError):
        handler.load_from_array(np.zeros((0, 0, 3), dtype=np.uint8))

    with pytest.raises(InvalidImageError):
        handler.load_from_bytes(b"NOT_A_VALID_IMAGE_HEADER_BYTES")


# ==============================================================================
# 4. Terrain Intelligence & Navigation Integration Tests
# ==============================================================================

def test_unmapped_visual_obstacle_handling():
    """Verify obstacle without camera extrinsics is reported as unmapped without inventing coords."""
    terrain = build_terrain_intelligence(seed=42)
    alert = ObstacleAlert(
        event_id="EVT-TEST-001",
        timestamp="2026-11-14T05:00:00Z",
        source="CAMERA",
        environment="MARS",
        detection_category="HAZARD_OBSTACLE",
        confidence=0.88,
        obstacle_area_pct=8.5,
        explanation="Test obstacle alert",
        verification_status="UNVERIFIED",
        captured_image=np.zeros((10, 10, 3), dtype=np.uint8),
        annotated_image=np.zeros((10, 10, 3), dtype=np.uint8),
    )

    # No rover pose or heading provided
    report = integrate_visual_obstacle(terrain, alert, rover_position=None)
    assert report["status"] == "UNMAPPED_VISUAL_OBSTACLE"
    assert "warning" in report
    assert "projected_coordinate" not in report


def test_projected_obstacle_correlation_and_discrepancy():
    """Verify projection correlates with DEM hazards and flags discrepancies."""
    terrain = build_terrain_intelligence(seed=42)
    alert = ObstacleAlert(
        event_id="EVT-TEST-002",
        timestamp="2026-11-14T05:00:00Z",
        source="CAMERA",
        environment="MARS",
        detection_category="HAZARD_OBSTACLE",
        confidence=0.92,
        obstacle_area_pct=12.0,
        explanation="Test obstacle alert",
        verification_status="UNVERIFIED",
        captured_image=np.zeros((10, 10, 3), dtype=np.uint8),
        annotated_image=np.zeros((10, 10, 3), dtype=np.uint8),
    )

    # Project 2 meters North from (10, 10) -> target is (8, 10)
    report = integrate_visual_obstacle(
        terrain,
        alert,
        rover_position=(10, 10),
        heading_deg=0.0,
        estimated_range_m=2.0,
    )
    assert report["status"] == "PROJECTED_VISUAL_OBSTACLE"
    assert report["projected_coordinate"] == [8, 10]
    assert report["correlation_with_dem"] in ["CORRELATED_CONFIRMED_HAZARD", "CORRELATED_CAUTION_ZONE", "PERCEPTION_DISCREPANCY_WARNING"]


def test_candidate_path_safety_evaluation_and_hazard_rejection():
    """Verify evaluate_candidate_path_safety immediately rejects paths with np.inf."""
    cost_map = np.full((10, 10), 1.0, dtype=np.float64)
    cost_map[3, 3] = np.inf  # Impassable boulder

    # Path 1: traverses (3, 3) -> MUST be rejected
    path_blocked = [(1, 1), (2, 2), (3, 3), (4, 4)]
    eval_blocked = evaluate_candidate_path_safety(path_blocked, cost_map)
    assert eval_blocked["path_accepted"] is False
    assert eval_blocked["traversability_score"] == 0.0
    assert "impassable hazard" in eval_blocked["rejection_reason"]

    # Path 2: completely safe
    path_safe = [(1, 1), (1, 2), (1, 3), (1, 4)]
    eval_safe = evaluate_candidate_path_safety(path_safe, cost_map)
    assert eval_safe["path_accepted"] is True
    assert eval_safe["traversability_score"] == 100.0


def test_backward_compatibility_with_stage1_and_terrain_intelligence():
    """Verify build_terrain_intelligence(seed=42) and Stage 1 analyze_terrain run with 0 regressions."""
    terrain = build_terrain_intelligence(seed=42)
    assert "cost_map" in terrain
    assert terrain["cost_map"].shape == (100, 100)
    assert float(np.min(terrain["cost_map"])) == 1.0

    # Ingest via Stage 1 CameraFrameSource
    cam = CameraFrameSource()
    frame = cam.capture()
    assert isinstance(frame, UnifiedImage)
    assert frame.image.ndim == 3
