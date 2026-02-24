# Desktop UI Phase 2: "Monitor Your Work" — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Start and monitor translations from the browser with real-time progress via WebSocket.

**Architecture:** Extract `PipelineService` from CLI to become a shared service layer. Add event pub/sub system. FastAPI WebSocket endpoint streams pipeline events to browser. New pages: Pipeline Monitor (real-time), New Translation Wizard, enhanced Dashboard with active jobs.

**Tech Stack:** Python (FastAPI, WebSocket, asyncio) · TypeScript (React, Next.js 15) · Tailwind CSS · Lucide React icons

**Design Doc:** [desktop-ui-design.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/docs/plans/2026-02-24-desktop-ui-design.md) → Phase 2

**Phase 1 Plan:** [desktop-ui-phase1.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/docs/plans/2026-02-24-desktop-ui-phase1.md) — Already implemented

### Current State (Phase 1 Complete)

| Component | Status |
|-----------|--------|
| FastAPI server (`api/server.py`) | ✅ Read-only book/chapter endpoints |
| CLI `ui` command | ✅ Starts both FastAPI + Next.js, custom signal handler |
| Next.js frontend | ✅ Dashboard, Library, Book Detail, Reader pages |
| `StreamingPipeline` | ✅ Existing, tightly coupled to Rich console |
| Service layer | ❌ Does not exist yet |
| WebSocket | ❌ Does not exist yet |

### Key Constraints

- CLI must remain 100% functional after every task
- `StreamingPipeline` output is coupled to Rich Live display — we hook into `PipelineStats`, **not** rewrite the pipeline
- `lifespan="off"` in uvicorn config — avoid startup/shutdown hooks (see `cli.md` → Caveats)
- All tests pass (`uv run pytest tests/ -v` — 130 tests)

### Design System Quick Reference

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0B1120` | Main background |
| `--bg-surface` | `#111827` | Cards, panels |
| `--bg-elevated` | `#1F2937` | Hover states, active items |
| `--color-primary` | `#0D9488` (teal) | Active nav, progress bars |
| `--color-cta` | `#F97316` (orange) | Start/action buttons |
| Status colors | `#10B981` / `#F59E0B` / `#3B82F6` / `#EF4444` | Translated / Crawled / Pending / Error |

---

## UI/UX Design Specifications

> **Source:** [MASTER.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/design-system/dich-truyen/MASTER.md) + ui-ux-pro-max skill research

### Global UX Rules (All Pages)

| Rule | Implementation |
|------|---------------|
| **Loading states** | Show skeleton screens (`.skeleton` class) for operations > 300ms. Never leave UI frozen. |
| **Continuous animations** | Use `animate-spin` / `animate-pulse` for loading indicators **only**. No decorative animations. |
| **Reduced motion** | Always check `prefers-reduced-motion: reduce`. Disable transition animations via media query. |
| **Cursor pointer** | All clickable elements: cards, buttons, links, table rows must have `cursor-pointer`. |
| **Transitions** | All hover/state changes: `transition-colors duration-150` or `transition-all duration-200`. |
| **No emojis** | All icons from Lucide React. No emoji icons in UI (headings in docs are OK). |
| **Form labels** | Every input must have a visible `<label>`. No placeholder-only inputs. |
| **Error feedback** | Show inline error messages with `text-[var(--color-error)]`. Toast for network errors. |
| **Focus states** | Visible `ring-2 ring-[var(--color-primary)]` on all interactive elements for keyboard nav. |

### Page: Pipeline Monitor (`/pipeline/[jobId]`)

