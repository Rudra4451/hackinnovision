"""
UI Component: Rover Telemetry, Mission Control Metrics & Terminal Mission Log
Lead Integration Architect — ODYSSEY MARS-09
"""

from typing import Dict, Any
import streamlit as st


def render_navigation_metrics(res: Dict[str, Any]):
    """
    Render NASA mission control style route comparison metrics.
    Handles edge case where shortest path is obstructed by hazards.

    Parameters:
        res: Standardized dictionary returned by core.navigation.compare_routes.
    """
    summary = res.get("summary", {})
    safest_route = res.get("safest", {}).get("route", {})
    shortest_route = res.get("shortest", {}).get("route", {})
    safest_success = safest_route.get("success", False)
    shortest_success = shortest_route.get("success", False)

    # Evaluate both_reachable
    both_reachable = summary.get("both_reachable", (safest_success and shortest_success))

    # Phase 4 Edge Case 3: Shortest obstructed by hazards, forcing safest route
    if not both_reachable and safest_success:
        st.warning("The shortest direct path was obstructed by infinite-cost hazards, forcing the rover to use the safest route.")

    # 1. Visually Striking Tactical Recommendation Banner
    recommendation = summary.get("recommendation", "Nominal trajectory calculated.")
    if "safest" in recommendation.lower():
        st.success(f"🛰️ **TACTICAL NAVIGATION DIRECTIVE:** {recommendation}")
    elif "abort" in recommendation.lower() or "failed" in recommendation.lower() or not safest_success:
        st.error(f"🚨 **MISSION ABORT DIRECTIVE:** {recommendation}")
    else:
        st.info(f"🛰️ **MISSION CONTROL ADVISORY:** {recommendation}")

    st.write("")

    # 2. Dual Route Telemetry Columns (Safest vs Shortest)
    col_safe, col_short = st.columns(2)

    with col_safe:
        st.markdown("### 🛡️ Safest Route (Risk-Averse)")
        safe_metrics = res.get("safest", {}).get("metrics", {})

        status_text = "🟢 TRAJECTORY NOMINAL" if safest_success else "🔴 UNREACHABLE"
        st.caption(f"Status: `{status_text}` | Algorithm: `8-Connected A* (Cost-Weighted)`")

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
        short_metrics = res.get("shortest", {}).get("metrics", {})

        status_text = "🟢 TRAJECTORY NOMINAL" if shortest_success else "🔴 OBSTRUCTED BY HAZARD"
        st.caption(f"Status: `{status_text}` | Algorithm: `8-Connected A* (Unit Distance)`")

        st.metric(
            label="Distance",
            value=f"{short_metrics.get('total_distance', 0.0):.2f} m" if shortest_success else "N/A",
            help="Direct physical path distance ignoring slope risk"
        )
        st.metric(
            label="Movement Cost",
            value=f"{short_metrics.get('total_cost', 0.0):.2f}" if shortest_success else "INF",
            help="Integrated movement cost without hazard diversion"
        )
        st.metric(
            label="Caution Steps",
            value=f"{short_metrics.get('caution_steps', 0)} cells" if shortest_success else "N/A",
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
        delta=f"+{dist_penalty:.1f}% vs Shortest" if shortest_success else "Forced Safe Route",
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


def render_mission_log(res: Dict[str, Any]):
    """
    Simulate a NASA mission control telemetry terminal log.
    Outputs dynamic log events styled with a black background and green monospace text.

    Parameters:
        res: Navigation payload from core.navigation.compare_routes.
    """
    summary = res.get("summary", {})
    safest_metrics = res.get("safest", {}).get("metrics", {})
    shortest_metrics = res.get("shortest", {}).get("metrics", {})
    safest_route = res.get("safest", {}).get("route", {})
    shortest_route = res.get("shortest", {}).get("route", {})

    both_reachable = summary.get("both_reachable", (
        safest_route.get("success", False) and shortest_route.get("success", False)
    ))

    # Dynamic log events incorporating Member 3 telemetry
    log_lines = [
        "[SYSTEM] Telemetry link: ACTIVE | Ground Station: Goldstone DSN (Sol 342)",
        "[SYSTEM] Digital Elevation Model ingested: 100x100 matrix resolution 1.0 m/cell",
        "[SYSTEM] A* Pathfinding complete.",
        f"[METRIC] Safest Traversal Distance : {safest_metrics.get('total_distance', 0.0):.2f} m",
        f"[METRIC] Shortest Baseline Distance: {shortest_metrics.get('total_distance', 0.0):.2f} m" if shortest_route.get("success") else "[METRIC] Shortest Baseline Distance: OBSTRUCTED (INF COST HAZARD)",
        f"[METRIC] Distance penalty accepted: {summary.get('distance_penalty_pct', 0.0)}%",
        f"[METRIC] Caution steps avoided: {summary.get('caution_steps_avoided', 0)}",
        f"[METRIC] Total cost reduction: {summary.get('cost_reduction_pct', 0.0)}%",
        f"[STATUS] Dual-mode reachability: {'BOTH REACHABLE' if both_reachable else 'SAFEST ONLY (SHORTEST PATH OBSTRUCTED)'}",
        f"[DECISION] {summary.get('recommendation', 'Nominal trajectory armed.')}",
        "[SYSTEM] Autopilot sequence armed. Telemetry stream nominal."
    ]

    log_content = "\n".join(log_lines)

    st.markdown("#### 📟 NASA Telemetry Console & Mission Log")
    st.markdown(
        f"""
        <div style="
            background-color: #000000;
            color: #00FF66;
            font-family: 'Courier New', Courier, monospace;
            padding: 20px;
            border-radius: 6px;
            border: 1px solid #1a3a2a;
            box-shadow: inset 0 0 15px rgba(0, 255, 102, 0.12), 0 4px 6px rgba(0, 0, 0, 0.4);
            font-size: 13.5px;
            line-height: 1.65;
            white-space: pre-wrap;
            letter-spacing: 0.5px;
        ">{log_content}</div>
        """,
        unsafe_allow_html=True
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
