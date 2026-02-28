"""Tests for PipelineService."""

import json

import pytest

from dich_truyen.services.events import EventBus
from dich_truyen.services.pipeline_service import PipelineService, JobStatus


def test_create_pipeline_service():
    """Service initializes with event bus and empty jobs."""
    bus = EventBus()
    service = PipelineService(bus)
    assert service.list_jobs() == []


def test_job_status_enum():
    """Job status values are valid."""
    assert JobStatus.PENDING == "pending"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"
    assert JobStatus.CANCELLED == "cancelled"


def test_create_job():
    """Creating a job returns a job dict with pending status."""
    bus = EventBus()
    service = PipelineService(bus)
    job = service.create_job(
        url="https://example.com/book",
        style="tien_hiep",
        workers=3,
    )
    assert job["status"] == JobStatus.PENDING
    assert job["url"] == "https://example.com/book"
    assert "id" in job
    assert "created_at" in job


def test_list_jobs_returns_created_jobs():
    """List jobs returns all created jobs."""
    bus = EventBus()
    service = PipelineService(bus)
    service.create_job(url="https://example.com/book1")
    service.create_job(book_dir="books/existing")
    jobs = service.list_jobs()
    assert len(jobs) == 2


def test_get_job_not_found():
    """Getting a nonexistent job returns None."""
    bus = EventBus()
    service = PipelineService(bus)
    assert service.get_job("nonexistent") is None


def test_save_pipeline_settings_creates_file(tmp_path):
    """Running a pipeline saves last_pipeline_settings.json to book dir."""
    from dich_truyen.services.pipeline_service import _save_pipeline_settings

    _save_pipeline_settings(
        book_dir=tmp_path,
        style="tien_hiep",
        workers=3,
        chapters=None,
        crawl_only=False,
        translate_only=False,
        no_glossary=False,
    )

    settings_file = tmp_path / "last_pipeline_settings.json"
    assert settings_file.exists()

    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert data["style"] == "tien_hiep"
    assert data["workers"] == 3
    assert data["chapters"] is None
    assert data["crawl_only"] is False
    assert "last_run_at" in data


def test_save_pipeline_settings_overwrites(tmp_path):
    """Subsequent runs overwrite previous settings."""
    from dich_truyen.services.pipeline_service import _save_pipeline_settings

    _save_pipeline_settings(book_dir=tmp_path, style="old_style", workers=1)
    _save_pipeline_settings(book_dir=tmp_path, style="new_style", workers=5)

    data = json.loads((tmp_path / "last_pipeline_settings.json").read_text(encoding="utf-8"))
    assert data["style"] == "new_style"
    assert data["workers"] == 5


def test_scan_books_creates_default_settings(tmp_path):
    """Startup scan creates default settings for incomplete books without one."""
    from dich_truyen.services.pipeline_service import scan_books_on_startup
    from dich_truyen.utils.progress import BookProgress, Chapter, ChapterStatus

    # Create incomplete book WITHOUT last_pipeline_settings.json
    book_dir = tmp_path / "incomplete-book"
    book_dir.mkdir()
    progress = BookProgress(
        url="https://example.com",
        title="Test",
        title_vi="",
        author="",
        author_vi="",
        encoding="utf-8",
        chapters=[
            Chapter(
                index=1,
                id="ch1",
                url="https://example.com/1",
                title_cn="第一章",
                status=ChapterStatus.CRAWLED,
            ),
        ],
    )
    progress.save(book_dir)

    # Create complete book WITHOUT settings (should NOT get a file)
    done_dir = tmp_path / "done-book"
    done_dir.mkdir()
    done_progress = BookProgress(
        url="https://example.com/done",
        title="Done",
        title_vi="",
        author="",
        author_vi="",
        encoding="utf-8",
        chapters=[
            Chapter(
                index=1,
                id="ch1",
                url="https://example.com/1",
                title_cn="第一章",
                status=ChapterStatus.TRANSLATED,
            ),
        ],
    )
    done_progress.save(done_dir)

    scan_books_on_startup(tmp_path)

    # Incomplete book should get default settings
    assert (book_dir / "last_pipeline_settings.json").exists()
    data = json.loads((book_dir / "last_pipeline_settings.json").read_text(encoding="utf-8"))
    assert data["style"] == "tien_hiep"
    assert data["workers"] == 3

    # Complete book should NOT get settings
    assert not (done_dir / "last_pipeline_settings.json").exists()


def test_scan_books_skips_existing_settings(tmp_path):
    """Startup scan does NOT overwrite existing settings."""
    from dich_truyen.services.pipeline_service import scan_books_on_startup
    from dich_truyen.utils.progress import BookProgress, Chapter, ChapterStatus

    book_dir = tmp_path / "book-with-settings"
    book_dir.mkdir()
    progress = BookProgress(
        url="https://example.com",
        title="Test",
        title_vi="",
        author="",
        author_vi="",
        encoding="utf-8",
        chapters=[
            Chapter(
                index=1,
                id="ch1",
                url="https://example.com/1",
                title_cn="第一章",
                status=ChapterStatus.CRAWLED,
            ),
        ],
    )
    progress.save(book_dir)

    # Pre-existing settings with custom style
    existing = {"style": "custom_style", "workers": 5, "last_run_at": "2026-01-01T00:00:00"}
    (book_dir / "last_pipeline_settings.json").write_text(json.dumps(existing))

    scan_books_on_startup(tmp_path)

    # Settings should be unchanged
    data = json.loads((book_dir / "last_pipeline_settings.json").read_text(encoding="utf-8"))
    assert data["style"] == "custom_style"
    assert data["workers"] == 5


