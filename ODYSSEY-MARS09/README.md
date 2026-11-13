# ODYSSEY MARS-09: Autonomous Rover Mission Control

> **Planetary Reconnaissance, Topographical Risk Intelligence, & Autonomous Navigation**  
> *Track A: Autonomous Planetary Exploration Hackathon*

---

## 1. Executive Summary & Pitch

**ODYSSEY MARS-09** is an AI-first autonomous rover mission control platform engineered for next-generation planetary surface exploration. Operating across high-resolution synthetic Digital Elevation Models (DEM), the system autonomously perceives topographical hazards, computes dual-mode traversability-optimized paths, scores scientific astrobiology targets, and streams telemetry downlinks to mission control in real time.

---

## 2. System Architecture

ODYSSEY MARS-09 is architected around a high-performance modular pipeline coupled to a reactive **Streamlit + Plotly** frontend dashboard:

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

### Module Directory Breakdown:
- **`app.py`**: Streamlit mission control application with defensive payload validation and crash-proof fallback handling.
- **`core/config.py`**: Mission constants (`GRID_SIZE = 100`, `START_POSITION = (5, 5)`, `GOAL_POSITION = (90, 90)`, `MAX_SLOPE = 30°`, `OBSTACLE_COST = np.inf`).
- **`core/terrain.py`**: Synthetic Martian elevation generator, 3-tier slope classifier, and movement cost mapper.
- **`core/navigation.py`**: 8-directional heuristic A* path planning engine with dual-mode trajectory evaluation.
- **`core/science.py`**: Spectrometric biosignature identification, Shannon entropy uncertainty, and accessibility safety gating.
- **`core/simulation.py`**: Rover kinematics, sol step timer, and terrain-dependent battery discharge dynamics.
- **`components/terrain_map.py`**: Dark satellite feed Plotly visualizer with square cell scaling (`scaleanchor="x"`).
- **`components/mission_panel.py`**: NASA terminal mission log console and side-by-side metric comparison readout.
- **`components/target_panel.py`**: Prioritized science target registry with confidence scores.
- **`utils/helpers.py`**: `validate_navigation_payload()` contract integrity checker and coordinate transforms.
- **`tests/`**: Automated test suite (`test_integration.py`, `test_terrain.py`, `test_navigation.py`, `test_science.py`).

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

### Launch Mission Control Dashboard
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
