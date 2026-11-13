"""
Mission Overview & Rover Telemetry Endpoints for MARS-09 Odyssey.
"""

from typing import Any, Dict
from fastapi import APIRouter
from backend.schemas import MissionTelemetry

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
