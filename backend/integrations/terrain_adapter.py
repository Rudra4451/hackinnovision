"""
Terrain Adapter Module for MARS-09 Odyssey.

Handles terrain simulation, benchmark crater generation (Jezero Crater analog),
elevation synthesis, and non-finite value sanitization (Rule 3) for JSON/Plotly serialization.
"""

import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


def generate_benchmark_terrain(
    rows: int = 50,
    cols: int = 50,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate a deterministic, scientifically realistic 50x50 Martian surface model.

    Returns:
        cost_map: 2D float ndarray where 1.0=nominal, 2.0-20.0=caution, np.inf=hazard
        elevation_map: 2D float ndarray of topographical height in meters
    """
    np.random.seed(seed)
    
    # 1. Base elevation map: gentle multi-frequency sinusoidal topography
    x = np.linspace(0, 4 * np.pi, cols)
    y = np.linspace(0, 4 * np.pi, rows)
    xx, yy = np.meshgrid(x, y)
    
    elevation = (
        15.0 * np.sin(xx * 0.5) * np.cos(yy * 0.5)
        + 8.0 * np.sin(xx * 1.2 + 0.4)
        + 5.0 * np.cos(yy * 1.4 - 0.2)
        + 30.0  # Base elevation in meters
    )
    
    # Add a prominent central crater depression at (25, 25) with radius 12
    crater_center = (25, 25)
    crater_radius = 12.0
    for r in range(rows):
        for c in range(cols):
            d = math.hypot(r - crater_center[0], c - crater_center[1])
            if d < crater_radius:
                # Crater floor depressed, crater rim elevated
                rim_factor = math.exp(-((d - crater_radius) ** 2) / 4.0)
                floor_depth = -18.0 * (1.0 - (d / crater_radius) ** 2)
                elevation[r, c] += floor_depth + 14.0 * rim_factor

    # 2. Derive base cost map from slope/roughness
    grad_y, grad_x = np.gradient(elevation)
    slope = np.sqrt(grad_x**2 + grad_y**2)
    
    # Base cost: 1.0 for flat ground, scaling up with slope
    cost_map = np.ones((rows, cols), dtype=float)
    cost_map += np.clip(slope * 1.8, 0.0, 15.0)

    # 3. Add Impassable Hazards (np.inf) scaled to grid size
    # Hazard A: Western Crater Rim Wall (fissure/escarpment)
    r_start, r_end = int(rows * 0.28), int(rows * 0.72)
    c_wall1, c_wall2 = int(cols * 0.26), int(cols * 0.28)
    cost_map[r_start:r_end, c_wall1:c_wall2 + 1] = np.inf
    
    # Hazard B: Eastern Boulder Ridge
    r_b_start, r_b_end = int(rows * 0.16), int(rows * 0.48)
    c_b_start, c_b_end = int(cols * 0.76), int(cols * 0.80)
    cost_map[r_b_start:r_b_end, c_b_start:c_b_end] = np.inf
    
    # Hazard C: Northern Rock Field Hazard
    r_c_start, r_c_end = int(rows * 0.08), int(rows * 0.14)
    c_c_start, c_c_end = int(cols * 0.36), int(cols * 0.56)
    cost_map[r_c_start:r_c_end, c_c_start:c_c_end] = np.inf
    
    # Hazard D: Isolated Deep Sinkholes / Breccias
    s1_r, s1_c = int(rows * 0.70), int(cols * 0.84)
    if s1_r < rows and s1_c < cols:
        cost_map[s1_r, min(s1_c + 2, cols - 1)] = np.inf
    s2_r, s2_c = int(rows * 0.84), int(cols * 0.20)
    if s2_r < rows and s2_c < cols:
        cost_map[s2_r, min(s2_c + 2, cols - 1)] = np.inf

    # 4. Add High-Slope Caution Hazard Zones (cost 5.0 - 20.0)
    # Caution Zone 1: Sandy dunes along Southern perimeter
    r_d_start, r_d_end = int(rows * 0.76), int(rows * 0.96)
    c_d_start, c_d_end = int(cols * 0.40), int(cols * 0.68)
    cost_map[r_d_start:r_d_end, c_d_start:c_d_end] = np.maximum(
        cost_map[r_d_start:r_d_end, c_d_start:c_d_end], 14.5
    )

    # Caution Zone 2: Loose regolith fan near Central Crater
    r_f_start, r_f_end = int(rows * 0.36), int(rows * 0.48)
    c_f_start, c_f_end = int(cols * 0.40), int(cols * 0.52)
    cost_map[r_f_start:r_f_end, c_f_start:c_f_end] = np.maximum(
        cost_map[r_f_start:r_f_end, c_f_start:c_f_end], 8.0
    )

    # Ensure start (0, 0) to (5, 5) and goal corridor are safe
    s_r, s_c = max(1, int(rows * 0.1)), max(1, int(cols * 0.1))
    cost_map[0:s_r, 0:s_c] = 1.0
    g_r, g_c = max(0, int(rows * 0.9)), max(0, int(cols * 0.9))
    cost_map[g_r:rows, g_c:cols] = np.minimum(cost_map[g_r:rows, g_c:cols], 2.0)

    return cost_map, elevation


def sanitize_cost_map_for_json(cost_map: np.ndarray) -> List[List[Optional[float]]]:
    """
    Safely serialize cost_map to JSON-compliant 2D list.
    Converts np.inf and values >= 1e9 to None (serializes to JSON null) (Rule 3).
    """
    rows, cols = cost_map.shape
    sanitized: List[List[Optional[float]]] = []
    
    for r in range(rows):
        row_vals: List[Optional[float]] = []
        for c in range(cols):
            val = float(cost_map[r, c])
            if math.isinf(val) or math.isnan(val) or val >= 1e9:
                row_vals.append(None)
            else:
                row_vals.append(round(val, 2))
        sanitized.append(row_vals)
    return sanitized


def extract_hazard_mask(cost_map: np.ndarray) -> List[List[bool]]:
    """Generate boolean 2D mask indicating impassable hazards."""
    rows, cols = cost_map.shape
    mask: List[List[bool]] = []
    for r in range(rows):
        mask.append([bool(math.isinf(cost_map[r, c]) or cost_map[r, c] >= 1e9) for c in range(cols)])
    return mask


def deserialize_cost_map_from_json(display_grid: List[List[Optional[float]]]) -> np.ndarray:
    """Reconstruct NumPy cost_map from JSON list, restoring null/None to np.inf."""
    rows = len(display_grid)
    cols = len(display_grid[0]) if rows > 0 else 0
    arr = np.ones((rows, cols), dtype=float)
    
    for r in range(rows):
        for c in range(cols):
            val = display_grid[r][c]
            if val is None or (isinstance(val, (int, float)) and val >= 1e9):
                arr[r, c] = np.inf
            else:
                arr[r, c] = float(val)
    return arr


# Singleton cache for benchmark terrain
_CACHED_TERRAIN: Optional[Tuple[np.ndarray, np.ndarray]] = None


def get_default_terrain() -> Tuple[np.ndarray, np.ndarray]:
    """Retrieve or generate default benchmark terrain."""
    global _CACHED_TERRAIN
    if _CACHED_TERRAIN is None:
        _CACHED_TERRAIN = generate_benchmark_terrain(50, 50, seed=42)
    return _CACHED_TERRAIN


def get_terrain_intelligence_data(seed: int = 42) -> Dict[str, Any]:
    """Retrieve complete topographical intelligence from core.terrain."""
    try:
        from core.terrain import build_terrain_intelligence
        return build_terrain_intelligence(seed=seed)
    except ImportError:
        cost_map, elevation = get_default_terrain()
        return {
            "cost_map": cost_map,
            "elevation": elevation,
            "slope": np.zeros_like(cost_map),
            "obstacle_mask": np.isinf(cost_map),
        }

