"""UI Component: 2D/3D Plotly Terrain & Path Visualizer."""
from typing import List, Tuple, Any


def render_terrain_map(
    elevation: Any,
    path: List[Tuple[int, int]] = None,
    targets: List[dict] = None
):
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    fig = go.Figure(data=[
        go.Heatmap(
            z=elevation,
            colorscale="YlOrRd",
            colorbar=dict(title="Elevation (m)")
        )
    ])
    if path:
        pr, pc = zip(*path)
        fig.add_trace(go.Scatter(
            x=pc, y=pr,
            mode="lines+markers",
            line=dict(color="cyan", width=3),
            marker=dict(size=4),
            name="Planned Path"
        ))
    if targets:
        for t in targets:
            fig.add_trace(go.Scatter(
                x=[t["pos"][1]], y=[t["pos"][0]],
                mode="markers+text",
                marker=dict(size=12, color="lime", symbol="star"),
                text=[t["id"]],
                textposition="top center",
                name=t["id"]
            ))
    fig.update_layout(
        title="Martian Surface Topography & Trajectory",
        xaxis_title="Grid X",
        yaxis_title="Grid Y",
        yaxis=dict(autorange="reversed"),
        height=650,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig
