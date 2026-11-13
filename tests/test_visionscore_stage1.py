"""
Comprehensive Unit Tests for ODYSSEY VisionScore Stage 1: Unified Image Input Foundation.

Validates:
1. Upload input (files, bytes, arrays).
2. Camera input abstraction (BaseCameraStream, SimulatedCameraFeed, CameraFrameSource).
3. Invalid and empty images (EmptyImageError, InvalidImageError).
4. Camera error handling (CameraUnavailableError, CameraPermissionError).
5. Environment profiles (MARS, EARTH, SIMULATION).
6. Simulation images.
7. Real image input simulation / normalization.
8. AnalysisResult schema completeness.
9. Confidence range verification [0.0, 1.0].
10. UNKNOWN category handling on underexposed/glare conditions.
11. Annotated image output and dimensions.
12. VisualResults presentation container and summary exports.
13. Non-interference with existing build_terrain_intelligence and cost_map contracts.
"""

import io
from pathlib import Path
import numpy as np
from PIL import Image
import pytest

from visionscore import (
    AnalysisResult,
    BaseCameraStream,
    CameraFrameSource,
    CameraPermissionError,
    CameraUnavailableError,
    DemoVisualTerrainModel,
    EmptyImageError,
    EnvironmentProfile,
    ImageUploadSource,
    InvalidImageError,
    SimulatedCameraFeed,
    UnifiedImage,
    VisionConfig,
    VisualResults,
    VisualTerrainClass,
    analyze_terrain,
)
from core.terrain import build_terrain_intelligence


# ==============================================================================
# 1. Image Upload Tests
# ==============================================================================

def test_upload_input_from_numpy_array():
    """Verify ImageUploadSource accurately ingests standard 2D and 3D NumPy arrays."""
    uploader = ImageUploadSource()

    # 3D RGB array
    arr = np.random.randint(50, 200, size=(120, 160, 3), dtype=np.uint8)
    img = uploader.load_from_array(arr, environment=EnvironmentProfile.MARS)

    assert isinstance(img, UnifiedImage)
    assert img.shape == (120, 160, 3)
    assert img.height == 120
    assert img.width == 160
    assert img.channels == 3
    assert img.source == "upload"
    assert img.environment == EnvironmentProfile.MARS
    assert "image_id" in img.metadata
    assert img.metadata["original_format"] == "NUMPY_ARRAY"


def test_upload_input_from_bytes_and_file(tmp_path):
    """Verify loading images from encoded bytes and filesystem paths."""
    uploader = ImageUploadSource()

    # Create temporary PNG on disk
    pil_img = Image.new("RGB", (200, 150), color=(180, 90, 50))
    file_path = tmp_path / "test_terrain.png"
    pil_img.save(file_path, format="PNG")

    # 1. Load from path
    img_from_path = uploader.load_from_path(file_path, environment=EnvironmentProfile.EARTH)
    assert img_from_path.shape == (150, 200, 3)
    assert img_from_path.environment == EnvironmentProfile.EARTH
    assert img_from_path.metadata["original_format"] == "PNG"

    # 2. Load from raw bytes buffer
    with open(file_path, "rb") as f:
        raw_bytes = f.read()
    img_from_bytes = uploader.load_from_bytes(raw_bytes, filename="buffer.png")
    assert img_from_bytes.shape == (150, 200, 3)
    assert img_from_bytes.metadata["file_size_bytes"] == len(raw_bytes)


def test_invalid_image_corrupted_data_raises():
    """Verify that corrupt byte streams raise InvalidImageError."""
    uploader = ImageUploadSource()
    garbage_bytes = b"NOT_A_VALID_IMAGE_HEADER_CORRUPTED_STREAM_12345"

    with pytest.raises(InvalidImageError):
        uploader.load_from_bytes(garbage_bytes)


