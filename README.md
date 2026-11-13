# MARS-09 ODYSSEY: Planetary Autonomy & Mission Control
**Track A: Planetary Reconnaissance & Autonomous Navigation**

**Autonomous Mars Rover Hackathon Project — Track A: Planetary Reconnaissance & Autonomous Navigation**

---

> [!WARNING]  
> **SIMULATED SYNTHETIC MARTIAN DATA NOTICE**  
> All topographical, elevation, slope, obstacle, science target, and sensor fields produced by this codebase are **simulated synthetic models** engineered for autonomous rover algorithm validation. They do **not** represent actual in-situ flight telemetry or certified orbital reconnaissance from Mars.

---

## 1. System Architecture

The MARS-09 Odyssey platform integrates three core autonomous sub-systems:
- **Member 2 — Terrain Intelligence (`terrain_intelligence/` & `core/terrain.py`):** 100x100 digital elevation models (DEM), central-difference slope and aspect analysis, Neyman-Scott spatial boulder clustering, 3-tier traversability classification, sensor epistemic uncertainty modeling, and traversability cost mapping.
- **VisionScore Engine (`visionscore/`):** Visual Terrain Scoring & Explainability foundation with unified adapters for uploaded imagery and camera streams, multi-environment profiles (MARS, EARTH, SIMULATION), and replaceable terrain classification interface (`analyze_terrain`).
- **Integration Contract (`core/costmap.py`):** Standardized 2D NumPy float cost mapping ensuring seamless handoff between terrain perception and path planning.
- **Member 3 — Autonomous Navigation (`core/navigation.py`):** 8-directional heuristic A* search, diagonal corner-cutting prevention, dual-mode routing (`shortest` vs. `safest`), multi-stop waypoint mission planning, and path telemetry metrics.
- **Science Intelligence & React Dark HUD (`backend/` & `frontend/`):** FastAPI backend and real-time React telemetry dashboard for mission control, spectroscopic target classification, and Shannon entropy estimation.

```
+---------------------------------------------------------------------------------------+
|                                MARS-09 ODYSSEY AUTONOMY                               |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|   MEMBER 2: TERRAIN INTELLIGENCE                   MEMBER 3: NAVIGATION ENGINE        |
|   - 100x100 Multi-Octave DEM (Hills, Craters)      - 8-Connected A* Search            |
|   - Spatial Gradients (dZ/dX, dZ/dY)               - Dual-Mode Routing:               |
|   - Neyman-Scott Boulder Clustering                  * 'shortest' (distance-minimal)  |
|   - Traversability Classification (0, 1, 2)          * 'safest' (risk-avoiding)       |
|   - Epistemic Sensor Uncertainty                   - Corner-Cutting Prevention        |
|   - Transect Profile Extraction                    - Multi-Stop Waypoint Missions     |
|                     │                                              ▲                  |
|                     ▼                                              │                  |
|   NAVIGATION INTEGRATION CONTRACT (`core/costmap.py`)              │                  |
|   - 2D NumPy float array (100, 100)                                │                  |
|   - Matrix indexing (row, col)                                     │                  |
|   - SAFE terrain:        cost == 1.0 ──────────────────────────────┤                  |
|   - CAUTION terrain:     cost in [5.0, 20.0] (> 2.0) ──────────────┤                  |
|   - IMPASSABLE HAZARD:   cost == np.inf ───────────────────────────┘                  |
|   - RISK MAP:            Separate continuous field in [0.0, 1.0]                      |
|                                                                                       |
|   SCIENCE INTELLIGENCE & MISSION CONTROL (`backend/` & `frontend/`)                   |
|   - FastAPI Backend endpoints (/api/navigation, /api/science, /api/mission)           |
|   - React Dark Space HUD with Plotly dual-route overlay & target scoring              |
+---------------------------------------------------------------------------------------+
```

---

## 2. Navigation Integration Contract

Per Member 3's navigation specification:
1. `cost_map` is a 2D NumPy array with `dtype=float` (`np.float64`).
2. Array shape matches all terrain grids: `(100, 100)`.
3. **SAFE** terrain has a cost of exactly **`1.0`**.
4. **CAUTION** terrain has costs strictly greater than **`2.0`** (scaled within `[5.0, 20.0]` based on slope and rock density).
5. **IMPASSABLE HAZARD** terrain (slope $\ge 20^\circ$, boulder obstacles) has cost **`np.inf`**.
6. Spatial coordinates use matrix indexing **`(row, col)`**.
7. `risk_map` is maintained as a separate continuous array normalized in `[0.0, 1.0]`.

### Integration API
```python
from core.terrain import build_terrain_intelligence
from core.navigation import find_path, compare_routes

# 1. Ingest terrain intelligence
terrain = build_terrain_intelligence(seed=42)
cost_map = terrain["cost_map"]  # 100x100 float array

# 2. Compute autonomous navigation trajectories
start = (10, 10)
goal = (85, 85)

comparison = compare_routes(cost_map, start, goal)
print(comparison["summary"]["recommendation"])
```

---

## 3. Directory Layout

