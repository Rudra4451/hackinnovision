"""
Automated Test Suite for ODYSSEY Task 1: Mars-Only Configuration & Semantic Taxonomy.

Verifies:
1. Operational environment defaults to MARS, with SIMULATION_MARS as active simulation.
2. EARTH is deprecated and excluded from active operational selection profiles.
3. Backward compatibility for legacy aliases (EARTH, SIMULATION, OBSTACLE, VEGETATION, WATER).
4. Extended Mars semantic terrain taxonomy (9 target classes).
5. Explicit, rigorous mapping between semantic material classes and visual traversability tiers.
6. Transparent model status disclosing heuristic limitations and listing supported vs planned classes.
7. SimulatedCameraFeed operational behavior under MARS and SIMULATION_MARS.
8. Preservation of Member 1 A* pathfinding and Member 3 navigation integration contract.
"""

import math
import numpy as np
import pytest

from backend.integrations.terrain_adapter import get_default_terrain
from core.terrain import build_terrain_intelligence
from visionscore.config import (
    ACTIVE_ENVIRONMENT_PROFILES,
    DEFAULT_ENVIRONMENT_PARAMETERS,
    EXTENDED_PLANNED_CLASSES,
    HEURISTIC_RECOGNIZED_CLASSES,
    MARS_TARGET_TAXONOMY,
    OPERATIONAL_ENVIRONMENTS,
    SEMANTIC_COLOR_PALETTE,
    SEMANTIC_TRAVERSABILITY_MAP,
    EnvironmentProfile,
    SemanticClass,
    VisionConfig,
    VisualTerrainClass,
    resolve_environment,
)
from visionscore.image_input import (
    CameraFrameSource,
    ImageInputHandler,
    SimulatedCameraFeed,
    UnifiedImage,
)
from visionscore.obstacle_detector import ObstacleAlert, get_obstacle_detector
from visionscore.semantic import (
    DemoSemanticSegmentationModel,
    SemanticSegmentationResult,
    segment_terrain,
)
from visionscore.terrain_integration import (
    evaluate_candidate_path_safety,
    integrate_visual_obstacle,
)


# ============================================================================
# 1. Operational Environment & Configuration Tests
# ============================================================================

def test_mars_is_default_environment():
    """Verify MARS is the default environment across global configurations."""
    cfg = VisionConfig()
    assert cfg.default_environment == EnvironmentProfile.MARS
    assert EnvironmentProfile.MARS.value == "MARS"


def test_active_environment_profiles_contain_only_mars_and_simulation():
    """Verify only MARS and SIMULATION_MARS are marked as active operational environments."""
    assert EnvironmentProfile.MARS in ACTIVE_ENVIRONMENT_PROFILES
    assert EnvironmentProfile.SIMULATION_MARS in ACTIVE_ENVIRONMENT_PROFILES
    assert EnvironmentProfile.EARTH not in ACTIVE_ENVIRONMENT_PROFILES
    assert EnvironmentProfile.SIMULATION not in ACTIVE_ENVIRONMENT_PROFILES
    assert len(ACTIVE_ENVIRONMENT_PROFILES) == 2
    assert OPERATIONAL_ENVIRONMENTS == ACTIVE_ENVIRONMENT_PROFILES


def test_backward_compatibility_environment_aliases():
    """Verify legacy environment profiles import and evaluate correctly without errors."""
    assert EnvironmentProfile.EARTH.value == "EARTH"
    assert EnvironmentProfile.SIMULATION.value == "SIMULATION"

    cfg = VisionConfig()
    # Test retrieving parameters for legacy aliases
    earth_params = cfg.get_env_params(EnvironmentProfile.EARTH)
    assert earth_params.name == "EARTH"

    sim_params = cfg.get_env_params(EnvironmentProfile.SIMULATION)
    assert "SIMULATION" in sim_params.name


def test_backend_environment_resolution():
    """Verify API endpoint resolver maps aliases and fallbacks cleanly to Mars."""
    assert resolve_environment("MARS") == EnvironmentProfile.MARS
    assert resolve_environment("mars") == EnvironmentProfile.MARS
    assert resolve_environment("SIMULATION_MARS") == EnvironmentProfile.SIMULATION_MARS
    assert resolve_environment("simulation") == EnvironmentProfile.SIMULATION_MARS
    assert resolve_environment("sim_mars") == EnvironmentProfile.SIMULATION_MARS
    assert resolve_environment("EARTH") == EnvironmentProfile.EARTH
    assert resolve_environment("NONEXISTENT_PLANET") == EnvironmentProfile.MARS


