"""
Navigation Adapter Module for MARS-09 Odyssey.

Bridges the REST API and Science Intelligence Engine to core/navigation.py
without modifying the existing navigation contract.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Strict import per Navigation Integration Contract
from core.navigation import (
    calculate_path_metrics,
    compare_routes,
    find_path,
    plan_mission_route,
)


def run_route_comparison(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
) -> Dict[str, Any]:
    """
    Execute compare_routes from core/navigation.py.

    Parameters:
        cost_map: 2D NumPy float array (1.0=nominal, >2.0=caution, np.inf=hazard)
        start: (row, col) coordinate tuple
        goal: (row, col) coordinate tuple

    Returns:
        Structured dictionary matching the navigation integration contract.
    """
    # Enforce integer coordinate tuples
    start_tuple = (int(start[0]), int(start[1]))
    goal_tuple = (int(goal[0]), int(goal[1]))

    return compare_routes(cost_map, start_tuple, goal_tuple)


def check_target_accessibility(
    cost_map: np.ndarray,
    rover_pos: Tuple[int, int],
    target_pos: Tuple[int, int],
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Determine if a science target is reachable and safe to navigate to.
    
    Returns:
        (is_accessible, route_comparison_result, reason)
    """
    rows, cols = cost_map.shape
    tr, tc = int(target_pos[0]), int(target_pos[1])
    
    # 1. Bounds check
    if not (0 <= tr < rows and 0 <= tc < cols):
        return False, None, f"Target out of bounds ({rows}x{cols})"

    # 2. Hard obstacle check: directly in hazard
    target_val = cost_map[tr, tc]
    if np.isinf(target_val) or target_val >= 1e9:
        return False, None, "Target is located inside an impassable hazard zone (np.inf)"

    # 3. Path planning reachability check via safest route
    res = compare_routes(cost_map, rover_pos, target_pos)
    safest_success = res["safest"]["route"]["success"]

    if not safest_success:
        reason = res["safest"]["route"].get("reason", "No traversable path exists")
        return False, res, f"Target is unreachable: {reason}"

    return True, res, "Reachable"


def run_multi_waypoint_mission(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    waypoints: List[Tuple[int, int]],
    mode: str = "safest",
) -> Dict[str, Any]:
    """
    Execute continuous multi-stop waypoint mission route using plan_mission_route.
    """
    start_tuple = (int(start[0]), int(start[1]))
    waypoints_tuples = [(int(r), int(c)) for r, c in waypoints]
    return plan_mission_route(cost_map, start_tuple, waypoints_tuples, mode=mode)

