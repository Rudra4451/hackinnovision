from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class Coordinate(BaseModel):
    row: int = Field(..., ge=0, description="0-indexed row (grid y)")
    col: int = Field(..., ge=0, description="0-indexed column (grid x)")


class PathMetrics(BaseModel):
    total_distance: float
    total_cost: float
    avg_terrain_cost: float
    max_cell_cost: float
    caution_steps: int
    step_count: int


class RouteResult(BaseModel):
    success: bool
    mode: str
    path: List[Tuple[int, int]]
    x: List[int]
    y: List[int]
    nodes_explored: int
    reason: str


class RouteComparisonSummary(BaseModel):
    both_reachable: bool
    distance_delta: float
    distance_penalty_pct: float
    cost_reduction_pct: float
    caution_steps_avoided: int
    recommendation: str


class RouteComparisonResponse(BaseModel):
    shortest: Dict[str, Any]
    safest: Dict[str, Any]
    summary: RouteComparisonSummary


class NavigationRequest(BaseModel):
    start: Tuple[int, int] = Field(default=(2, 2))
    goal: Tuple[int, int] = Field(default=(45, 45))
    use_custom_cost_map: Optional[bool] = False
    custom_cost_map: Optional[List[List[Any]]] = None


class MissionWaypointRequest(BaseModel):
    start: Tuple[int, int] = Field(default=(2, 2))
    waypoints: List[Tuple[int, int]] = Field(..., description="Ordered list of waypoint tuples")
    mode: str = Field(default="safest", description="'safest' or 'shortest'")



class TerrainMetadata(BaseModel):
    rows: int
    cols: int
    hazard_count: int
    caution_count: int
    safe_count: int
    resolution_meters_per_cell: float = 1.0


class TerrainResponse(BaseModel):
    dimensions: Tuple[int, int]
    cost_map_display: List[List[Optional[float]]]
    hazard_mask: List[List[bool]]
    elevation_map: List[List[float]]
    metadata: TerrainMetadata


class ScienceTarget(BaseModel):
    id: str
    name: str
    target_type: str
    location: Tuple[int, int]
    scientific_value: float = Field(..., ge=0.0, le=100.0)
    operational_priority: float = Field(..., ge=0.0, le=100.0)
    accessibility_status: str  # "OPTIMAL", "CAUTION", "UNREACHABLE_HAZARD"
    uncertainty_score: float = Field(..., ge=0.0, le=1.0)
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    estimated_distance: float
    estimated_energy_cost: float
    spectral_signature: Dict[str, float]
    justification: str
    route_details: Optional[Dict[str, Any]] = None


class ScienceAnalysisResponse(BaseModel):
    targets: List[ScienceTarget]
    ranked_target_ids: List[str]
    accessible_count: int
    gated_count: int
    highest_priority_target: Optional[ScienceTarget] = None
    overall_recommendation: str


class MissionTelemetry(BaseModel):
    sol: int = 142
    rover_name: str = "MARS-09 Odyssey"
    rover_position: Tuple[int, int] = (2, 2)
    battery_level_pct: float = 94.2
    solar_irradiance_w_m2: float = 582.4
    chassis_temperature_c: float = -28.4
    drive_motor_health: str = "NOMINAL"
    spectrometer_status: str = "CALIBRATED"
    active_navigation_mode: str = "safest"
    comms_latency_sec: float = 874.1  # ~14.5 minutes Earth-Mars
    mission_phase: str = "PRIMARY_RECONNAISSANCE"