# ============================================================================
# 2. Extended Mars Semantic Terrain Taxonomy Tests
# ============================================================================

def test_full_mars_semantic_taxonomy_classes():
    """Verify all 9 target Mars geological semantic categories are defined."""
    target_names = [
        "ROCK",
        "BOULDER",
        "SAND",
        "REGOLITH",
        "SOIL",
        "BEDROCK",
        "DUST",
        "CRATER",
        "UNKNOWN",
    ]
    for name in target_names:
        assert hasattr(SemanticClass, name), f"SemanticClass missing target class {name}"
        assert getattr(SemanticClass, name).value == name

    # Verify MARS_TARGET_TAXONOMY tuple matches
    taxonomy_values = [c.value for c in MARS_TARGET_TAXONOMY]
    assert set(target_names).issubset(set(taxonomy_values))


def test_backward_compatibility_class_aliases():
    """Verify legacy classes remain accessible for existing code."""
    assert hasattr(SemanticClass, "OBSTACLE")
    assert hasattr(SemanticClass, "VEGETATION")
    assert hasattr(SemanticClass, "WATER")


def test_semantic_to_traversability_mapping_contract():
    """Verify strict, explicit mapping from each semantic class to traversability tier."""
    # SAFE: SAND, SOIL, REGOLITH, BEDROCK
    assert SEMANTIC_TRAVERSABILITY_MAP[SemanticClass.SAND] == VisualTerrainClass.SAFE
    assert SEMANTIC_TRAVERSABILITY_MAP[SemanticClass.SOIL] == VisualTerrainClass.SAFE
    assert SEMANTIC_TRAVERSABILITY_MAP[SemanticClass.REGOLITH] == VisualTerrainClass.SAFE
    assert SEMANTIC_TRAVERSABILITY_MAP[SemanticClass.BEDROCK] == VisualTerrainClass.SAFE

    # CAUTION: ROCK, DUST
    assert SEMANTIC_TRAVERSABILITY_MAP[SemanticClass.ROCK] == VisualTerrainClass.CAUTION
    assert SEMANTIC_TRAVERSABILITY_MAP[SemanticClass.DUST] == VisualTerrainClass.CAUTION

    # HAZARD: BOULDER, CRATER, OBSTACLE, WATER
    assert SEMANTIC_TRAVERSABILITY_MAP[SemanticClass.BOULDER] == VisualTerrainClass.HAZARD
    assert SEMANTIC_TRAVERSABILITY_MAP[SemanticClass.CRATER] == VisualTerrainClass.HAZARD
    assert SEMANTIC_TRAVERSABILITY_MAP[SemanticClass.OBSTACLE] == VisualTerrainClass.HAZARD
    assert SEMANTIC_TRAVERSABILITY_MAP[SemanticClass.WATER] == VisualTerrainClass.HAZARD

    # UNKNOWN: UNKNOWN
    assert SEMANTIC_TRAVERSABILITY_MAP[SemanticClass.UNKNOWN] == VisualTerrainClass.UNKNOWN


def test_all_classes_have_distinctive_colors():
    """Verify publication-grade RGB palette covers all classes with valid RGB values."""
    for cls in SemanticClass:
        assert cls in SEMANTIC_COLOR_PALETTE, f"Missing color for {cls}"
        color = SEMANTIC_COLOR_PALETTE[cls]
        assert len(color) == 3
        for channel in color:
            assert 0 <= channel <= 255


# ============================================================================
# 3. Model Transparency & Truthful Capability Disclosure Tests
# ============================================================================

