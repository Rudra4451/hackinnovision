"""
Coordinate conversions, file loaders, formatting helpers, and payload validators.
"""
from typing import Tuple, Any


def grid_to_world_coords(grid_pos: Tuple[int, int], resolution_m: float = 1.0) -> Tuple[float, float]:
    return (grid_pos[0] * resolution_m, grid_pos[1] * resolution_m)


def validate_navigation_payload(res: Any) -> Tuple[bool, str]:
    """
    Validate that a compare_routes response payload strictly satisfies
    the MARS-09 navigation interface contract.

    Parameters:
        res: The dictionary returned by compare_routes.

    Returns:
        (is_valid, error_message): Tuple where is_valid is True if all required
        nested keys exist, or False with an informative error message identifying
        the exact missing key.
    """
    if not isinstance(res, dict):
        return False, "Payload must be a dictionary"

    required_keys = [
        "safest",
        "safest.route",
        "safest.route.success",
        "safest.route.x",
        "safest.route.y",
        "safest.route.path",
        "safest.metrics",
        "safest.metrics.total_cost",
        "safest.metrics.caution_steps",
        "summary",
        "summary.distance_penalty_pct",
        "summary.recommendation",
    ]

    for key_path in required_keys:
        parts = key_path.split(".")
        current = res
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return False, f"Missing required navigation key: '{key_path}'"
            current = current[part]

    return True, ""
