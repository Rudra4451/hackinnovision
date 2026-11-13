"""
Autonomous path planning, metrics calculation, and route risk analysis for MARS-09.

Features:
- 8-directional A* search with admissible Euclidean heuristics.
- Dual-mode routing: 'shortest' (distance-minimal) vs. 'safest' (terrain risk-aware).
- Strict obstacle clearance & diagonal corner-cutting prevention.
- Path telemetry (energy cost, distance, caution steps, max/avg terrain penalty).
- Route comparison and automated mission recommendation engine.

Theoretical Foundations & Modeling Assumptions:
- Algorithm: A* heuristic search over an 8-connected 2D grid.
- Optimality: A* is mathematically optimal for the discrete 8-connected grid cost
  model when the heuristic is admissible and consistent, satisfying:
    h(n) <= d(n, goal) * min_finite_cost
  where d(n, goal) is the Euclidean distance and min_finite_cost is the minimum
  traversable cell cost in the grid.
- Physical Abstraction: Rover dynamics (turning radius, slip angles, chassis
  inertia, and steering actuator delay) are abstracted into cell transition penalties
  and strict diagonal corner-cutting constraints.
"""

import heapq
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Import shared configuration with standalone fallback defaults
try:
    from core.config import GRID_SIZE, START_POSITION, GOAL_POSITION, OBSTACLE_COST
except ImportError:
    GRID_SIZE: Tuple[int, int] = (50, 50)
    START_POSITION: Tuple[int, int] = (0, 0)
    GOAL_POSITION: Tuple[int, int] = (49, 49)
    OBSTACLE_COST: float = float("inf")

# 8-connected neighbor offsets and Euclidean step lengths:
# Orthogonal = 1.0, Diagonal = sqrt(2)
_SQRT2: float = math.sqrt(2.0)
_NEIGHBORS: List[Tuple[int, int, float]] = [
    (-1, 0, 1.0),    # North
    (1, 0, 1.0),     # South
    (0, -1, 1.0),    # West
    (0, 1, 1.0),     # East
    (-1, -1, _SQRT2), # Northwest
    (-1, 1, _SQRT2),  # Northeast
    (1, -1, _SQRT2),  # Southwest
    (1, 1, _SQRT2),   # Southeast
]


def _is_hazard(val: float) -> bool:
    """Check if a terrain cost represents an impassable hazard."""
    return math.isinf(val) or val >= 1e9


def find_path(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    mode: str = "safest",
) -> Dict[str, Any]:
    """
    Find an 8-directional path on the cost_map using the A* algorithm.

    Parameters:
        cost_map: 2D float ndarray where:
                  >= 1.0: Traversable terrain (1.0 = flat, 2.0-25.0 = caution)
                  np.inf: Impassable hazard
        start: (row, col) coordinate of start point
        goal: (row, col) coordinate of destination
        mode: "safest" (minimizes risk-weighted distance) or
              "shortest" (minimizes physical distance while avoiding np.inf)

    Returns:
        Structured dictionary conforming to the mission control schema:
        Success:
            {
                "success": True,
                "mode": mode,
                "path": [(r0, c0), ...],
                "x": [c0, ...],
                "y": [r0, ...],
                "nodes_explored": int,
                "reason": "Path found"
            }
        Failure:
            {
                "success": False,
                "mode": mode,
                "path": [],
                "x": [],
                "y": [],
                "nodes_explored": int,
                "reason": str
            }
    """
    if mode not in ("safest", "shortest"):
        raise ValueError(f"Invalid mode '{mode}'. Expected 'safest' or 'shortest'.")

    rows, cols = cost_map.shape

    # Boundary checks
    if not (0 <= start[0] < rows and 0 <= start[1] < cols):
        return {
            "success": False,
            "mode": mode,
            "path": [],
            "x": [],
            "y": [],
            "nodes_explored": 0,
            "reason": f"Start position {start} is out of grid bounds ({rows}x{cols})",
        }

    if not (0 <= goal[0] < rows and 0 <= goal[1] < cols):
        return {
            "success": False,
            "mode": mode,
            "path": [],
            "x": [],
            "y": [],
            "nodes_explored": 0,
            "reason": f"Goal position {goal} is out of grid bounds ({rows}x{cols})",
        }

    # Start or goal impassable hazard checks
    if _is_hazard(cost_map[start]):
        return {
            "success": False,
            "mode": mode,
            "path": [],
            "x": [],
            "y": [],
            "nodes_explored": 0,
            "reason": f"Start position {start} is inside an impassable hazard zone",
        }

    if _is_hazard(cost_map[goal]):
        return {
            "success": False,
            "mode": mode,
            "path": [],
            "x": [],
            "y": [],
            "nodes_explored": 0,
            "reason": f"Goal position {goal} is inside an impassable hazard zone",
        }

    # Start and goal are identical on valid cell
    if start == goal:
        return {
            "success": True,
            "mode": mode,
            "path": [start],
            "x": [start[1]],
            "y": [start[0]],
            "nodes_explored": 1,
            "reason": "Start and goal are identical",
        }

    # Determine minimum traversable finite cost for admissible heuristic in 'safest' mode
    finite_mask = np.isfinite(cost_map) & (cost_map < 1e9)
    if np.any(finite_mask):
        min_finite_cost = float(np.min(cost_map[finite_mask]))
        if min_finite_cost <= 0:
            min_finite_cost = 1.0
    else:
        min_finite_cost = 1.0

    def heuristic(r: int, c: int) -> float:
        dist = math.hypot(r - goal[0], c - goal[1])
        if mode == "safest":
            return dist * min_finite_cost
        return dist

    # A* Priority Queue: (f_score, h_score, tie_breaker, (row, col))
    tie_counter = 0
    start_h = heuristic(start[0], start[1])
    open_heap: List[Tuple[float, float, int, Tuple[int, int]]] = [
        (start_h, start_h, tie_counter, start)
    ]
    g_scores: Dict[Tuple[int, int], float] = {start: 0.0}
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    closed_set = set()
    nodes_explored = 0

    while open_heap:
        _, _, _, current = heapq.heappop(open_heap)

        if current in closed_set:
            continue
        closed_set.add(current)
        nodes_explored += 1

        if current == goal:
            # Reconstruct path from start to goal
            path: List[Tuple[int, int]] = [current]
            curr_step = current
            while curr_step in came_from:
                curr_step = came_from[curr_step]
                path.append(curr_step)
            path.reverse()

            return {
                "success": True,
                "mode": mode,
                "path": path,
                "x": [c for _, c in path],
                "y": [r for r, _ in path],
                "nodes_explored": nodes_explored,
                "reason": "Path found",
            }

        cr, cc = current
        current_g = g_scores[current]

        for dr, dc, step_length in _NEIGHBORS:
            nr, nc = cr + dr, cc + dc

            # Boundary check
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue

            # Direct destination impassable check
            neighbor_cost = cost_map[nr, nc]
            if _is_hazard(neighbor_cost):
                continue

            # Prevent diagonal corner-cutting and squeezing through pinch points
            # A physical rover with finite chassis width cannot cut across obstacle corners
            # or squeeze diagonally between two obstacles touching at a point.
            if dr != 0 and dc != 0:
                # The two adjacent orthogonal cells are (cr + dr, cc) and (cr, cc + dc)
                ortho1_is_hazard = _is_hazard(cost_map[cr + dr, cc])
                ortho2_is_hazard = _is_hazard(cost_map[cr, cc + dc])
                if ortho1_is_hazard or ortho2_is_hazard:
                    continue

            # Transition step cost calculation
            if mode == "safest":
                step_cost = step_length * float(neighbor_cost)
            else:  # "shortest"
                step_cost = step_length

            tentative_g = current_g + step_cost
            neighbor = (nr, nc)

            if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                g_scores[neighbor] = tentative_g
                came_from[neighbor] = current
                h_val = heuristic(nr, nc)
                f_val = tentative_g + h_val
                tie_counter += 1
                heapq.heappush(open_heap, (f_val, h_val, tie_counter, neighbor))

    # Open set exhausted without finding a traversable route
    return {
        "success": False,
        "mode": mode,
        "path": [],
        "x": [],
        "y": [],
        "nodes_explored": nodes_explored,
        "reason": "No traversable path exists",
    }


