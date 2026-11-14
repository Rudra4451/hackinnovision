# ODYSSEY MARS-09
Autonomous Mars rover simulation demonstrating terrain risk analysis, cost-aware A* pathfinding, and scientific target prioritization.

## Core Capabilities
- Procedural terrain and hazard generation (2D cost maps)
- Autonomous A* navigation (evaluating shortest vs. safest routes)
- Geological target ranking with explicit confidence scoring
- Interactive Plotly-based mission control dashboard

## System Architecture
- `core/terrain.py`
- `core/navigation.py`
- `core/science.py`
- `app.py`

The backend modules communicate using strict 2D matrix payloads and standard data dictionaries. This decouples the algorithmic logic from the Streamlit UI.

## Tech Stack
- Python 3.11
- Streamlit
- Plotly
- NumPy
- SciPy
- Pandas

## Local Execution
```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

## Engineering Disclaimer (Note for Judges)
Data Note: To meet the 12-hour hackathon constraint, terrain data is procedurally generated using NumPy. Because the system architecture relies on decoupled data contracts, the `generate_terrain()` module can be replaced with real NASA HiRISE satellite elevation data without altering the A* navigation engine or routing algorithms.

## Team
- Member 1 (Integration)
- Member 2 (Terrain)
- Member 3 (Navigation)
- Member 4 (Science & UI)
