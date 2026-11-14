"""
Terrain Adapter Module for MARS-09 Odyssey.

Handles 200x200 expanded Martian geomorphological simulation, Jezero & Valles Marineris analog
generation, multi-hazard classification, and non-finite value sanitization.
"""

import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


def generate_benchmark_terrain(
    rows: int = 200,
    cols: int = 200,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate a deterministic, scientifically grounded high-resolution Martian terrain model.
    Features:
    - Multi-ring impact crater with central peak and elevated rim
    - Valles-style steep canyon escarpment / chasma
    - Flat basaltic plains (Planitia) for high-speed rover transit
    - Low-elevation aeolian basins with sand dune ripples
    - 5 Distinct Martian hazard classifications:
        1. LANDSLIDE_SCARP (cost = inf, talus runout = 4.5+)
        2. VOLCANIC_VENT (cost = inf, geothermal magma fissures)
        3. BOULDER_EJECTA (cost = inf core, 2.8+ apron)
        4. SAND_TRAP_DUNE (cost = 3.2 - 5.5, high slip)
        5. WIND_VORTEX_CORRIDOR (cost = 2.2 - 4.0, shear corridor)

    Returns:
        cost_map: 2D float ndarray (1.0 = safe, 2.0-20.0 = caution, np.inf = hazard)
        elevation_map: 2D float ndarray of elevation in meters
    """
    np.random.seed(seed)

    # 1. Base Topography: Multi-frequency harmonic Martian surface
    x = np.linspace(0, 6 * np.pi, cols)
    y = np.linspace(0, 6 * np.pi, rows)
    xx, yy = np.meshgrid(x, y)

    elevation = (
        18.0 * np.sin(xx * 0.35) * np.cos(yy * 0.35)
        + 10.0 * np.sin(xx * 0.85 + 0.4)
        + 6.0 * np.cos(yy * 0.95 - 0.2)
        + 4.0 * np.sin(xx * 1.8) * np.sin(yy * 1.8)
        + 42.0  # Base datum altitude in meters
    )

    # 2. Valles-Style Canyon Chasma / Escarpment (running diagonally through sector)
    canyon_r_center = int(rows * 0.52)
    canyon_width = max(4.0, rows * 0.08)
    for r in range(rows):
        dist_canyon = abs(r - canyon_r_center)
        if dist_canyon < canyon_width:
            canyon_depth = -26.0 * (1.0 - (dist_canyon / canyon_width) ** 1.8)
            elevation[r, :] += canyon_depth

    # 3. Multi-Ring Impact Crater with Central Peak
    crater_center = (int(rows * 0.32), int(cols * 0.32))
    crater_radius = max(8.0, rows * 0.16)
    for r in range(rows):
        for c in range(cols):
            d = math.hypot(r - crater_center[0], c - crater_center[1])
            if d < crater_radius * 1.25:
                norm_d = d / crater_radius
                # Central peak uplift at d < 0.28 * radius
                if norm_d < 0.28:
                    elevation[r, c] += 12.0 * math.exp(-((norm_d / 0.15) ** 2))
                # Depressed floor and elevated rim
                floor_depth = -22.0 * math.exp(-((norm_d - 0.55) ** 2) / 0.12)
                rim_height = 14.0 * math.exp(-((norm_d - 1.0) ** 2) / 0.06)
                elevation[r, c] += floor_depth + rim_height

    # 4. Secondary Crater
    c2_center = (int(rows * 0.76), int(cols * 0.72))
    c2_radius = max(6.0, rows * 0.11)
    for r in range(rows):
        for c in range(cols):
            d2 = math.hypot(r - c2_center[0], c - c2_center[1])
            if d2 < c2_radius * 1.2:
                norm_d2 = d2 / c2_radius
                floor_depth2 = -16.0 * math.exp(-((norm_d2 - 0.5) ** 2) / 0.15)
                rim_height2 = 10.0 * math.exp(-((norm_d2 - 1.0) ** 2) / 0.08)
                elevation[r, c] += floor_depth2 + rim_height2

    # 5. Slope Analysis & Base Traversability Cost
    grad_y, grad_x = np.gradient(elevation)
    slope = np.sqrt(grad_x**2 + grad_y**2)

    cost_map = np.ones((rows, cols), dtype=float)
    cost_map += np.clip(slope * 1.9, 0.0, 16.0)

    # 6. Five Distinct Martian Hazards Placement:
    # -------------------------------------------------------------
    # Hazard 1: LANDSLIDE_SCARP on steep canyon walls (cost = inf, talus = 4.5+)
    scarp_r1 = int(canyon_r_center - canyon_width * 0.75)
    scarp_r2 = int(canyon_r_center - canyon_width * 0.35)
    c_scarp_start, c_scarp_end = int(cols * 0.15), int(cols * 0.85)
    cost_map[scarp_r1:scarp_r2, c_scarp_start:c_scarp_end] = np.inf
    # Talus runout apron
    cost_map[scarp_r2:int(canyon_r_center), c_scarp_start:c_scarp_end] = np.maximum(
        cost_map[scarp_r2:int(canyon_r_center), c_scarp_start:c_scarp_end], 6.5
    )

    # Hazard 2: VOLCANIC_VENT Geothermal Fissures (cost = inf)
    v_r_start, v_r_end = int(rows * 0.14), int(rows * 0.28)
    v_c_start, v_c_end = int(cols * 0.65), int(cols * 0.82)
    for r in range(v_r_start, min(rows, v_r_end)):
        # Sinusoidal magma fissure vein
        c_fissure = int(v_c_start + (v_c_end - v_c_start) * ((r - v_r_start) / max(1, v_r_end - v_r_start)) + 3 * math.sin(r * 0.6))
        if 0 <= c_fissure < cols:
            cost_map[r, max(0, c_fissure - 1):min(cols, c_fissure + 2)] = np.inf

    # Hazard 3: BOULDER_EJECTA Blanket (Crater rim block fields)
    rim_r, rim_c = crater_center
    boulder_r_start, boulder_r_end = int(rim_r - crater_radius * 1.1), int(rim_r - crater_radius * 0.7)
    boulder_c_start, boulder_c_end = int(rim_c - crater_radius * 0.2), int(rim_c + crater_radius * 0.8)
    cost_map[max(0, boulder_r_start):min(rows, boulder_r_end), max(0, boulder_c_start):min(cols, boulder_c_end)] = np.inf

    # Outer boulder apron
    apron_r_start, apron_r_end = int(rim_r - crater_radius * 1.4), int(rim_r - crater_radius * 1.1)
    if apron_r_start >= 0 and apron_r_end < rows:
        cost_map[apron_r_start:apron_r_end, max(0, boulder_c_start):min(cols, boulder_c_end)] = np.maximum(
            cost_map[apron_r_start:apron_r_end, max(0, boulder_c_start):min(cols, boulder_c_end)], 5.2
        )

    # Hazard 4: SAND_TRAP_DUNE Cohesionless Transverse Dunes (cost = 3.2 - 5.5)
    dune_r_start, dune_r_end = int(rows * 0.80), int(rows * 0.95)
    dune_c_start, dune_c_end = int(cols * 0.20), int(cols * 0.55)
    cost_map[dune_r_start:dune_r_end, dune_c_start:dune_c_end] = np.maximum(
        cost_map[dune_r_start:dune_r_end, dune_c_start:dune_c_end], 4.8
    )

    # Hazard 5: WIND_VORTEX_CORRIDOR (cost = 2.4 - 3.8)
    vortex_r_start, vortex_r_end = int(rows * 0.05), int(rows * 0.18)
    vortex_c_start, vortex_c_end = int(cols * 0.35), int(cols * 0.58)
    cost_map[vortex_r_start:vortex_r_end, vortex_c_start:vortex_c_end] = np.maximum(
        cost_map[vortex_r_start:vortex_r_end, vortex_c_start:vortex_c_end], 3.2
    )

    # Guarantee Start (0..5%) and Goal (95..100%) safety corridors
    safe_margin_r = max(2, int(rows * 0.08))
    safe_margin_c = max(2, int(cols * 0.08))
    cost_map[0:safe_margin_r, 0:safe_margin_c] = 1.0

    goal_margin_r = max(0, int(rows * 0.90))
    goal_margin_c = max(0, int(cols * 0.90))
    cost_map[goal_margin_r:rows, goal_margin_c:cols] = np.minimum(cost_map[goal_margin_r:rows, goal_margin_c:cols], 1.8)

    return cost_map, elevation


def sanitize_cost_map_for_json(cost_map: np.ndarray) -> List[List[Optional[float]]]:
    """Safely serialize cost_map to JSON-compliant 2D list with null sentinels."""
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
    """Reconstruct NumPy cost_map from JSON list, restoring null to np.inf."""
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


# Resolution-keyed cache for generated benchmark terrains
_TERRAIN_CACHE: Dict[Tuple[int, int, int], Tuple[np.ndarray, np.ndarray]] = {}


def get_default_terrain(rows: int = 200, cols: int = 200, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """Retrieve or generate default benchmark terrain (cached by dimensions)."""
    key = (rows, cols, seed)
    if key not in _TERRAIN_CACHE:
        _TERRAIN_CACHE[key] = generate_benchmark_terrain(rows, cols, seed=seed)
    return _TERRAIN_CACHE[key]


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