def test_empty_image_raises(tmp_path):
    """Verify that 0-byte or zero-dimension images raise EmptyImageError."""
    uploader = ImageUploadSource()

    # Empty bytes
    with pytest.raises(EmptyImageError):
        uploader.load_from_bytes(b"")

    # Empty 0-byte file
    empty_file = tmp_path / "zero_bytes.jpg"
    empty_file.write_bytes(b"")
    with pytest.raises(EmptyImageError):
        uploader.load_from_path(empty_file)

    # Empty NumPy array
    with pytest.raises(EmptyImageError):
        uploader.load_from_array(np.array([]))


# ==============================================================================
# 2. Camera Input Abstraction Tests
# ==============================================================================

class MockFailingCamera(BaseCameraStream):
    """Mock camera stream simulating hardware permission denial."""
    def capture_frame(self):
        raise CameraPermissionError("OS denied camera access: /dev/video0 permission denied.")
    def is_available(self):
        return True
    def release(self):
        pass


class MockUnavailableCamera(BaseCameraStream):
    """Mock camera stream simulating disconnected hardware."""
    def capture_frame(self):
        raise CameraUnavailableError("Camera disconnected or device not found.")
    def is_available(self):
        return False
    def release(self):
        pass


def test_camera_input_abstraction_simulated_stream():
    """Verify CameraFrameSource seamlessly queries simulated camera stream."""
    feed = SimulatedCameraFeed(resolution=(240, 320), seed=42, environment=EnvironmentProfile.MARS)
    cam_source = CameraFrameSource(stream=feed, environment=EnvironmentProfile.MARS)

    frame1 = cam_source.capture()
    assert isinstance(frame1, UnifiedImage)
    assert frame1.shape == (240, 320, 3)
    assert frame1.source == "camera_frame"
    assert frame1.environment == EnvironmentProfile.MARS
    assert frame1.metadata["camera_model"] == "MARS09_MastCam_Simulated"
    assert frame1.metadata["extra"]["ephemeral"] is True

    # Capture sequential frame
    frame2 = cam_source.capture()
    assert frame2.image_id != frame1.image_id


def test_camera_unavailable_and_permission_denial():
    """Verify camera failure modes are handled with structured, graceful exceptions."""
    # 1. Unavailable camera
    unavail_cam = CameraFrameSource(stream=MockUnavailableCamera())
    with pytest.raises(CameraUnavailableError):
        unavail_cam.capture()

    # 2. Permission denied camera
    denied_cam = CameraFrameSource(stream=MockFailingCamera())
    with pytest.raises(CameraPermissionError):
        denied_cam.capture()


# ==============================================================================
# 3. Environment Profiles & Analysis Interface Tests
# ==============================================================================

def test_environment_profiles_mars_earth_simulation():
    """Verify analysis responds predictably to MARS, EARTH, and SIMULATION environments."""
    uploader = ImageUploadSource()
    arr = np.ones((100, 100, 3), dtype=np.uint8) * 128  # Mid-gray test patch

    for env in (EnvironmentProfile.MARS, EnvironmentProfile.EARTH, EnvironmentProfile.SIMULATION):
        img = uploader.load_from_array(arr, environment=env)
        result = analyze_terrain(img, environment=env)

        assert isinstance(result, AnalysisResult)
        assert result.overall_status.startswith("OPERATIONAL_")
        assert result.model_status["environment_calibrated"] == env.value
        assert result.model_status["is_real_ai_model"] is False  # Transparency rule


def test_unknown_handling_on_extreme_lighting():
    """Verify that severe shadow (underexposure) or optical glare (saturation) is categorized as UNKNOWN."""
    uploader = ImageUploadSource()

    # Pitch black shadow crevice (luminance < 10)
    shadow_patch = np.zeros((80, 80, 3), dtype=np.uint8)
    shadow_img = uploader.load_from_array(shadow_patch, environment=EnvironmentProfile.MARS)
    shadow_result = analyze_terrain(shadow_img)

    assert shadow_result.terrain_class == VisualTerrainClass.UNKNOWN
    assert shadow_result.classification[VisualTerrainClass.UNKNOWN.value] > 0.80

    # Blinding glare saturation (luminance > 250)
    glare_patch = np.ones((80, 80, 3), dtype=np.uint8) * 255
    glare_img = uploader.load_from_array(glare_patch, environment=EnvironmentProfile.MARS)
    glare_result = analyze_terrain(glare_img)

    assert glare_result.terrain_class == VisualTerrainClass.UNKNOWN
    assert glare_result.classification[VisualTerrainClass.UNKNOWN.value] > 0.80


