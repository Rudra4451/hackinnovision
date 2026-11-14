"""Standalone execution script for Odyssey Terrain Intelligence.

Run this script directly to execute the entire pipeline, display comprehensive metrics,
and generate high-resolution visualization artifacts.

Usage:
    python main.py [--seed 42] [--output-dir outputs] [--resolution 1.0]
"""

import argparse
import sys
import time
from pathlib import Path

# Add practice directory to Python path if executed directly
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from terrain_intelligence import (
    SIMULATION_NOTICE,
    TerrainConfig,
    TerrainPipeline,
)

# Expose top-level FastAPI application instance for Vercel and ASGI runners
try:
    from backend.main import app
except ImportError:
    app = None


def print_banner():
    banner = r"""
================================================================================
   ____  ______     _______ _____ ______     __   __  __          _____   _____ 
  / __ \|  __ \ \   / / ____/ ____|  ____| \ \   / / |  \/  |   /\   |  __ \ / ____|
 | |  | | |  | \ \_/ / (___| (___ | |__     \ \_/ /  | \  / |  /  \  | |__) | (___  
 | |  | | |  | |\   / \___ \\___ \|  __|     \   /   | |\/| | / /\ \ |  _  / \___ \ 
 | |__| | |__| | | |  ____) |___) | |____     | |    | |  | |/ ____ \| | \ \ ____) |
  \____/|_____/  |_| |_____/_____/|______|    |_|    |_|  |_/_/    \_\_|  \_\_____/ 
                                                                                
          ODYSSEY TERRAIN INTELLIGENCE MODULE (MEMBER 2 INDEPENDENT SYSTEM)
================================================================================
    """
    print(banner)
    print(f"[!] SYSTEM NOTICE: {SIMULATION_NOTICE}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Odyssey Terrain Intelligence - Autonomous Mars Rover Hackathon Module"
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility (default: 42)")
    parser.add_argument("--resolution", type=float, default=1.0, help="Grid cell resolution in meters (default: 1.0)")
    parser.add_argument("--output-dir", type=str, default="outputs", help="Output directory for visualizations (default: outputs)")
    parser.add_argument("--skip-viz", action="store_true", help="Skip rendering visualization plots")

    args = parser.parse_args()

    print_banner()

    print(f"[*] Initializing Terrain Intelligence Pipeline...")
    print(f"    - Grid Shape       : 100 x 100 cells")
    print(f"    - Ground Resolution: {args.resolution} m/cell")
    print(f"    - Random Seed      : {args.seed}")
    print(f"    - Output Directory : {args.output_dir}\n")

    config = TerrainConfig(
        grid_shape=(100, 100),
        resolution_m=args.resolution,
        seed=args.seed,
    )
    pipeline = TerrainPipeline(config)

    t0 = time.perf_counter()
    result = pipeline.run(seed=args.seed)
    elapsed = time.perf_counter() - t0

    print(f"[+] Pipeline executed successfully in {elapsed:.3f} seconds.\n")

    # Component 1 & 2: Elevation Metrics
    print("--------------------------------------------------------------------------------")
    print("COMPONENT 1 & 2: TERRAIN GENERATION & ELEVATION ANALYSIS")
    print("--------------------------------------------------------------------------------")
    em = result.elevation_metrics
    print(f"  Shape              : {result.elevation_array.shape}")
    print(f"  Min Elevation      : {em.min_m:+.2f} m")
    print(f"  Max Elevation      : {em.max_m:+.2f} m")
    print(f"  Mean Elevation     : {em.mean_m:+.2f} m")
    print(f"  Median Elevation   : {em.median_m:+.2f} m")
    print(f"  Standard Deviation : {em.std_m:.2f} m")
    print(f"  Relief Dynamic Span: {em.span_m:.2f} m")
    print(f"  Hypsometric Ratio  : {em.hypsometric_integral:.3f}")
    print(f"  Seeded Hills       : {len(result.terrain.metadata['features'].hills)}")
    print(f"  Seeded Craters     : {len(result.terrain.metadata['features'].craters)}")
    print(f"  Flat Basin Center  : {result.terrain.metadata['features'].flat_center}")
    print(f"  Rocky Field Center : {result.terrain.metadata['features'].rocky_center}")

    # Component 3: Slope Analysis
    print("\n--------------------------------------------------------------------------------")
    print("COMPONENT 3: SLOPE & GRADIENT ANALYSIS")
    print("--------------------------------------------------------------------------------")
    slp = result.slope
    print(f"  Min Slope          : {slp.min_slope_deg:.2f}°")
    print(f"  Max Slope          : {slp.max_slope_deg:.2f}°")
    print(f"  Mean Slope         : {slp.mean_slope_deg:.2f}°")
    print(f"  Caution Fraction   : {slp.caution_fraction * 100.0:.1f}% (> {config.slope_caution_thresh_deg}°)")
    print(f"  Hazard Fraction    : {slp.hazard_fraction * 100.0:.1f}% (> {config.slope_hazard_thresh_deg}°)")

    # Component 4: Obstacle Detection
    print("\n--------------------------------------------------------------------------------")
    print("COMPONENT 4: SPATIAL OBSTACLE CLUSTERING")
    print("--------------------------------------------------------------------------------")
    obs = result.obstacles
    print(f"  Total Obstacle Cells: {obs.total_obstacle_cells} / {result.elevation_array.size} cells")
    print(f"  Obstacle Coverage   : {obs.obstacle_fraction * 100.0:.2f}%")
    print(f"  Identified Clusters : {obs.num_clusters}")
    if obs.cluster_sizes:
        print(f"  Max Cluster Size    : {max(obs.cluster_sizes)} cells")
        print(f"  Mean Cluster Size   : {sum(obs.cluster_sizes)/len(obs.cluster_sizes):.1f} cells")

    # Component 5: Terrain Classification
    print("\n--------------------------------------------------------------------------------")
    print("COMPONENT 5: TERRAIN TRAVERSABILITY CLASSIFICATION")
    print("--------------------------------------------------------------------------------")
    cls = result.classification
    print(f"  SAFE    (0) : {cls.safe_fraction * 100.0:5.1f}% ({int(cls.safe_fraction * cls.total_cells)} cells)")
    print(f"  CAUTION (1) : {cls.caution_fraction * 100.0:5.1f}% ({int(cls.caution_fraction * cls.total_cells)} cells)")
    print(f"  HAZARD  (2) : {cls.hazard_fraction * 100.0:5.1f}% ({int(cls.hazard_fraction * cls.total_cells)} cells)")
    print(f"  Total Classified   : {cls.total_cells} / {cls.total_cells} (100.0% coverage)")

    # Component 6: Movement Cost Map
    print("\n--------------------------------------------------------------------------------")
    print("COMPONENT 6: MOVEMENT COST MAP")
    print("--------------------------------------------------------------------------------")
    cost = result.cost_map
    print(f"  Min Navigable Cost : {cost.min_finite_cost:.2f}")
    print(f"  Max Navigable Cost : {cost.max_finite_cost:.2f}")
    print(f"  Mean Navigable Cost: {cost.mean_finite_cost:.2f}")
    print(f"  Impassable Cells   : {cost.impassable_cells} cells ({cost.impassable_fraction * 100.0:.1f}%) [Cost = infinity]")

    # Component 7: Uncertainty Estimation
    print("\n--------------------------------------------------------------------------------")
    print("COMPONENT 7: PERCEPTUAL TERRAIN UNCERTAINTY")
    print("--------------------------------------------------------------------------------")
    unc = result.uncertainty
    print(f"  Sensor Vantage Point : (row={unc.sensor_origin[0]}, col={unc.sensor_origin[1]})")
    print(f"  Mean Uncertainty     : {unc.mean_uncertainty:.3f} [Range: {unc.min_uncertainty:.3f} - {unc.max_uncertainty:.3f}]")
    print(f"  High Uncertainty (>0.7): {unc.high_uncertainty_fraction * 100.0:.1f}%")

    # Component 8: Visualizations
    if not args.skip_viz:
        print("\n--------------------------------------------------------------------------------")
        print("COMPONENT 8: GENERATING VISUALIZATIONS & ARTIFACTS")
        print("--------------------------------------------------------------------------------")
        viz_paths = result.save_all_visualizations(output_dir=args.output_dir)
        for name, p in viz_paths.items():
            print(f"  [SAVED] {name.ljust(15)}: {p}")

    print("\n================================================================================")
    print("ODYSSEY TERRAIN INTELLIGENCE MODULE EXECUTION COMPLETE.")
    print("Ready for autonomous path planner integration.")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