```
┌─────────────────────────────────────────────────────────────────────┐
│ ← Back to Dashboard                              [Cancel Job]      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  JOB STATUS: ● Running                           Started 2m ago    │
│                                                                     │
│  ┌─ Overall Progress ──────────────────────────────────────────┐   │
│  │  ██████████████████████░░░░░░░░░░░░░░░░░░░  45/120 (38%)   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌── Crawl ──────┐ ┌── Translate ───┐ ┌── Errors ────┐            │
│  │  🔢 78/120    │ │  🔢 45/120     │ │  🔢 2        │            │
│  │  (65%)        │ │  (38%)         │ │              │            │
│  └───────────────┘ └────────────────┘ └──────────────┘            │
│                                                                     │
│  ┌── Worker 1 ─────┐ ┌── Worker 2 ─────┐ ┌── Worker 3 ─────┐     │
│  │ Ch.47: 3/5 ██▒  │ │ Ch.48: 1/4 █▒▒  │ │ idle           │     │
│  │ 第四十七章...    │ │ 第四十八章...    │ │ [dim]waiting   │     │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘     │
│                                                                     │
│  ┌── Event Log ────────────────────────────────────── auto-scroll ┐│
│  │ ✓ Ch.45 translated (Worker 1)              17:23:05           ││
│  │ ✓ Ch.46 translated (Worker 2)              17:23:12           ││
│  │ ↓ Ch.49 crawled                            17:23:15           ││
│  │ ✗ Ch.44 error: API timeout                 17:23:18           ││
│  └────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

**Component Specs:**

| Component | Styling |
|-----------|---------|
| **Progress bar** | Track: `bg-[var(--bg-elevated)] h-3 rounded-full`. Fill: `bg-gradient-to-r from-[var(--color-primary)] to-[#14B8A6]`. Smooth width transition: `transition-all duration-500 ease-out`. |
| **Status badge** | Running: `bg-[var(--color-primary)]/15 text-[var(--color-primary)]` with `animate-pulse` dot. Completed: `bg-[var(--color-success)]/15 text-[var(--color-success)]`. Failed: `bg-[var(--color-error)]/15 text-[var(--color-error)]`. |
| **Stat cards** | 3-column grid: `grid grid-cols-1 md:grid-cols-3 gap-4`. Card: `bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5`. Value: `text-2xl font-bold font-[var(--font-fira-code)]`. Label: `text-[var(--text-muted)] text-xs uppercase tracking-wider`. |
| **Worker cards** | 3-column grid. Active: `border-l-3 border-l-[var(--color-primary)]`. Idle: `opacity-50`. Chapter progress: mini bar inside card. Current chapter: `text-[var(--text-secondary)] text-sm truncate`. |
| **Cancel button** | `bg-[var(--color-error)]/10 text-[var(--color-error)] border border-[var(--color-error)]/30 hover:bg-[var(--color-error)]/20 rounded-lg px-4 py-2 text-sm font-medium transition-colors duration-150 cursor-pointer`. |
| **Event log** | Container: `bg-[var(--bg-surface)] rounded-xl border border-[var(--border-default)] max-h-[40vh] overflow-y-auto`. Each row: `px-4 py-2 border-b border-[var(--border-default)] text-sm`. Icons: `CheckCircle2` green, `Download` yellow, `AlertCircle` red. Timestamp: `text-[var(--text-muted)] text-xs font-mono`. Auto-scroll: `useRef` with `scrollIntoView({ behavior: 'smooth' })` on new events. |

**Interactions:**
- Progress bar updates via WebSocket `progress` events (every chapter status change)
- Worker cards update from `worker_status` in progress data
- Event log auto-scrolls to bottom, pauses if user scrolls up manually
- Cancel button shows confirmation dialog before cancelling
- Back button: `ChevronLeft` icon + "Dashboard"

**Accessibility:**
- Progress bar: `role="progressbar"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- Status badge: use `aria-label` for screen readers (e.g., "Job status: running")
- Event log: `aria-live="polite"` for screen reader announcements
- `prefers-reduced-motion: reduce` → disable `animate-pulse` on status dot, disable smooth scroll

---

### Page: New Translation Wizard (`/new`)

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ①━━━━━━━━②━━━━━━━━③                                               │
│  URL      Options   Confirm                                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  │  STEP 1: Enter Book URL                                     │   │
│  │                                                             │   │
│  │  Book URL                                                   │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │ https://truyenfull.vn/tien-nghich/                    │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │                                                             │   │
│  │  — or —                                                     │   │
│  │                                                             │   │
│  │  Existing Book Directory                                    │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │ books/tien-nghich                                     │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │                                                             │   │
│  │                                          [Next →]           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Component Specs:**

| Component | Styling |
|-----------|---------|
| **Step indicator** | Circles: `w-8 h-8 rounded-full` centered numbers. Active: `bg-[var(--color-primary)] text-white`. Completed: `bg-[var(--color-success)] text-white` with `Check` icon. Future: `bg-[var(--bg-elevated)] text-[var(--text-muted)]`. Connector lines: `h-0.5 flex-1`. Active/done: `bg-[var(--color-primary)]`. Future: `bg-[var(--border-default)]`. |
| **Text inputs** | `bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150`. Label: `text-[var(--text-secondary)] text-sm font-medium mb-2 block`. |
| **Select/Dropdown** | Same base as text input. Custom dropdown with `bg-[var(--bg-elevated)]` options. Active option: `bg-[var(--color-primary-subtle)]`. |
| **Checkbox** | Custom: `w-5 h-5 rounded bg-[var(--bg-surface)] border border-[var(--border-default)]`. Checked: `bg-[var(--color-primary)] border-[var(--color-primary)]` with white check. |
| **Next button** | `bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg px-6 py-2.5 font-medium transition-colors duration-150 cursor-pointer`. With `ChevronRight` icon. |
| **Start button** | CTA: `bg-[var(--color-cta)] hover:bg-[var(--color-cta-hover)] text-white rounded-lg px-8 py-3 font-semibold text-lg transition-colors duration-150 cursor-pointer`. With `Play` icon. Loading: replace text with `Loader2` spinner. |
| **Summary card** | Confirm step: `bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6`. Row: `flex justify-between py-2 border-b border-[var(--border-default)] last:border-0`. Label: `text-[var(--text-muted)]`. Value: `text-[var(--text-primary)] font-medium`. |

**Step 2: Options Grid**

```
┌── Translation Style ─┐  ┌── Workers ──────────┐
│ ▾ Tiên Hiệp          │  │ [1] [2] [③] [4] [5] │
└──────────────────────┘  └──────────────────────┘

┌── Chapter Range (optional) ─────────────────────┐
│  1-100                                           │
└──────────────────────────────────────────────────┘

☑ Auto-generate glossary    ☐ Crawl only
☐ Translate only             ☐ Force re-process
```

**Interactions:**
- Step 1 validates URL format before enabling "Next"
- Step 2 pre-selects `tien_hiep` style and 3 workers
- Workers: either slider or button group (1-5)
- Step 3 shows summary of all selections → "Start Translation" CTA
- On start: POST to `/api/v1/pipeline/start` → redirect to `/pipeline/[jobId]`
- "Start" button shows loading spinner during API call
- Back button on each step (except step 1)

**Accessibility:**
- Step indicator: `aria-current="step"` on active step
- All inputs: visible labels (not placeholder-only)
- Button group (workers): `role="radiogroup"` with `role="radio"` on each
- Keyboard: `Enter` to proceed, tab order follows step flow

---

### Page: Enhanced Dashboard (`/`)

**New section: Active Jobs** (between Stats and Recent Books)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Active Jobs                                                        │
│                                                                     │
│  ┌── Job: abc-123 ─────────────────────────────────────────────┐   │
│  │ ● Running  │  https://truyenfull.vn/tien-nghich/            │   │
│  │            │  45/120 chapters (38%)                          │   │
│  │            │  ██████████████░░░░░░░░░░░░░░░░░░               │   │
│  │            │                                   [View →]      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Component Specs:**

| Component | Styling |
|-----------|---------|
| **Active job card** | `bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5 cursor-pointer hover:border-[var(--border-hover)] transition-all duration-200`. Click → `/pipeline/[jobId]`. |
| **Mini progress bar** | `h-2 rounded-full bg-[var(--bg-elevated)]`. Fill: `bg-[var(--color-primary)]`. |
| **Running dot** | `w-2 h-2 rounded-full bg-[var(--color-primary)] animate-pulse` inline before status text. |
| **Auto-refresh** | `setInterval` every 5s while jobs are `running` or `pending`. Clear interval when all done. |
| **Empty state** | Hide section entirely when no active jobs (don't show "No active jobs" message). |

**Updated Quick Actions:**
- Replace "Open Settings" with "New Translation" → `/new`
- Icon: `PlusCircle` (teal)

**Updated Sidebar Navigation:**

| Order | Icon | Label | Route |
|-------|------|-------|-------|
| 1 | `LayoutDashboard` | Dashboard | `/` |
| 2 | `BookOpen` | Library | `/library` |
| 3 | `PlusCircle` | New Translation | `/new` |
| 4 | `Activity` | Pipeline | `/pipeline` (future: job list) |
| 5 | `Settings` | Settings | `/settings` |

---

## Task 1: Event System

**Files:**
- Create: `src/dich_truyen/services/__init__.py`
- Create: `src/dich_truyen/services/events.py`
- Create: `tests/test_events.py`

The event system is the foundation that decouples pipeline progress from the display layer.

**Step 1: Write failing test**

Create `tests/test_events.py`:

```python
"""Tests for the event pub/sub system."""

import asyncio

import pytest

from dich_truyen.services.events import EventBus, PipelineEvent


def test_event_bus_subscribe_and_emit():
    """Synchronous callback receives events."""
    received = []
    bus = EventBus()
    bus.subscribe(lambda event: received.append(event))
    bus.emit(PipelineEvent(type="test", data={"key": "value"}))
    assert len(received) == 1
    assert received[0].type == "test"
    assert received[0].data["key"] == "value"


def test_event_bus_multiple_subscribers():
    """Multiple subscribers each get a copy of the event."""
    count = {"a": 0, "b": 0}
    bus = EventBus()
    bus.subscribe(lambda _: count.__setitem__("a", count["a"] + 1))
    bus.subscribe(lambda _: count.__setitem__("b", count["b"] + 1))
    bus.emit(PipelineEvent(type="test", data={}))
    assert count["a"] == 1
    assert count["b"] == 1


def test_event_bus_unsubscribe():
    """Unsubscribed callback no longer receives events."""
    received = []
    bus = EventBus()
    callback = lambda event: received.append(event)
    sub_id = bus.subscribe(callback)
    bus.emit(PipelineEvent(type="first", data={}))
    bus.unsubscribe(sub_id)
    bus.emit(PipelineEvent(type="second", data={}))
    assert len(received) == 1
    assert received[0].type == "first"


def test_pipeline_event_to_dict():
    """Event serializes to dict for WebSocket JSON transport."""
    event = PipelineEvent(
        type="chapter_translated",
        data={"chapter": 5, "worker": 1, "total": 100},
        job_id="abc-123",
    )
    d = event.to_dict()
    assert d["type"] == "chapter_translated"
    assert d["job_id"] == "abc-123"
    assert d["data"]["chapter"] == 5
    assert "timestamp" in d
```

**Step 2: Run test — verify it fails**

```bash
uv run pytest tests/test_events.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'dich_truyen.services'`

**Step 3: Implement event system**

Create `src/dich_truyen/services/__init__.py`:

```python
"""Shared service layer for CLI and Web UI."""
```

Create `src/dich_truyen/services/events.py`:

```python
"""Event pub/sub system for pipeline progress.

Enables decoupled communication between pipeline execution and display layers:
- CLI subscribes → Rich console output (future refactor)
- Web subscribes → WebSocket → React state updates
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class PipelineEvent:
    """A single pipeline event."""

    type: str
    data: dict = field(default_factory=dict)
    job_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Serialize for WebSocket JSON transport."""
        return {
            "type": self.type,
            "data": self.data,
            "job_id": self.job_id,
            "timestamp": self.timestamp,
        }


class EventBus:
    """Simple synchronous event bus.

    Subscribers receive events synchronously in the emitter's thread.
    For WebSocket delivery, the subscriber puts events into an asyncio.Queue.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, Callable[[PipelineEvent], None]] = {}

    def subscribe(self, callback: Callable[[PipelineEvent], None]) -> str:
        """Register a callback. Returns subscription ID for unsubscribe."""
        sub_id = str(uuid.uuid4())
        self._subscribers[sub_id] = callback
        return sub_id

    def unsubscribe(self, sub_id: str) -> None:
        """Remove a subscriber by ID."""
        self._subscribers.pop(sub_id, None)

    def emit(self, event: PipelineEvent) -> None:
        """Send event to all subscribers."""
        for callback in list(self._subscribers.values()):
            try:
                callback(event)
            except Exception:
                pass  # Never let a bad subscriber crash the emitter
```

**Step 4: Run tests — verify they pass**

```bash
uv run pytest tests/test_events.py -v
```

Expected: 4 PASS

**Step 5: Commit**

```bash
git add src/dich_truyen/services/ tests/test_events.py
git commit -m "feat(services): add event pub/sub system"
```

---

## Task 2: PipelineService

**Files:**
- Create: `src/dich_truyen/services/pipeline_service.py`
- Create: `tests/test_pipeline_service.py`

The `PipelineService` wraps `StreamingPipeline` and emits events. It manages multiple concurrent jobs and provides a dict-based API for REST/WebSocket consumers.

**Step 1: Write failing test**

Create `tests/test_pipeline_service.py`:

```python
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
```

**Step 2: Run test — verify it fails**

```bash
uv run pytest tests/test_pipeline_service.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement PipelineService**

Create `src/dich_truyen/services/pipeline_service.py`:

```python
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
                self._emit(job_id, f"chapter_{status.value}", {
                    "chapter_index": chapter.index,
                    "chapter_title": chapter.title_cn or "",
                    "status": status.value,
                })
                # Update job progress from pipeline stats
                job["progress"] = {
                    "total_chapters": pipeline.stats.total_chapters,
                    "crawled": pipeline.stats.chapters_crawled,
                    "translated": pipeline.stats.chapters_translated,
                    "errors": pipeline.stats.crawl_errors + pipeline.stats.translate_errors,
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
            self._emit(job_id, "job_completed", {
                "result": result.model_dump(),
            })

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
        self._event_bus.emit(PipelineEvent(
            type=event_type,
            data=data,
            job_id=job_id,
        ))
```

**Step 4: Run tests — verify they pass**

```bash
uv run pytest tests/test_pipeline_service.py -v
```

Expected: 5 PASS

**Step 5: Run all existing tests to verify no breakage**

```bash
uv run pytest tests/ -v 2>&1 | Select-Object -Last 5
```

Expected: 130+ tests pass, 0 failures.

**Step 6: Commit**

```bash
git add src/dich_truyen/services/ tests/test_pipeline_service.py
git commit -m "feat(services): add PipelineService with job management"
```

---

## Task 3: Pipeline REST API Endpoints

**Files:**
- Create: `src/dich_truyen/api/routes/pipeline.py`
- Modify: `src/dich_truyen/api/server.py`
- Modify: `tests/test_api.py`

**Step 1: Write failing tests**

Add to `tests/test_api.py`:

```python
def test_start_pipeline_requires_url_or_book_dir():
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
    assert data["status"] == "pending"
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
```

**Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/test_api.py::test_start_pipeline_requires_url_or_book_dir -v
```

**Step 3: Implement pipeline routes**

Create `src/dich_truyen/api/routes/pipeline.py`:

```python
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
```

Update `src/dich_truyen/api/server.py` to register pipeline routes and create shared services:

```python
# Add imports at top
from dich_truyen.api.routes import books, pipeline
from dich_truyen.services.events import EventBus
from dich_truyen.services.pipeline_service import PipelineService

# Inside create_app(), after books router:
event_bus = EventBus()
pipeline_service = PipelineService(event_bus)
pipeline.set_services(event_bus, pipeline_service)
app.include_router(pipeline.router)

# Store on app.state for WebSocket access
app.state.event_bus = event_bus
app.state.pipeline_service = pipeline_service
```

**Step 4: Run tests — verify they pass**

```bash
uv run pytest tests/test_api.py -v
```

Expected: all PASS (existing + new)

**Step 5: Run all tests**

```bash
uv run pytest tests/ -v 2>&1 | Select-Object -Last 5
```

Expected: all pass

**Step 6: Commit**

```bash
git add src/dich_truyen/api/ tests/test_api.py
git commit -m "feat(api): add pipeline start/list/cancel endpoints"
```

---

## Task 4: WebSocket Endpoint

**Files:**
- Create: `src/dich_truyen/api/websocket.py`
- Modify: `src/dich_truyen/api/server.py`
- Modify: `tests/test_api.py`

**Step 1: Write failing test**

Add to `tests/test_api.py`:

```python
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
```

**Step 2: Implement WebSocket handler**

Create `src/dich_truyen/api/websocket.py`:

```python
"""WebSocket handler for real-time pipeline events."""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from dich_truyen.services.events import EventBus, PipelineEvent


router = APIRouter()


@router.websocket("/ws/pipeline/{job_id}")
async def pipeline_websocket(websocket: WebSocket, job_id: str) -> None:
    """Stream pipeline events for a specific job via WebSocket."""
    await websocket.accept()

    event_bus: EventBus = websocket.app.state.event_bus
    queue: asyncio.Queue[PipelineEvent] = asyncio.Queue()

    # Subscribe to events for this job
    def on_event(event: PipelineEvent) -> None:
        if event.job_id == job_id:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop events if client can't keep up

    sub_id = event_bus.subscribe(on_event)

    try:
        while True:
            try:
                # Wait for events with timeout to check connection
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(event.to_dict())
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_json({"type": "heartbeat"})
            except WebSocketDisconnect:
                break
    finally:
        event_bus.unsubscribe(sub_id)
```

Update `src/dich_truyen/api/server.py` to include WebSocket router:

```python
from dich_truyen.api import websocket
app.include_router(websocket.router)
```

**Step 3: Run tests**

```bash
uv run pytest tests/test_api.py -v
```

Expected: all PASS

**Step 4: Commit**

```bash
git add src/dich_truyen/api/ tests/test_api.py
git commit -m "feat(api): add WebSocket endpoint for pipeline events"
```

---

## Task 5: Frontend Types and API Client Extensions

**Files:**
- Modify: `web/src/lib/types.ts`
- Modify: `web/src/lib/api.ts`
- Create: `web/src/hooks/useWebSocket.ts`

**Step 1: Add pipeline types**

Add to `web/src/lib/types.ts`:

```typescript
/** Pipeline job. */
export interface PipelineJob {
  id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  url: string | null;
  book_dir: string | null;
  style: string;
  workers: number;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
  progress: PipelineProgress;
  error: string | null;
}

/** Pipeline progress stats. */
export interface PipelineProgress {
  total_chapters: number;
  crawled: number;
  translated: number;
  errors: number;
  worker_status?: Record<string, string>;
  glossary_count?: number;
}

/** WebSocket pipeline event. */
export interface PipelineEventMessage {
  type: string;
  data: Record<string, unknown>;
  job_id: string;
  timestamp: number;
}

/** Start pipeline request. */
export interface StartPipelineRequest {
  url?: string;
  book_dir?: string;
  style?: string;
  workers?: number;
  chapters?: string;
  crawl_only?: boolean;
  translate_only?: boolean;
  no_glossary?: boolean;
  force?: boolean;
}
```

**Step 2: Add API client functions**

Add to `web/src/lib/api.ts`:

```typescript
export async function startPipeline(
  request: StartPipelineRequest
): Promise<PipelineJob> {
  const res = await fetch(`${API_BASE}/pipeline/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function getPipelineJobs(): Promise<PipelineJob[]> {
  return fetchJson<PipelineJob[]>(`${API_BASE}/pipeline/jobs`);
}

export async function getPipelineJob(jobId: string): Promise<PipelineJob> {
  return fetchJson<PipelineJob>(`${API_BASE}/pipeline/jobs/${jobId}`);
}

export async function cancelPipelineJob(jobId: string): Promise<PipelineJob> {
  const res = await fetch(`${API_BASE}/pipeline/jobs/${jobId}/cancel`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

**Step 3: Create WebSocket hook**

Create `web/src/hooks/useWebSocket.ts`:

```typescript
"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { PipelineEventMessage } from "@/lib/types";

export function usePipelineWebSocket(jobId: string | null) {
  const [events, setEvents] = useState<PipelineEventMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!jobId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // Connect to FastAPI directly on port 8000 for WebSocket
    const ws = new WebSocket(`${protocol}//localhost:8000/ws/pipeline/${jobId}`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      const msg: PipelineEventMessage = JSON.parse(event.data);
      if (msg.type !== "heartbeat") {
        setEvents((prev) => [...prev.slice(-200), msg]); // Keep last 200
      }
    };

    wsRef.current = ws;
    return () => ws.close();
  }, [jobId]);

  useEffect(() => {
    const cleanup = connect();
    return cleanup;
  }, [connect]);

  const latestProgress = events
    .filter((e) => e.type === "progress")
    .at(-1)?.data;

  return { events, connected, latestProgress };
}
```

**Step 4: Verify build**

```bash
cd web && npm run build
```

Expected: builds successfully

**Step 5: Commit**

```bash
git add web/src/
git commit -m "feat(web): add pipeline types, API client, and WebSocket hook"
```

---

## Task 6: Pipeline Monitor Page

**Files:**
- Create: `web/src/app/pipeline/[jobId]/page.tsx`
- Create: `web/src/components/pipeline/ProgressPanel.tsx`
- Create: `web/src/components/pipeline/WorkerCards.tsx`
- Create: `web/src/components/pipeline/EventLog.tsx`

> **Design reference:** MASTER.md → Cards, Status Badges, Progress Bars

**Step 1: Create ProgressPanel component**

Create `web/src/components/pipeline/ProgressPanel.tsx`:
- Overall progress bar: teal fill, `h-3 rounded-full`
- Stats row: Crawled / Translated / Errors as mini stat cards
- ETA (estimated from rate if available)
- Job status badge: `running` (teal pulse), `completed` (green), `failed` (red), `cancelled` (yellow)

**Step 2: Create WorkerCards component**

Create `web/src/components/pipeline/WorkerCards.tsx`:
- Grid of worker status cards (`grid grid-cols-1 md:grid-cols-3 gap-4`)
- Each card: worker ID, current chapter, chunk progress
- Active workers: `border-[var(--color-primary)]` left accent
- Idle workers: dimmed styling

**Step 3: Create EventLog component**

Create `web/src/components/pipeline/EventLog.tsx`:
- Scrolling list of recent events, newest at bottom
- Auto-scroll to bottom on new events
- Event type icons: `CheckCircle2` for translated, `Download` for crawled, `AlertCircle` for error
- Max height: `max-h-[40vh] overflow-y-auto`

**Step 4: Create Pipeline Monitor page**

Create `web/src/app/pipeline/[jobId]/page.tsx`:
- `usePipelineWebSocket(jobId)` for real-time updates
- Fetch job info on mount via `getPipelineJob()`
- Layout: ProgressPanel at top → WorkerCards → EventLog
- Cancel button: `bg-[var(--color-error)]` styled button
- Back link to Dashboard
- Loading/error states

**Step 5: Add Pipeline route to sidebar**

Update `web/src/components/layout/Sidebar.tsx`:
- Add `Activity` icon (from Lucide) → "Pipeline" nav item → `/pipeline`
- This will be a list of active/recent jobs (but for now, direct job links)

**Step 6: Verify with build**

```bash
cd web && npm run lint && npm run build
```

Expected: builds with all routes including `/pipeline/[jobId]`

**Step 7: Commit**

```bash
git add web/src/
git commit -m "feat(web): add real-time pipeline monitor page"
```

---

## Task 7: New Translation Wizard

**Files:**
- Create: `web/src/app/new/page.tsx`
- Create: `web/src/components/wizard/WizardSteps.tsx`

> **Design reference:** Design doc → New Translation Wizard (4 steps)

**Step 1: Create WizardSteps component**

Create `web/src/components/wizard/WizardSteps.tsx`:
- Step indicator: numbered circles connected with lines
- Active step: teal circle, previous: green check, future: gray
- Content area switches per step

**Step 2: Create New Translation page**

Create `web/src/app/new/page.tsx` with 3 steps:

**Step A: Enter URL**
- Text input: `bg-[var(--bg-surface)]` with border, `focus:border-[var(--color-primary)]`
- Optional: book directory input (for translate-only)
- "Next" button in CTA orange

**Step B: Configure Options**
- Style dropdown: `tien_hiep`, `kiem_hiep`, `huyen_huyen`, `do_thi`
- Workers slider/input (1-5, default 3)
- Chapter range input (optional)
- Checkboxes: Crawl only, translate only, auto-glossary
- All styled with design system

**Step C: Confirm & Start**
- Summary card: URL, style, workers, chapters
- "Start Translation" CTA button
- On click: calls `startPipeline()` → redirects to `/pipeline/[jobId]`

**Step 3: Add "New Translation" to Dashboard**

Update `web/src/app/page.tsx`:
- Change "Open Settings" quick action to "New Translation" linking to `/new`
- Add `PlusCircle` icon

**Step 4: Add to sidebar navigation**

Update `web/src/components/layout/Sidebar.tsx`:
- Add `PlusCircle` icon → "New Translation" → `/new`

**Step 5: Verify with build**

```bash
cd web && npm run lint && npm run build
```

**Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(web): add new translation wizard"
```

---

## Task 8: Enhanced Dashboard with Active Jobs

**Files:**
- Modify: `web/src/app/page.tsx`
- Create: `web/src/components/dashboard/ActiveJobs.tsx`

**Step 1: Create ActiveJobs component**

Create `web/src/components/dashboard/ActiveJobs.tsx`:
- Fetches from `/api/v1/pipeline/jobs`
- Shows running/pending jobs with mini progress bars
- Each job card: book URL/title, progress %, status badge
- Click → navigate to `/pipeline/[jobId]`
- Empty state: "No active jobs" message
- Auto-refreshes every 5 seconds while jobs are running

**Step 2: Update Dashboard page**

Update `web/src/app/page.tsx`:
- Add `ActiveJobs` component between stats and recent books
- Section title: "Active Jobs" with `Activity` Lucide icon
- Only shows section when there are active (running/pending) jobs

**Step 3: Verify with build**

```bash
cd web && npm run lint && npm run build
```

**Step 4: Commit**

```bash
git add web/src/
git commit -m "feat(web): add active jobs to dashboard"
```

---

## Task 9: Final Integration & Polish

**Step 1: Run all Python tests**

```bash
uv run pytest tests/ -v
```

Expected: ALL pass (existing + new event/service/API tests).

**Step 2: Run frontend lint**

```bash
cd web && npm run lint
```

Expected: 0 errors.

**Step 3: Build frontend**

```bash
cd web && npm run build
```

Expected: all routes compile.

**Step 4: Full integration test**

Run both servers and verify the complete flow:
1. `uv run dich-truyen ui` → both servers start
2. Dashboard loads with stats
3. Click "New Translation" → Wizard page
4. Enter a URL, configure options, start
5. Redirected to Pipeline Monitor page
6. WebSocket shows real-time progress (crawl → translate events)
7. Worker cards update in real-time
8. Event log scrolls automatically
9. Cancel button works
10. CLI `uv run dich-truyen pipeline --help` still works

**Step 5: Verify CLI unchanged**

```bash
uv run dich-truyen --help
uv run dich-truyen pipeline --help
uv run dich-truyen glossary show --book-dir books/<dir>
```

Expected: all CLI commands work identically.

**Step 6: Commit**

```bash
git add -A
git commit -m "feat(web): complete Phase 2 — pipeline monitor and translation wizard"
```

---

## Verification Plan

### Automated Tests

```bash
# All Python tests (existing + new)
uv run pytest tests/ -v

# Frontend lint
cd web && npm run lint

# Frontend build (type checking)
cd web && npm run build
```

### Manual Verification

> [!IMPORTANT]
> The Pipeline Monitor requires a real `OPENAI_API_KEY` to test the actual translation flow.
> For WebSocket testing without API keys, create a mock job and verify the Monitor page connects.

1. Start app: `uv run dich-truyen ui`
2. Dashboard: verify stats, active jobs section visible
3. Click "New Translation" → fill URL → configure → start
4. Pipeline Monitor: verify real-time progress updates
5. Worker cards update as chunks translate
6. Event log auto-scrolls
7. Cancel button stops the job
8. CLI: `uv run dich-truyen pipeline --help` → still shows all options
9. CLI: `uv run dich-truyen --version` → prints version
