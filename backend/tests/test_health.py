from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_cors_headers() -> None:
    origin = "http://10.30.84.238:5173"
    response = client.get("/api/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin


