# ODYSSEY MARS-09 Rover Simulation

Architectural foundation for the Streamlit-based Mars rover simulation.

## Project Structure
```
ODYSSEY-MARS09/
├── app.py                      # Main Streamlit dashboard application
├── requirements.txt            # Project dependencies
├── README.md                   # Project documentation & team contracts
├── core/                       # Core simulation logic & algorithmic modules
│   ├── __init__.py
│   ├── config.py               # Mission constants & simulation parameters
│   ├── terrain.py              # Terrain generation & cost mapping stubs
│   ├── navigation.py           # Pathfinding (A*, Dijkstra) & route comparison stubs
│   ├── science.py              # Science target ranking & confidence scoring stubs
│   └── simulation.py           # Rover step-by-step state simulation stubs
├── data/                       # Static & cached assets
│   ├── terrain/                # DEM (Digital Elevation Model) maps & textures
│   └── targets/                # Geological target registry & spectrometer samples
├── components/                 # Streamlit UI visual components
│   ├── __init__.py
│   ├── terrain_map.py          # 2D/3D Plotly elevation and path renderer
│   ├── mission_panel.py        # Telemetry, battery, and sol timer widgets
│   ├── target_panel.py         # Science target priority queue UI
│   └── rover_animation.py      # Frame-by-frame traversal animator
├── utils/                      # Helper utilities & analytical metrics
│   ├── __init__.py
│   ├── metrics.py              # Path cost, energy consumption & traversal risk formulas
│   └── helpers.py              # Coordinate transforms and file I/O helpers
└── tests/                      # Automated unit tests
    ├── __init__.py
    ├── test_terrain.py         # Terrain generator & cost map test suite
    ├── test_navigation.py      # Pathfinding validation tests
    └── test_science.py         # Target ranking & confidence unit tests
```

## Team Module Ownership
- **Teammate A (Terrain & Hazards):** `core/terrain.py`, `components/terrain_map.py`, `tests/test_terrain.py`
- **Teammate B (Navigation & Pathfinding):** `core/navigation.py`, `core/simulation.py`, `tests/test_navigation.py`
- **Teammate C (Science Operations):** `core/science.py`, `components/target_panel.py`, `tests/test_science.py`

## Quick Start
```bash
pip install -r requirements.txt
streamlit run app.py
```
