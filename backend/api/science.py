"""
Science Intelligence API Endpoints for MARS-09 Odyssey.
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Query

from backend.integrations.terrain_adapter import get_default_terrain
from backend.schemas import ScienceAnalysisResponse, ScienceTarget
from backend.science.recommendations import generate_mission_recommendation_report
from backend.science.scoring import evaluate_and_rank_targets

router = APIRouter(prefix="/api/science", tags=["Science Intelligence"])

TARGETS_FILE = os.path.join("data", "sample", "targets_catalog.json")


def load_raw_targets() -> List[Dict[str, Any]]:
    if not os.path.exists(TARGETS_FILE):
        return []
    try:
        with open(TARGETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


@router.get("/targets", response_model=ScienceAnalysisResponse)
def get_ranked_science_targets(
    rover_r: int = Query(default=2, ge=0, le=400),
    rover_c: int = Query(default=2, ge=0, le=400),
) -> Dict[str, Any]:
    """
    Evaluate, gate, and rank all candidate science targets based on current rover position.
    """
    raw_targets = load_raw_targets()
    cost_map, _ = get_default_terrain()
    rover_pos = (rover_r, rover_c)

    evaluated, ranked_ids = evaluate_and_rank_targets(
        raw_targets=raw_targets,
        cost_map=cost_map,
        rover_pos=rover_pos,
    )

    accessible_count = sum(1 for t in evaluated if t["operational_priority"] > 0)
    gated_count = len(evaluated) - accessible_count

    top_target = evaluated[0] if evaluated else None
    overall_rec = generate_mission_recommendation_report(evaluated, rover_pos=rover_pos)

    return {
        "targets": evaluated,
        "ranked_target_ids": ranked_ids,
        "accessible_count": accessible_count,
        "gated_count": gated_count,
        "highest_priority_target": top_target,
        "overall_recommendation": overall_rec,
    }


@router.get("/targets/{target_id}", response_model=ScienceTarget)
def get_target_detail(
    target_id: str,
    rover_r: int = Query(default=2, ge=0, le=400),
    rover_c: int = Query(default=2, ge=0, le=400),
) -> Dict[str, Any]:
    """Retrieve detailed assessment and route breakdown for a specific target."""
    raw_targets = load_raw_targets()
    matched = [t for t in raw_targets if t["id"].lower() == target_id.lower()]
    if not matched:
        raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found.")

    cost_map, _ = get_default_terrain()
    evaluated, _ = evaluate_and_rank_targets(
        raw_targets=matched,
        cost_map=cost_map,
        rover_pos=(rover_r, rover_c),
    )
    return evaluated[0]


@router.get("/report")
def get_mission_brief_report(
    rover_r: int = Query(default=2, ge=0, le=400),
    rover_c: int = Query(default=2, ge=0, le=400),
) -> Dict[str, str]:
    """Generate Markdown mission briefing."""
    raw_targets = load_raw_targets()
    cost_map, _ = get_default_terrain()
    rover_pos = (rover_r, rover_c)

    evaluated, _ = evaluate_and_rank_targets(raw_targets, cost_map, rover_pos)
    report_md = generate_mission_recommendation_report(evaluated, rover_pos=rover_pos)

    return {"report_markdown": report_md}