def test_model_status_truthful_capability_disclosure():
    """Verify model status honestly declares heuristic nature and separates supported vs planned classes."""
    model = DemoSemanticSegmentationModel()
    assert model.is_real_ai_model is False

    # Create synthetic test frame
    frame = np.full((100, 100, 3), (180, 90, 50), dtype=np.uint8)
    handler = ImageInputHandler()
    img = handler.load_from_array(frame, environment=EnvironmentProfile.MARS)

    res = model.segment(img, VisionConfig())
    status = res.model_status

    assert status["is_real_ai_model"] is False
    assert status["environment_profile"] == "MARS"
    assert "supported_classes" in status
    assert "extended_taxonomy" in status
    assert "unsupported_extended_classes" in status

    # Verify supported vs extended split
    supported = set(status["supported_classes"])
    assert "ROCK" in supported
    assert "BOULDER" in supported
    assert "SAND" in supported
    assert "SOIL" in supported
    assert "UNKNOWN" in supported

    unsupported = set(status["unsupported_extended_classes"])
    assert "REGOLITH" in unsupported
    assert "BEDROCK" in unsupported
    assert "DUST" in unsupported
    assert "CRATER" in unsupported

    # Verify transparency text in limitations
    assert "does not distinguish" in status["limitations"].lower()
    assert "deep-learning" in status["limitations"].lower() or "ai4mars" in status["limitations"].lower()


# ============================================================================
# 4. Mars Simulation & Camera Frame Source Tests
# ============================================================================

def test_simulated_camera_feed_mars_and_simulation_mars():
    """Verify SimulatedCameraFeed functions identically under MARS and SIMULATION_MARS."""
    feed_mars = SimulatedCameraFeed(resolution=(60, 80), seed=42, environment=EnvironmentProfile.MARS)
    feed_sim = SimulatedCameraFeed(resolution=(60, 80), seed=42, environment=EnvironmentProfile.SIMULATION_MARS)

    frame_mars, meta_mars = feed_mars.capture_frame()
    frame_sim, meta_sim = feed_sim.capture_frame()

    assert frame_mars.shape == (60, 80, 3)
    assert frame_sim.shape == (60, 80, 3)
    assert meta_mars["camera_model"] == "MARS09_MastCam_Simulated"
    assert meta_sim["camera_model"] == "MARS09_MastCam_Simulated"


def test_segmentation_under_simulation_mars():
    """Verify segment_terrain executes properly under SIMULATION_MARS profile."""
    feed = SimulatedCameraFeed(resolution=(60, 80), seed=42, environment=EnvironmentProfile.SIMULATION_MARS)
    frame, _ = feed.capture_frame()

    res = segment_terrain(frame, environment=EnvironmentProfile.SIMULATION_MARS)
    assert res.environment == "SIMULATION_MARS"
    assert res.segmentation_mask.shape == (60, 80)
    assert res.color_map.shape == (60, 80, 3)
    assert res.dominant_class in [c.value for c in SemanticClass]


# ============================================================================
# 5. Preservation of Member 1 & 3 Navigation Contracts
# ============================================================================

def test_cost_map_and_risk_map_contract_preservation():
    """Verify build_terrain_intelligence(seed=42) contract remains completely unaltered."""
    terrain = build_terrain_intelligence(seed=42)
    cost_map = terrain["cost_map"]
    risk_map = terrain["risk_map"]

    assert cost_map.shape == (100, 100)
    assert risk_map.shape == (100, 100)
    assert cost_map.dtype == np.float64
    assert risk_map.dtype == np.float64

    # Safe cells cost 1.0, hazard cells cost np.inf
    assert np.any(cost_map == 1.0)
    assert np.any(np.isinf(cost_map))
    assert np.all(risk_map >= 0.0)
    assert np.all(risk_map <= 1.0)


def test_path_safety_evaluation_with_extended_taxonomy():
    """Verify candidate path safety scoring correctly rejects paths traversing hazard cells."""
    terrain = build_terrain_intelligence(seed=42)
    cost_map = terrain["cost_map"]
    risk_map = terrain["risk_map"]

    # Safe path
    safe_path = [(0, 0), (0, 1), (0, 2), (0, 3)]
    res_safe = evaluate_candidate_path_safety(safe_path, cost_map, risk_map)
    assert res_safe["traversability_score"] > 0.0

    # Path crossing an impassable cell (np.inf)
    hazard_idx = np.argwhere(np.isinf(cost_map))[0]
    hazard_path = [(0, 0), (hazard_idx[0], hazard_idx[1])]
    res_hazard = evaluate_candidate_path_safety(hazard_path, cost_map, risk_map)
    assert res_hazard["path_accepted"] is False
    assert res_hazard["hazard_step_count"] >= 1
