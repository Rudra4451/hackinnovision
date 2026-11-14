# ODYSSEY MARS-09: Autonomous Rover Mission Control

> **Planetary Reconnaissance, Topographical Risk Intelligence, & Autonomous Navigation**  
> *Track A: Autonomous Planetary Exploration Hackathon*

---

> [!WARNING]  
> **SIMULATED SYNTHETIC MARTIAN DATA NOTICE**  
> All topographical, elevation, slope, obstacle, science target, and sensor fields produced by this codebase are **simulated synthetic models** engineered for autonomous rover algorithm validation. They do **not** represent actual in-situ flight telemetry or certified orbital reconnaissance from Mars.

---

## 1. Executive Summary & Pitch

**ODYSSEY MARS-09** is an AI-first autonomous rover mission control platform engineered for next-generation planetary surface exploration. Operating across high-resolution synthetic Digital Elevation Models (DEM), the system autonomously perceives topographical hazards, computes dual-mode traversability-optimized paths, scores scientific astrobiology targets, and streams telemetry downlinks to mission control in real time.

The MARS-09 Odyssey platform integrates core autonomous sub-systems:
- **Member 2 — Terrain Intelligence (`terrain_intelligence/` & `core/terrain.py`):** 100x100 digital elevation models (DEM), central-difference slope and aspect analysis, Neyman-Scott spatial boulder clustering, 3-tier traversability classification, sensor epistemic uncertainty modeling, and traversability cost mapping.
- **VisionScore 2.0 Engine (`visionscore/`):** Semantic Terrain Segmentation & Automatic Obstacle Image Alerts with 7-class pixel classification (ROCK, SAND, SOIL, VEGETATION, WATER, OBSTACLE, UNKNOWN), automatic camera event capture, temporal cooldown deduplication, unmapped obstacle safety gating, and candidate path safety scoring.
- **Integration Contract (`core/costmap.py`):** Standardized 2D NumPy float cost mapping ensuring seamless handoff between terrain perception and path planning.
- **Member 3 — Autonomous Navigation (`core/navigation.py`):** 8-directional heuristic A* search, diagonal corner-cutting prevention, dual-mode routing (`shortest` vs. `safest`), multi-stop waypoint mission planning, and path telemetry metrics.
- **Science Intelligence & React Dark HUD (`backend/` & `frontend/`):** FastAPI backend and real-time React telemetry dashboard for mission control, spectroscopic target classification, and Shannon entropy estimation.
- **Streamlit Mission Control Console (`ODYSSEY-MARS09/`):** Reactive Streamlit + Plotly satellite reconnaissance feed and NASA terminal mission log.

---

## 2. System Architecture

```
+-----------------------------------------------------------------------------------------+
|                         ODYSSEY MARS-09 MISSION CONTROL PLATFORM                        |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|   TERRAIN PERCEPTION (core/terrain.py)               AUTONOMOUS NAVIGATION ENGINE       |
|   - Multi-Octave Fractal DEM Topography              (core/navigation.py)               |
|   - Central Differences Gradient Slope Analysis      - 8-Connected Admissible A* Search |
|   - 3-Tier Traversability Classification:            - Diagonal Corner-Cutting Guard    |
|       * SAFE:    1.0 cost (< 12° slope)              - Dual-Mode Route Synthesis:       |
|       * CAUTION: 5.0 - 20.0 (12° - 30° slope)            * Shortest Route (Distance)    |
|       * HAZARD:  np.inf (>= 30° / boulders)              * Safest Route (Risk-Averse)   |
|                         │                                         ▲                     |
|                         └───────────────┬─────────────────────────┘                     |
|                                         ▼                                               |
|                      DEFENSIVE VALIDATION & PAYLOAD CONTRACT                            |
|                                (utils/helpers.py)                                       |
|                                         │                                               |
|                                         ▼                                               |
|                      MISSION CONTROL INTERFACE (app.py)                                 |
|   - Streamlit Reactive Mission Dashboard with NASA Telemetry Terminal Console           |
|   - Plotly Dark Satellite Feed Visualizer (Square-Aspect Grid, High-Contrast Overlays)  |
|   - Multi-Objective Science Target Ranking with Shannon Entropy Uncertainty Estimation  |
|   - Kinematic Rover Dynamics Simulation (Sol Duration, Speed & Battery Power Budget)   |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Navigation Engine Logic: Dual-Mode A* & Risk Optimization

Unlike conventional pathfinders that merely compute the shortest geometric distance, the ODYSSEY MARS-09 navigation engine evaluates a continuous **2D cost map matrix** ($100 \times 100$) to balance physical distance against planetary hazard exposure.

### A. 8-Connected Admissible Search & Kinematic Clearance
- The pathfinder searches an 8-connected neighborhood using the admissible **Euclidean distance heuristic**:
  $$h(n) = \sqrt{(r_n - r_{\text{goal}})^2 + (c_n - c_{\text{goal}})^2}$$
- **Diagonal Corner-Cutting Prevention:** To account for finite rover chassis width ($185\text{ kg}$, $1.2\text{ m}$ wheelbase), diagonal transitions are strictly barred if either adjacent orthogonal neighbor cell contains an impassable obstacle (`np.inf`), preventing impossible pinch-point maneuvers.

### B. Dual-Mode Route Comparison
The engine simultaneously generates and contrasts two discrete paths:
1. **"Shortest Route"**: Optimizes purely for physical distance ($\min \sum \text{step\_dist}$), traversing caution zones if they offer a direct line to the target.
2. **"Safest Route"**: Minimizes accumulated terrain cost ($\min \sum (\text{step\_dist} \times \text{cell\_cost})$), diverting the rover around steep slopes, loose regolith, and boulder clusters.

### C. Quantitative Trade-Off Synthesis
The engine calculates vital mission trade-off metrics provided in `res["summary"]`:
- **Distance Penalty (`distance_penalty_pct`):** The percentage detour required by the safest route:
  $$\text{distance\_penalty\_pct} = \frac{d_{\text{safe}} - d_{\text{short}}}{d_{\text{short}}} \times 100\%$$
- **Cost Reduction (`cost_reduction_pct`):** The mechanical risk and energy savings achieved by avoiding caution slopes:
  $$\text{cost\_reduction\_pct} = \frac{C_{\text{short}} - C_{\text{safe}}}{C_{\text{short}}} \times 100\%$$
- **Caution Steps Avoided (`caution_steps_avoided`):** The count of high-slope ($12^\circ - 30^\circ$) cells bypassed to prevent wheel slippage and motor thermal strain.

### D. Mission Abort & Forced Safe Route Fallbacks
- **Total Hazard Barrier:** If `res["safest"]["route"]["success"]` is `False`, the UI blocks route overlay, displays the bare satellite feed, and triggers a critical mission abort using `res["safest"]["route"]["reason"]`.
- **Shortest Path Obstructed:** If `res["summary"]["both_reachable"]` is `False` but the safest route succeeds, mission control triggers an advisory warning that the direct path is completely blocked by infinite-cost hazards, forcing safe autonomous diversion.

---

## 4. Quick Start & Execution

### Prerequisites
- Python 3.10+
- Recommended: clean virtual environment (`python -m venv .venv`)

### Installation
```bash
# 1. Clone repository
git clone https://github.com/Rudra4451/hackinnovision.git
cd hackinnovision/ODYSSEY-MARS09

