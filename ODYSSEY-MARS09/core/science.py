"""
ODYSSEY MARS-09: Science Target Prioritization & Spectrometric Intelligence
Lead Architect Specification - Integrates Accessibility Gating & Shannon Entropy
"""

import math
from typing import List, Dict, Any, Tuple
try:
    import numpy as np
except ImportError:
    np = None

from core.config import START_POSITION, OBSTACLE_COST

# Target mineral types and baseline scientific value (1 - 10)
MINERAL_REGISTRY = {
    "PHYLLOSILICATES": {"base_value": 9.5, "biosignature_relevance": 0.95},
    "HEMATITE_RIDGE": {"base_value": 8.0, "biosignature_relevance": 0.80},
    "SULFATE_DEPOSIT": {"base_value": 7.5, "biosignature_relevance": 0.70},
    "BASALTIC_BEDROCK": {"base_value": 4.0, "biosignature_relevance": 0.30},
    "OLIVINE_CUMULATE": {"base_value": 6.5, "biosignature_relevance": 0.50},
}


def calculate_shannon_entropy(probabilities: List[float]) -> float:
    """Calculate Shannon entropy in bits for mineral classification uncertainty."""
    entropy = 0.0
    for p in probabilities:
        if p > 0:
            entropy -= p * math.log2(p)
    return float(entropy)


def calculate_confidence(
    target_data: Dict[str, Any],
    reading_type: str = "spectrometry"
) -> float:
    """
    Calculate sensor confidence score (0.0 to 1.0) based on SNR and Shannon entropy.
    """
    probs = target_data.get("class_probabilities", [0.85, 0.10, 0.05])
    entropy = calculate_shannon_entropy(probs)
    # Max possible entropy for 3 classes is log2(3) ~ 1.585
    max_entropy = math.log2(len(probs)) if len(probs) > 1 else 1.0
    normalized_uncertainty = min(entropy / max_entropy, 1.0)
    confidence = max(0.0, min(1.0, 1.0 - (0.7 * normalized_uncertainty)))
    return round(float(confidence), 3)


def rank_targets(
    targets: List[Dict[str, Any]],
    rover_pos: Tuple[int, int] = START_POSITION,
    cost_map: Any = None,
    weight_priority: float = 0.6,
    weight_distance: float = 0.4
) -> List[Dict[str, Any]]:
    """
    Rank scientific targets based on scientific value, proximity, and terrain accessibility.
    Unreachable targets (in hazard zones) receive operational score of 0.0.
    """
    if not targets:
        targets = [
            {"id": "TARGET_ALPHA", "pos": (25, 30), "type": "PHYLLOSILICATES", "priority": 10},
            {"id": "TARGET_BETA", "pos": (45, 60), "type": "HEMATITE_RIDGE", "priority": 8},
            {"id": "TARGET_GAMMA", "pos": (80, 85), "type": "SULFATE_DEPOSIT", "priority": 9},
            {"id": "TARGET_DELTA", "pos": (15, 75), "type": "OLIVINE_CUMULATE", "priority": 7},
            {"id": "TARGET_EPSILON", "pos": (60, 20), "type": "BASALTIC_BEDROCK", "priority": 4},
        ]

    scored = []
    for t in targets:
        pos = t["pos"]
        dr = pos[0] - rover_pos[0]
        dc = pos[1] - rover_pos[1]
        dist = math.hypot(dr, dc)
        norm_dist = max(dist / 141.4, 0.01)

        mineral_info = MINERAL_REGISTRY.get(t.get("type", "BASALTIC_BEDROCK"), {"base_value": 5.0})
        sci_val = mineral_info["base_value"]

        # Check accessibility if cost_map is provided
        is_accessible = True
        if cost_map is not None:
            r, c = pos
            try:
                cell_cost = cost_map[r][c] if isinstance(cost_map, list) else cost_map[r, c]
                if math.isinf(cell_cost) or cell_cost >= 1e9:
                    is_accessible = False
            except Exception:
                pass

        if not is_accessible:
            operational_score = 0.0
            status = "IMPASSABLE_HAZARD"
        else:
            operational_score = (weight_priority * (sci_val / 10.0)) - (weight_distance * norm_dist)
            status = "ACCESSIBLE"

        target_copy = dict(t)
        target_copy["distance_m"] = round(float(dist), 2)
        target_copy["scientific_value"] = sci_val
        target_copy["composite_score"] = round(float(operational_score), 3)
        target_copy["status"] = status
        target_copy["confidence"] = calculate_confidence(target_copy)
        scored.append(target_copy)

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    return scored
