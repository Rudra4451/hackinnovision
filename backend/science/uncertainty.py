"""
Uncertainty Reasoning Module for MARS-09 Odyssey Science Intelligence Engine.

Provides Shannon Entropy calculations, multi-sensor variance assessment,
and observational confidence mapping for candidate geological targets.
"""

import math
from typing import Dict, List, Optional


def calculate_shannon_entropy(probabilities: List[float]) -> float:
    """
    Compute base-2 Shannon entropy for a discrete probability distribution.
    H(p) = - sum(p_i * log2(p_i)) for all p_i > 0
    """
    valid_probs = [p for p in probabilities if p > 0.0]
    total = sum(valid_probs)
    if total <= 0:
        return 0.0
    
    # Normalize probabilities to sum to 1.0
    normalized = [p / total for p in valid_probs]
    entropy = -sum(p * math.log2(p) for p in normalized)
    return max(0.0, float(entropy))


def compute_target_uncertainty(
    class_probabilities: Dict[str, float],
    sensor_variance: float = 0.05,
) -> Dict[str, float]:
    """
    Calculate normalized uncertainty score [0.0 - 1.0] and confidence level [0.0 - 1.0].
    
    Returns:
        {
            "shannon_entropy": float,
            "normalized_uncertainty": float,  # 0.0 = completely certain, 1.0 = maximum ambiguity
            "confidence_level": float,        # 1.0 = high confidence, 0.0 = low confidence
        }
    """
    probs = list(class_probabilities.values())
    k = max(2, len(probs))
    max_possible_entropy = math.log2(k)

    raw_entropy = calculate_shannon_entropy(probs)
    normalized_uncertainty = raw_entropy / max_possible_entropy if max_possible_entropy > 0 else 0.0

    # Fold in physical sensor noise/atmospheric dust obscuration
    adjusted_uncertainty = min(1.0, max(0.0, normalized_uncertainty + sensor_variance))
    confidence_level = round(float(1.0 - adjusted_uncertainty), 4)

    return {
        "shannon_entropy": round(float(raw_entropy), 4),
        "normalized_uncertainty": round(float(adjusted_uncertainty), 4),
        "confidence_level": confidence_level,
    }
