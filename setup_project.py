"""
ODYSSEY MARS-09 Project Setup Script
Creates the foundational project directory structure, configuration,
interface contracts, and stubs for independent module development.
"""

from pathlib import Path

BASE_DIR = Path("ODYSSEY-MARS09")

# Define directory structure
DIRECTORIES = [
    BASE_DIR / "core",
    BASE_DIR / "data" / "terrain",
    BASE_DIR / "data" / "targets",
    BASE_DIR / "components",
    BASE_DIR / "utils",
    BASE_DIR / "tests",
]

# File contents mapping
FILES = {
    BASE_DIR / "requirements.txt": """streamlit>=1.30.0
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
plotly>=5.18.0
opencv-python>=4.8.0
pytest>=7.4.0
""",

    BASE_DIR / "README.md": """# ODYSSEY MARS-09 Rover Simulation

Architectural foundation for the Streamlit-based Mars rover simulation.

## Project Structure
```
ODYSSEY-MARS09/
├── app.py                      # Main Streamlit dashboard application
├── requirements.txt            # Project dependencies
├── README.md                   # Project documentation & team contracts
├── core/                       # Core simulation logic & algorithmic modules
│   ├── __init__.py
│   ├── config.py               # Mission constants & simulation parameters
│   ├── terrain.py              # Terrain generation & cost mapping stubs
│   ├── navigation.py           # Pathfinding (A*, Dijkstra) & route comparison stubs
│   ├── science.py              # Science target ranking & confidence scoring stubs
│   └── simulation.py           # Rover step-by-step state simulation stubs
├── data/                       # Static & cached assets
│   ├── terrain/                # DEM (Digital Elevation Model) maps & textures
│   └── targets/                # Geological target registry & spectrometer samples
├── components/                 # Streamlit UI visual components
│   ├── __init__.py
│   ├── terrain_map.py          # 2D/3D Plotly elevation and path renderer
│   ├── mission_panel.py        # Telemetry, battery, and sol timer widgets
│   ├── target_panel.py         # Science target priority queue UI
│   └── rover_animation.py      # Frame-by-frame traversal animator
├── utils/                      # Helper utilities & analytical metrics
│   ├── __init__.py
│   ├── metrics.py              # Path cost, energy consumption & traversal risk formulas
│   └── helpers.py              # Coordinate transforms and file I/O helpers
└── tests/                      # Automated unit tests
    ├── __init__.py
    ├── test_terrain.py         # Terrain generator & cost map test suite
    ├── test_navigation.py      # Pathfinding validation tests
    └── test_science.py         # Target ranking & confidence unit tests
```

## Team Module Ownership
- **Teammate A (Terrain & Hazards):** `core/terrain.py`, `components/terrain_map.py`, `tests/test_terrain.py`
- **Teammate B (Navigation & Pathfinding):** `core/navigation.py`, `core/simulation.py`, `tests/test_navigation.py`
- **Teammate C (Science Operations):** `core/science.py`, `components/target_panel.py`, `tests/test_science.py`

## Quick Start
```bash
pip install -r requirements.txt
streamlit run app.py
```
""",

    BASE_DIR / "core" / "__init__.py": '"""ODYSSEY MARS-09 Core Simulation Package."""\n',

    BASE_DIR / "core" / "config.py": '''"""
ODYSSEY MARS-09: Mission Configuration and Environment Constants
Lead Software Architect Specification
"""

from typing import Tuple

# Environment & Grid Boundaries
GRID_SIZE: int = 100
START_POSITION: Tuple[int, int] = (5, 5)
GOAL_POSITION: Tuple[int, int] = (90, 90)

# Hazard & Navigation Constraints
MAX_SLOPE: float = 30.0  # Maximum traversable slope in degrees
OBSTACLE_COST: float = float("inf")  # Non-traversable cost penalty

# Rover Vehicle Dynamics
ROVER_MASS_KG: float = 185.0
MAX_SPEED_MPS: float = 0.05  # Meters per second
BATTERY_CAPACITY_WH: float = 1200.0  # Watt-hours
ENERGY_PER_STEP_BASE_WH: float = 1.2
SOL_DURATION_SECONDS: int = 300
''',

    BASE_DIR / "core" / "terrain.py": '''"""
Terrain Generation, Classification, and Traversability Cost Mapping
"""

from typing import Optional, Union, List, Any
try:
    import numpy as np
except ImportError:
    np = None

from core.config import GRID_SIZE, MAX_SLOPE, OBSTACLE_COST


def generate_terrain(
    grid_size: int = GRID_SIZE,
    seed: Optional[int] = 42,
    roughness: float = 0.5
) -> Any:
    """
    Generate a 2D synthetic Martian digital elevation model (DEM).

    Returns:
        np.ndarray (or 2D list if numpy is not installed) of shape (grid_size, grid_size).
    """
    if np is not None:
        rng = np.random.default_rng(seed)
        x = np.linspace(0, 10, grid_size)
        y = np.linspace(0, 10, grid_size)
        xx, yy = np.meshgrid(x, y)
        elevation = np.sin(xx / 2.0) * np.cos(yy / 2.0) * 15.0 + rng.normal(0, 0.5, (grid_size, grid_size))
        return elevation.astype(np.float32)
    
    # Fallback to pure Python list structure
    return [[float((r * c) % 25) for c in range(grid_size)] for r in range(grid_size)]


def classify_terrain(
    elevation_map: Any,
    max_slope: float = MAX_SLOPE
) -> Any:
    """
    Classify terrain into traversability zones based on gradient/slope.
    0 = Smooth, 1 = Rough, 2 = Obstacle.

    Returns:
        np.ndarray (or 2D list) of matching shape.
    """
    if np is not None and isinstance(elevation_map, np.ndarray):
        dy, dx = np.gradient(elevation_map)
        slope_degrees = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
        classified = np.zeros_like(elevation_map, dtype=np.int32)
        classified[slope_degrees > 15.0] = 1
        classified[slope_degrees > max_slope] = 2
        return classified
    
    rows = len(elevation_map)
    cols = len(elevation_map[0]) if rows > 0 else 0
    return [[0 for _ in range(cols)] for _ in range(rows)]


def generate_cost_map(
    elevation_map: Any,
    obstacle_cost: float = OBSTACLE_COST,
    max_slope: float = MAX_SLOPE
) -> Any:
    """
    Generate a traversal cost grid for pathfinding algorithms.

    Returns:
        np.ndarray (or 2D list) of matching shape.
    """
    if np is not None and isinstance(elevation_map, np.ndarray):
        dy, dx = np.gradient(elevation_map)
        slope_degrees = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
        cost_map = 1.0 + (slope_degrees / 5.0)
        cost_map[slope_degrees > max_slope] = obstacle_cost
        return cost_map.astype(np.float64)

    rows = len(elevation_map)
    cols = len(elevation_map[0]) if rows > 0 else 0
    return [[1.0 for _ in range(cols)] for _ in range(rows)]
''',

    BASE_DIR / "core" / "navigation.py": '''"""
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
''',

    BASE_DIR / "core" / "science.py": '''"""
Science Target Evaluation, Ranking, and Spectrometric Confidence Scoring
"""

import math
import random
from typing import List, Dict, Any, Tuple
try:
    import numpy as np
except ImportError:
    np = None

from core.config import START_POSITION


def rank_targets(
    targets: List[Dict[str, Any]],
    rover_pos: Tuple[int, int] = START_POSITION,
    weight_priority: float = 0.6,
    weight_distance: float = 0.4
) -> List[Dict[str, Any]]:
    """
    Rank scientific targets based on priority score and proximity to rover.

    Returns:
        List[Dict[str, Any]]: Targets sorted by composite priority score (descending).
    """
    if not targets:
        targets = [
            {"id": "TARGET_ALPHA", "pos": (25, 30), "priority": 9, "type": "Hematite Ridge"},
            {"id": "TARGET_BETA", "pos": (45, 60), "priority": 7, "type": "Hydrated Silicates"},
            {"id": "TARGET_GAMMA", "pos": (80, 85), "priority": 10, "type": "Ancient Biosignature Site"},
        ]

    scored = []
    for t in targets:
        dr = t["pos"][0] - rover_pos[0]
        dc = t["pos"][1] - rover_pos[1]
        dist = math.hypot(dr, dc)
        norm_dist = max(dist / 141.4, 0.01)
        composite_score = (weight_priority * (t["priority"] / 10.0)) - (weight_distance * norm_dist)
        target_copy = dict(t)
        target_copy["distance"] = round(float(dist), 2)
        target_copy["composite_score"] = round(float(composite_score), 3)
        scored.append(target_copy)

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    return scored


def calculate_confidence(
    target_data: Dict[str, Any],
    reading_type: str = "spectrometry"
) -> float:
    """
    Calculate confidence score (0.0 to 1.0) for a scientific reading.
    """
    base_confidence = 0.85
    noise = float(random.uniform(0.01, 0.08))
    confidence = max(0.0, min(1.0, base_confidence - noise))
    return round(confidence, 3)
''',

    BASE_DIR / "core" / "simulation.py": '''"""
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
''',

    BASE_DIR / "components" / "__init__.py": '"""Streamlit UI visual presentation components."""\n',

    BASE_DIR / "components" / "terrain_map.py": '''"""UI Component: 2D/3D Plotly Terrain & Path Visualizer."""
from typing import List, Tuple, Any


def render_terrain_map(
    elevation: Any,
    path: List[Tuple[int, int]] = None,
    targets: List[dict] = None
):
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    fig = go.Figure(data=[
        go.Heatmap(
            z=elevation,
            colorscale="YlOrRd",
            colorbar=dict(title="Elevation (m)")
        )
    ])
    if path:
        pr, pc = zip(*path)
        fig.add_trace(go.Scatter(
            x=pc, y=pr,
            mode="lines+markers",
            line=dict(color="cyan", width=3),
            marker=dict(size=4),
            name="Planned Path"
        ))
    if targets:
        for t in targets:
            fig.add_trace(go.Scatter(
                x=[t["pos"][1]], y=[t["pos"][0]],
                mode="markers+text",
                marker=dict(size=12, color="lime", symbol="star"),
                text=[t["id"]],
                textposition="top center",
                name=t["id"]
            ))
    fig.update_layout(
        title="Martian Surface Topography & Trajectory",
        xaxis_title="Grid X",
        yaxis_title="Grid Y",
        yaxis=dict(autorange="reversed"),
        height=650,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig
''',

    BASE_DIR / "components" / "mission_panel.py": '''"""UI Component: Mission Status & Telemetry Metrics."""
from typing import Dict, Any


def render_mission_panel(telemetry: Dict[str, Any]):
    import streamlit as st
    st.subheader("Rover Telemetry & Health")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mission Status", telemetry.get("status", "NOMINAL"))
    c2.metric("Steps Executed", telemetry.get("steps_completed", 0))
    battery = telemetry.get("battery_levels", [100.0])[-1]
    c3.metric("Battery Remaining", f"{battery:.1f} Wh")
    c4.metric("Cumulative Cost", telemetry.get("cumulative_cost", 0.0))
''',

    BASE_DIR / "components" / "target_panel.py": '''"""UI Component: Science Target Registry."""
from typing import List, Dict, Any


def render_target_panel(ranked_targets: List[Dict[str, Any]]):
    import streamlit as st
    st.subheader("Prioritized Science Targets")
    if ranked_targets:
        try:
            import pandas as pd
            df = pd.DataFrame(ranked_targets)
            st.dataframe(df, use_container_width=True)
        except ImportError:
            st.write(ranked_targets)
    else:
        st.info("No active science targets registered.")
''',

    BASE_DIR / "components" / "rover_animation.py": '''"""UI Component: Rover Step-by-Step Traversal Animator."""
import time
from typing import List, Tuple


def animate_traversal(path: List[Tuple[int, int]], speed: float = 0.05):
    import streamlit as st
    placeholder = st.empty()
    for idx, step in enumerate(path):
        placeholder.markdown(f"**Rover moving...** Step `{idx + 1}/{len(path)}` at coordinate `{step}`")
        time.sleep(speed)
    placeholder.success("Traversal Completed.")
''',

    BASE_DIR / "utils" / "__init__.py": '"""Utility functions and mathematical helpers."""\n',

    BASE_DIR / "utils" / "metrics.py": '''"""Metrics computation for energy, roughness, and path efficiency."""
import math
from typing import List, Tuple


def calculate_path_length(path: List[Tuple[int, int]]) -> float:
    if len(path) < 2:
        return 0.0
    total = 0.0
    for i in range(len(path) - 1):
        dr = path[i+1][0] - path[i][0]
        dc = path[i+1][1] - path[i][1]
        total += math.hypot(dr, dc)
    return float(total)
''',

    BASE_DIR / "utils" / "helpers.py": '''"""Coordinate conversions, file loaders, and formatting helpers."""
from typing import Tuple


def grid_to_world_coords(grid_pos: Tuple[int, int], resolution_m: float = 1.0) -> Tuple[float, float]:
    return (grid_pos[0] * resolution_m, grid_pos[1] * resolution_m)
''',

    BASE_DIR / "tests" / "__init__.py": '"""Automated test suite."""\n',

    BASE_DIR / "tests" / "test_terrain.py": '''import unittest
from core.terrain import generate_terrain, classify_terrain, generate_cost_map
from core.config import GRID_SIZE, MAX_SLOPE, OBSTACLE_COST


class TestTerrain(unittest.TestCase):
    def test_terrain_dimensions(self):
        elev = generate_terrain(grid_size=50)
        self.assertEqual(len(elev), 50)

    def test_terrain_classification(self):
        elev = generate_terrain(grid_size=30)
        classified = classify_terrain(elev, max_slope=MAX_SLOPE)
        self.assertEqual(len(classified), 30)

    def test_cost_map_bounds(self):
        elev = generate_terrain(grid_size=30)
        cost = generate_cost_map(elev, obstacle_cost=OBSTACLE_COST)
        self.assertEqual(len(cost), 30)


if __name__ == "__main__":
    unittest.main()
''',

    BASE_DIR / "tests" / "test_navigation.py": '''import unittest
from core.navigation import find_path, compare_routes
from core.terrain import generate_terrain, generate_cost_map


class TestNavigation(unittest.TestCase):
    def test_find_path(self):
        elev = generate_terrain(grid_size=40)
        cost = generate_cost_map(elev)
        path = find_path(cost, start=(0, 0), goal=(39, 39))
        self.assertTrue(len(path) > 0)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (39, 39))

    def test_compare_routes(self):
        elev = generate_terrain(grid_size=20)
        cost = generate_cost_map(elev)
        r1 = [(i, i) for i in range(10)]
        r2 = [(i, 0) for i in range(10)]
        res = compare_routes(cost, [r1, r2], ["RouteA", "RouteB"])
        self.assertIn("RouteA", res)
        self.assertIn("RouteB", res)


if __name__ == "__main__":
    unittest.main()
''',

    BASE_DIR / "tests" / "test_science.py": '''import unittest
from core.science import rank_targets, calculate_confidence


class TestScience(unittest.TestCase):
    def test_rank_targets(self):
        targets = [
            {"id": "A", "pos": (10, 10), "priority": 5},
            {"id": "B", "pos": (90, 90), "priority": 10},
        ]
        ranked = rank_targets(targets, rover_pos=(0, 0))
        self.assertEqual(len(ranked), 2)
        self.assertIn("composite_score", ranked[0])

    def test_confidence(self):
        conf = calculate_confidence({"id": "SAMPLE_1"})
        self.assertTrue(0.0 <= conf <= 1.0)


if __name__ == "__main__":
    unittest.main()
''',

    BASE_DIR / "app.py": '''"""
ODYSSEY MARS-09: Streamlit Rover Mission Control Application
Main Entrypoint
"""

import streamlit as st

# Core contract imports
from core.config import (
    GRID_SIZE,
    START_POSITION,
    GOAL_POSITION,
    MAX_SLOPE,
    BATTERY_CAPACITY_WH
)
from core.terrain import generate_terrain, classify_terrain, generate_cost_map
from core.navigation import find_path, compare_routes
from core.science import rank_targets, calculate_confidence
from core.simulation import simulate_rover

# UI Component imports
from components.terrain_map import render_terrain_map
from components.mission_panel import render_mission_panel
from components.target_panel import render_target_panel

st.set_page_config(
    page_title="ODYSSEY MARS-09 Mission Control",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header & Subtitle
st.title("🔴 ODYSSEY MARS-09: Planetary Rover Simulation")
st.caption("Autonomous Pathfinding, Topographical Hazard Analysis, & Science Exploration")

# Sidebar Controls
st.sidebar.header("🕹️ Mission Control & Parameters")

grid_size = st.sidebar.slider("Terrain Grid Dimensions", min_value=50, max_value=200, value=GRID_SIZE, step=10)
max_slope = st.sidebar.slider("Max Traversable Slope (deg)", min_value=10.0, max_value=45.0, value=MAX_SLOPE, step=1.0)
terrain_seed = st.sidebar.number_input("Terrain Seed", min_value=0, max_value=9999, value=42)

st.sidebar.subheader("📍 Waypoint Coordinates")
col_s1, col_s2 = st.sidebar.columns(2)
start_r = col_s1.number_input("Start Row", min_value=0, max_value=grid_size - 1, value=START_POSITION[0])
start_c = col_s2.number_input("Start Col", min_value=0, max_value=grid_size - 1, value=START_POSITION[1])

col_g1, col_g2 = st.sidebar.columns(2)
goal_r = col_g1.number_input("Goal Row", min_value=0, max_value=grid_size - 1, value=min(GOAL_POSITION[0], grid_size - 1))
goal_c = col_g2.number_input("Goal Col", min_value=0, max_value=grid_size - 1, value=min(GOAL_POSITION[1], grid_size - 1))

run_sim = st.sidebar.button("🚀 Run Mission Simulation", use_container_width=True, type="primary")

# Compute / Cache Core Algorithms
@st.cache_data
def get_mission_state(size: int, seed: int, slope: float, start: tuple, goal: tuple):
    elevation = generate_terrain(grid_size=size, seed=seed)
    classified = classify_terrain(elevation, max_slope=slope)
    cost_map = generate_cost_map(elevation, max_slope=slope)
    path = find_path(cost_map, start=start, goal=goal)
    targets = rank_targets([], rover_pos=start)
    telemetry = simulate_rover(path, cost_map, initial_battery_wh=BATTERY_CAPACITY_WH)
    return elevation, classified, cost_map, path, targets, telemetry

elevation, classified, cost_map, path, targets, telemetry = get_mission_state(
    grid_size, terrain_seed, max_slope, (start_r, start_c), (goal_r, goal_c)
)

# Render Primary Telemetry Strip
render_mission_panel(telemetry)

# Tabs Layout
tab_map, tab_science, tab_nav, tab_arch = st.tabs([
    "🗺️ Surface Topography",
    "🔬 Science Operations",
    "🧭 Navigation Analysis",
    "📐 Architecture & Contracts"
])

with tab_map:
    map_fig = render_terrain_map(elevation, path=path, targets=targets)
    if map_fig is not None:
        st.plotly_chart(map_fig, use_container_width=True)
    else:
        st.warning("Plotly not installed. Please install plotly to view interactive surface maps.")

with tab_science:
    render_target_panel(targets)
    st.write("---")
    st.subheader("Sample Target Confidence Verification")
    sample_conf = calculate_confidence({"id": "SELECTED_SAMPLE"})
    st.progress(sample_conf, text=f"Spectrometric Confidence: {sample_conf * 100:.1f}%")

with tab_nav:
    st.subheader("Route Comparison & Feasibility")
    alt_path = [(r, c) for r, c in path if r % 2 == 0]
    comparison = compare_routes(cost_map, [path, alt_path], ["Primary Planned Route", "Alternative Route"])
    st.json(comparison)

with tab_arch:
    st.subheader("System Contracts & Module Division")
    st.markdown("""
    - **Teammate A (Terrain):** Implements fractal DEM generation & gradient cost calculation in `core/terrain.py`.
    - **Teammate B (Navigation):** Implements A* / Dijkstra graph search & rover dynamics in `core/navigation.py` and `core/simulation.py`.
    - **Teammate C (Science):** Implements multi-objective priority ranking & instrument telemetry in `core/science.py`.
    """)
''',
}


def main():
    print("🚀 Initializing ODYSSEY MARS-09 project setup...")

    # Create directories
    for directory in DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"  [DIR]  Created: {directory}")

    # Create files
    for file_path, content in FILES.items():
        file_path.write_text(content, encoding="utf-8")
        print(f"  [FILE] Created: {file_path}")

    print("\n✅ ODYSSEY MARS-09 foundational project structure successfully deployed!")
    print("   Run tests with: pytest ODYSSEY-MARS09/tests")
    print("   Run app with:   cd ODYSSEY-MARS09 && streamlit run app.py")


if __name__ == "__main__":
    main()
