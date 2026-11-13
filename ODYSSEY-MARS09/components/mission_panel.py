"""
UI Component: Rover Telemetry, Power & Mission Status Dashboard
Lead Integration Architect — ODYSSEY MARS-09
"""

from typing import Dict, Any
import streamlit as st


def render_navigation_metrics(res: Dict[str, Any]):
    """
    Render NASA mission control style route comparison metrics.

    Parameters:
        res: Standardized dictionary returned by core.navigation.compare_routes.
    """
    # 1. Visually Striking Tactical Recommendation Banner
    summary = res.get("summary", {})
    recommendation = summary.get("recommendation", "Nominal trajectory calculated.")

    if "safest" in recommendation.lower():
        st.success(f"🛰️ **TACTICAL NAVIGATION DIRECTIVE:** {recommendation}")
    elif "abort" in recommendation.lower() or "failed" in recommendation.lower():
        st.error(f"🚨 **MISSION ABORT DIRECTIVE:** {recommendation}")
    else:
        st.info(f"🛰️ **MISSION CONTROL ADVISORY:** {recommendation}")

    st.write("")

    # 2. Dual Route Telemetry Columns (Safest vs Shortest)
    col_safe, col_short = st.columns(2)

    with col_safe:
        st.markdown("### 🛡️ Safest Route (Risk-Averse)")
        safe_route = res.get("safest", {}).get("route", {})
        safe_metrics = res.get("safest", {}).get("metrics", {})

        status_text = "🟢 TRAJECTORY NOMINAL" if safe_route.get("success") else "🔴 UNREACHABLE"
        st.caption(f"Status: `{status_text}` | Algorithm: `8-Connected A* (Weighted)`")

        # Metrics display
        st.metric(
            label="Distance",
            value=f"{safe_metrics.get('total_distance', 0.0):.2f} m",
            help="Total physical Euclidean distance traversed over the terrain"
        )
        st.metric(
            label="Movement Cost",
            value=f"{safe_metrics.get('total_cost', 0.0):.2f}",
            help="Cumulative terrain cost including gradient slope resistance"
        )
        st.metric(
            label="Caution Steps",
            value=f"{safe_metrics.get('caution_steps', 0)} cells",
            help="Number of waypoints intersecting high-slope caution zones (12° - 30°)"
        )

    with col_short:
        st.markdown("### ⚡ Shortest Route (Distance-Minimal)")
        short_route = res.get("shortest", {}).get("route", {})
        short_metrics = res.get("shortest", {}).get("metrics", {})

        status_text = "🟢 TRAJECTORY NOMINAL" if short_route.get("success") else "🔴 UNREACHABLE"
        st.caption(f"Status: `{status_text}` | Algorithm: `8-Connected A* (Unit Cost)`")

        # Metrics display
        st.metric(
            label="Distance",
            value=f"{short_metrics.get('total_distance', 0.0):.2f} m",
            help="Direct physical path distance ignoring slope risk"
        )
        st.metric(
            label="Movement Cost",
            value=f"{short_metrics.get('total_cost', 0.0):.2f}",
            help="Integrated movement cost without hazard diversion"
        )
        st.metric(
            label="Caution Steps",
            value=f"{short_metrics.get('caution_steps', 0)} cells",
            help="Number of waypoints intersecting high-slope caution zones"
        )

    # 3. Comparison Summary Readout
    st.markdown("---")
    st.markdown("#### 📊 Route Trade-Off & Telemetry Synthesis")

    dist_penalty = summary.get("distance_penalty_pct", 0.0)
    caution_avoided = summary.get("caution_steps_avoided", 0)

    c_sum1, c_sum2 = st.columns(2)
    c_sum1.metric(
        label="Distance Detour Penalty",
        value=f"{dist_penalty:.1f}%",
        delta=f"+{dist_penalty:.1f}% vs Shortest",
        delta_color="inverse",
        help="Extra ground distance required to avoid terrain rollover risks"
    )
    c_sum2.metric(
        label="Caution Steps Avoided",
        value=f"{caution_avoided} steps",
        delta=f"-{caution_avoided} caution cells" if caution_avoided > 0 else "0",
        delta_color="normal",
        help="High-slope cells successfully avoided to preserve rover chassis integrity"
    )


def render_mission_panel(telemetry: Dict[str, Any], comparison: Dict[str, Any] = None):
    """
    Render top-level rover health, battery, and sol timing strip.
    """
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
