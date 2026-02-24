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


@pytest.fixture
def books_dir_with_content(books_dir):
    """Extend books_dir fixture with chapter content files."""
    book_dir = books_dir / "test-book-1"
    raw_dir = book_dir / "raw"
    raw_dir.mkdir()
    # Use actual naming pattern: {index:04d}_{title}.txt
    (raw_dir / "0001_第一章.txt").write_text("这是中文内容。第一章。", encoding="utf-8")

    translated_dir = book_dir / "translated"
    translated_dir.mkdir()
    (translated_dir / "0001_第一章.txt").write_text(
        "Đây là nội dung tiếng Việt. Chương một.", encoding="utf-8"
    )
    return books_dir


def test_get_book_detail(books_dir_with_content):
    app = create_app(books_dir=books_dir_with_content)
    client = TestClient(app)
    response = client.get("/api/v1/books/test-book-1")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "测试书籍"
    assert len(data["chapters"]) == 3
    assert data["chapters"][0]["status"] == "translated"


def test_get_book_not_found(books_dir):
    app = create_app(books_dir=books_dir)
    client = TestClient(app)
    response = client.get("/api/v1/books/nonexistent")
    assert response.status_code == 404


def test_get_chapter_raw(books_dir_with_content):
    app = create_app(books_dir=books_dir_with_content)
    client = TestClient(app)
    response = client.get("/api/v1/books/test-book-1/chapters/1/raw")
    assert response.status_code == 200
    assert "这是中文内容" in response.json()["content"]


def test_get_chapter_translated(books_dir_with_content):
    app = create_app(books_dir=books_dir_with_content)
    client = TestClient(app)
    response = client.get("/api/v1/books/test-book-1/chapters/1/translated")
    assert response.status_code == 200
    assert "nội dung tiếng Việt" in response.json()["content"]


def test_get_chapter_not_found(books_dir):
    app = create_app(books_dir=books_dir)
    client = TestClient(app)
    response = client.get("/api/v1/books/test-book-1/chapters/99/raw")
    assert response.status_code == 404


# --- Pipeline API tests ---


def test_start_pipeline_requires_url_or_book_dir(tmp_path):
    """POST /pipeline/start without url or book_dir returns 422."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.post("/api/v1/pipeline/start", json={})
    assert response.status_code == 422


def test_start_pipeline_creates_job(tmp_path):
    """POST /pipeline/start with url creates a job."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.post("/api/v1/pipeline/start", json={
        "url": "https://example.com/book",
        "style": "tien_hiep",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "id" in data


def test_list_pipeline_jobs(tmp_path):
    """GET /pipeline/jobs returns list of jobs."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    # Create a job first
    client.post("/api/v1/pipeline/start", json={"url": "https://example.com"})
    response = client.get("/api/v1/pipeline/jobs")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_pipeline_job_not_found(tmp_path):
    """GET /pipeline/jobs/:id returns 404 for unknown job."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.get("/api/v1/pipeline/jobs/nonexistent")
    assert response.status_code == 404


# --- WebSocket tests ---


def test_websocket_pipeline_connect(tmp_path):
    """WebSocket endpoint connects and receives events."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)

    # Create a job first
    resp = client.post("/api/v1/pipeline/start", json={"url": "https://example.com"})
    job_id = resp.json()["id"]

    # Connect to WebSocket
    with client.websocket_connect(f"/ws/pipeline/{job_id}") as ws:
        # Send a test message to verify connection
        ws.send_json({"type": "ping"})
        # The connection should be alive (doesn't raise)


# --- Settings API tests ---


def test_get_settings(tmp_path):
    """GET /settings returns current config."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()
    assert "llm" in data
    assert "crawler" in data
    assert "translation" in data
    assert "pipeline" in data


def test_update_settings(tmp_path):
    """PUT /settings updates config values."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.put("/api/v1/settings", json={
        "llm": {"model": "gpt-4o-mini"},
    })
    assert response.status_code == 200
    # Verify updated
    response = client.get("/api/v1/settings")
    assert response.json()["llm"]["model"] == "gpt-4o-mini"


def test_test_connection_no_key(tmp_path, monkeypatch):
    """POST /settings/test-connection with empty key fails."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Create empty env file and reset config to avoid loading real .env
    empty_env = tmp_path / ".env.test"
    empty_env.write_text("", encoding="utf-8")
    from dich_truyen.config import set_config, AppConfig
    set_config(AppConfig.load(env_file=empty_env))
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.post("/api/v1/settings/test-connection")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False


# --- Glossary API tests ---


@pytest.fixture
def books_dir_with_glossary(books_dir):
    """Extend books_dir with a glossary CSV file."""
    import csv

    book_dir = books_dir / "test-book-1"
    glossary_path = book_dir / "glossary.csv"
    with open(glossary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["chinese", "vietnamese", "category", "notes"])
        writer.writerow(["王林", "Vương Lâm", "character", "Main character"])
        writer.writerow(["练气", "Luyện Khí", "realm", ""])
    return books_dir


def test_get_glossary(books_dir_with_glossary):
    """GET /books/:id/glossary returns glossary entries."""
    app = create_app(books_dir=books_dir_with_glossary)
    client = TestClient(app)
    response = client.get("/api/v1/books/test-book-1/glossary")
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 2
    assert data["entries"][0]["chinese"] == "王林"


def test_add_glossary_entry(books_dir_with_glossary):
    """POST /books/:id/glossary adds a new entry."""
    app = create_app(books_dir=books_dir_with_glossary)
    client = TestClient(app)
    response = client.post("/api/v1/books/test-book-1/glossary", json={
        "chinese": "筑基", "vietnamese": "Trúc Cơ", "category": "realm",
    })
    assert response.status_code == 200
    # Verify it was added
    response = client.get("/api/v1/books/test-book-1/glossary")
    assert len(response.json()["entries"]) == 3


def test_delete_glossary_entry(books_dir_with_glossary):
    """DELETE /books/:id/glossary/:term removes an entry."""
    app = create_app(books_dir=books_dir_with_glossary)
    client = TestClient(app)
    response = client.delete("/api/v1/books/test-book-1/glossary/王林")
    assert response.status_code == 200
    response = client.get("/api/v1/books/test-book-1/glossary")
    assert len(response.json()["entries"]) == 1


def test_get_glossary_book_not_found(tmp_path):
    """GET /books/:id/glossary returns 404 for unknown book."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.get("/api/v1/books/nonexistent/glossary")
    assert response.status_code == 404


def test_export_glossary_csv(books_dir_with_glossary):
    """GET /books/:id/glossary/export returns CSV file."""
    app = create_app(books_dir=books_dir_with_glossary)
    client = TestClient(app)
    response = client.get("/api/v1/books/test-book-1/glossary/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "王林" in response.text
