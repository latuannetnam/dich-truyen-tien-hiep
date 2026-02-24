"""Pipeline service — manages translation jobs.

Wraps StreamingPipeline and emits events for WebSocket consumers.
Does NOT replace the CLI pipeline command — both coexist.
"""

import asyncio
import time
import uuid
from enum import StrEnum
from pathlib import Path
from typing import Any, Optional

from dich_truyen.services.events import EventBus, PipelineEvent


class JobStatus(StrEnum):
    """Pipeline job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineService:
    """Manages pipeline jobs and emits progress events.

    Each job wraps a StreamingPipeline execution. Jobs run as background
    asyncio.Tasks and emit events via the EventBus.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._jobs: dict[str, dict[str, Any]] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def create_job(
        self,
        url: Optional[str] = None,
        book_dir: Optional[str] = None,
        style: str = "tien_hiep",
        workers: int = 3,
        chapters: Optional[str] = None,
        crawl_only: bool = False,
        translate_only: bool = False,
        no_glossary: bool = False,
        glossary: Optional[str] = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Create a new pipeline job (pending, not yet started)."""
        job_id = str(uuid.uuid4())[:8]
        job = {
            "id": job_id,
            "status": JobStatus.PENDING,
            "url": url,
            "book_dir": book_dir,
            "style": style,
            "workers": workers,
            "chapters": chapters,
            "crawl_only": crawl_only,
            "translate_only": translate_only,
            "no_glossary": no_glossary,
            "glossary": glossary,
            "force": force,
            "created_at": time.time(),
            "started_at": None,
            "completed_at": None,
            "progress": {
                "total_chapters": 0,
                "crawled": 0,
                "translated": 0,
                "errors": 0,
            },
            "error": None,
        }
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all jobs, newest first."""
        return sorted(
            self._jobs.values(),
            key=lambda j: j["created_at"],
            reverse=True,
        )

    async def start_job(self, job_id: str) -> dict[str, Any]:
        """Start a pending job as a background task.

        Returns the updated job dict, or raises ValueError if not found.
        """
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        if job["status"] != JobStatus.PENDING:
            raise ValueError(f"Job is not pending: {job['status']}")

        job["status"] = JobStatus.RUNNING
        job["started_at"] = time.time()

        task = asyncio.create_task(self._run_pipeline(job))
        self._tasks[job_id] = task
        return job

    async def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Cancel a running job."""
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()

        job["status"] = JobStatus.CANCELLED
        job["completed_at"] = time.time()
        self._emit(job_id, "job_cancelled", {})
        return job

    async def _run_pipeline(self, job: dict[str, Any]) -> None:
        """Execute the pipeline and emit events."""
        from dich_truyen.config import get_config
        from dich_truyen.crawler.downloader import create_book_directory
        from dich_truyen.pipeline.streaming import StreamingPipeline
        from dich_truyen.translator.glossary import Glossary

        job_id = job["id"]
        self._emit(job_id, "job_started", {"job_id": job_id})

        try:
            # Determine book directory
            if job["book_dir"]:
                target_dir = Path(job["book_dir"])
                if not target_dir.exists():
                    raise FileNotFoundError(f"Directory not found: {target_dir}")
            else:
                target_dir = await create_book_directory(
                    job["url"], get_config().books_dir
                )
                job["book_dir"] = str(target_dir)

            # Import glossary if provided
            if job["glossary"]:
                imported = Glossary.from_csv(Path(job["glossary"]))
                imported.save(target_dir)

            # Create and run pipeline
            pipeline = StreamingPipeline(translator_workers=job["workers"])

            # Hook into pipeline stats for event emission
            original_update = pipeline._update_chapter_status

            async def emitting_update(chapter, status, error=None):
                await original_update(chapter, status, error)
                self._emit(
                    job_id,
                    f"chapter_{status.value}",
                    {
                        "chapter_index": chapter.index,
                        "chapter_title": chapter.title_cn or "",
                        "status": status.value,
                    },
                )
                # Update job progress from pipeline stats
                job["progress"] = {
                    "total_chapters": pipeline.stats.total_chapters,
                    "crawled": pipeline.stats.chapters_crawled,
                    "translated": pipeline.stats.chapters_translated,
                    "errors": pipeline.stats.crawl_errors
                    + pipeline.stats.translate_errors,
                    "worker_status": dict(pipeline.stats.worker_status),
                    "glossary_count": pipeline.stats.glossary_count,
                }
                self._emit(job_id, "progress", job["progress"])

            pipeline._update_chapter_status = emitting_update

            result = await pipeline.run(
                book_dir=target_dir,
                url=job["url"] if not job["translate_only"] else None,
                chapters_spec=job["chapters"],
                style_name=job["style"],
                auto_glossary=not job["no_glossary"],
                force=job["force"],
                crawl_only=job["crawl_only"],
            )

            job["status"] = JobStatus.COMPLETED
            job["completed_at"] = time.time()
            job["progress"]["total_chapters"] = result.total_chapters
            job["progress"]["crawled"] = result.crawled
            job["progress"]["translated"] = result.translated
            self._emit(
                job_id,
                "job_completed",
                {
                    "result": result.model_dump(),
                },
            )

        except asyncio.CancelledError:
            job["status"] = JobStatus.CANCELLED
            job["completed_at"] = time.time()
            self._emit(job_id, "job_cancelled", {})

        except Exception as e:
            job["status"] = JobStatus.FAILED
            job["completed_at"] = time.time()
            job["error"] = str(e)
            self._emit(job_id, "job_failed", {"error": str(e)})

    def _emit(self, job_id: str, event_type: str, data: dict) -> None:
        """Emit a pipeline event."""
        self._event_bus.emit(
            PipelineEvent(
                type=event_type,
                data=data,
                job_id=job_id,
            )
        )
