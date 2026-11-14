"""
Mission Overview & Rover Telemetry Endpoints for MARS-09 Odyssey.
"""

import math
from typing import Any, Dict, Optional, Tuple
from fastapi import APIRouter, HTTPException, Query
import numpy as np

from backend.integrations.terrain_adapter import get_default_terrain
from backend.schemas import MissionTelemetry
from core.navigation import compare_routes

router = APIRouter(prefix="/api/mission", tags=["Mission Telemetry"])

# Current live rover state in memory
_ROVER_STATE = MissionTelemetry(
    sol=142,
    rover_name="MARS-09 Odyssey",
    rover_position=(2, 2),
    battery_level_pct=94.2,
    solar_irradiance_w_m2=582.4,
    chassis_temperature_c=-28.4,
    drive_motor_health="NOMINAL",
    spectrometer_status="CALIBRATED",
    active_navigation_mode="safest",
    comms_latency_sec=874.1,
    mission_phase="PRIMARY_RECONNAISSANCE",
)


def _safe_cost(c: float) -> Any:
    if math.isinf(c) or c >= 1e9:
        return "Infinity"
    if math.isnan(c):
        return "NaN"
    return round(float(c), 3)


def _safe_json_value(val: Any) -> Any:
    if isinstance(val, (float, np.floating)):
        if math.isinf(val) or val >= 1e9:
            return "Infinity"
        if math.isnan(val):
            return "NaN"
        return round(float(val), 4)
    elif isinstance(val, (int, np.integer)):
        return int(val)
    elif isinstance(val, (list, tuple)):
        return [_safe_json_value(x) for x in val]
    elif isinstance(val, dict):
        return {k: _safe_json_value(v) for k, v in val.items()}
    return val


@router.get("")
@router.get("/")
def get_mission_data(
    start_r: int = Query(default=5, ge=0),
    start_c: int = Query(default=5, ge=0),
    goal_r: int = Query(default=180, ge=0),
    goal_c: int = Query(default=180, ge=0),
    rows: int = Query(default=200, ge=20, le=400),
    cols: int = Query(default=200, ge=20, le=400),
) -> Dict[str, Any]:
    """
    Standard Mission Data Endpoint (§7.1) bridging DEM elevation, cost map, and navigation comparison.
    Conforms to the serialization protocol:
    - np.inf -> 'Infinity' sentinel
    - nan -> 'NaN' sentinel
    """
    cost_map, dem = get_default_terrain(rows=rows, cols=cols)
    if cost_map.shape != dem.shape:
        raise HTTPException(
            status_code=400,
            detail=f"Grid mismatch: DEM {dem.shape}, cost map {cost_map.shape}",
        )

    r_count, c_count = cost_map.shape
    start = (min(int(start_r), r_count - 1), min(int(start_c), c_count - 1))
    goal = (min(int(goal_r), r_count - 1), min(int(goal_c), c_count - 1))

    res = compare_routes(cost_map, start, goal)

    cost_matrix = [[_safe_cost(cost_map[r, c]) for c in range(c_count)] for r in range(r_count)]
    rounded_elevation = [[round(float(dem[r, c]), 2) for c in range(c_count)] for r in range(r_count)]

    return {
        "dem": {
            "elevation": rounded_elevation,
            "rows": r_count,
            "cols": c_count,
            "elevationUnit": "meters",
            "source": f"HiRISE Jezero-Valles {r_count}x{c_count} Multi-Hazard Sector",
            "bounds": {
                "minRow": 0,
                "maxRow": r_count - 1,
                "minCol": 0,
                "maxCol": c_count - 1,
            },
        },
        "cost_map": {
            "cost": cost_matrix,
            "rows": r_count,
            "cols": c_count,
        },
        "navigation": _safe_json_value(res),
    }


@router.get("/telemetry", response_model=MissionTelemetry)
def get_mission_telemetry() -> MissionTelemetry:
    """Retrieve live rover system telemetry and environmental status."""
    return _ROVER_STATE


@router.post("/telemetry", response_model=MissionTelemetry)
def update_rover_position(row: int, col: int) -> MissionTelemetry:
    """Update rover location for active simulation and planning."""
    global _ROVER_STATE
    _ROVER_STATE.rover_position = (row, col)
    return _ROVER_STATE

