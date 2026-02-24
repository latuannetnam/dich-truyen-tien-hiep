"""Tests for the FastAPI API server."""

import json

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


@pytest.fixture
def books_dir(tmp_path):
    """Create a temporary books directory with test data."""
    book1 = tmp_path / "test-book-1"
    book1.mkdir()
    (book1 / "book.json").write_text(json.dumps({
        "url": "https://example.com/book1",
        "title": "测试书籍",
        "title_vi": "Sách Thử Nghiệm",
        "author": "作者",
        "author_vi": "Tác Giả",
        "encoding": "utf-8",
        "patterns": {},
        "chapters": [
            {"index": 1, "id": "ch1", "title_cn": "第一章", "url": "https://example.com/ch1", "status": "translated"},
            {"index": 2, "id": "ch2", "title_cn": "第二章", "url": "https://example.com/ch2", "status": "crawled"},
            {"index": 3, "id": "ch3", "title_cn": "第三章", "url": "https://example.com/ch3", "status": "pending"},
        ],
        "metadata": {},
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }), encoding="utf-8")
    return tmp_path


def test_list_books(books_dir):
    app = create_app(books_dir=books_dir)
    client = TestClient(app)
    response = client.get("/api/v1/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    book = data[0]
    assert book["id"] == "test-book-1"
    assert book["title"] == "测试书籍"
    assert book["title_vi"] == "Sách Thử Nghiệm"
    assert book["total_chapters"] == 3
    assert book["translated_chapters"] == 1
    assert book["crawled_chapters"] == 1


def test_list_books_empty(tmp_path):
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.get("/api/v1/books")
    assert response.status_code == 200
    assert response.json() == []

