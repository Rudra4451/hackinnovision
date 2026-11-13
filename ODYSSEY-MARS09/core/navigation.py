"""
ODYSSEY MARS-09: Autonomous Navigation and A* Path Planning Engine
Lead Architect Specification - Incorporates 8-Directional Search & Corner-Cutting Prevention
"""

import heapq
import math
from typing import List, Tuple, Dict, Any, Optional
try:
    import numpy as np
except ImportError:
    np = None

from core.config import START_POSITION, GOAL_POSITION, OBSTACLE_COST

_SQRT2 = math.sqrt(2.0)
_NEIGHBORS = [
    (-1, 0, 1.0),      # North
    (1, 0, 1.0),       # South
    (0, -1, 1.0),      # West
    (0, 1, 1.0),       # East
    (-1, -1, _SQRT2),  # Northwest
    (-1, 1, _SQRT2),   # Northeast
    (1, -1, _SQRT2),   # Southwest
    (1, 1, _SQRT2),    # Southeast
]


def _is_hazard(val: float) -> bool:
    return math.isinf(val) or val >= 1e9


def _get_cost(cost_map: Any, r: int, c: int) -> float:
    if isinstance(cost_map, list):
        return float(cost_map[r][c])
    return float(cost_map[r, c])


def find_path(
    cost_map: Any,
    start: Tuple[int, int] = START_POSITION,
    goal: Tuple[int, int] = GOAL_POSITION,
    mode: str = "safest"
) -> List[Tuple[int, int]]:
    """
    Find optimal 8-directional path on cost_map using A* search.
    mode: 'safest' (minimizes risk cost) or 'shortest' (minimizes distance).

    Returns:
        List[Tuple[int, int]]: Ordered sequence of coordinate waypoints from start to goal.
    """
    if isinstance(cost_map, list):
        rows, cols = len(cost_map), len(cost_map[0])
    else:
        rows, cols = cost_map.shape

    # Boundary and obstacle checks on start and goal
    if not (0 <= start[0] < rows and 0 <= start[1] < cols):
        return []
    if not (0 <= goal[0] < rows and 0 <= goal[1] < cols):
        return []

    if _is_hazard(_get_cost(cost_map, start[0], start[1])) or _is_hazard(_get_cost(cost_map, goal[0], goal[1])):
        return []

    def heuristic(pos: Tuple[int, int]) -> float:
        return math.hypot(pos[0] - goal[0], pos[1] - goal[1])

    open_set: List[Tuple[float, float, int, Tuple[int, int]]] = []
    heapq.heappush(open_set, (heuristic(start), 0.0, 0, start))

    g_scores: Dict[Tuple[int, int], float] = {start: 0.0}
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    closed_set = set()
    counter = 0

    while open_set:
        f, current_g, _, current = heapq.heappop(open_set)

        if current in closed_set:
            continue
        closed_set.add(current)

        if current == goal:
            path = [current]
            curr = current
            while curr in came_from:
                curr = came_from[curr]
                path.append(curr)
            path.reverse()
            return path

        cr, cc = current
        for dr, dc, step_dist in _NEIGHBORS:
            nr, nc = cr + dr, cc + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue

            neighbor_cost = _get_cost(cost_map, nr, nc)
            if _is_hazard(neighbor_cost):
                continue

            # Strict diagonal corner-cutting prevention
            if dr != 0 and dc != 0:
                ortho1 = _get_cost(cost_map, cr + dr, cc)
                ortho2 = _get_cost(cost_map, cr, cc + dc)
                if _is_hazard(ortho1) or _is_hazard(ortho2):
                    continue

            # Transition step cost calculation
            step_cost = step_dist * (neighbor_cost if mode == "safest" else 1.0)
            tentative_g = current_g + step_cost
            neighbor = (nr, nc)

            if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                g_scores[neighbor] = tentative_g
                came_from[neighbor] = current
                counter += 1
                heapq.heappush(open_set, (tentative_g + heuristic(neighbor), tentative_g, counter, neighbor))

    return []


def calculate_path_metrics(path: List[Tuple[int, int]], cost_map: Any) -> Dict[str, Any]:
    """Calculate comprehensive mission telemetry for a path."""
    if not path:
        return {
            "total_distance": 0.0,
            "total_cost": 0.0,
            "caution_steps": 0,
            "step_count": 0,
            "feasible": False,
        }

    total_distance = 0.0
    total_cost = 0.0
    caution_steps = 0

    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]
        step_dist = _SQRT2 if (abs(r2 - r1) != 0 and abs(c2 - c1) != 0) else 1.0
        target_cost = _get_cost(cost_map, r2, c2)

        total_distance += step_dist
        total_cost += step_dist * target_cost
        if target_cost > 2.0:
            caution_steps += 1

    return {
        "total_distance": round(total_distance, 2),
        "total_cost": round(total_cost, 2),
        "caution_steps": caution_steps,
        "step_count": len(path) - 1,
        "feasible": True,
    }


def compare_routes(
    cost_map: Any,
    start: Tuple[int, int] = START_POSITION,
    goal: Tuple[int, int] = GOAL_POSITION,
) -> Dict[str, Any]:
    """
    Evaluate and compare candidate routes across key mission metrics.
    Conforms to the exact MARS-09 Member 3 navigation contract schema.
    """
    shortest_path = find_path(cost_map, start, goal, mode="shortest")
    safest_path = find_path(cost_map, start, goal, mode="safest")

    shortest_metrics = calculate_path_metrics(shortest_path, cost_map)
    safest_metrics = calculate_path_metrics(safest_path, cost_map)

    shortest_success = len(shortest_path) > 0
    safest_success = len(safest_path) > 0

    s_dist = shortest_metrics["total_distance"]
    safe_dist = safest_metrics["total_distance"]
    dist_penalty = round(((safe_dist - s_dist) / s_dist * 100.0), 2) if (s_dist > 0 and safest_success) else 0.0

    if safest_success:
        recommendation = "Safest route recommended: minimizes terrain slope & hazard exposure."
    elif shortest_success:
        recommendation = "Safest route blocked; shortest route available with elevated risk."
    else:
        recommendation = "Mission Abort: Destination unreachable by planners due to terrain hazards."

    caution_avoided = max(0, shortest_metrics["caution_steps"] - safest_metrics["caution_steps"])

    return {
        "shortest": {
            "route": {
                "success": shortest_success,
                "mode": "shortest",
                "path": shortest_path,
                "x": [c for _, c in shortest_path],
                "y": [r for r, _ in shortest_path],
                "reason": "Path found" if shortest_success else "Goal unreachable due to surrounding hazards or boundaries",
            },
            "metrics": shortest_metrics,
        },
        "safest": {
            "route": {
                "success": safest_success,
                "mode": "safest",
                "path": safest_path,
                "x": [c for _, c in safest_path],
                "y": [r for r, _ in safest_path],
                "reason": "Path found" if safest_success else "Goal unreachable due to surrounding hazards or boundaries",
            },
            "metrics": safest_metrics,
        },
        "summary": {
            "distance_penalty_pct": dist_penalty,
            "caution_steps_avoided": caution_avoided,
            "recommendation": recommendation,
        },
    }
