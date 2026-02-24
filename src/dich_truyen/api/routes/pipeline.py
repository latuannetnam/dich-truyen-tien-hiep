"""Pipeline API routes — start, monitor, and cancel translations."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dich_truyen.services.events import EventBus
from dich_truyen.services.pipeline_service import PipelineService


router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

# Shared instances (set by server.py)
_event_bus: EventBus = EventBus()
_pipeline_service: PipelineService = PipelineService(_event_bus)


def set_services(event_bus: EventBus, pipeline_service: PipelineService) -> None:
    """Set shared service instances."""
    global _event_bus, _pipeline_service
    _event_bus = event_bus
    _pipeline_service = pipeline_service


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
