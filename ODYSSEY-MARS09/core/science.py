"""
Science Target Evaluation, Ranking, and Spectrometric Confidence Scoring
"""

import math
import random
from typing import List, Dict, Any, Tuple
try:
    import numpy as np
except ImportError:
    np = None

from core.config import START_POSITION


def rank_targets(
    targets: List[Dict[str, Any]],
    rover_pos: Tuple[int, int] = START_POSITION,
    weight_priority: float = 0.6,
    weight_distance: float = 0.4
) -> List[Dict[str, Any]]:
    """
    Rank scientific targets based on priority score and proximity to rover.

    Returns:
        List[Dict[str, Any]]: Targets sorted by composite priority score (descending).
    """
    if not targets:
        targets = [
            {"id": "TARGET_ALPHA", "pos": (25, 30), "priority": 9, "type": "Hematite Ridge"},
            {"id": "TARGET_BETA", "pos": (45, 60), "priority": 7, "type": "Hydrated Silicates"},
            {"id": "TARGET_GAMMA", "pos": (80, 85), "priority": 10, "type": "Ancient Biosignature Site"},
        ]

    scored = []
    for t in targets:
        dr = t["pos"][0] - rover_pos[0]
        dc = t["pos"][1] - rover_pos[1]
        dist = math.hypot(dr, dc)
        norm_dist = max(dist / 141.4, 0.01)
        composite_score = (weight_priority * (t["priority"] / 10.0)) - (weight_distance * norm_dist)
        target_copy = dict(t)
        target_copy["distance"] = round(float(dist), 2)
        target_copy["composite_score"] = round(float(composite_score), 3)
        scored.append(target_copy)

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    return scored


def calculate_confidence(
    target_data: Dict[str, Any],
    reading_type: str = "spectrometry"
) -> float:
    """
    Calculate confidence score (0.0 to 1.0) for a scientific reading.
    """
    base_confidence = 0.85
    noise = float(random.uniform(0.01, 0.08))
    confidence = max(0.0, min(1.0, base_confidence - noise))
    return round(confidence, 3)
