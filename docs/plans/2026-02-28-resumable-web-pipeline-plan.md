# Resumable Web UI Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow the Web UI to detect books with incomplete translations and resume them after app restart — matching the CLI's resume behavior.

**Architecture:** Add a `last_pipeline_settings.json` file per book dir (saved when pipeline runs). Add a `GET /api/v1/pipeline/resumable` endpoint that scans `books/` for incomplete books. Frontend shows a "Resumable Books" section on the pipeline page and a contextual banner on the book detail page. Resume action uses the existing `POST /api/v1/pipeline/start` endpoint.

**Tech Stack:** Python/FastAPI (backend), Next.js/React/TypeScript (frontend), pytest (tests)

---

## Task 1: Save `last_pipeline_settings.json` on pipeline run

**Files:**
- Modify: `src/dich_truyen/services/pipeline_service.py`
- Test: `tests/test_pipeline_service.py`

**Step 1: Write the failing test**

Add to `tests/test_pipeline_service.py`:

```python
import json


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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pipeline_service.py::test_save_pipeline_settings_creates_file tests/test_pipeline_service.py::test_save_pipeline_settings_overwrites -v`
Expected: FAIL with `ImportError` (function doesn't exist yet)

**Step 3: Write minimal implementation**

Add to `src/dich_truyen/services/pipeline_service.py`:

```python
import json
from datetime import datetime, timezone

def _save_pipeline_settings(
    book_dir: Path,
    style: str = "tien_hiep",
    workers: int = 3,
    chapters: Optional[str] = None,
    crawl_only: bool = False,
    translate_only: bool = False,
    no_glossary: bool = False,
) -> None:
    """Save pipeline settings to book directory for resume pre-fill."""
    settings = {
        "style": style,
        "workers": workers,
        "chapters": chapters,
        "crawl_only": crawl_only,
        "translate_only": translate_only,
        "no_glossary": no_glossary,
        "last_run_at": datetime.now(timezone.utc).isoformat(),
    }
    settings_file = book_dir / "last_pipeline_settings.json"
    settings_file.write_text(json.dumps(settings, indent=2), encoding="utf-8")
```

Then call `_save_pipeline_settings()` inside `PipelineService._run_pipeline()`, right after `job["book_dir"]` is determined (around line 146), passing the job's settings:

```python
# Save pipeline settings for resume
_save_pipeline_settings(
    book_dir=target_dir,
    style=job["style"],
    workers=job["workers"],
    chapters=job["chapters"],
    crawl_only=job["crawl_only"],
    translate_only=job["translate_only"],
    no_glossary=job["no_glossary"],
)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pipeline_service.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/dich_truyen/services/pipeline_service.py tests/test_pipeline_service.py
git commit -m "feat: save last_pipeline_settings.json on pipeline run"
```

---

## Task 2: Add `GET /api/v1/pipeline/resumable` endpoint

**Files:**
- Modify: `src/dich_truyen/api/routes/pipeline.py`
- Modify: `src/dich_truyen/api/routes/books.py` (import `_books_dir`)
- Test: `tests/test_api.py`

**Step 1: Write the failing test**

Add to `tests/test_api.py` (or create a new `tests/test_api_pipeline.py` if test_api.py is too large):

```python
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from dich_truyen.api.server import create_app
from dich_truyen.utils.progress import BookProgress, Chapter, ChapterStatus


@pytest.fixture
def app_with_books(tmp_path):
    """Create app with a books dir containing a book with incomplete chapters."""
    books_dir = tmp_path / "books"
    books_dir.mkdir()

    # Create book with mixed statuses (incomplete)
    book_dir = books_dir / "test-book"
    book_dir.mkdir()
    (book_dir / "raw").mkdir()

    progress = BookProgress(
        url="https://example.com/book",
        title="Test Book",
        title_vi="Sách Test",
        author="Author",
        author_vi="Tác giả",
        encoding="utf-8",
        chapters=[
            Chapter(index=1, id="ch1", url="https://example.com/1", title_cn="第一章", status=ChapterStatus.TRANSLATED),
            Chapter(index=2, id="ch2", url="https://example.com/2", title_cn="第二章", status=ChapterStatus.CRAWLED),
            Chapter(index=3, id="ch3", url="https://example.com/3", title_cn="第三章", status=ChapterStatus.PENDING),
        ],
    )
    progress.save(book_dir)

    # Save pipeline settings
    settings = {"style": "tien_hiep", "workers": 3, "last_run_at": "2026-02-28T00:00:00"}
    (book_dir / "last_pipeline_settings.json").write_text(json.dumps(settings))

    app = create_app(books_dir=books_dir)
    return TestClient(app)


@pytest.fixture
def app_all_translated(tmp_path):
    """App where all chapters are translated (should not appear in resumable)."""
    books_dir = tmp_path / "books"
    books_dir.mkdir()

    book_dir = books_dir / "done-book"
    book_dir.mkdir()

    progress = BookProgress(
        url="https://example.com/done",
        title="Done Book",
        title_vi="Sách Hoàn Thành",
        author="Author",
        author_vi="Tác giả",
        encoding="utf-8",
        chapters=[
            Chapter(index=1, id="ch1", url="https://example.com/1", title_cn="第一章", status=ChapterStatus.TRANSLATED),
        ],
    )
    progress.save(book_dir)

    app = create_app(books_dir=books_dir)
    return TestClient(app)


def test_resumable_returns_incomplete_books(app_with_books):
    """Resumable endpoint returns books with incomplete chapters."""
    response = app_with_books.get("/api/v1/pipeline/resumable")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    book = data[0]
    assert book["book_id"] == "test-book"
    assert book["title_vi"] == "Sách Test"
    assert book["translated"] == 1
    assert book["crawled"] == 1
    assert book["pending"] == 1
    assert book["total_chapters"] == 3
    assert book["last_settings"]["style"] == "tien_hiep"


def test_resumable_excludes_fully_translated(app_all_translated):
    """Fully translated books do not appear in resumable list."""
    response = app_all_translated.get("/api/v1/pipeline/resumable")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api.py::test_resumable_returns_incomplete_books tests/test_api.py::test_resumable_excludes_fully_translated -v`
Expected: FAIL (404 — endpoint doesn't exist yet)

> Note: If `BookProgress` requires `patterns` field, add `patterns=BookPatterns()` to the fixture. Check the model and adjust.

**Step 3: Write minimal implementation**

Add to `src/dich_truyen/api/routes/pipeline.py`:

```python
import json

from dich_truyen.api.routes.books import _books_dir
from dich_truyen.utils.progress import BookProgress, ChapterStatus


@router.get("/resumable")
async def get_resumable_books() -> list[dict]:
    """List books with incomplete translation progress."""
    resumable = []

    if not _books_dir.exists():
        return resumable

    for book_dir in sorted(_books_dir.iterdir()):
        book_json = book_dir / "book.json"
        if not book_json.exists():
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

        resumable.append({
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
        })

    return resumable
```

Also update `src/dich_truyen/api/routes/pipeline.py` to share `_books_dir` — the `_books_dir` is set in `books.py`. Import it directly:

```python
from dich_truyen.api.routes.books import _books_dir
```

> **Important:** The route `/resumable` must be registered BEFORE `/jobs/{job_id}` to avoid FastAPI treating "resumable" as a `job_id` path parameter. Since we're adding to the pipeline router, verify route ordering.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_api.py -v -k resumable`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/dich_truyen/api/routes/pipeline.py tests/test_api.py
git commit -m "feat: add GET /api/v1/pipeline/resumable endpoint"
```

---

## Task 3: Add `getResumableBooks()` to frontend API client + types

**Files:**
- Modify: `web/src/lib/types.ts`
- Modify: `web/src/lib/api.ts`

**Step 1: Add TypeScript interface**

Add to `web/src/lib/types.ts`:

```typescript
/** Book with incomplete translation, available for resume. */
export interface ResumableBook {
  book_dir: string;
  book_id: string;
  title: string;
  title_vi: string;
  total_chapters: number;
  translated: number;
  crawled: number;
  pending: number;
  errors: number;
  last_settings: Partial<StartPipelineRequest> | null;
  last_run_at: string | null;
}
```

**Step 2: Add API function**

Add to `web/src/lib/api.ts`:

```typescript
import type { ResumableBook } from "./types";

export async function getResumableBooks(): Promise<ResumableBook[]> {
  return fetchJson<ResumableBook[]>(`${API_BASE}/pipeline/resumable`);
}
```

**Step 3: Commit**

```bash
git add web/src/lib/types.ts web/src/lib/api.ts
git commit -m "feat: add ResumableBook type and getResumableBooks API function"
```

---

## Task 4: Add "Resumable Books" section to Pipeline page

**Files:**
- Create: `web/src/components/pipeline/ResumableSection.tsx`
- Modify: `web/src/app/pipeline/page.tsx`

**Step 1: Create ResumableSection component**

Create `web/src/components/pipeline/ResumableSection.tsx`:

A new React component that:
- Calls `getResumableBooks()` on mount (with polling every 30s)
- For each resumable book, renders a card with:
  - Book title (title_vi fallback to title)
  - Progress bar (`translated / total_chapters`)
  - Status badges (`X pending · Y crawled · Z errors`)
  - "▶ Resume" button — calls `startPipeline({ book_dir })` then `router.push(/pipeline/${job.id})`
  - "⚙ Options" button — toggles an inline form pre-filled with `last_settings`
- The inline form has: style dropdown (from `getStyles()`), workers number input, chapters text input, translate_only and force checkboxes
- Matches existing design system (CSS variables, lucide icons, same card styling as `JobCard`)

**Step 2: Integrate into pipeline page**

Modify `web/src/app/pipeline/page.tsx`:
- Import and render `<ResumableSection />` at the top of the page, between the header and the Active Jobs section
- Only renders if there are resumable books

**Step 3: Verify in browser**

1. Start the app: `uv run dich-truyen ui`
2. Ensure there is at least one book with incomplete chapters in `books/`
3. Navigate to Pipeline page (`http://localhost:3000/pipeline`)
4. Verify the "Resumable Books" section appears with correct progress info
5. Click "Resume" — verify it starts a job and redirects to job detail page
6. Click "Options" — verify the form expands with pre-filled settings

**Step 4: Commit**

```bash
git add web/src/components/pipeline/ResumableSection.tsx web/src/app/pipeline/page.tsx
git commit -m "feat: add Resumable Books section to pipeline page"
```

---

## Task 5: Add resume banner to Book Detail page

**Files:**
- Create: `web/src/components/library/ResumeBanner.tsx`
- Find and modify: the book detail page in `web/src/app/library/[slug]/page.tsx` (or equivalent)

**Step 1: Create ResumeBanner component**

Create `web/src/components/library/ResumeBanner.tsx`:

A banner component that:
- Receives `bookId: string` and `bookDetail: BookDetail` props
- Calculates remaining = total - translated
- If remaining > 0, renders a banner:
  - Alert-style box with warning color
  - Text: "⚠ Translation incomplete — {remaining} chapters remaining"
  - "▶ Resume" button — calls `startPipeline({ book_dir: bookId })` then redirects
  - "⚙ Resume with options..." button — same inline form as ResumableSection
- Fetches `getResumableBooks()` to get `last_settings` for pre-fill (filter by book_id)

**Step 2: Integrate into book detail page**

Modify the book detail page to render `<ResumeBanner />` at the top, above the chapter table.

**Step 3: Verify in browser**

1. Navigate to a book with incomplete chapters in Library
2. Verify the banner appears at the top
3. Verify "Resume" button works and redirects to pipeline job
4. Verify "Resume with options" expands the form

**Step 4: Commit**

```bash
git add web/src/components/library/ResumeBanner.tsx web/src/app/library/*/page.tsx
git commit -m "feat: add resume banner to book detail page"
```

---

## Task 6: Final verification and cleanup

**Step 1: Run all backend tests**

```bash
uv run pytest tests/ -v
```

Expected: ALL PASS — no regressions.

**Step 2: Run linter**

```bash
uv run ruff check .
uv run ruff format .
```

**Step 3: Full end-to-end test**

1. Start the app with `uv run dich-truyen ui`
2. Start a pipeline for a book via the Web UI
3. Wait for some chapters to translate (at least 5-10)
4. Kill the app (Ctrl+C)
5. Restart the app
6. Navigate to Pipeline page — verify the book appears in "Resumable Books"
7. Click "Resume" — verify it starts from where it left off (not re-translating already-done chapters)
8. Navigate to the book's detail page — verify the resume banner shows
9. Verify "Resume with options" pre-fills with last settings

**Step 4: Commit any final fixes**

```bash
git add -A
git commit -m "feat: final polish for resumable web pipeline"
```

---

## Verification Plan

### Automated Tests

| Command | What it tests |
|---------|---------------|
| `uv run pytest tests/test_pipeline_service.py -v` | `_save_pipeline_settings()` saves/overwrites JSON correctly |
| `uv run pytest tests/test_api.py -v -k resumable` | `/resumable` endpoint returns incomplete books, excludes done books |
| `uv run pytest tests/ -v` | Full regression — no existing tests broken |
| `uv run ruff check .` | No lint errors |

### Manual Verification

Full end-to-end test as described in Task 6, Step 3.
