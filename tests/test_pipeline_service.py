"""Tests for PipelineService."""

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