# 2. Install dependencies
pip install -r requirements.txt
```

### Launch Streamlit Mission Control Dashboard
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501` to view the live mission control feed.

### Run Automated Integration & Unit Tests
```bash
# Execute integration contract tests
pytest tests/test_integration.py -v

# Run complete test suite
pytest tests -v
```

---

## 5. Verification & Testing Summary
- **Interface Contract:** Verified via `tests/test_integration.py` ensuring exact nested schema keys (`safest.route.success`, `safest.route.x`, `summary.recommendation`).
- **Defensive Error Handling:** Guaranteed via `validate_navigation_payload()` in `utils/helpers.py`.
- **Display Standardization:** Plotly dark satellite projection maintaining 1:1 square grid cells (`scaleanchor="x"`).

---

## 6. VisionScore 2.0: Semantic Terrain Segmentation & Obstacle Image Alerts

VisionScore 2.0 extends ODYSSEY with real-time visual perception, automated hazard detection, and mission-control explainability.

### Key Capabilities
- **Pixel-Level Semantic Segmentation (`segment_terrain`):** Classifies terrain images into 7 distinct surface categories: `ROCK`, `SAND`, `SOIL`, `VEGETATION`, `WATER`, `OBSTACLE`, and `UNKNOWN`.
- **Strict Semantic vs. Traversability Separation:** Semantic surface classes map deterministically to traversability tiers (`SAFE`, `CAUTION`, `HAZARD`, `UNKNOWN`), ensuring geological understanding does not compromise rover safety constraints.
- **Automated Event-Based Image Capture (`ObstacleEventDetector`):** Detects prominent obstacles in incoming camera feeds, captures the frame, generates unique event IDs (`EVT-YYYYMMDD-HHMMSS-xxxx`), persists diagnostic snapshots to managed local storage, and emits alerts to the dashboard.
- **Cooldown Deduplication:** Suppresses repetitive alerts for the same persistent obstacle using spatial centroid tracking, feature signatures, and configurable cooldown windows.
- **Multi-Environment Profiles (`MARS`, `EARTH`, `SIMULATION`):** Strictly enforces planetary atmospheric and geological rules (e.g. biological vegetation and liquid water are prohibited on Mars and tagged as anomalies/unknowns).
- **DEM & Navigation Integration (`evaluate_candidate_path_safety`):** Evaluates candidate paths against visual detections and cost maps; immediately rejects paths traversing `np.inf` hazard cells. Uncalibrated visual obstacles are strictly reported as `UNMAPPED_VISUAL_OBSTACLE` without fabricating artificial coordinates.
- **Mission Control UI:** Real-time visual monitoring available in both the React Dark Space HUD (`/api/visionscore/*`) and Streamlit Reconnaissance Console.