def calculate_path_metrics(
    path: List[Tuple[int, int]],
    cost_map: np.ndarray,
) -> Dict[str, Any]:
    """
    Calculate telemetry metrics for a planned path over the terrain cost map.

    Parameters:
        path: List of ordered (row, col) coordinates from start to goal
        cost_map: 2D float ndarray of terrain costs

    Returns:
        {
            "total_distance": float,   # Sum of step lengths (1.0 orthogonal, sqrt(2) diagonal)
            "total_cost": float,       # Sum of (step_length * cost_map[r, c]) for each step after start
            "avg_terrain_cost": float, # Mean cost_map value of traversed cells (0.0 if empty)
            "max_cell_cost": float,    # Highest single-cell cost along path (0.0 if empty)
            "caution_steps": int,      # Count of steps into cells where cost_map[r, c] > 2.0
            "step_count": int          # len(path) - 1 (0 if len(path) <= 1)
        }
    """
    if not path:
        return {
            "total_distance": 0.0,
            "total_cost": 0.0,
            "avg_terrain_cost": 0.0,
            "max_cell_cost": 0.0,
            "caution_steps": 0,
            "step_count": 0,
        }

    traversed_costs = [float(cost_map[r, c]) for r, c in path]
    avg_terrain_cost = float(np.mean(traversed_costs))
    max_cell_cost = float(max(traversed_costs))

    if len(path) == 1:
        return {
            "total_distance": 0.0,
            "total_cost": 0.0,
            "avg_terrain_cost": avg_terrain_cost,
            "max_cell_cost": max_cell_cost,
            "caution_steps": 0,
            "step_count": 0,
        }

    total_distance = 0.0
    total_cost = 0.0
    caution_steps = 0

    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]
        dr = abs(r2 - r1)
        dc = abs(c2 - c1)

        step_dist = _SQRT2 if (dr != 0 and dc != 0) else 1.0
        target_cost = float(cost_map[r2, c2])

        total_distance += step_dist
        total_cost += step_dist * target_cost

        if target_cost > 2.0:
            caution_steps += 1

    return {
        "total_distance": round(total_distance, 4),
        "total_cost": round(total_cost, 4),
        "avg_terrain_cost": round(avg_terrain_cost, 4),
        "max_cell_cost": round(max_cell_cost, 4),
        "caution_steps": int(caution_steps),
        "step_count": len(path) - 1,
    }


