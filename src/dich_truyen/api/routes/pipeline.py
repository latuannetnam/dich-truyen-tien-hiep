"""Pipeline API routes — start, monitor, and cancel translations."""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dich_truyen.services.events import EventBus
from dich_truyen.services.pipeline_service import PipelineService
from dich_truyen.utils.progress import BookProgress, ChapterStatus

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

# Shared instances (set by server.py)
_event_bus: EventBus = EventBus()
_pipeline_service: PipelineService = PipelineService(_event_bus)
_books_dir: Path = Path("books")


def set_services(event_bus: EventBus, pipeline_service: PipelineService) -> None:
    """Set shared service instances."""
    global _event_bus, _pipeline_service
    _event_bus = event_bus
    _pipeline_service = pipeline_service


def set_books_dir(books_dir: Path) -> None:
    """Set the books directory path."""
    global _books_dir
    _books_dir = books_dir


class StartPipelineRequest(BaseModel):
    """Request body for starting a pipeline job."""

    url: Optional[str] = None
    book_dir: Optional[str] = None
    style: str = "tien_hiep"
    workers: int = 3
    chapters: Optional[str] = None
    crawl_only: bool = False
    translate_only: bool = False
    no_glossary: bool = False
    force: bool = False


@router.post("/start")
async def start_pipeline(request: StartPipelineRequest) -> dict:
    """Create a new pipeline job (returns immediately, runs in background)."""
    if not request.url and not request.book_dir:
        raise HTTPException(
            status_code=422,
            detail="Either 'url' or 'book_dir' is required",
        )

    if request.crawl_only and request.translate_only:
        raise HTTPException(
            status_code=422,
            detail="Cannot use both 'crawl_only' and 'translate_only'",
        )

    job = _pipeline_service.create_job(
        url=request.url,
        book_dir=request.book_dir,
        style=request.style,
        workers=request.workers,
        chapters=request.chapters,
        crawl_only=request.crawl_only,
        translate_only=request.translate_only,
        no_glossary=request.no_glossary,
        force=request.force,
    )

    # Start the job in the background
    await _pipeline_service.start_job(job["id"])
    return job


@router.get("/resumable")
async def get_resumable_books() -> list[dict]:
    """List books with incomplete translation progress."""
    resumable = []

    if not _books_dir.exists():
        return resumable

    # Exclude books that already have an active (running/pending) job
    active_book_dirs = set()
    for job in _pipeline_service.list_jobs():
        if job["status"] in ("running", "pending"):
            job_book_dir = job.get("book_dir")
            if job_book_dir:
                active_book_dirs.add(Path(job_book_dir).name)

    for book_dir in sorted(_books_dir.iterdir()):
        book_json = book_dir / "book.json"
        if not book_json.exists():
            continue

        # Skip if already has an active job
        if book_dir.name in active_book_dirs:
            continue

        progress = BookProgress.load(book_dir)
        if progress is None:
            continue

        status_counts = {s: 0 for s in ChapterStatus}
        for ch in progress.chapters:
            status_counts[ch.status] += 1

        pending = status_counts[ChapterStatus.PENDING]
        crawled = status_counts[ChapterStatus.CRAWLED]
        errors = status_counts[ChapterStatus.ERROR]
        translated = status_counts[ChapterStatus.TRANSLATED]

        # Only include if there's remaining work
        if pending == 0 and crawled == 0 and errors == 0:
            continue

        # Load last pipeline settings if available
        last_settings = None
        last_run_at = None
        settings_file = book_dir / "last_pipeline_settings.json"
        if settings_file.exists():
            try:
                settings_data = json.loads(settings_file.read_text(encoding="utf-8"))
                last_run_at = settings_data.pop("last_run_at", None)
                last_settings = settings_data
            except (json.JSONDecodeError, OSError):
                pass

        resumable.append(
            {
                "book_dir": str(book_dir),
                "book_id": book_dir.name,
                "title": progress.title,
                "title_vi": progress.title_vi,
                "total_chapters": len(progress.chapters),
                "translated": translated,
                "crawled": crawled,
                "pending": pending,
                "errors": errors,
                "last_settings": last_settings,
                "last_run_at": last_run_at,
            }
        )

    return resumable


@router.get("/jobs")
async def list_jobs() -> list[dict]:
    """List all pipeline jobs."""
    return _pipeline_service.list_jobs()


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    """Get a specific pipeline job."""
    job = _pipeline_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    """Cancel a running job."""
    try:
        return await _pipeline_service.cancel_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
