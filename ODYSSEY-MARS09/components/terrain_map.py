"""
UI Component: Satellite Feed Terrain Map & Autonomous Route Visualizer
Lead Integration Architect — ODYSSEY MARS-09
Visual Polish: Clean dark satellite feed styling (plotly_dark) with square grid cells.
"""

from typing import Tuple, Dict, Any, Optional
import numpy as np
import plotly.graph_objects as go


def render_terrain_map(
    cost_map: Any,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    route_data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> go.Figure:
    """
    Render satellite-feed style 2D terrain cost map with start/goal beacons
    and high-contrast dual-mode route trajectories.

    Parameters:
        cost_map: 2D array or list representing traversal costs:
                  1.0 = SAFE (light gray)
                  > 2.0 = CAUTION (yellow/orange)
                  np.inf = HAZARD (dark red)
        start: (row, col) start coordinates.
        goal: (row, col) goal coordinates.
        route_data: Output dictionary from core.navigation.compare_routes.

    Returns:
        plotly.graph_objects.Figure styled as a clean dark satellite feed.
    """
    if isinstance(cost_map, np.ndarray):
        grid = np.copy(cost_map)
    else:
        grid = np.array(cost_map, dtype=np.float64)

    # Ceiling for infinite hazard cost visualization
    HAZARD_CEILING = 25.0
    grid[np.isinf(grid) | (grid >= 1e9)] = HAZARD_CEILING

    # Custom satellite feed palette:
    # 1.0 (SAFE) = light gray
    # > 2.0 (CAUTION) = yellow / orange
    # 25.0 (HAZARD) = dark red
    cost_colorscale = [
        [0.0, "rgb(215, 215, 215)"],     # 1.0: SAFE - Light Gray
        [0.04, "rgb(215, 215, 215)"],    # 2.0: Threshold
        [0.05, "rgb(255, 235, 59)"],     # >2.0: Caution - Yellow
        [0.45, "rgb(255, 152, 0)"],      # Mid-caution: Orange
        [0.80, "rgb(230, 81, 0)"],       # High-caution: Deep Orange
        [1.0, "rgb(139, 0, 0)"],         # 25.0: HAZARD - Dark Red
    ]

    fig = go.Figure()

    # 1. 2D Heatmap (Clean Satellite Feed)
    fig.add_trace(go.Heatmap(
        z=grid,
        colorscale=cost_colorscale,
        zmin=1.0,
        zmax=HAZARD_CEILING,
        colorbar=dict(
            title=dict(text="Cost", side="top", font=dict(color="#00E5FF", size=12)),
            tickvals=[1.0, 5.0, 15.0, 25.0],
            ticktext=["1.0 Safe", "5.0 Caution", "15.0 Caution", "Hazard (Inf)"],
            tickfont=dict(color="#B0BEC5", size=10),
            len=0.75,
            thickness=15
        ),
        hovertemplate="Northing: %{y}<br>Easting: %{x}<br>Cost: %{z:.1f}<extra></extra>"
    ))

    # 2. Route Traces (Only render if route_data is valid and successful)
    if route_data and isinstance(route_data, dict):
        safest_info = route_data.get("safest", {}).get("route", {})
        shortest_info = route_data.get("shortest", {}).get("route", {})

        # Check if safest was successful (Task 1: if false, route rendering is blocked)
        if safest_info.get("success", False):
            # Shortest Route: Rejected baseline (dark gray, dotted, width=2)
            if shortest_info.get("success", False) and shortest_info.get("x") and shortest_info.get("y"):
                fig.add_trace(go.Scatter(
                    x=shortest_info["x"],
                    y=shortest_info["y"],
                    mode="lines",
                    line=dict(color="#555555", width=2, dash="dot"),
                    name="Shortest Route (Rejected Baseline)",
                    hoverinfo="skip"
                ))

            # Safest Route: Visually dominant (cyan/blue with width=4)
            if safest_info.get("x") and safest_info.get("y"):
                fig.add_trace(go.Scatter(
                    x=safest_info["x"],
                    y=safest_info["y"],
                    mode="lines",
                    line=dict(color="#00E5FF", width=4),
                    name="Safest Route (Tactical Path)",
                    hoverinfo="name"
                ))

    # 3. Optional Science Targets
    targets = kwargs.get("targets")
    if targets:
        for t in targets:
            pos = t["pos"]
            status = t.get("status", "ACCESSIBLE")
            color = "#00FF66" if status == "ACCESSIBLE" else "#FF0055"
            fig.add_trace(go.Scatter(
                x=[pos[1]],
                y=[pos[0]],
                mode="markers+text",
                marker=dict(size=11, color=color, symbol="star-diamond"),
                text=[t["id"]],
                textposition="top center",
                textfont=dict(size=9, color="#E0E0E0"),
                name=t["id"],
                showlegend=False
            ))

    # 4. Start (Green Marker) and Goal (Red Marker)
    # Mapping (row, col) matrix indices to Plotly (y, x)
    start_row, start_col = start
    goal_row, goal_col = goal

    fig.add_trace(go.Scatter(
        x=[start_col],
        y=[start_row],
        mode="markers+text",
        marker=dict(size=17, color="#00E676", symbol="circle", line=dict(color="#003300", width=2)),
        text=["START"],
        textposition="bottom center",
        textfont=dict(color="#00E676", size=11, family="Courier New"),
        name="Start Beacon",
        hovertemplate="START<br>Row: %{y}<br>Col: %{x}<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=[goal_col],
        y=[goal_row],
        mode="markers+text",
        marker=dict(size=17, color="#FF1744", symbol="star", line=dict(color="#4A0000", width=2)),
        text=["GOAL"],
        textposition="bottom center",
        textfont=dict(color="#FF1744", size=11, family="Courier New"),
        name="Goal Target",
        hovertemplate="GOAL<br>Row: %{y}<br>Col: %{x}<extra></extra>"
    ))

    # 5. Dark Satellite Feed Layout: plotly_dark with stripped axes grids, ticks & labels
    rows, cols = grid.shape
    fig.update_layout(
        template="plotly_dark",
        clickmode="event+select",
        title=dict(
            text="📡 SATELLITE RECONNAISSANCE: TERRAIN COST & AUTONOMOUS TRAJECTORY FEED",
            font=dict(size=14, color="#E0E0E0", family="Courier New")
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            ticks="",
            title="",
            range=[-0.5, cols - 0.5]
        ),
        yaxis=dict(
            scaleanchor="x",
            scaleratio=1,
            autorange="reversed",
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            ticks="",
            title="",
            range=[rows - 0.5, -0.5]
        ),
        height=720,
        margin=dict(l=15, r=15, t=55, b=15),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color="#B0BEC5")
        )
    )

    return fig
