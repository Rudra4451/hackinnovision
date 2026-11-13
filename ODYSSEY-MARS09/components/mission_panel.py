"""
UI Component: Rover Telemetry, Power & Mission Status Dashboard
"""

from typing import Dict, Any


def render_mission_panel(telemetry: Dict[str, Any], comparison: Dict[str, Any] = None):
    import streamlit as st

    st.subheader("🛰️ Rover Real-Time Telemetry & Systems Status")

    c1, c2, c3, c4 = st.columns(4)

    status = telemetry.get("status", "NOMINAL")
    if status == "GOAL_REACHED":
        status_label = "🟢 GOAL REACHED"
    elif status == "OBSTACLE_COLLISION":
        status_label = "🔴 OBSTACLE HAZARD"
    elif status == "BATTERY_DEPLETED":
        status_label = "⚠️ POWER DEPLETED"
    else:
        status_label = f"🔵 {status}"

    c1.metric("Mission Status", status_label)
    c2.metric("Waypoints Traversed", telemetry.get("steps_completed", 0))

    battery = telemetry.get("battery_levels", [100.0])[-1]
    c3.metric("Battery Remaining", f"{battery:.1f} Wh", delta=f"-{(1200.0 - battery):.1f} Wh used")

    sol_pct = telemetry.get("sol_fraction", 0.0) * 100.0
    c4.metric("Sol Traversal Time", f"{telemetry.get('time_elapsed_s', 0):.0f}s", f"{sol_pct:.1f}% of Sol")
