"""
Scoring and Ranking Module for MARS-09 Odyssey Science Intelligence Engine.

Strictly enforces Rule 2:
Separates Scientific Value (how interesting a feature is) from Operational Priority
(whether it is safe/accessible to visit). Unsafe or unreachable targets (np.inf or blocked paths)
MUST automatically receive an operational priority score of 0.0.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.integrations.navigation_adapter import check_target_accessibility
from backend.science.identification import calculate_scientific_value
from backend.science.uncertainty import compute_target_uncertainty


def evaluate_and_rank_targets(
    raw_targets: List[Dict[str, Any]],
    cost_map: np.ndarray,
    rover_pos: Tuple[int, int] = (2, 2),
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Evaluate all candidate science targets with hard safety gating and weighted ranking.

    Parameters:
        raw_targets: Catalog of candidate sites with coordinates and spectral attributes
        cost_map: 2D NumPy float grid
        rover_pos: Current (row, col) coordinates of MARS-09

    Returns:
        evaluated_targets: List of target dictionaries populated with scores, status & route metrics
        ranked_target_ids: Ordered list of target IDs by operational priority (descending)
    """
    evaluated: List[Dict[str, Any]] = []

    for tgt in raw_targets:
        target_id = tgt["id"]
        name = tgt.get("name", f"Target-{target_id}")
        target_type = tgt.get("target_type", "BASALTIC_BEDROCK")
        loc = tuple(tgt["location"])
        spectral_sig = tgt.get("spectral_signature", {})
        class_probs = tgt.get("class_probabilities", {target_type: 0.85})

        # 1. Scientific Value (Unconstrained by accessibility - Rule 2)
        sci_value = calculate_scientific_value(
            target_type=target_type,
            spectral_signature=spectral_sig,
            rarity_factor=tgt.get("rarity_factor", 1.0),
        )

        # 2. Uncertainty & Confidence Mapping
        unc_metrics = compute_target_uncertainty(
            class_probabilities=class_probs,
            sensor_variance=tgt.get("sensor_variance", 0.04),
        )
        uncertainty_score = unc_metrics["normalized_uncertainty"]
        confidence_level = unc_metrics["confidence_level"]

        # 3. Hard Operational Safety & Accessibility Gating (Rule 2)
        is_accessible, route_res, reason = check_target_accessibility(
            cost_map=cost_map,
            rover_pos=rover_pos,
            target_pos=loc,
        )

        if not is_accessible:
            # HARD SAFETY GATE: Priority is locked to 0.0
            operational_priority = 0.0
            accessibility_status = "UNREACHABLE_HAZARD"
            justification = (
                f"SAFETY GATE ENGAGED: Target is operational priority 0.0 because "
                f"it cannot be safely navigated. Reason: {reason}."
            )
            estimated_distance = 0.0
            estimated_energy_cost = 0.0
            route_details = route_res
        else:
            # Target is physically accessible; evaluate traversal cost and distance
            safest_metrics = route_res["safest"]["metrics"]
            dist = safest_metrics["total_distance"]
            cost = safest_metrics["total_cost"]
            caution_steps = safest_metrics["caution_steps"]
            avg_cost = safest_metrics["avg_terrain_cost"]

            # Operational status categorization
            if caution_steps > 8 or avg_cost > 6.0:
                accessibility_status = "CAUTION"
            else:
                accessibility_status = "OPTIMAL"

            # Operational Priority formulation:
            # Distance penalty (diminishing return past 100 meters)
            dist_factor = max(0.15, 1.0 - (dist / 140.0))
            # Terrain cost penalty (penalize rocky/rough paths)
            cost_factor = max(0.20, 1.0 - (cost / 250.0))
            # Confidence weighting
            conf_factor = 0.65 + (0.35 * confidence_level)

            operational_priority = round(
                float(sci_value * dist_factor * cost_factor * conf_factor), 2
            )
            # Ensure priority stays within [0.0, 100.0]
            operational_priority = min(100.0, max(0.0, operational_priority))

            justification = (
                f"Candidate exhibits high astrobiological merit ({sci_value:.1f}/100) with "
                f"{confidence_level*100:.1f}% confidence. Safest traverse requires {dist:.1f} m "
                f"with {caution_steps} caution steps and accumulated cost {cost:.1f}."
            )
            estimated_distance = dist
            estimated_energy_cost = cost
            route_details = route_res

        evaluated.append({
            "id": target_id,
            "name": name,
            "target_type": target_type,
            "location": loc,
            "scientific_value": sci_value,
            "operational_priority": operational_priority,
            "accessibility_status": accessibility_status,
            "uncertainty_score": uncertainty_score,
            "confidence_level": confidence_level,
            "estimated_distance": round(estimated_distance, 2),
            "estimated_energy_cost": round(estimated_energy_cost, 2),
            "spectral_signature": spectral_sig,
            "justification": justification,
            "route_details": route_details,
        })

    # Sort descending by operational priority, breaking ties by scientific value
    evaluated.sort(
        key=lambda x: (x["operational_priority"], x["scientific_value"]),
        reverse=True,
    )

    ranked_ids = [t["id"] for t in evaluated]
    return evaluated, ranked_ids
