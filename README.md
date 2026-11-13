# MARS-09 ODYSSEY: Science Intelligence & React Mission Control
**Track A: Planetary Reconnaissance & Autonomous Navigation**

MARS-09 Odyssey is an autonomous planetary exploration system engineered for 12-hour reconnaissance hackathons. It integrates an 8-directional heuristic path planner (`core/navigation.py`) with a **Science Intelligence Engine** and a real-time **React Dark HUD Mission Control Dashboard**.

---

## 🚀 Key Architecture & Modules

```
innovision/
├── core/
│   └── navigation.py            # Finished autonomous navigation engine (DO NOT MODIFY)
│
├── backend/
│   ├── main.py                  # FastAPI server entry point (CORS enabled)
│   ├── schemas.py               # Pydantic v2 schemas for telemetry & targets
│   ├── integrations/
│   │   ├── navigation_adapter.py# Bridge to core.navigation.compare_routes
│   │   └── terrain_adapter.py   # Benchmark Jezero crater terrain & JSON inf sanitization
│   ├── science/
│   │   ├── identification.py    # Multi-band spectral geological categorization
│   │   ├── scoring.py           # Hard safety gating & operational ranking (Rule 2)
│   │   ├── uncertainty.py       # Shannon entropy & observational confidence
│   │   └── recommendations.py   # Evidence-based Markdown mission briefing
│   └── api/
│       ├── navigation.py        # /api/navigation/compare & /api/navigation/terrain
│       ├── science.py           # /api/science/targets & /api/science/report
│       └── mission.py           # /api/mission/telemetry
│
├── frontend/
│   ├── src/
│   │   ├── api/client.js        # Axios REST client
│   │   ├── components/
│   │   │   ├── MissionOverview.jsx   # Sol, battery, comms delay, motor status
│   │   │   ├── NavigationMap.jsx     # Plotly dual-route overlay (Safest vs Shortest)
│   │   │   ├── RouteMetrics.jsx      # Telemetry trade-off delta table & risk reduction
│   │   │   ├── RoverSimulation.jsx   # Step-by-step waypoint scrubber & playback
│   │   │   ├── ScienceTargets.jsx    # Ranked matrix with Rule 2 gating badges
│   │   │   ├── TargetDetails.jsx     # Spectroscopic analysis & Shannon entropy
│   │   │   ├── TerrainExplorer.jsx   # Point inspection & custom goal planner
│   │   │   └── MissionReport.jsx     # Tactical reconnaissance briefing
│   │   └── styles/
│   │       ├── global.css            # Dark space HUD theme & scanlines
│   │       └── dashboard.css         # Grid layout & telemetry styling
│
├── data/sample/
│   └── targets_catalog.json     # Geological candidate sites
├── tests/
│   ├── test_navigation.py       # Autonomous path planning test suite
│   └── test_science_and_backend.py # Science intelligence & API unit tests
├── requirements.txt
└── README.md
```

---

## 🔬 Science Intelligence Engine

### 1. Rule 2: Separation of Scientific Value & Operational Priority
- **Scientific Value ($V_{\text{sci}} \in [0, 100]$)**: Inherent astrobiological merit, hydration index, and geological rarity.
- **Operational Priority ($P_{\text{op}} \in [0, 100]$)**: Distance, terrain cost, and uncertainty discounted score.
- **Hard Safety Gate**: If a candidate site is located inside an impassable hazard ($C = \infty$), or if `compare_routes(cost_map, rover, target)["safest"]["route"]["success"] == False`, its operational priority is **locked to 0.0** and marked `UNREACHABLE_HAZARD`.

### 2. Shannon Entropy Uncertainty Reasoning
For class probability distribution $\mathbf{p} = [p_1, \dots, p_K]$:
$$H(\mathbf{p}) = -\sum_{i=1}^K p_i \log_2(p_i), \quad U = \frac{H(\mathbf{p})}{\log_2(K)}, \quad \text{Confidence} = 1.0 - U$$

### 3. Rule 3: Safe Non-Finite JSON Serialization
All `np.inf` values in terrain grids are serialized to `null` in JSON with a parallel boolean `hazard_mask`, preventing browser `JSON.parse` crashes while enabling distinct crimson hazard rendering in Plotly.

---

## 🛰️ Navigation Integration Contract

The backend interacts with `core/navigation.py` strictly via:
```python
from core.navigation import find_path, calculate_path_metrics, compare_routes

res = compare_routes(cost_map, start, goal)
```
- **Inputs**: `cost_map` (2D float ndarray where 1.0=nominal, >2.0=caution, np.inf=hazard), `start` & `goal` (row, col) tuples.
- **Dual Outputs**:
  - `res["safest"]`: Risk-weighted A* route avoiding high-cost caution terrain.
  - `res["shortest"]`: Direct distance-minimizing A* route.
  - `res["summary"]`: `both_reachable`, `distance_delta`, `distance_penalty_pct`, `cost_reduction_pct`, `caution_steps_avoided`, `recommendation`.

---

## 🛠️ Quick Start Instructions

### 1. Backend Setup & Launch
```bash
# Activate virtual environment
.\.venv\Scripts\activate

# Run all unit and integration tests (13 tests)
python -m unittest discover tests

# Launch FastAPI backend on port 8000
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 2. Frontend Setup & Launch
```bash
cd frontend

# Install dependencies (already installed)
npm install

# Start Vite development server
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser to access the **MARS-09 Odyssey Mission Control**.
