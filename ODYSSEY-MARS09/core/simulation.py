"""
Rover State Simulation, Telemetry Progression, and Energy Consumption
"""

from typing import List, Tuple, Dict, Any
from core.config import (
    BATTERY_CAPACITY_WH,
    ENERGY_PER_STEP_BASE_WH,
    OBSTACLE_COST
)


def simulate_rover(
    path: List[Tuple[int, int]],
    cost_map: Any,
    initial_battery_wh: float = BATTERY_CAPACITY_WH
) -> Dict[str, Any]:
    """
    Simulate rover motion across a path trajectory, logging step-by-step telemetry.
    """
    battery = initial_battery_wh
    battery_levels = [battery]
    visited = []
    cumulative_cost = 0.0
    status = "GOAL_REACHED"

    for r, c in path:
        try:
            cost = cost_map[r][c] if isinstance(cost_map, list) else cost_map[r, c]
        except Exception:
            cost = 1.0

        if cost >= OBSTACLE_COST:
            status = "OBSTACLE_COLLISION"
            break

        energy_spent = ENERGY_PER_STEP_BASE_WH * cost
        battery -= energy_spent
        cumulative_cost += cost
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
    }