def test_confidence_range_and_metrics():
    """Verify confidence metrics are strictly clamped in [0.0, 1.0]."""
    uploader = ImageUploadSource()
    arr = np.random.randint(40, 220, size=(128, 128, 3), dtype=np.uint8)
    img = uploader.load_from_array(arr, environment=EnvironmentProfile.MARS)
    result = analyze_terrain(img)

    assert 0.0 <= result.confidence <= 1.0
    for reg in result.terrain_regions:
        assert 0.0 <= reg.confidence <= 1.0
        assert reg.terrain_class in (
            VisualTerrainClass.SAFE,
            VisualTerrainClass.CAUTION,
            VisualTerrainClass.HAZARD,
            VisualTerrainClass.UNKNOWN,
        )


def test_annotated_image_output_and_dimensions():
    """Verify that annotated output image matches original resolution and has valid RGB uint8 type."""
    uploader = ImageUploadSource()
    arr = np.random.randint(60, 180, size=(90, 140, 3), dtype=np.uint8)
    img = uploader.load_from_array(arr)
    result = analyze_terrain(img)

    annot = result.annotated_image
    assert isinstance(annot, np.ndarray)
    assert annot.shape == arr.shape
    assert annot.dtype == np.uint8


# ==============================================================================
# 4. VisualResults Container Tests
# ==============================================================================

def test_visual_results_container_methods(tmp_path):
    """Verify VisualResults interface, dictionary serialization, and disk export helpers."""
    uploader = ImageUploadSource()
    arr = np.random.randint(80, 170, size=(100, 120, 3), dtype=np.uint8)
    img = uploader.load_from_array(arr, environment=EnvironmentProfile.MARS)
    analysis = analyze_terrain(img)

    results = VisualResults.from_analysis(img, analysis, duration_ms=12.5)

    assert results.environment == "MARS"
    assert results.image_source == "upload"
    assert results.processing_status["duration_ms"] == 12.5
    assert len(results.detected_terrain_classes) > 0

    # Summary string check
    summary_text = results.get_summary()
    assert "Environment : MARS" in summary_text
    assert "Latency     : 12.5 ms" in summary_text

    # Disk export check
    save_path = tmp_path / "diagnostic_overlay.png"
    saved = results.save_annotated_image(save_path)
    assert saved.exists()
    assert saved.stat().st_size > 0

    comparison_path = tmp_path / "side_by_side.png"
    comp_saved = results.save_side_by_side(comparison_path)
    assert comp_saved.exists()
    assert comp_saved.stat().st_size > 0


# ==============================================================================
# 5. Non-Interference Regression Tests
# ==============================================================================

def test_existing_terrain_and_costmap_contract_unaffected():
    """Verify that build_terrain_intelligence and Member 3 cost_map contract remain 100% operational."""
    terrain = build_terrain_intelligence(seed=42)
    cost_map = terrain["cost_map"]

    assert cost_map.shape == (100, 100)
    assert cost_map.dtype == np.float64

    # Contract checks: SAFE == 1.0, CAUTION > 2.0, HAZARD == np.inf
    safe_cells = cost_map[terrain["classification"] == 0]
    if len(safe_cells) > 0:
        np.testing.assert_allclose(safe_cells, 1.0)

    caution_cells = cost_map[terrain["classification"] == 1]
    if len(caution_cells) > 0:
        assert np.all(caution_cells > 2.0)

    hazard_cells = cost_map[terrain["classification"] == 2]
    if len(hazard_cells) > 0:
        assert np.all(np.isinf(hazard_cells))

