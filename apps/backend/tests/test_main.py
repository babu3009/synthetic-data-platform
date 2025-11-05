import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Synthetic Data Platform API is running"


def test_api_health_check(client: TestClient) -> None:
    """Test the API v1 health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["message"] == "Synthetic Data Platform API is operational"
    assert data["version"] == "0.1.0"


def test_openapi_docs(client: TestClient) -> None:
    """Test that OpenAPI documentation is accessible."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    
    data = response.json()
    assert data["info"]["title"] == "Synthetic Data Platform"