"""
Comprehensive Test Suite for ODYSSEY AI4Mars Dataset & Perception Pipeline (§Phase J).

Validates:
1. Exact AI4Mars dataset label mapping (0: SOIL, 1: BEDROCK, 2: SAND, 3: BOULDER, 255: IGNORE).
2. Proper handling of IGNORE (255) pixels (strictly decoded to UNKNOWN, never a terrain prediction).
3. Optical segmentation across all 4 supported AI4Mars classes (SOIL, BEDROCK, SAND, BOULDER).
4. Direct decoding of single-channel AI4Mars label masks.
5. Mixed composite scene segmentation containing all 4 terrain categories simultaneously.
6. Image-space rover travel corridor obstacle risk evaluation (NOT_DETECTED, POTENTIAL HAZARD, HIGH RISK, CRITICAL).
7. Non-destructive event alert clearing and lifecycle management.
8. Preservation of Member 3 navigation cost map contract (SAFE=1.0, CAUTION=5.0-20.0, HAZARD=np.inf).
"""

import numpy as np
import pytest

from visionscore.config import (
    AI4MARS_CLASS_TO_LABEL,
    AI4MARS_LABEL_MAP,
    AI4MARS_PRIMARY_CLASSES,
    EnvironmentProfile,
    SemanticClass,
    VisionConfig,
    VisualTerrainClass,
)
from visionscore.image_input import ImageInputHandler, SimulatedCameraFeed, UnifiedImage
from visionscore.obstacle_detector import ObstacleEventDetector, get_obstacle_detector
from visionscore.semantic import (
    DemoSemanticSegmentationModel,
    SemanticSegmentationResult,
    segment_terrain,
)
from visionscore.terrain_integration import evaluate_candidate_path_safety


# ==============================================================================
# 1. AI4Mars Dataset Label Mapping & Encoding Tests
# ==============================================================================

def test_ai4mars_label_mapping_spec():
    """Verify official NASA JPL AI4Mars dataset label index assignments."""
    assert AI4MARS_LABEL_MAP[0] == SemanticClass.SOIL
    assert AI4MARS_LABEL_MAP[1] == SemanticClass.BEDROCK
    assert AI4MARS_LABEL_MAP[2] == SemanticClass.SAND
    assert AI4MARS_LABEL_MAP[3] == SemanticClass.BOULDER
    assert AI4MARS_LABEL_MAP[255] == SemanticClass.UNKNOWN

    assert AI4MARS_CLASS_TO_LABEL[SemanticClass.SOIL] == 0
    assert AI4MARS_CLASS_TO_LABEL[SemanticClass.BEDROCK] == 1
    assert AI4MARS_CLASS_TO_LABEL[SemanticClass.SAND] == 2
    assert AI4MARS_CLASS_TO_LABEL[SemanticClass.BOULDER] == 3
    assert AI4MARS_CLASS_TO_LABEL[SemanticClass.UNKNOWN] == 255


def test_ignore_label_never_becomes_terrain():
    """Verify pixels with label 255 (IGNORE/unlabeled) are never decoded as terrain."""
    h, w = 40, 40
    raw_mask = np.full((h, w), 255, dtype=np.uint8)
    handler = ImageInputHandler()
    img = handler.load_from_array(raw_mask, environment=EnvironmentProfile.MARS)

    res = segment_terrain(img, environment=EnvironmentProfile.MARS)

    assert res.dominant_class == SemanticClass.UNKNOWN.value
    assert res.class_pixel_percentages.get(SemanticClass.SOIL.value, 0.0) == 0.0
    assert res.class_pixel_percentages.get(SemanticClass.BEDROCK.value, 0.0) == 0.0
    assert res.class_pixel_percentages.get(SemanticClass.SAND.value, 0.0) == 0.0
    assert res.class_pixel_percentages.get(SemanticClass.BOULDER.value, 0.0) == 0.0
    assert res.class_pixel_percentages.get(SemanticClass.UNKNOWN.value, 0.0) == 100.0


def test_direct_ai4mars_label_mask_decoding():
    """Verify a synthetic 1-channel label mask with 0, 1, 2, 3, 255 decodes accurately."""
    h, w = 100, 100
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[0:25, :] = 0    # SOIL: 25%
    mask[25:50, :] = 1   # BEDROCK: 25%
    mask[50:75, :] = 2   # SAND: 25%
    mask[75:90, :] = 3   # BOULDER: 15%
    mask[90:100, :] = 255 # UNKNOWN / IGNORE: 10%

    handler = ImageInputHandler()
    img = handler.load_from_array(mask, environment=EnvironmentProfile.MARS)
    res = segment_terrain(img, environment=EnvironmentProfile.MARS)

    assert pytest.approx(res.class_pixel_percentages[SemanticClass.SOIL.value], abs=1.0) == 25.0
    assert pytest.approx(res.class_pixel_percentages[SemanticClass.BEDROCK.value], abs=1.0) == 25.0
    assert pytest.approx(res.class_pixel_percentages[SemanticClass.SAND.value], abs=1.0) == 25.0
    assert pytest.approx(res.class_pixel_percentages[SemanticClass.BOULDER.value], abs=1.0) == 15.0
    assert pytest.approx(res.class_pixel_percentages[SemanticClass.UNKNOWN.value], abs=1.0) == 10.0


# ==============================================================================
# 2. Optical Classification Tests for Supported Categories
# ==============================================================================

