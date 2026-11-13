"""
Cost Map and Risk Map generation module for MARS-09 autonomous navigation.

Navigation Integration Contract (Member 3):
1. cost_map is a 2D NumPy array with dtype float (np.float64).
2. Its shape matches all other terrain grids, nominally (100, 100).
3. SAFE terrain cells have a cost of exactly 1.0.
4. CAUTION terrain cells have costs strictly greater than 2.0, scaled within [5.0, 20.0].
5. IMPASSABLE HAZARD terrain cells have cost np.inf.
6. Coordinates use matrix indexing (row, col).
7. risk_map is maintained separately from cost_map as a continuous normalized risk score [0.0, 1.0].

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from typing import Optional, Tuple
import numpy as np

# Traversability classification constants
SAFE_CLASS: int = 0
CAUTION_CLASS: int = 1
HAZARD_CLASS: int = 2

# Standard cost values per navigation contract
SAFE_COST: float = 1.0
DEFAULT_CAUTION_MIN: float = 5.0
DEFAULT_CAUTION_MAX: float = 20.0
HAZARD_COST: float = float("inf")


def create_cost_map(
    classification_map: np.ndarray,
    slope_deg: np.ndarray,
    obstacle_mask: np.ndarray,
    obstacle_density: Optional[np.ndarray] = None,
    caution_min_cost: float = DEFAULT_CAUTION_MIN,
    caution_max_cost: float = DEFAULT_CAUTION_MAX,
    slope_caution_thresh_deg: float = 12.0,
    slope_hazard_thresh_deg: float = 20.0,
) -> np.ndarray:
    """
    Generate a 2D numerical traversal cost array according to Member 3's navigation contract.

    Cost Value Specifications:
    - 1.0 (SAFE): Flat, obstacle-free regolith with nominal rolling resistance.
    - 5.0 to 20.0 (CAUTION): Navigable but challenging terrain (moderate slopes, loose
      sand, or scattered pebbles). Traversal requires slower speeds and careful steering.
      Cost scales smoothly within [caution_min_cost, caution_max_cost] based on local slope
      and rock concentration.
    - np.inf (HAZARD / IMPASSABLE): Extreme slopes (>= 20° rollover limit), discrete
      boulders, or dense rock clusters. Path planners must strictly avoid these cells.

    Parameters:
        classification_map: 2D integer ndarray (0=SAFE, 1=CAUTION, 2=HAZARD).
        slope_deg: 2D float ndarray of terrain slope in degrees.
        obstacle_mask: 2D boolean ndarray where True indicates an impassable obstacle.
        obstacle_density: Optional 2D float ndarray in [0.0, 1.0] of spatial rock density.
        caution_min_cost: Lower bound cost for caution cells (> 2.0, default 5.0).
        caution_max_cost: Upper bound cost for caution cells (default 20.0).
        slope_caution_thresh_deg: Slope in degrees defining caution threshold (default 12.0°).
        slope_hazard_thresh_deg: Slope in degrees defining hazard threshold (default 20.0°).

    Returns:
        cost_map: 2D NumPy float array of identical shape (normally 100x100) indexed by (row, col).
    """
    if classification_map.shape != slope_deg.shape:
        raise ValueError(
            f"Shape mismatch: classification {classification_map.shape} vs slope {slope_deg.shape}"
        )
    if classification_map.shape != obstacle_mask.shape:
        raise ValueError(
            f"Shape mismatch: classification {classification_map.shape} vs obstacle {obstacle_mask.shape}"
        )
    if caution_min_cost <= 2.0:
        raise ValueError(f"caution_min_cost must be > 2.0 per contract, got {caution_min_cost}")

    rows, cols = classification_map.shape
    cost_map = np.full((rows, cols), HAZARD_COST, dtype=np.float64)

    density = obstacle_density if obstacle_density is not None else np.zeros((rows, cols), dtype=np.float64)

    # 1. SAFE terrain: Exactly 1.0 per contract item 3
    is_safe = (classification_map == SAFE_CLASS) & (~obstacle_mask)
    cost_map[is_safe] = SAFE_COST

    # 2. CAUTION terrain: Configurable finite cost > 2.0, scaled in [caution_min_cost, caution_max_cost]
    is_caution = (classification_map == CAUTION_CLASS) & (~obstacle_mask)
    if np.any(is_caution):
        # Normalized slope excess in [0.0, 1.0] across caution interval
        denom = max(slope_hazard_thresh_deg - slope_caution_thresh_deg, 1e-3)
        slope_factor = np.clip((slope_deg[is_caution] - slope_caution_thresh_deg) / denom, 0.0, 1.0)
        density_factor = np.clip(density[is_caution], 0.0, 1.0)

        # Composite difficulty factor combining slope severity and rockiness
        combined_severity = 0.70 * slope_factor + 0.30 * density_factor
        caution_costs = caution_min_cost + (caution_max_cost - caution_min_cost) * combined_severity

        # Guarantee all caution costs are strictly > 2.0 and <= caution_max_cost
        cost_map[is_caution] = np.clip(caution_costs, caution_min_cost, caution_max_cost)

    # 3. IMPASSABLE HAZARD terrain: Strictly np.inf per contract item 5
    cost_map[obstacle_mask] = HAZARD_COST
    cost_map[classification_map == HAZARD_CLASS] = HAZARD_COST

    return cost_map


def create_risk_map(
    slope_deg: np.ndarray,
    obstacle_density: np.ndarray,
    uncertainty_map: Optional[np.ndarray] = None,
    obstacle_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Generate a 2D continuous risk map normalized in [0.0, 1.0].

    Kept separate from cost_map per contract specification.
    Provides a graded, continuous probability of traversal difficulty or chassis stress.

    Parameters:
        slope_deg: 2D float ndarray of terrain slope in degrees.
        obstacle_density: 2D float ndarray in [0.0, 1.0] of rock density.
        uncertainty_map: Optional 2D float ndarray in [0.0, 1.0] of sensor uncertainty.
        obstacle_mask: Optional 2D bool ndarray where True represents discrete obstacles.

    Returns:
        risk_map: 2D float ndarray of shape (rows, cols) with values in [0.0, 1.0].
    """
    rows, cols = slope_deg.shape
    # Normalize slope (0° to 30° mapped to [0.0, 1.0])
    norm_slope = np.clip(slope_deg / 30.0, 0.0, 1.0)
    norm_density = np.clip(obstacle_density, 0.0, 1.0)
    norm_unc = np.clip(uncertainty_map, 0.0, 1.0) if uncertainty_map is not None else np.zeros((rows, cols))

    risk = 0.50 * norm_slope + 0.30 * norm_density + 0.20 * norm_unc
    if obstacle_mask is not None:
        risk[obstacle_mask] = 1.0

    return np.clip(risk, 0.0, 1.0).astype(np.float64)


def build_costmap(
    classification_map: np.ndarray,
    slope_deg: np.ndarray,
    obstacle_mask: np.ndarray,
    obstacle_density: Optional[np.ndarray] = None,
    uncertainty_map: Optional[np.ndarray] = None,
    caution_min_cost: float = DEFAULT_CAUTION_MIN,
    caution_max_cost: float = DEFAULT_CAUTION_MAX,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates both the navigation cost_map and the separate risk_map.

    Returns:
        Tuple of (cost_map, risk_map)
    """
    c_map = create_cost_map(
        classification_map=classification_map,
        slope_deg=slope_deg,
        obstacle_mask=obstacle_mask,
        obstacle_density=obstacle_density,
        caution_min_cost=caution_min_cost,
        caution_max_cost=caution_max_cost,
    )
    density = obstacle_density if obstacle_density is not None else np.zeros_like(slope_deg)
    r_map = create_risk_map(
        slope_deg=slope_deg,
        obstacle_density=density,
        uncertainty_map=uncertainty_map,
        obstacle_mask=obstacle_mask,
    )
    return c_map, r_map
