"""
ODYSSEY MARS-09: Streamlit Rover Mission Control Application
Autonomous Mars Rover Simulation — Lead Architect Interface
Features Dynamic Click-to-Target Route Replanning via Plotly on_select events.
"""

import streamlit as st

# Core Engine Imports
from core.config import (
    GRID_SIZE,
    START_POSITION,
    GOAL_POSITION,
    MAX_SLOPE,
    OBSTACLE_COST,
    BATTERY_CAPACITY_WH
)
from core.terrain import generate_terrain, classify_terrain, generate_cost_map
from core.navigation import compare_routes
from core.science import rank_targets, calculate_confidence
from core.simulation import simulate_rover
from utils.helpers import validate_navigation_payload

# UI Visual Component Imports
from components.terrain_map import render_terrain_map
from components.mission_panel import render_mission_panel, render_navigation_metrics, render_mission_log
from components.target_panel import render_target_panel
from components.visionscore_panel import render_visionscore_panel

st.set_page_config(
    page_title="ODYSSEY MARS-09 Mission Control",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State for Interactive Goal Targeting
if "GOAL_POSITION" not in st.session_state:
    st.session_state.GOAL_POSITION = GOAL_POSITION

# Header
st.title("🔴 MARS-09 ODYSSEY: Autonomous Rover Mission Control")
st.caption("Planetary Reconnaissance & Autonomous Navigation — Lead Architect Interface")

# Sidebar Controls
st.sidebar.header("🕹️ Mission Control Parameters")

grid_size = st.sidebar.slider("Terrain Grid Dimensions (cells)", min_value=30, max_value=150, value=GRID_SIZE, step=10)
max_slope = st.sidebar.slider("Max Traversable Slope (°)", min_value=15.0, max_value=35.0, value=MAX_SLOPE, step=1.0)
terrain_seed = st.sidebar.number_input("Synthetic DEM Seed", min_value=0, max_value=99999, value=42)

st.sidebar.subheader("📍 Rover Waypoints (Row, Col)")
c_s1, c_s2 = st.sidebar.columns(2)
start_r = c_s1.number_input("Start Row", min_value=0, max_value=grid_size - 1, value=START_POSITION[0])
start_c = c_s2.number_input("Start Col", min_value=0, max_value=grid_size - 1, value=START_POSITION[1])

c_g1, c_g2 = st.sidebar.columns(2)
goal_r = c_g1.number_input(
    "Goal Row",
    min_value=0,
    max_value=grid_size - 1,
    value=min(int(st.session_state.GOAL_POSITION[0]), grid_size - 1)
)
goal_c = c_g2.number_input(
    "Goal Col",
    min_value=0,
    max_value=grid_size - 1,
    value=min(int(st.session_state.GOAL_POSITION[1]), grid_size - 1)
)

# Synchronize session state if user manually altered sidebar number inputs
if (int(goal_r), int(goal_c)) != st.session_state.GOAL_POSITION:
    st.session_state.GOAL_POSITION = (int(goal_r), int(goal_c))

current_start = (int(start_r), int(start_c))
current_goal = st.session_state.GOAL_POSITION

# 1. Terrain Perception & Cost Map Generation
elevation = generate_terrain(grid_size=grid_size, seed=terrain_seed)
classified = classify_terrain(elevation, max_slope=max_slope)
cost_map = generate_cost_map(elevation, max_slope=max_slope)

# 2. Call compare_routes from core.navigation
res = compare_routes(cost_map, current_start, current_goal)

# Defensive validation of navigation payload
is_valid, error_msg = validate_navigation_payload(res)
if not is_valid:
    st.error(f"Navigation Payload Schema Error: {error_msg}")
    st.stop()

# 3. Edge Case Evaluation
safest_success = res["safest"]["route"]["success"]
both_reachable = res["summary"].get(
    "both_reachable",
    (safest_success and res["shortest"]["route"]["success"])
)

# If safest route fails: block route rendering, display critical error, and let user click to recover
if not safest_success:
    st.error(res["safest"]["route"]["reason"])
    st.caption("💡 *Selectable Map: Click on any clear terrain point below to replan to a safe target.*")
    bare_map = render_terrain_map(cost_map, current_start, current_goal, route_data=None)
    event = st.plotly_chart(
        bare_map,
        use_container_width=True,
        on_select="rerun"
    )
    if event and "selection" in event and event["selection"].get("points"):
        selected = event["selection"]["points"][0]
        cx, cy = selected.get("x"), selected.get("y")
        if cx is not None and cy is not None:
            new_g = (max(0, min(int(round(cy)), grid_size - 1)), max(0, min(int(round(cx)), grid_size - 1)))
            if new_g != st.session_state.GOAL_POSITION:
                st.session_state.GOAL_POSITION = new_g
                st.rerun()
    st.stop()

# 4. Extract Paths and Pass `res` to UI Components
path_safest = res["safest"]["route"]["path"]
path_shortest = res["shortest"]["route"]["path"]

# Science Target Intelligence
targets = rank_targets([], rover_pos=current_start, cost_map=cost_map)

# Rover Dynamics Simulation along Safest Path
telemetry = simulate_rover(path_safest, cost_map, initial_battery_wh=BATTERY_CAPACITY_WH)

# Render Primary Telemetry Bar
render_mission_panel(telemetry, res)

st.write("")

# Tabs Interface
tab_map, tab_nav, tab_science, tab_visionscore, tab_contracts = st.tabs([
    "🗺️ Satellite Reconnaissance Feed",
    "🧭 Dual-Mode Route Telemetry",
    "🔬 Science Target Operations",
    "👁️ VisionScore 2.0 & Obstacle Alerts",
    "📐 System Architecture & Contracts"
])

with tab_map:
    st.caption("🎯 **Interactive Targeting Enabled:** Click anywhere on the terrain feed to dynamically re-aim the rover's goal coordinate.")
    map_fig = render_terrain_map(
        cost_map=cost_map,
        start=current_start,
        goal=current_goal,
        route_data=res,
        targets=targets
    )
    if map_fig is not None:
        # Native Streamlit Plotly Selection Event: on_select='rerun'
        event = st.plotly_chart(
            map_fig,
            use_container_width=True,
            on_select="rerun"
        )

        # Capture clicked coordinate and recalculate route dynamically
        if event and "selection" in event and event["selection"].get("points"):
            clicked_point = event["selection"]["points"][0]
            clicked_x = clicked_point.get("x")
            clicked_y = clicked_point.get("y")

            if clicked_x is not None and clicked_y is not None:
                # Map Plotly (x, y) where x=col, y=row back to matrix (row, col)
                new_goal = (
                    max(0, min(int(round(clicked_y)), grid_size - 1)),
                    max(0, min(int(round(clicked_x)), grid_size - 1))
                )

                if new_goal != st.session_state.GOAL_POSITION:
                    st.session_state.GOAL_POSITION = new_goal
                    st.rerun()
    else:
        st.warning("Plotly required for interactive map rendering.")

with tab_nav:
    render_navigation_metrics(res)
    st.write("---")
    render_mission_log(res)
    st.write("---")
    with st.expander("🔍 Raw Telemetry JSON Payload"):
        st.json(res)

with tab_science:
    render_target_panel(targets)
    st.write("---")
    st.subheader("Spectrometer Confidence & Biosignature Verification")
    if targets:
        top_target = targets[0]
        conf = top_target.get("confidence", 0.85)
        st.markdown(f"**Top Ranked Candidate:** `{top_target['id']}` ({top_target.get('type')})")
        st.progress(conf, text=f"Spectrometric Confidence Score: {conf * 100:.1f}%")

with tab_visionscore:
    render_visionscore_panel()

with tab_contracts:
    st.subheader("Architectural Module Ownership & Interface Contracts")
    st.markdown("""
    | Subsystem | Owner | Primary Module | Exported Contract |
    |---|---|---|---|
    | **Terrain Intelligence** | Member 2 | `core/terrain.py` | `cost_map` (2D float: `1.0` Safe, `[5, 20]` Caution, `inf` Hazard) |
    | **Autonomous Navigation** | Member 3 | `core/navigation.py` | 8-connected A* (`compare_routes`) returning `res` with shortest & safest routes |
    | **Interactive Map** | Lead Architect | `components/terrain_map.py` | Native Plotly `on_select='rerun'` click-to-target trajectory recalculator |
    | **Science Intelligence** | Member 4 | `core/science.py` | Shannon entropy uncertainty & accessibility-gated operational scoring |
    | **Payload Validator** | Lead Architect | `utils/helpers.py` | `validate_navigation_payload` (guarantees schema integrity) |
    | **Mission Simulation** | Lead Architect | `core/simulation.py` | Rover kinematics, energy draw, and sol time progression |
    """)
