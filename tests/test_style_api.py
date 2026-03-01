"""Tests for Style API CRUD routes."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dich_truyen.api.routes import styles
from dich_truyen.services.style_service import StyleService


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Create a test client with style routes."""
    from fastapi import FastAPI

    app = FastAPI()
    styles_dir = tmp_path / "styles"
    styles_dir.mkdir()
    svc = StyleService(styles_dir=styles_dir)
    styles.set_style_service(svc)
    app.include_router(styles.router)
    return TestClient(app)


VALID_STYLE = {
    "name": "test_api",
    "description": "API test style",
    "guidelines": ["Rule 1"],
    "vocabulary": {"你": "ngươi"},
    "tone": "formal",
    "examples": [{"chinese": "你好", "vietnamese": "Xin chào"}],
}


def test_create_style(client: TestClient) -> None:
    """POST /api/v1/styles creates a style."""
    r = client.post("/api/v1/styles", json=VALID_STYLE)
    assert r.status_code == 201
    assert r.json()["name"] == "test_api"


def test_create_style_duplicate(client: TestClient) -> None:
    """POST /api/v1/styles with existing name returns 409."""
    client.post("/api/v1/styles", json=VALID_STYLE)
    r = client.post("/api/v1/styles", json=VALID_STYLE)
    assert r.status_code == 409


def test_update_style(client: TestClient) -> None:
    """PUT /api/v1/styles/{name} updates a style."""
    client.post("/api/v1/styles", json=VALID_STYLE)
    r = client.put(
        "/api/v1/styles/test_api",
        json={**VALID_STYLE, "description": "Updated"},
    )
    assert r.status_code == 200
    assert r.json()["description"] == "Updated"


def test_update_builtin_rejected(client: TestClient) -> None:
    """PUT /api/v1/styles/{name} for built-in returns 403."""
    r = client.put("/api/v1/styles/tien_hiep", json=VALID_STYLE)
    assert r.status_code == 403


def test_delete_style(client: TestClient) -> None:
    """DELETE /api/v1/styles/{name} removes a style."""
    client.post("/api/v1/styles", json=VALID_STYLE)
    r = client.delete("/api/v1/styles/test_api")
    assert r.status_code == 200


def test_delete_builtin_rejected(client: TestClient) -> None:
    """DELETE /api/v1/styles/{name} for built-in returns 403."""
    r = client.delete("/api/v1/styles/tien_hiep")
    assert r.status_code == 403


def test_duplicate_style(client: TestClient) -> None:
    """POST /api/v1/styles/{name}/duplicate clones a style."""
    r = client.post("/api/v1/styles/tien_hiep/duplicate")
    assert r.status_code == 201
    assert r.json()["name"] == "tien_hiep"


def test_import_style(client: TestClient) -> None:
    """POST /api/v1/styles/import validates YAML (does not save)."""
    yaml_content = """
name: imported
description: From YAML
guidelines:
  - Rule
tone: formal
"""
    r = client.post("/api/v1/styles/import", json={"yaml_content": yaml_content})
    assert r.status_code == 200
    assert r.json()["name"] == "imported"


def test_import_invalid_yaml(client: TestClient) -> None:
    """POST /api/v1/styles/import with bad YAML returns 422."""
    r = client.post("/api/v1/styles/import", json={"yaml_content": "{{{bad"})
    assert r.status_code == 422


def test_export_style(client: TestClient) -> None:
    """GET /api/v1/styles/{name}/export returns YAML."""
    r = client.get("/api/v1/styles/tien_hiep/export")
    assert r.status_code == 200
    assert "tien_hiep" in r.text
    assert r.headers["content-type"].startswith("application/x-yaml")