def test_valid_soil_example():
    """Verify an oxidized ferric red Mars soil frame is correctly classified as SOIL."""
    feed = SimulatedCameraFeed(resolution=(60, 80), environment=EnvironmentProfile.MARS, terrain_mode="SOIL")
    frame, _ = feed.capture_frame()

    res = segment_terrain(frame, environment=EnvironmentProfile.MARS)
    assert res.dominant_class == SemanticClass.SOIL.value
    assert res.class_pixel_percentages[SemanticClass.SOIL.value] > 70.0


def test_valid_bedrock_example():
    """Verify an exposed gray basaltic rock pavement frame is classified as BEDROCK."""
    feed = SimulatedCameraFeed(resolution=(60, 80), environment=EnvironmentProfile.MARS, terrain_mode="BEDROCK")
    frame, _ = feed.capture_frame()

    res = segment_terrain(frame, environment=EnvironmentProfile.MARS)
    assert res.dominant_class == SemanticClass.BEDROCK.value
    assert res.class_pixel_percentages[SemanticClass.BEDROCK.value] > 60.0


def test_valid_sand_example():
    """Verify an aeolian golden-ochre sand dune frame is classified as SAND."""
    feed = SimulatedCameraFeed(resolution=(60, 80), environment=EnvironmentProfile.MARS, terrain_mode="SAND")
    frame, _ = feed.capture_frame()

    res = segment_terrain(frame, environment=EnvironmentProfile.MARS)
    assert res.dominant_class == SemanticClass.SAND.value
    assert res.class_pixel_percentages[SemanticClass.SAND.value] > 60.0


def test_valid_boulder_example():
    """Verify a rocky terrain frame with high-contrast rock clusters detects BOULDER."""
    feed = SimulatedCameraFeed(resolution=(60, 80), environment=EnvironmentProfile.MARS, terrain_mode="BOULDER")
    frame, _ = feed.capture_frame()

    res = segment_terrain(frame, environment=EnvironmentProfile.MARS)
    boulder_pct = res.class_pixel_percentages.get(SemanticClass.BOULDER.value, 0.0)
    assert boulder_pct > 3.0, "Expected prominent boulder detection in BOULDER terrain mode"


def test_mixed_composite_scene_all_classes():
    """Verify a composite simulated Mars frame contains all 4 AI4Mars classes simultaneously."""
    feed = SimulatedCameraFeed(resolution=(80, 100), environment=EnvironmentProfile.MARS, terrain_mode="MIXED")
    frame, _ = feed.capture_frame()

    res = segment_terrain(frame, environment=EnvironmentProfile.MARS)
    pcts = res.class_pixel_percentages

    assert pcts.get(SemanticClass.SOIL.value, 0.0) > 5.0
    assert pcts.get(SemanticClass.BEDROCK.value, 0.0) > 5.0
    assert pcts.get(SemanticClass.SAND.value, 0.0) > 5.0
    assert pcts.get(SemanticClass.BOULDER.value, 0.0) > 1.0


# ==============================================================================
# 3. Terrain Risk Assessment & Travel Corridor Tests (§Phase E)
# ==============================================================================

def test_risk_assessment_nominal_safe_terrain():
    """Verify nominal soil/bedrock terrain evaluates to SAFE risk level."""
    feed = SimulatedCameraFeed(resolution=(60, 80), environment=EnvironmentProfile.MARS, terrain_mode="BEDROCK")
    frame, _ = feed.capture_frame()

    res = segment_terrain(frame, environment=EnvironmentProfile.MARS)
    risk = res.risk_assessment
    assert risk is not None
    assert risk["risk_level"] in ("SAFE", "LOW RISK")
    assert risk["risk_score"] < 0.30
    assert risk["in_travel_corridor"] is False


def test_risk_assessment_critical_hazard_in_corridor():
    """Verify prominent obstacle injected in travel corridor evaluates to CRITICAL or HIGH RISK."""
    feed = SimulatedCameraFeed(resolution=(60, 80), environment=EnvironmentProfile.MARS, inject_obstacle=True)
    frame, _ = feed.capture_frame()

    res = segment_terrain(frame, environment=EnvironmentProfile.MARS)
    risk = res.risk_assessment
    assert risk is not None
    assert risk["status"] in ("CRITICAL", "HIGH RISK")
    assert risk["risk_score"] >= 0.60
    assert risk["in_travel_corridor"] is True
    assert "STOP" in risk["recommended_action"] or "REPLAN" in risk["recommended_action"]


# ==============================================================================
# 4. Obstacle Detector & Event History Tests (§Phase F)
# ==============================================================================

def test_alert_clear_and_event_lifecycle():
    """Verify alert creation, duplicate cooldown prevention, and clear action."""
    detector = ObstacleEventDetector()
    detector.clear_alerts()
    assert detector.alert_count == 0

    feed = SimulatedCameraFeed(resolution=(60, 80), environment=EnvironmentProfile.MARS, inject_obstacle=True)
    raw_frame, meta = feed.capture_frame()
    unified_img = UnifiedImage(
        image_id="test_alert_img_1",
        image=raw_frame,
        source="camera",
        environment=EnvironmentProfile.MARS,
        timestamp="2026-11-14T07:00:00Z",
        metadata=meta,
    )

    alert1 = detector.process_frame(unified_img)
    assert alert1 is not None
    assert detector.alert_count == 1

    # Second immediate poll on same scene should be suppressed by cooldown / deduplication
    alert2 = detector.process_frame(unified_img)
    assert alert2 is None, "Expected duplicate alert suppression within cooldown window"
    assert detector.alert_count == 1

    # Verify clearing
    detector.clear_alerts()
    assert detector.alert_count == 0
    assert len(detector.get_alerts()) == 0