def compare_routes(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
) -> Dict[str, Any]:
    """
    Run pathfinding under both 'shortest' and 'safest' modes and synthesize
    a trade-off analysis summary for mission control telemetry.

    Parameters:
        cost_map: 2D float terrain cost grid
        start: (row, col) start coordinates
        goal: (row, col) goal coordinates

    Returns:
        Structured comparison dictionary conforming to the mission brief.
    """
    shortest_route = find_path(cost_map, start, goal, mode="shortest")
    safest_route = find_path(cost_map, start, goal, mode="safest")

    shortest_metrics = calculate_path_metrics(shortest_route["path"], cost_map)
    safest_metrics = calculate_path_metrics(safest_route["path"], cost_map)

    both_reachable = bool(shortest_route["success"] and safest_route["success"])

    if not both_reachable:
        distance_delta = 0.0
        distance_penalty_pct = 0.0
        cost_reduction_pct = 0.0
        caution_steps_avoided = 0

        if not shortest_route["success"] and not safest_route["success"]:
            recommendation = (
                f"Mission Abort: Destination unreachable by both planners. "
                f"Reason: {shortest_route.get('reason', 'Blocked by terrain hazards')}."
            )
        elif not shortest_route["success"]:
            recommendation = f"Shortest planner failed: {shortest_route.get('reason')}."
        else:
            recommendation = f"Safest planner failed: {safest_route.get('reason')}."

    elif start == goal:
        distance_delta = 0.0
        distance_penalty_pct = 0.0
        cost_reduction_pct = 0.0
        caution_steps_avoided = 0
        recommendation = "Rover is already at the target destination (distance = 0.0 m)."

    else:
        s_dist = shortest_metrics["total_distance"]
        safe_dist = safest_metrics["total_distance"]
        s_cost = shortest_metrics["total_cost"]
        safe_cost = safest_metrics["total_cost"]

        distance_delta = round(safe_dist - s_dist, 4)
        distance_penalty_pct = (
            round(((safe_dist - s_dist) / s_dist) * 100.0, 2) if s_dist > 0 else 0.0
        )
        cost_reduction_pct = (
            round(((s_cost - safe_cost) / s_cost) * 100.0, 2) if s_cost > 0 else 0.0
        )
        caution_steps_avoided = (
            shortest_metrics["caution_steps"] - safest_metrics["caution_steps"]
        )

        if safe_cost < s_cost:
            recommendation = (
                f"MARS-09 recommends the SAFEST route. Although requiring a {distance_penalty_pct:.1f}% "
                f"distance detour (+{distance_delta:.2f} m), it reduces accumulated terrain risk/cost "
                f"by {cost_reduction_pct:.1f}% and avoids {caution_steps_avoided} caution zone steps, "
                f"substantially lowering chassis wear and slip probability."
            )
        elif math.isclose(safe_cost, s_cost, abs_tol=1e-3) and math.isclose(
            safe_dist, s_dist, abs_tol=1e-3
        ):
            recommendation = (
                "Terrain is uniform or unobstructed; shortest and safest routes are identical "
                "in both distance and terrain cost. Proceeding with nominal trajectory."
            )
        else:
            recommendation = (
                f"Safest route provides equivalent or balanced safety (cost={safe_cost:.2f}) "
                f"relative to shortest route (cost={s_cost:.2f})."
            )

    return {
        "shortest": {
            "route": shortest_route,
            "metrics": shortest_metrics,
        },
        "safest": {
            "route": safest_route,
            "metrics": safest_metrics,
        },
        "summary": {
            "both_reachable": both_reachable,
            "distance_delta": float(distance_delta),
            "distance_penalty_pct": float(distance_penalty_pct),
            "cost_reduction_pct": float(cost_reduction_pct),
            "caution_steps_avoided": int(caution_steps_avoided),
            "recommendation": recommendation,
        },
    }


def plan_mission_route(
    cost_map: np.ndarray,
    start: Tuple[int, int],
    waypoints: List[Tuple[int, int]],
    mode: str = "safest",
) -> Dict[str, Any]:
    """
    Plan a continuous multi-stop mission route connecting start through an ordered list of waypoints.

    Parameters:
        cost_map: 2D float terrain cost grid
        start: Initial rover coordinates (row, col)
        waypoints: Ordered list of (row, col) target stops
        mode: "safest" or "shortest" path planning mode

    Returns:
        Structured dictionary with stitched path coordinates and combined telemetry metrics,
        or an immediate failure dictionary if any waypoint segment is unreachable.
    """
    if not waypoints:
        initial_check = find_path(cost_map, start, start, mode=mode)
        if not initial_check["success"]:
            return {
                "success": False,
                "mode": mode,
                "path": [],
                "x": [],
                "y": [],
                "metrics": calculate_path_metrics([], cost_map),
                "reason": initial_check.get("reason", "Start position is invalid"),
            }
        return {
            "success": True,
            "mode": mode,
            "path": [start],
            "x": [start[1]],
            "y": [start[0]],
            "metrics": calculate_path_metrics([start], cost_map),
            "reason": "Mission route planned successfully",
        }

    stitched_path: List[Tuple[int, int]] = []
    current_pos = start

    for idx, wp in enumerate(waypoints):
        segment_res = find_path(cost_map, current_pos, wp, mode=mode)
        if not segment_res["success"]:
            return {
                "success": False,
                "mode": mode,
                "path": [],
                "x": [],
                "y": [],
                "metrics": calculate_path_metrics([], cost_map),
                "reason": f"Waypoint {idx + 1} unreachable",
            }

        seg_path = segment_res["path"]
        if idx == 0:
            stitched_path.extend(seg_path)
        else:
            # Avoid duplicate overlapping waypoint coordinate at the transition
            stitched_path.extend(seg_path[1:])

        current_pos = wp

    combined_metrics = calculate_path_metrics(stitched_path, cost_map)

    return {
        "success": True,
        "mode": mode,
        "path": stitched_path,
        "x": [c for _, c in stitched_path],
        "y": [r for r, _ in stitched_path],
        "metrics": combined_metrics,
        "reason": "Mission route planned successfully",
    }


