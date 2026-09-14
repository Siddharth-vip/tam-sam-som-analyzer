from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_read_root() -> None:
    """Verify that the root health check endpoint returns 200 and status ok."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert "message" in data


def test_health_check_endpoint() -> None:
    """Verify that the dedicated /health endpoint returns comprehensive status information."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"
    assert "app_name" in data
    assert "version" in data
    assert "environment" in data
    assert "llm" in data
    assert "search" in data
    assert data["llm"]["provider"] == "ollama"


def test_validation_error_structured_response() -> None:
    """Verify that request validation failures return clean, structured error responses."""
    response = client.post(
        "/api/v1/pipeline/analyze",
        json={"business_idea": ""},  # empty string violates min_length
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("status") == "error"
    assert data.get("error_type") == "ValidationError"
    assert "detail" in data
