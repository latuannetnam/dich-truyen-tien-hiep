"""Tests for the FastAPI API server."""

import pytest
from fastapi.testclient import TestClient

from dich_truyen.api.server import create_app


def test_create_app_returns_fastapi_instance():
    app = create_app()
    assert app is not None


def test_health_endpoint():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
