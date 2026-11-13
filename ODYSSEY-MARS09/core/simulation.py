"""
ODYSSEY MARS-09: Rover Dynamics & Sol State Simulation
Lead Architect Specification
"""

import math
from typing import List, Tuple, Dict, Any
from core.config import (
    BATTERY_CAPACITY_WH,
    ENERGY_PER_STEP_BASE_WH,
    OBSTACLE_COST,
    SOL_DURATION_SECONDS
)


def simulate_rover(
    path: List[Tuple[int, int]],
    cost_map: Any,
    initial_battery_wh: float = BATTERY_CAPACITY_WH
) -> Dict[str, Any]:
    """
    Simulate rover traversal along a planned path.
    Logs telemetry, battery consumption, terrain resistance, and status.
    """
    if not path:
        return {
            "trajectory": [],
            "battery_levels": [initial_battery_wh],
            "cumulative_cost": 0.0,
            "steps_completed": 0,
            "status": "NO_PATH_PROVIDED",
            "time_elapsed_s": 0.0,
        }

    battery = initial_battery_wh
    battery_levels = [round(battery, 2)]
    visited = []
    cumulative_cost = 0.0
    time_elapsed = 0.0
    status = "GOAL_REACHED"

    for idx in range(len(path)):
        r, c = path[idx]
        try:
            cost = cost_map[r][c] if isinstance(cost_map, list) else cost_map[r, c]
        except Exception:
            cost = 1.0

        if math.isinf(cost) or cost >= 1e9:
            status = "OBSTACLE_COLLISION"
            break

        if idx > 0:
            pr, pc = path[idx - 1]
            is_diagonal = (abs(r - pr) != 0 and abs(c - pc) != 0)
            step_dist = math.sqrt(2.0) if is_diagonal else 1.0

            # Step energy consumption proportional to terrain cost
            energy_draw = ENERGY_PER_STEP_BASE_WH * cost * step_dist
            battery -= energy_draw
            cumulative_cost += cost * step_dist

            # Traversal time: base 20s per step scaled by slope resistance
            time_elapsed += 20.0 * cost * step_dist

        visited.append((r, c))
        battery_levels.append(round(max(battery, 0.0), 2))

        if battery <= 0:
            status = "BATTERY_DEPLETED"
            break

    return {
        "trajectory": visited,
        "battery_levels": battery_levels,
        "cumulative_cost": round(cumulative_cost, 2),
        "steps_completed": len(visited),
        "status": status,
        "time_elapsed_s": round(time_elapsed, 1),
        "sol_fraction": round(time_elapsed / SOL_DURATION_SECONDS, 3),
    }
