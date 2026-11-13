"""
UI Component: Interactive Topography & Dual-Route Trajectory Visualizer
"""

from typing import List, Tuple, Any, Dict, Optional


def render_terrain_map(
    elevation: Any,
    path_safest: Optional[List[Tuple[int, int]]] = None,
    path_shortest: Optional[List[Tuple[int, int]]] = None,
    targets: Optional[List[Dict[str, Any]]] = None,
    view_mode: str = "2D Topography"
):
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    fig = go.Figure()

    if view_mode == "3D Surface":
        fig.add_trace(go.Surface(
            z=elevation,
            colorscale="Viridis",
            colorbar=dict(title="Elevation (m)", len=0.7)
        ))
    else:
        # 2D Heatmap with contour lines
        fig.add_trace(go.Heatmap(
            z=elevation,
            colorscale="YlOrRd",
            colorbar=dict(title="Elevation (m)", len=0.8),
            hoverinfo="z+x+y"
        ))

    # Safest Route Overlay (Gold)
    if path_safest:
        sr, sc = zip(*path_safest)
        fig.add_trace(go.Scatter(
            x=sc, y=sr,
            mode="lines+markers",
            line=dict(color="#FFD700", width=4),
            marker=dict(size=4, color="#FFD700"),
            name="Safest Route (Risk-Averse)"
        ))

    # Shortest Route Overlay (Cyan)
    if path_shortest:
        kr, kc = zip(*path_shortest)
        fig.add_trace(go.Scatter(
            x=kc, y=kr,
            mode="lines",
            line=dict(color="#00FFFF", width=2.5, dash="dot"),
            name="Shortest Route (Direct)"
        ))

    # Science Targets
    if targets:
        for t in targets:
            pos = t["pos"]
            status = t.get("status", "ACCESSIBLE")
            color = "#00FF66" if status == "ACCESSIBLE" else "#FF0055"
            fig.add_trace(go.Scatter(
                x=[pos[1]], y=[pos[0]],
                mode="markers+text",
                marker=dict(size=14, color=color, symbol="star-diamond"),
                text=[t["id"]],
                textposition="top center",
                hovertemplate=f"<b>{t['id']}</b><br>Type: {t.get('type', 'N/A')}<br>Priority: {t.get('composite_score', 0)}<extra></extra>",
                name=t["id"]
            ))

    fig.update_layout(
        title="MARS-09 Topographical Reconnaissance & Route Telemetry",
        xaxis_title="Easting (m)",
        yaxis_title="Northing (m)",
        yaxis=dict(autorange="reversed"),
        height=680,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig
