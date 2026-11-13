"""Visualization module for Odyssey Terrain Intelligence.

Notice:
    ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC AND SIMULATED.
    IT DOES NOT REPRESENT ACTUAL IN-SITU MARS TELEMETRY OR RECONNAISSANCE MEASUREMENTS.
"""

from pathlib import Path
from typing import Optional, Union
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless execution
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import plotly.graph_objects as go

from terrain_intelligence.config import SIMULATION_NOTICE, TerrainClass


class TerrainVisualizer:
    """Generates 2D publication heatmaps and interactive 3D visualizations."""

    def __init__(self, output_dir: Union[str, Path] = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plot_elevation(
        self,
        elevation: np.ndarray,
        resolution_m: float = 1.0,
        save_path: Optional[str] = None,
    ) -> Path:
        """Renders and saves a 2D elevation heatmap with contour lines."""
        path = Path(save_path) if save_path else self.output_dir / "elevation_heatmap.png"
        fig, ax = plt.subplots(figsize=(8, 7), dpi=150)

        im = ax.imshow(
            elevation,
            cmap="terrain",
            origin="lower",
            extent=[0, elevation.shape[1] * resolution_m, 0, elevation.shape[0] * resolution_m],
        )
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Elevation (m)", rotation=270, labelpad=15)

        # Add elevation contour lines
        contours = ax.contour(
            elevation,
            levels=10,
            colors="black",
            alpha=0.35,
            linewidths=0.75,
            extent=[0, elevation.shape[1] * resolution_m, 0, elevation.shape[0] * resolution_m],
        )
        ax.clabel(contours, inline=True, fontsize=7, fmt="%.1f")

        ax.set_title("Martian Synthetic Elevation Field (DEM)", fontsize=13, fontweight="bold")
        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")
        fig.text(0.5, 0.01, f"[!] {SIMULATION_NOTICE}", ha="center", fontsize=7, color="gray")

        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_slope(
        self,
        slope_deg: np.ndarray,
        caution_thresh: float = 12.0,
        hazard_thresh: float = 20.0,
        save_path: Optional[str] = None,
    ) -> Path:
        """Renders and saves a 2D slope angle heatmap with hazard contour boundaries."""
        path = Path(save_path) if save_path else self.output_dir / "slope_heatmap.png"
        fig, ax = plt.subplots(figsize=(8, 7), dpi=150)

        im = ax.imshow(slope_deg, cmap="magma", origin="lower", vmin=0, vmax=max(35, float(np.max(slope_deg))))
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Slope Angle (degrees)", rotation=270, labelpad=15)

        # Draw contour lines for caution and hazard limits
        ax.contour(slope_deg, levels=[caution_thresh], colors=["yellow"], linewidths=1.2, linestyles="--")
        ax.contour(slope_deg, levels=[hazard_thresh], colors=["red"], linewidths=1.5, linestyles="-")

        ax.set_title(f"Terrain Slope (°)\n[Caution: >{caution_thresh}°, Hazard: >{hazard_thresh}°]", fontsize=12, fontweight="bold")
        ax.set_xlabel("X (cells)")
        ax.set_ylabel("Y (cells)")
        fig.text(0.5, 0.01, f"[!] {SIMULATION_NOTICE}", ha="center", fontsize=7, color="gray")

        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_obstacles(
        self,
        obstacle_mask: np.ndarray,
        obstacle_density: Optional[np.ndarray] = None,
        save_path: Optional[str] = None,
    ) -> Path:
        """Renders and saves an obstacle map showing density and discrete rock clusters."""
        path = Path(save_path) if save_path else self.output_dir / "obstacle_map.png"
        fig, ax = plt.subplots(figsize=(8, 7), dpi=150)

        if obstacle_density is not None:
            im = ax.imshow(obstacle_density, cmap="copper", origin="lower", alpha=0.85)
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label("Rock Spatial Density [0.0 - 1.0]", rotation=270, labelpad=15)
        else:
            im = ax.imshow(np.zeros_like(obstacle_mask, dtype=float), cmap="gray", origin="lower")

        # Overlay discrete obstacles in bright crimson
        obs_overlay = np.ma.masked_where(~obstacle_mask, obstacle_mask)
        ax.imshow(obs_overlay, cmap=ListedColormap(["#ff2222"]), origin="lower", alpha=0.95)

        ax.set_title("Obstacle Detection & Boulder Clusters\n(Crimson = Impassable Boulders)", fontsize=12, fontweight="bold")
        ax.set_xlabel("X (cells)")
        ax.set_ylabel("Y (cells)")
        fig.text(0.5, 0.01, f"[!] {SIMULATION_NOTICE}", ha="center", fontsize=7, color="gray")

        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_classification(
        self,
        classification_map: np.ndarray,
        save_path: Optional[str] = None,
    ) -> Path:
        """Renders and saves a discrete 3-tier terrain classification map (SAFE, CAUTION, HAZARD)."""
        path = Path(save_path) if save_path else self.output_dir / "terrain_classification_map.png"
        fig, ax = plt.subplots(figsize=(8, 7), dpi=150)

        # Discrete colormap: SAFE (#2ecc71), CAUTION (#f39c12), HAZARD (#e74c3c)
        cmap = ListedColormap(["#2ecc71", "#f39c12", "#e74c3c"])
        bounds = [-0.5, 0.5, 1.5, 2.5]
        norm = BoundaryNorm(bounds, cmap.N)

        im = ax.imshow(classification_map, cmap=cmap, norm=norm, origin="lower")

        cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2], fraction=0.046, pad=0.04)
        cbar.ax.set_yticklabels(["SAFE (0)", "CAUTION (1)", "HAZARD (2)"])

        # Annotate percentages
        total = classification_map.size
        s_pct = 100.0 * np.count_nonzero(classification_map == int(TerrainClass.SAFE)) / total
        c_pct = 100.0 * np.count_nonzero(classification_map == int(TerrainClass.CAUTION)) / total
        h_pct = 100.0 * np.count_nonzero(classification_map == int(TerrainClass.HAZARD)) / total

        ax.set_title(
            f"Terrain Traversability Classification\n"
            f"[Safe: {s_pct:.1f}% | Caution: {c_pct:.1f}% | Hazard: {h_pct:.1f}%]",
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel("X (cells)")
        ax.set_ylabel("Y (cells)")
        fig.text(0.5, 0.01, f"[!] {SIMULATION_NOTICE}", ha="center", fontsize=7, color="gray")

        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_cost_map(
        self,
        cost_map: np.ndarray,
        save_path: Optional[str] = None,
    ) -> Path:
        """Renders and saves the movement cost map with impassable infinity cells highlighted."""
        path = Path(save_path) if save_path else self.output_dir / "movement_cost_map.png"
        fig, ax = plt.subplots(figsize=(8, 7), dpi=150)

        # Mask inf cells for colorbar normalization
        finite_mask = np.isfinite(cost_map)
        masked_cost = np.ma.masked_where(~finite_mask, cost_map)

        # Plot navigable finite costs
        try:
            cmap = plt.cm.viridis.with_extremes(bad="#1a1a1a")
        except AttributeError:
            cmap = plt.cm.viridis.copy()
            cmap.set_bad(color="#1a1a1a")  # Fallback for older matplotlib

        im = ax.imshow(masked_cost, cmap=cmap, origin="lower")
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Traversal Cost Factor (Arbitrary Units)", rotation=270, labelpad=15)

        # Overlay impassable cells with red hatch
        impassable_overlay = np.ma.masked_where(finite_mask, np.ones_like(cost_map))
        ax.imshow(impassable_overlay, cmap=ListedColormap(["#262626"]), origin="lower")

        impass_pct = 100.0 * np.count_nonzero(~finite_mask) / cost_map.size
        ax.set_title(f"Movement Cost Map\n(Dark = Impassable / Cost=∞: {impass_pct:.1f}%)", fontsize=12, fontweight="bold")
        ax.set_xlabel("X (cells)")
        ax.set_ylabel("Y (cells)")
        fig.text(0.5, 0.01, f"[!] {SIMULATION_NOTICE}", ha="center", fontsize=7, color="gray")

        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_uncertainty(
        self,
        uncertainty_map: np.ndarray,
        sensor_origin: Optional[tuple[int, int]] = None,
        save_path: Optional[str] = None,
    ) -> Path:
        """Renders and saves the simulated terrain uncertainty map."""
        path = Path(save_path) if save_path else self.output_dir / "uncertainty_map.png"
        fig, ax = plt.subplots(figsize=(8, 7), dpi=150)

        im = ax.imshow(uncertainty_map, cmap="plasma", origin="lower", vmin=0.0, vmax=1.0)
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Uncertainty Metric [0.0 = Known, 1.0 = Unknown]", rotation=270, labelpad=15)

        if sensor_origin:
            ax.plot(sensor_origin[1], sensor_origin[0], "c*", markersize=14, label="Sensor / Rover Origin")
            ax.legend(loc="upper right", fontsize=8)

        ax.set_title("Perceptual Terrain Uncertainty Field", fontsize=12, fontweight="bold")
        ax.set_xlabel("X (cells)")
        ax.set_ylabel("Y (cells)")
        fig.text(0.5, 0.01, f"[!] {SIMULATION_NOTICE}", ha="center", fontsize=7, color="gray")

        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_dashboard(
        self,
        elevation: np.ndarray,
        slope_deg: np.ndarray,
        obstacle_mask: np.ndarray,
        obstacle_density: np.ndarray,
        classification_map: np.ndarray,
        cost_map: np.ndarray,
        uncertainty_map: np.ndarray,
        save_path: Optional[str] = None,
    ) -> Path:
        """Creates a comprehensive 6-panel engineering dashboard summarizing all terrain layers."""
        path = Path(save_path) if save_path else self.output_dir / "terrain_intelligence_dashboard.png"
        fig, axes = plt.subplots(2, 3, figsize=(18, 11), dpi=150)

        # Panel 1: Elevation
        im1 = axes[0, 0].imshow(elevation, cmap="terrain", origin="lower")
        axes[0, 0].set_title("1. Elevation (m)", fontweight="bold")
        fig.colorbar(im1, ax=axes[0, 0], fraction=0.046, pad=0.04)

        # Panel 2: Slope
        im2 = axes[0, 1].imshow(slope_deg, cmap="magma", origin="lower")
        axes[0, 1].set_title("2. Slope Angle (°)", fontweight="bold")
        fig.colorbar(im2, ax=axes[0, 1], fraction=0.046, pad=0.04)

        # Panel 3: Obstacles
        axes[0, 2].imshow(obstacle_density, cmap="copper", origin="lower")
        obs_ov = np.ma.masked_where(~obstacle_mask, obstacle_mask)
        axes[0, 2].imshow(obs_ov, cmap=ListedColormap(["#ff2222"]), origin="lower")
        axes[0, 2].set_title("3. Obstacles (Red = Rocks)", fontweight="bold")

        # Panel 4: Classification
        cmap_cls = ListedColormap(["#2ecc71", "#f39c12", "#e74c3c"])
        norm_cls = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap_cls.N)
        im4 = axes[1, 0].imshow(classification_map, cmap=cmap_cls, norm=norm_cls, origin="lower")
        axes[1, 0].set_title("4. Classification (Safe/Caution/Hazard)", fontweight="bold")
        cbar4 = fig.colorbar(im4, ax=axes[1, 0], ticks=[0, 1, 2], fraction=0.046, pad=0.04)
        cbar4.ax.set_yticklabels(["Safe", "Caution", "Hazard"])

        # Panel 5: Movement Cost Map
        finite_mask = np.isfinite(cost_map)
        masked_c = np.ma.masked_where(~finite_mask, cost_map)
        im5 = axes[1, 1].imshow(masked_c, cmap="viridis", origin="lower")
        impass_ov = np.ma.masked_where(finite_mask, np.ones_like(cost_map))
        axes[1, 1].imshow(impass_ov, cmap=ListedColormap(["#1a1a1a"]), origin="lower")
        axes[1, 1].set_title("5. Traversal Cost (Dark = ∞)", fontweight="bold")
        fig.colorbar(im5, ax=axes[1, 1], fraction=0.046, pad=0.04)

        # Panel 6: Uncertainty
        im6 = axes[1, 2].imshow(uncertainty_map, cmap="plasma", origin="lower", vmin=0, vmax=1)
        axes[1, 2].set_title("6. Perceptual Uncertainty", fontweight="bold")
        fig.colorbar(im6, ax=axes[1, 2], fraction=0.046, pad=0.04)

        for ax in axes.flat:
            ax.set_xlabel("X (cells)", fontsize=8)
            ax.set_ylabel("Y (cells)", fontsize=8)

        fig.suptitle(
            "ODYSSEY TERRAIN INTELLIGENCE - PLANETARY RECONNAISSANCE SUITE\n"
            f"[!] {SIMULATION_NOTICE}",
            fontsize=13,
            fontweight="bold",
            y=0.99,
        )

        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def create_3d_interactive(
        self,
        elevation: np.ndarray,
        surface_color: Optional[np.ndarray] = None,
        color_label: str = "Elevation (m)",
        save_path: Optional[str] = None,
    ) -> Path:
        """Builds an interactive Plotly 3D surface mesh and exports as standalone HTML."""
        path = Path(save_path) if save_path else self.output_dir / "terrain_3d.html"
        rows, cols = elevation.shape

        xx, yy = np.meshgrid(np.arange(cols), np.arange(rows))
        color_data = surface_color if surface_color is not None else elevation

        surface = go.Surface(
            x=xx,
            y=yy,
            z=elevation,
            surfacecolor=color_data,
            colorscale="Earth",
            colorbar=dict(title=color_label),
            lighting=dict(ambient=0.4, diffuse=0.6, roughness=0.5, specular=0.2),
        )

        fig = go.Figure(data=[surface])
        fig.update_layout(
            title=dict(
                text="Odyssey Terrain Intelligence - 3D Martian Surface Model<br>"
                     "<sub>Interactive DEM (Click and drag to rotate / scroll to zoom) | "
                     "Simulated Martian Topography</sub>",
                x=0.5,
            ),
            scene=dict(
                xaxis_title="Easting X (m)",
                yaxis_title="Northing Y (m)",
                zaxis_title="Elevation Z (m)",
                aspectmode="manual",
                aspectratio=dict(x=1.0, y=1.0, z=0.35),
                camera=dict(
                    eye=dict(x=1.4, y=-1.5, z=0.9)
                ),
            ),
            margin=dict(l=0, r=0, b=0, t=60),
        )

        fig.write_html(str(path))
        return path

    def plot_3d_static(
        self,
        elevation: np.ndarray,
        save_path: Optional[str] = None,
    ) -> Path:
        """Renders and saves a static 3D perspective surface using Matplotlib Axes3D."""
        path = Path(save_path) if save_path else self.output_dir / "terrain_3d.png"
        rows, cols = elevation.shape
        xx, yy = np.meshgrid(np.arange(cols), np.arange(rows))

        fig = plt.figure(figsize=(10, 8), dpi=150)
        ax = fig.add_subplot(111, projection="3d")

        # Downsample for crisp wireframe/surface rendering if needed
        surf = ax.plot_surface(
            xx,
            yy,
            elevation,
            cmap="terrain",
            linewidth=0,
            antialiased=True,
            alpha=0.9,
            rstride=1,
            cstride=1,
        )

        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label="Elevation (m)")
        ax.set_title("Odyssey Terrain - 3D Perspective Elevation Mesh", fontsize=12, fontweight="bold")
        ax.set_xlabel("X (cells)")
        ax.set_ylabel("Y (cells)")
        ax.set_zlabel("Elevation (m)")
        ax.view_init(elev=40, azim=-55)

        fig.text(0.5, 0.02, f"[!] {SIMULATION_NOTICE}", ha="center", fontsize=7, color="gray")
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path
