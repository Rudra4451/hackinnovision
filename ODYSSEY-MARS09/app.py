"""
ODYSSEY MARS-09: Streamlit Rover Mission Control Application
Autonomous Mars Rover Simulation — Lead Architect Interface
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
from components.mission_panel import render_mission_panel
from components.target_panel import render_target_panel

st.set_page_config(
    page_title="ODYSSEY MARS-09 Mission Control",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.title("🔴 MARS-09 ODYSSEY: Planetary Autonomy & Mission Control")
st.caption("Track A: Planetary Reconnaissance & Autonomous Navigation — Lead Architect Interface")

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
goal_r = c_g1.number_input("Goal Row", min_value=0, max_value=grid_size - 1, value=min(GOAL_POSITION[0], grid_size - 1))
goal_c = c_g2.number_input("Goal Col", min_value=0, max_value=grid_size - 1, value=min(GOAL_POSITION[1], grid_size - 1))

view_mode = st.sidebar.radio("Map Visualization Mode", ["2D Topography", "3D Surface"], index=0)

start_coords = (int(start_r), int(start_c))
goal_coords = (int(goal_r), int(goal_c))

# 1. Terrain Perception & Cost Map Generation
elevation = generate_terrain(grid_size=grid_size, seed=terrain_seed)
classified = classify_terrain(elevation, max_slope=max_slope)
cost_map = generate_cost_map(elevation, max_slope=max_slope)

# 2. Define Start and Goal Positions from core.config (or sidebar coordinates)
current_start = start_coords if (start_coords != START_POSITION) else START_POSITION
current_goal = goal_coords if (goal_coords != GOAL_POSITION) else GOAL_POSITION

# 3. Call compare_routes from core.navigation
res = compare_routes(cost_map, current_start, current_goal)

# Defensive validation of navigation payload
is_valid, error_msg = validate_navigation_payload(res)
if not is_valid:
    st.error(f"Navigation Payload Schema Error: {error_msg}")
    st.stop()

# 4. Graceful Fallback: Check if safest route was found
if not res["safest"]["route"]["success"]:
    st.error(f"🚨 Navigation Failure: {res['safest']['route']['reason']}")
    st.stop()

# 5. Extract Paths and Pass `res` to UI Components
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
tab_map, tab_nav, tab_science, tab_contracts = st.tabs([
    "🗺️ Topographical Reconnaissance",
    "🧭 Dual-Mode Route Analysis",
    "🔬 Science Target Queue",
    "📐 System Contracts & Architecture"
])

with tab_map:
    map_fig = render_terrain_map(
        elevation,
        path_safest=path_safest,
        path_shortest=path_shortest,
        targets=targets,
        view_mode=view_mode
    )
    if map_fig is not None:
        st.plotly_chart(map_fig, use_container_width=True)
    else:
        st.warning("Plotly required for interactive map rendering.")

with tab_nav:
    st.subheader("Dual-Mode A* Navigation & Trade-Off Matrix")
    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.markdown("#### ⚡ Shortest Route (Distance-Minimal)")
        m_short = res["shortest"]["metrics"]
        r_short = res["shortest"]["route"]
        st.write(f"- **Status:** `{'✅ FOUND' if r_short.get('success') else '❌ FAILED'}`")
        st.write(f"- **Distance:** `{m_short.get('total_distance', 0):.2f} m`")
        st.write(f"- **Total Cumulative Cost:** `{m_short.get('total_cost', 0):.2f}`")
        st.write(f"- **Caution Zone Steps:** `{m_short.get('caution_steps', 0)}`")

    with c_right:
        st.markdown("#### 🛡️ Safest Route (Risk-Averse)")
        m_safe = res["safest"]["metrics"]
        r_safe = res["safest"]["route"]
        st.write(f"- **Status:** `{'✅ FOUND' if r_safe.get('success') else '❌ FAILED'}`")
        st.write(f"- **Distance:** `{m_safe.get('total_distance', 0):.2f} m`")
        st.write(f"- **Total Cumulative Cost:** `{m_safe.get('total_cost', 0):.2f}`")
        st.write(f"- **Caution Zone Steps:** `{m_safe.get('caution_steps', 0)}`")

    st.write("---")
    st.info(f"**Tactical Recommendation:** {res['summary'].get('recommendation', 'N/A')}")
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

with tab_contracts:
    st.subheader("Architectural Module Ownership & Interface Contracts")
    st.markdown("""
    | Subsystem | Owner | Primary Module | Exported Contract |
    |---|---|---|---|
    | **Terrain Intelligence** | Member 2 | `core/terrain.py` | `cost_map` (2D float: `1.0` Safe, `[5, 20]` Caution, `inf` Hazard) |
    | **Autonomous Navigation** | Member 3 | `core/navigation.py` | 8-connected A* (`compare_routes`) returning `res` with shortest & safest routes |
    | **Science Intelligence** | Member 4 | `core/science.py` | Shannon entropy uncertainty & accessibility-gated operational scoring |
    | **Payload Validator** | Lead Architect | `utils/helpers.py` | `validate_navigation_payload` (guarantees schema integrity) |
    | **Mission Simulation** | Lead Architect | `core/simulation.py` | Rover kinematics, energy draw, and sol time progression |
    """)
