"""
MARS-09 Odyssey Mission Control — FastAPI Backend Application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.mission import router as mission_router
from backend.api.navigation import router as navigation_router
from backend.api.science import router as science_router
from backend.api.visionscore import router as visionscore_router

app = FastAPI(
    title="MARS-09 Odyssey Mission Control API",
    description=(
        "Autonomous Planetary Reconnaissance & Autonomous Navigation Engine (Track A). "
        "Provides Science Intelligence, Hard Safety Gating, Dual-Route Navigation Comparison, "
        "and VisionScore 2.0 Semantic Terrain Segmentation & Obstacle Image Alerts."
    ),
    version="2.0.0",
)

# Enable CORS for React frontend (Vite default :5173, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(navigation_router)
app.include_router(science_router)
app.include_router(mission_router)
app.include_router(visionscore_router)


@app.get("/")
def health_check():
    return {
        "system": "MARS-09 Odyssey Mission Control",
        "status": "OPERATIONAL",
        "version": "2.0.0",
        "docs_url": "/docs",
        "endpoints": [
            "/api/navigation/compare",
            "/api/navigation/terrain",
            "/api/science/targets",
            "/api/science/targets/{target_id}",
            "/api/science/report",
            "/api/mission/telemetry",
            "/api/visionscore/status",
            "/api/visionscore/segment",
            "/api/visionscore/alerts",
            "/api/visionscore/camera/frame",
            "/api/visionscore/camera/trigger",
            "/api/visionscore/evaluate-path",
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
