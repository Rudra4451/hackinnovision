"""
Navigation API Endpoints for MARS-09 Odyssey.
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException
import numpy as np

from backend.integrations.navigation_adapter import (
    run_multi_waypoint_mission,
    run_route_comparison,
)
from backend.integrations.terrain_adapter import (
    deserialize_cost_map_from_json,
    extract_hazard_mask,
    get_default_terrain,
    sanitize_cost_map_for_json,
)
from backend.schemas import (
    MissionWaypointRequest,
    NavigationRequest,
    RouteComparisonResponse,
    TerrainMetadata,
    TerrainResponse,
)

router = APIRouter(prefix="/api/navigation", tags=["Navigation"])


@router.post("/compare", response_model=RouteComparisonResponse)
def compare_navigation_routes(req: NavigationRequest) -> Dict[str, Any]:
    """
    Execute dual-route comparison ('shortest' vs 'safest') between start and goal.
    """
    if req.use_custom_cost_map and req.custom_cost_map:
        cost_map = deserialize_cost_map_from_json(req.custom_cost_map)
    else:
        cost_map, _ = get_default_terrain()

    try:
        result = run_route_comparison(
            cost_map=cost_map,
            start=req.start,
            goal=req.goal,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Navigation planning failed: {str(e)}")


@router.post("/mission-waypoints")
def plan_mission_waypoints(req: MissionWaypointRequest) -> Dict[str, Any]:
    """
    Execute continuous multi-stop waypoint mission route connecting all waypoints.
    """
    cost_map, _ = get_default_terrain()
    try:
        result = run_multi_waypoint_mission(
            cost_map=cost_map,
            start=req.start,
            waypoints=req.waypoints,
            mode=req.mode,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Mission waypoint planning failed: {str(e)}")



@router.get("/terrain", response_model=TerrainResponse)
def get_mission_terrain() -> Dict[str, Any]:
    """
    Retrieve sanitized terrain cost grid and topographical elevation.
    """
    cost_map, elevation = get_default_terrain()
    rows, cols = cost_map.shape

    hazard_mask = extract_hazard_mask(cost_map)
    sanitized_cost_map = sanitize_cost_map_for_json(cost_map)

    # Count cell stats
    hazard_count = sum(sum(row) for row in hazard_mask)
    caution_count = 0
    safe_count = 0

    for r in range(rows):
        for c in range(cols):
            if not hazard_mask[r][c]:
                val = cost_map[r, c]
                if val > 2.0:
                    caution_count += 1
                else:
                    safe_count += 1

    return {
        "dimensions": (rows, cols),
        "cost_map_display": sanitized_cost_map,
        "hazard_mask": hazard_mask,
        "elevation_map": elevation.tolist(),
        "metadata": {
            "rows": rows,
            "cols": cols,
            "hazard_count": hazard_count,
            "caution_count": caution_count,
            "safe_count": safe_count,
            "resolution_meters_per_cell": 1.0,
        },
    }
