import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.integrations.terrain_adapter import deserialize_cost_map_from_json
import numpy as np


@pytest.fixture
def client():
    return TestClient(app)


def test_cors_not_wildcard_with_credentials(client):
    """Verify CORS uses secure local origins and does not expose wildcard with credentials."""
    response = client.options(
        "/api/navigation/compare",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"

    # Untrusted remote origin should NOT be allowed
    response_bad = client.options(
        "/api/navigation/compare",
        headers={
            "Origin": "http://evil-attacker-site.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response_bad.headers.get("access-control-allow-origin") is None


def test_deserialize_cost_map_validates_dimensions():
    """Verify deserialize_cost_map_from_json catches jagged, empty, or oversized matrices."""
    # Empty list
    with pytest.raises(ValueError, match="non-empty"):
        deserialize_cost_map_from_json([])

    # Jagged rows
    with pytest.raises(ValueError, match="length does not match"):
        deserialize_cost_map_from_json([[1.0, 2.0], [1.0]])

    # Oversized matrix (>500)
    with pytest.raises(ValueError, match="between 2 and 500"):
        deserialize_cost_map_from_json([[1.0] * 10] * 501)


def test_deserialize_cost_map_handles_sentinels():
    """Verify deserialize_cost_map_from_json cleanly handles null, Infinity, and NaN strings."""
    grid = [
        [1.0, "Infinity", None],
        ["NaN", 2.5, 9999999999.0],
    ]
    arr = deserialize_cost_map_from_json(grid)
    assert arr.shape == (2, 3)
    assert arr[0, 0] == 1.0
    assert np.isinf(arr[0, 1])
    assert np.isinf(arr[0, 2])
    assert np.isinf(arr[1, 0])
    assert arr[1, 1] == 2.5
    assert np.isinf(arr[1, 2])


def test_image_upload_size_limit(client):
    """Verify that uploading files exceeding 15MB triggers HTTP 413 Payload Too Large."""
    huge_bytes = b"0" * (16 * 1024 * 1024)  # 16 MB
    response = client.post(
        "/api/visionscore/segment",
        files={"file": ("bomb.png", huge_bytes, "image/png")},
    )
    assert response.status_code == 413
    assert "maximum allowed limit" in response.json()["detail"]


def test_static_outputs_path_traversal_prevention(client):
    """Verify static mount prevents directory traversal."""
    response = client.get("/outputs/../backend/main.py")
    # Path traversal should be rejected by FastAPI / Starlette StaticFiles (404 or 400)
    assert response.status_code in (404, 400)
