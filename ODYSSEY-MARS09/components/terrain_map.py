"""
UI Component: Interactive Terrain Cost Map and Trajectory Visualizer
Lead Integration Architect — ODYSSEY MARS-09
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
    Render 2D terrain cost map with start, goal, and dual-mode route traces.

    Parameters:
        cost_map: 2D array or list representing traversal costs:
                  1.0 = SAFE (light gray)
                  > 2.0 = CAUTION (yellow/orange)
                  np.inf = HAZARD (dark red)
        start: (row, col) start coordinates.
        goal: (row, col) goal coordinates.
        route_data: Output dictionary from core.navigation.compare_routes.

    Returns:
        plotly.graph_objects.Figure with square grid cells (scaleanchor="x").
    """
    # Convert cost_map to 2D numpy array for numeric processing
    if isinstance(cost_map, np.ndarray):
        grid = np.copy(cost_map)
    else:
        grid = np.array(cost_map, dtype=np.float64)

    # Map np.inf / impassable costs to a discrete ceiling for colorscale rendering
    HAZARD_CEILING = 25.0
    grid[np.isinf(grid) | (grid >= 1e9)] = HAZARD_CEILING

    # Custom colorscale:
    # 1.0 (SAFE) -> light gray
    # > 2.0 (CAUTION) -> yellow / orange
    # 25.0 (HAZARD) -> dark red
    cost_colorscale = [
        [0.0, "rgb(220, 220, 220)"],     # 1.0: SAFE - Light Gray
        [0.04, "rgb(220, 220, 220)"],    # 2.0: Caution threshold
        [0.05, "rgb(255, 235, 59)"],     # >2.0: Yellow
        [0.45, "rgb(255, 152, 0)"],      # Mid-caution: Orange
        [0.80, "rgb(230, 81, 0)"],       # High-caution: Deep Orange
        [1.0, "rgb(139, 0, 0)"],         # 25.0: HAZARD - Dark Red
    ]

    fig = go.Figure()

    # 1. 2D Heatmap of Cost Map
    fig.add_trace(go.Heatmap(
        z=grid,
        colorscale=cost_colorscale,
        zmin=1.0,
        zmax=HAZARD_CEILING,
        colorbar=dict(
            title="Terrain Cost",
            tickvals=[1.0, 5.0, 15.0, 25.0],
            ticktext=["1.0 (Safe)", "5.0 (Caution)", "15.0 (Caution)", "Hazard (Inf)"],
            len=0.75
        ),
        hovertemplate="Col (X): %{x}<br>Row (Y): %{y}<br>Cost: %{z:.1f}<extra></extra>"
    ))

    # 2. Dual-Mode Route Traces (if route_data is provided)
    if route_data and isinstance(route_data, dict):
        # Shortest Route: dashed gray line
        if "shortest" in route_data and "route" in route_data["shortest"]:
            short_route = route_data["shortest"]["route"]
            if short_route.get("x") and short_route.get("y"):
                fig.add_trace(go.Scatter(
                    x=short_route["x"],
                    y=short_route["y"],
                    mode="lines",
                    line=dict(color="#757575", width=2.5, dash="dash"),
                    name="Shortest Route"
                ))

        # Safest Route: thick, solid blue line
        if "safest" in route_data and "route" in route_data["safest"]:
            safe_route = route_data["safest"]["route"]
            if safe_route.get("x") and safe_route.get("y"):
                fig.add_trace(go.Scatter(
                    x=safe_route["x"],
                    y=safe_route["y"],
                    mode="lines",
                    line=dict(color="#1E88E5", width=4.5),
                    name="Safest Route"
                ))

    # Optional targets overlay if provided via kwargs
    targets = kwargs.get("targets")
    if targets:
        for t in targets:
            pos = t["pos"]
            status = t.get("status", "ACCESSIBLE")
            color = "#00E676" if status == "ACCESSIBLE" else "#D50000"
            fig.add_trace(go.Scatter(
                x=[pos[1]],
                y=[pos[0]],
                mode="markers+text",
                marker=dict(size=12, color=color, symbol="star-diamond"),
                text=[t["id"]],
                textposition="top center",
                name=t["id"],
                showlegend=False
            ))

    # 3. Start (Green Marker) and Goal (Red Marker)
    # Mapping (row, col) to Plotly (y, x)
    start_row, start_col = start
    goal_row, goal_col = goal

    fig.add_trace(go.Scatter(
        x=[start_col],
        y=[start_row],
        mode="markers+text",
        marker=dict(size=16, color="#00C853", symbol="circle", line=dict(color="black", width=2)),
        text=["START"],
        textposition="bottom center",
        name="Start",
        hovertemplate="Start Position<br>Row: %{y}<br>Col: %{x}<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=[goal_col],
        y=[goal_row],
        mode="markers+text",
        marker=dict(size=16, color="#D50000", symbol="circle", line=dict(color="black", width=2)),
        text=["GOAL"],
        textposition="bottom center",
        name="Goal",
        hovertemplate="Goal Position<br>Row: %{y}<br>Col: %{x}<extra></extra>"
    ))

    # 4. Layout configuration with square grid cells (scaleanchor="x")
    rows, cols = grid.shape
    fig.update_layout(
        title="MARS-09 Topographical Cost Map & Autonomous Trajectories",
        xaxis=dict(
            title="Column (Easting)",
            range=[-0.5, cols - 0.5],
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            title="Row (Northing)",
            scaleanchor="x",
            scaleratio=1,
            autorange="reversed",
            range=[rows - 0.5, -0.5],
            showgrid=True,
            zeroline=False
        ),
        height=700,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig
