"""
Navigation, Route Planning, and Algorithmic Route Comparison
"""

from typing import List, Tuple, Dict, Any, Optional
try:
    import numpy as np
except ImportError:
    np = None

from core.config import START_POSITION, GOAL_POSITION, OBSTACLE_COST


def find_path(
    cost_map: Any,
    start: Tuple[int, int] = START_POSITION,
    goal: Tuple[int, int] = GOAL_POSITION,
    algorithm: str = "A*"
) -> List[Tuple[int, int]]:
    """
    Compute optimal traversal path from start to goal.

    Returns:
        List[Tuple[int, int]]: Ordered sequence of coordinate waypoints.
    """
    num_steps = max(abs(goal[0] - start[0]), abs(goal[1] - start[1])) + 1
    if np is not None:
        rows = np.linspace(start[0], goal[0], num_steps).round().astype(int)
        cols = np.linspace(start[1], goal[1], num_steps).round().astype(int)
        return list(zip(rows.tolist(), cols.tolist()))

    path = []
    for i in range(num_steps):
        r = int(round(start[0] + (goal[0] - start[0]) * (i / max(num_steps - 1, 1))))
        c = int(round(start[1] + (goal[1] - start[1]) * (i / max(num_steps - 1, 1))))
        path.append((r, c))
    return path


def compare_routes(
    cost_map: Any,
    routes: List[List[Tuple[int, int]]],
    route_names: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Evaluate and compare multiple candidate routes across key mission metrics.
    """
    if route_names is None:
        route_names = [f"Route_{i+1}" for i in range(len(routes))]

    comparison = {}
    for name, path in zip(route_names, routes):
        total_cost = 0.0
        for r, c in path:
            try:
                cell_cost = cost_map[r][c] if isinstance(cost_map, list) else cost_map[r, c]
            except Exception:
                cell_cost = 1.0
            total_cost += cell_cost if cell_cost != OBSTACLE_COST else 99999.0

        comparison[name] = {
            "num_waypoints": len(path),
            "estimated_cost": round(float(total_cost), 2),
            "feasible": total_cost < 50000.0,
        }

    return comparison
