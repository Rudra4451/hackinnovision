import sys
from pathlib import Path

# Ensure project root is in sys.path for serverless execution
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.main import app

# Export ASGI app instance for Vercel Serverless Function
__all__ = ["app"]
