"""
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