```
.
├── core/
│   ├── __init__.py                    # Core exports
│   ├── config.py                      # Global grid & threshold constants
│   ├── costmap.py                     # Member 3 cost map contract generator
│   ├── navigation.py                  # Member 3 A* navigation engine
│   └── terrain.py                     # build_terrain_intelligence integration API
│
├── terrain_intelligence/              # Member 2 Modular Architecture
│   ├── __init__.py
│   ├── config.py                      # Configuration dataclasses & enums
│   ├── cost_map_generator.py          # Movement cost map computation
│   ├── elevation_analyzer.py          # Geomorphic statistics & transects
│   ├── obstacle_detector.py           # Neyman-Scott spatial clustering & masks
│   ├── pipeline.py                    # End-to-end processing pipeline
│   ├── slope_analyzer.py              # Gradient vectors, slope (°) & aspect
│   ├── terrain_classifier.py          # SAFE, CAUTION, HAZARD classification
│   ├── terrain_generator.py           # Multi-octave synthetic DEM generator
│   ├── uncertainty_estimator.py       # Epistemic sensor range & shadow model
│   └── visualizer.py                  # Matplotlib heatmaps & Plotly 3D HTML
│
├── visionscore/                       # VisionScore Visual Terrain Scoring
│   ├── __init__.py                    # Unified adapters, analyzer, results
│   ├── config.py                      # Environment profiles & terrain classes
│   ├── image_input.py                 # Unified image input (upload, camera)
│   ├── analyzer.py                    # PMTCS segmentation & classification
│   └── results.py                     # VisualResults presentation container
│
├── backend/                           # Science Intelligence & REST API
│   ├── main.py                        # FastAPI entry point
│   ├── schemas.py                     # Pydantic v2 schemas
│   ├── api/                           # API routes (navigation, science, mission)
│   ├── integrations/                  # Navigation and terrain adapters
│   └── science/                       # Spectral identification & safety scoring
│
├── frontend/                          # React Dark HUD Dashboard
│   ├── src/                           # Components, Plotly maps, HUD styling
│   └── package.json
│
├── tests/
│   ├── test_cost_map_generator.py     # Cost map generator tests
│   ├── test_elevation_analyzer.py     # Elevation statistics tests
│   ├── test_navigation.py             # Member 3 navigation scenario tests
│   ├── test_navigation_contract.py    # Contract verification tests
│   ├── test_obstacle_detector.py      # Spatial obstacle clustering tests
│   ├── test_pipeline.py               # Integrated pipeline tests
│   ├── test_science_and_backend.py    # Science intelligence & API tests
│   ├── test_slope_analyzer.py         # Analytical slope & gradient tests
│   ├── test_terrain_classifier.py     # Classification partition tests
│   ├── test_terrain_generator.py      # Terrain generation & seed tests
│   ├── test_uncertainty_estimator.py  # Sensor uncertainty tests
│   ├── test_visionscore_stage1.py     # VisionScore Stage 1 foundation tests
│   └── test_visualizer.py             # Visualization artifact tests
│
├── outputs/                           # Generated visualization artifacts
│   ├── elevation_heatmap.png
│   ├── slope_heatmap.png
│   ├── obstacle_map.png
│   ├── terrain_classification_map.png
│   ├── movement_cost_map.png
│   ├── uncertainty_map.png
│   ├── terrain_intelligence_dashboard.png
│   ├── terrain_3d.png
│   └── terrain_3d.html
│
├── main.py                            # Standalone demonstration CLI
├── requirements.txt                   # Project dependencies
└── pyproject.toml                     # Packaging configuration
```

---

## 4. Installation & Verification

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run full automated test suite:**
   ```bash
   pytest tests -v
   ```

3. **Execute standalone terrain pipeline:**
   ```bash
   python main.py
   ```

---

## 5. 3D Terrain Visualization & Mission Control Telemetry

The MARS-09 Odyssey platform features a mission-control-grade 3D interface built with React, Vite, and Plotly.js conforming to NASA/JPL telemetry specifications.

### Key Capabilities
- **Real Martian Topography (DEM):** Renders elevation relief with custom geological colormaps, contour lines, and dynamic vertical exaggeration ($0.5\times$ to $3.0\times$).
- **Dual-Mode Trajectory Overlays:** Displays completed traversal (solid `#10B981`) and remaining path (dotted `#10B981`).
- **Hazard & Caution Classification:** Real-time visual markers distinguishing impassable obstacles (`np.inf` / `"Infinity"` $\rightarrow$ crimson diamonds `#EF4444`) and caution zones (cost $> 2.0$ $\rightarrow$ amber circles `#F59E0B`).
- **Rover Simulation Engine:** Leak-free React state machine supporting Play, Pause, Step ($\pm 1$), Reset, speed selection ($0.5\times$ to $4\times$), and position scrubbing.
- **Route Comparison Drawer:** Collapsible side-by-side metric comparison table contrasting Safest vs. Shortest routes with semantic delta coloring and quoted navigator recommendations.
- **Debounced Inspection & Telemetry:** 60ms debounced hover inspects `(row, col) · Elevation · Cost Class`, with temporary click-to-pin navigation targeting.

### Launching the Dashboard

1. **Start the FastAPI Backend:**
   ```bash
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start the React Mission Control HUD:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open `http://127.0.0.1:5173` in your browser.

