"""UI Component: Mission Status & Telemetry Metrics."""
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