if __name__ == "__main__":
    print("=" * 70)
    print("ODYSSEY — MARS-09 AUTONOMOUS NAVIGATION DEMO (20x20 Grid)")
    print("=" * 70)

    # Initialize 20x20 nominal grid (flat regolith = 1.0)
    demo_grid = np.ones((20, 20), dtype=float)

    # Impassable hazard wall (#): crater ridge at rows 4..15, col 7 with opening at row 16..17
    demo_grid[4:15, 7] = np.inf

    # Caution hazard zone (~): high-slope rocky field at rows 8..15, cols 8..15 (cost = 15.0)
    demo_grid[8:15, 8:15] = 15.0

    start_pt = (2, 2)
    goal_pt = (12, 17)

    comparison = compare_routes(demo_grid, start_pt, goal_pt)
    shortest_path_set = set(comparison["shortest"]["route"]["path"])
    safest_path_set = set(comparison["safest"]["route"]["path"])

    print("\nTERRAIN & ROUTE MAP:")
    print("Legend:  . Safe (1.0)  |  ~ Caution (15.0)  |  # Hazard (inf)")
    print("         S Shortest Path only  |  * Safest Path only  |  B Both paths coincide\n")

    header = "   " + "".join(f"{c % 10}" for c in range(20))
    print(header)

    for r in range(20):
        row_str = []
        for c in range(20):
            pos = (r, c)
            in_s = pos in shortest_path_set
            in_safe = pos in safest_path_set

            if pos == start_pt:
                row_str.append("O")  # Origin / Start
            elif pos == goal_pt:
                row_str.append("X")  # Destination / Goal
            elif in_s and in_safe:
                row_str.append("B")
            elif in_s:
                row_str.append("S")
            elif in_safe:
                row_str.append("*")
            elif _is_hazard(demo_grid[r, c]):
                row_str.append("#")
            elif demo_grid[r, c] > 2.0:
                row_str.append("~")
            else:
                row_str.append(".")
        print(f"{r:2d} " + "".join(row_str))

    print("\n" + "-" * 70)
    print("TELEMETRY METRICS:")
    print(f"Shortest Route: Distance = {comparison['shortest']['metrics']['total_distance']:.2f} m | "
          f"Cost = {comparison['shortest']['metrics']['total_cost']:.2f} | "
          f"Caution Steps = {comparison['shortest']['metrics']['caution_steps']}")
    print(f"Safest Route:   Distance = {comparison['safest']['metrics']['total_distance']:.2f} m | "
          f"Cost = {comparison['safest']['metrics']['total_cost']:.2f} | "
          f"Caution Steps = {comparison['safest']['metrics']['caution_steps']}")
    print("-" * 70)
    print(f"Both Reachable:         {comparison['summary']['both_reachable']}")
    print(f"Distance Delta:        +{comparison['summary']['distance_delta']:.2f} m "
          f"({comparison['summary']['distance_penalty_pct']:.1f}% penalty)")
    print(f"Cost Reduction:         {comparison['summary']['cost_reduction_pct']:.1f}% risk reduction")
    print(f"Caution Steps Avoided:  {comparison['summary']['caution_steps_avoided']}")
    print(f"\nMARS-09 RECOMMENDATION:\n{comparison['summary']['recommendation']}")
    print("=" * 70)

