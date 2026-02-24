# Desktop UI Phase 1: "See Your Library" — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Working web UI that displays existing books and lets you read translated chapters in the browser.

**Architecture:** FastAPI backend (read-only endpoints reading `books/*/book.json` and chapter `.txt` files) + Next.js frontend (dark theme, sidebar nav, 3 pages: Library, Book Detail, Chapter Reader). CLI remains 100% unchanged.

**Tech Stack:** Python (FastAPI, uvicorn) · TypeScript (React, Next.js 15, App Router) · Tailwind CSS · Lucide React icons

**Design Doc:** [desktop-ui-design.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/docs/plans/2026-02-24-desktop-ui-design.md)

**Design System:** [MASTER.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/design-system/dich-truyen/MASTER.md) — Source of truth for colors, typography, components, page layouts

### Design System Quick Reference

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0B1120` | Main background |
| `--bg-surface` | `#111827` | Cards, panels, sidebar |
| `--bg-elevated` | `#1F2937` | Hover states, active items |
| `--color-primary` | `#0D9488` (teal) | Active nav, progress bars, links |
| `--color-cta` | `#F97316` (orange) | Action buttons |
| `--text-primary` | `#F9FAFB` | Headings, main content |
| `--text-secondary` | `#9CA3AF` | Descriptions, labels |
| Heading font | Fira Code | Page titles, card titles |
| Body font | Fira Sans | Body text, labels |
| Reader font | Noto Serif | Chapter reading view |
| Icons | Lucide React | All UI icons (no emojis) |
| Status colors | `#10B981` / `#F59E0B` / `#3B82F6` / `#EF4444` | Translated / Crawled / Pending / Error |

---

## Task 1: Add Python Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add fastapi and uvicorn to dependencies**

Add to the `dependencies` list in `pyproject.toml`:

```toml
"fastapi>=0.115.0",
"uvicorn[standard]>=0.34.0",
```

Also add `httpx` to dev/test dependencies (required by FastAPI's `TestClient`):

```toml
[project.optional-dependencies]
dev = [
    # ... existing dev deps ...
    "httpx>=0.27.0",
]
```

**Step 2: Sync dependencies**

```bash
uv sync
```

Expected: installs successfully, no errors.

**Step 3: Verify CLI still works**

```bash
uv run dich-truyen --version
```

Expected: prints version number.

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat(ui): add fastapi and uvicorn dependencies"
```

---

## Task 2: Create FastAPI Server Skeleton

**Files:**
- Create: `src/dich_truyen/api/__init__.py`
- Create: `src/dich_truyen/api/server.py`

**Step 1: Write test for server creation**

Create `tests/test_api.py`:

```python
"""Tests for the FastAPI API server."""

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
```

**Step 2: Run test — verify it fails**

```bash
uv run pytest tests/test_api.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'dich_truyen.api'`

**Step 3: Create API package and server**

Create `src/dich_truyen/api/__init__.py`:

```python
"""FastAPI web server for dich-truyen."""
```

Create `src/dich_truyen/api/server.py`:

```python
"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dich_truyen import __version__


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Dịch Truyện API",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    return app
```

**Step 4: Run test — verify it passes**

```bash
uv run pytest tests/test_api.py -v
```

Expected: 2 PASS

**Step 5: Commit**

```bash
git add src/dich_truyen/api/ tests/test_api.py
git commit -m "feat(api): create FastAPI server skeleton with health endpoint"
```

---

## Task 3: Books List API Endpoint

**Files:**
- Create: `src/dich_truyen/api/routes/__init__.py`
- Create: `src/dich_truyen/api/routes/books.py`
- Modify: `src/dich_truyen/api/server.py`
- Modify: `tests/test_api.py`

**Step 1: Write test**

Add to `tests/test_api.py`:

```python
from pathlib import Path
import json
import tempfile


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
```

**Step 2: Run test — verify it fails**

```bash
uv run pytest tests/test_api.py::test_list_books -v
```

Expected: FAIL — `create_app() got an unexpected keyword argument 'books_dir'`

**Step 3: Implement books route**

Create `src/dich_truyen/api/routes/__init__.py`:

```python
"""API route modules."""
```

Create `src/dich_truyen/api/routes/books.py`:

```python
"""Book listing and detail API routes."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dich_truyen.utils.progress import BookProgress, ChapterStatus


router = APIRouter(prefix="/api/v1/books", tags=["books"])

# Set by server.py at startup
_books_dir: Path = Path("books")


def set_books_dir(books_dir: Path) -> None:
    """Set the books directory path."""
    global _books_dir
    _books_dir = books_dir


class BookSummary(BaseModel):
    """Book summary for list view."""

    id: str
    title: str
    title_vi: str
    author: str
    author_vi: str
    url: str
    total_chapters: int
    pending_chapters: int
    crawled_chapters: int
    translated_chapters: int
    formatted_chapters: int
    exported_chapters: int
    error_chapters: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("", response_model=list[BookSummary])
async def list_books() -> list[BookSummary]:
    """List all books with summary stats."""
    books: list[BookSummary] = []

    if not _books_dir.exists():
        return books

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

        books.append(BookSummary(
            id=book_dir.name,
            title=progress.title,
            title_vi=progress.title_vi,
            author=progress.author,
            author_vi=progress.author_vi,
            url=progress.url,
            total_chapters=len(progress.chapters),
            pending_chapters=status_counts[ChapterStatus.PENDING],
            crawled_chapters=status_counts[ChapterStatus.CRAWLED],
            translated_chapters=status_counts[ChapterStatus.TRANSLATED],
            formatted_chapters=status_counts.get(ChapterStatus.FORMATTED, 0),
            exported_chapters=status_counts.get(ChapterStatus.EXPORTED, 0),
            error_chapters=status_counts[ChapterStatus.ERROR],
            created_at=str(progress.created_at) if progress.created_at else None,
            updated_at=str(progress.updated_at) if progress.updated_at else None,
        ))

    return books
```

Update `src/dich_truyen/api/server.py` — add `books_dir` parameter to `create_app()` and include the books router:

```python
"""FastAPI application factory."""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dich_truyen import __version__
from dich_truyen.api.routes import books


def create_app(books_dir: Optional[Path] = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Dịch Truyện API",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure books directory
    if books_dir:
        books.set_books_dir(books_dir)

    app.include_router(books.router)

    @app.get("/api/v1/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    return app
```

**Step 4: Run tests — verify they pass**

```bash
uv run pytest tests/test_api.py -v
```

Expected: all PASS

**Step 5: Commit**

```bash
git add src/dich_truyen/api/ tests/test_api.py
git commit -m "feat(api): add book listing endpoint with chapter stats"
```

---

## Task 4: Book Detail & Chapter Content Endpoints

**Files:**
- Modify: `src/dich_truyen/api/routes/books.py`
- Modify: `tests/test_api.py`

**Step 1: Write tests**

Add to `tests/test_api.py`:

```python
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
```

**Step 2: Run — verify fails**

```bash
uv run pytest tests/test_api.py::test_get_book_detail -v
```

**Step 3: Implement endpoints**

Add to `src/dich_truyen/api/routes/books.py`:

```python
class ChapterDetail(BaseModel):
    """Chapter info for book detail view."""
    index: int
    id: str
    title_cn: str
    title_vi: Optional[str] = None
    status: str
    has_raw: bool = False
    has_translated: bool = False


class BookDetail(BaseModel):
    """Full book detail."""
    id: str
    title: str
    title_vi: str
    author: str
    author_vi: str
    url: str
    encoding: str
    chapters: list[ChapterDetail]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChapterContent(BaseModel):
    """Chapter text content."""
    chapter_index: int
    content: str


@router.get("/{book_id}", response_model=BookDetail)
async def get_book(book_id: str) -> BookDetail:
    """Get book detail with chapter list."""
    book_dir = _books_dir / book_id
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail="Book not found")

    progress = BookProgress.load(book_dir)
    if progress is None:
        raise HTTPException(status_code=404, detail="Book not found")

    raw_dir = book_dir / "raw"
    translated_dir = book_dir / "translated"

    chapters = []
    for ch in progress.chapters:
        has_raw = _find_chapter_file(raw_dir, ch.index) is not None
        has_translated = _find_chapter_file(translated_dir, ch.index) is not None
        chapters.append(ChapterDetail(
            index=ch.index,
            id=ch.id,
            title_cn=ch.title_cn,
            title_vi=ch.title_vi,
            status=ch.status.value,
            has_raw=has_raw,
            has_translated=has_translated,
        ))

    return BookDetail(
        id=book_id,
        title=progress.title,
        title_vi=progress.title_vi,
        author=progress.author,
        author_vi=progress.author_vi,
        url=progress.url,
        encoding=progress.encoding,
        chapters=chapters,
        created_at=str(progress.created_at) if progress.created_at else None,
        updated_at=str(progress.updated_at) if progress.updated_at else None,
    )


def _find_chapter_file(directory: Path, chapter_index: int) -> Optional[Path]:
    """Find chapter file using dual-pattern lookup.

    Matches the existing logic in formatter/assembler.py:
    1. Try new pattern: {index}.txt
    2. Fall back to old pattern: {index:04d}_*.txt (glob)

    Returns:
        Path to file if found, None otherwise.
    """
    if not directory.exists():
        return None
    # New pattern first
    new_pattern = directory / f"{chapter_index}.txt"
    if new_pattern.exists():
        return new_pattern
    # Old pattern with glob
    old_pattern = f"{chapter_index:04d}_*.txt"
    files = list(directory.glob(old_pattern))
    return files[0] if files else None


@router.get("/{book_id}/chapters/{chapter_num}/raw", response_model=ChapterContent)
async def get_chapter_raw(book_id: str, chapter_num: int) -> ChapterContent:
    """Get raw Chinese chapter content."""
    file_path = _find_chapter_file(_books_dir / book_id / "raw", chapter_num)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    content = file_path.read_text(encoding="utf-8")
    return ChapterContent(chapter_index=chapter_num, content=content)


@router.get("/{book_id}/chapters/{chapter_num}/translated", response_model=ChapterContent)
async def get_chapter_translated(book_id: str, chapter_num: int) -> ChapterContent:
    """Get translated Vietnamese chapter content."""
    file_path = _find_chapter_file(_books_dir / book_id / "translated", chapter_num)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    content = file_path.read_text(encoding="utf-8")
    return ChapterContent(chapter_index=chapter_num, content=content)
```

**Step 4: Run all tests**

```bash
uv run pytest tests/test_api.py -v
```

Expected: all PASS

**Step 5: Commit**

```bash
git add src/dich_truyen/api/ tests/test_api.py
git commit -m "feat(api): add book detail and chapter content endpoints"
```

---

## Task 5: CLI `ui` Command

**Files:**
- Modify: `src/dich_truyen/cli.py`

**Step 1: Add `ui` command**

Add before the `if __name__` block in `cli.py`:

```python
# =============================================================================
# UI Command
# =============================================================================


@cli.command()
@click.option("--port", default=8000, type=int, help="API server port")
@click.option("--host", default="127.0.0.1", help="API server host")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
def ui(port: int, host: str, no_browser: bool) -> None:
    """Launch web UI in browser.

    Starts the FastAPI server and opens the UI in your default browser.
    """
    import uvicorn
    import webbrowser
    import threading

    from dich_truyen.api.server import create_app
    from dich_truyen.config import get_config

    config = get_config()
    app = create_app(books_dir=config.books_dir.resolve())

    if not no_browser:
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=open_browser, daemon=True).start()

    console.print(f"[bold green]🚀 Dịch Truyện UI starting...[/bold green]")
    console.print(f"[blue]   API: http://{host}:{port}/api/docs[/blue]")
    console.print(f"[blue]   UI:  http://{host}:{port}[/blue]")
    console.print("[dim]   Press Ctrl+C to stop[/dim]\n")

    uvicorn.run(app, host=host, port=port, log_level="info")
```

**Step 2: Verify CLI still works**

```bash
uv run dich-truyen --help
```

Expected: shows `ui` in command list alongside `pipeline`, `export`, `glossary`, `style`.

**Step 3: Verify existing commands unchanged**

```bash
uv run dich-truyen pipeline --help
uv run dich-truyen export --help
```

Expected: both show same options as before.

**Step 4: Run all existing tests to verify no breakage**

```bash
uv run pytest tests/ -v
```

Expected: all existing tests still pass.

**Step 5: Commit**

```bash
git add src/dich_truyen/cli.py
git commit -m "feat(cli): add 'ui' command to launch web server"
```

---

## Task 6: Scaffold Next.js Frontend

**Files:**
- Create: `web/` directory (Next.js project)

**Step 1: Initialize Next.js project**

```bash
npx create-next-app@latest --help
```

Review options, then run:

```bash
npx -y create-next-app@latest ./web --typescript --tailwind --eslint --app --src-dir --no-import-alias --no-turbopack
```

**Step 2: Install design system dependencies**

```bash
cd web && npm install lucide-react
```

- `lucide-react`: SVG icon library (see MASTER.md → Icons section)

**Step 3: Verify Next.js runs**

```bash
npm run dev
```

Expected: Next.js starts on `http://localhost:3000`.

**Step 4: Configure `next.config.ts` for API proxy**

Replace `web/next.config.ts`:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
```

**Step 5: Verify `.gitignore`**

`create-next-app` generates a `web/.gitignore` that excludes `node_modules/` and `.next/`. Verify it exists. If the root `.gitignore` doesn't already exclude these, add:

```gitignore
# Next.js
web/node_modules/
web/.next/
```

**Step 6: Commit**

```bash
git add web/
git commit -m "feat(web): scaffold Next.js app with design dependencies"
```

---

## Task 7: App Layout with Dark Theme & Sidebar

**Files:**
- Modify: `web/src/app/layout.tsx`
- Modify: `web/src/app/globals.css`
- Create: `web/src/components/layout/Sidebar.tsx`
- Modify: `web/src/app/page.tsx`

> **Design reference:** [MASTER.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/design-system/dich-truyen/MASTER.md) → Color Palette, Typography, Sidebar Navigation

**Step 1: Set up `globals.css` with design system**

Replace `web/src/app/globals.css` with:

```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&family=Noto+Serif:wght@400;500;600;700&display=swap');
@import "tailwindcss";

:root {
  /* Backgrounds */
  --bg-primary: #0B1120;
  --bg-surface: #111827;
  --bg-elevated: #1F2937;
  /* Borders */
  --border-default: #1F2937;
  --border-hover: #374151;
  /* Text */
  --text-primary: #F9FAFB;
  --text-secondary: #9CA3AF;
  --text-muted: #6B7280;
  /* Brand */
  --color-primary: #0D9488;
  --color-primary-hover: #14B8A6;
  --color-primary-subtle: rgba(13, 148, 136, 0.12);
  --color-cta: #F97316;
  --color-cta-hover: #FB923C;
  /* Status */
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
  --color-info: #3B82F6;
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.5);
  --shadow-glow: 0 0 20px rgba(13,148,136,0.15);
  /* Radius */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
}

body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: 'Fira Sans', sans-serif;
}

/* Skeleton loading animation */
@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}
.skeleton {
  background: var(--bg-elevated);
  animation: skeleton-pulse 1.5s ease-in-out infinite;
  border-radius: var(--radius-md);
}
```

**Step 2: Create Sidebar component**

Create `web/src/components/layout/Sidebar.tsx` with:
- Logo area (64px height): app name "Dịch Truyện" in Fira Code
- Nav items using **Lucide React icons** (NOT emojis):
  - `LayoutDashboard` → Dashboard (`/`)
  - `BookOpen` → Library (`/library`)
  - `Settings` → Settings (`/settings`)
- Active link: `bg-[var(--color-primary-subtle)]` + `text-[var(--color-primary)]` + left 3px teal border
- Hover: `bg-[var(--bg-elevated)]` + `text-[var(--text-primary)]`
- Default: `text-[var(--text-secondary)]`
- `usePathname()` hook for active state detection
- Sidebar width: `w-60` (240px), `bg-[var(--bg-surface)]`, right border `border-r border-[var(--border-default)]`
- All transitions: `transition-colors duration-150`
- All clickable items: `cursor-pointer`

**Step 3: Update root layout**

Update `web/src/app/layout.tsx`:
- Import Fira Code + Fira Sans via `next/font/google`
- Apply font classes to `<body>`
- Flex layout: `<Sidebar />` (fixed) + main content area (scrollable)
- Main area: `ml-60 min-h-screen p-8`

**Step 4: Update home page placeholder**

Replace `web/src/app/page.tsx` with a Dashboard placeholder:
- Page title in Fira Code: "Dashboard"
- Subtitle in text-secondary: "Welcome to Dịch Truyện"

**Step 5: Verify in browser**

```bash
cd web && npm run dev
```

Verify:
- Deep dark background (#0B1120)
- Sidebar with teal active state on Dashboard
- Fira Code heading, Fira Sans body text
- Lucide icons rendering correctly
- Hover transitions on nav items (150ms)
- `cursor-pointer` on nav items

**Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(web): add dark theme layout with sidebar navigation"
```

---

## Task 8: Library Page

**Files:**
- Create: `web/src/app/library/page.tsx`
- Create: `web/src/components/library/BookCard.tsx`
- Create: `web/src/components/library/BookCardSkeleton.tsx`
- Create: `web/src/lib/api.ts`
- Create: `web/src/lib/types.ts`

> **Design reference:** MASTER.md → Cards, Status Badges, Progress Bars, Library wireframe

**Step 1: Create TypeScript types matching API models**

Create `web/src/lib/types.ts` with `BookSummary`, `BookDetail`, `ChapterDetail`, `ChapterContent` interfaces matching the Pydantic models.

**Step 2: Create API client**

Create `web/src/lib/api.ts` with fetch wrapper functions:
- `getBooks(): Promise<BookSummary[]>`
- `getBook(id: string): Promise<BookDetail>`
- `getChapterRaw(bookId: string, chapterNum: number): Promise<ChapterContent>`
- `getChapterTranslated(bookId: string, chapterNum: number): Promise<ChapterContent>`

Base URL: `/api/v1` (proxied to FastAPI via next.config.ts rewrite).

**Step 3: Create BookCard component**

Create `web/src/components/library/BookCard.tsx`:
- Card styling from MASTER.md: `bg-[var(--bg-surface)]`, `border border-[var(--border-default)]`, `rounded-xl`, `p-6`
- Hover: `border-[var(--border-hover)]`, `shadow-md`, `translateY(-1px)`, `transition-all duration-200`
- `cursor-pointer` on the card
- Chinese title: `font-['Fira_Code'] text-[var(--text-primary)] font-semibold`
- Vietnamese title: `text-[var(--color-primary)] text-sm`
- Author: `text-[var(--text-muted)] text-xs`
- Progress bar: 6px height, `bg-[var(--bg-elevated)]` track, teal gradient fill
- Chapter count: `"45/120 chapters"` in text-secondary
- Status badge using MASTER.md status colors:
  - If `translated == total`: green "Completed" badge
  - If `translated > 0`: teal "Translating" badge
  - Else: blue "Pending" badge
- Badge: rounded-full, small padding, semi-transparent bg + colored text
- Click: `useRouter().push(/books/${book.id})`

**Step 4: Create BookCardSkeleton**

Create `web/src/components/library/BookCardSkeleton.tsx`:
- Same card dimensions as BookCard
- Skeleton pulse animation (`.skeleton` class) for title, subtitle, progress bar
- Show 6 skeletons in grid while loading

**Step 5: Create Library page**

Create `web/src/app/library/page.tsx`:
- Page title: `Library` in Fira Code
- `useEffect` + `useState` to fetch from `/api/v1/books`
- Loading state: show 6x BookCardSkeleton in grid
- Loaded: `grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6`
- Empty state: centered message with `BookOpen` Lucide icon

**Step 6: Verify with running backend**

Terminal 1: `uv run dich-truyen ui --no-browser`
Terminal 2: `cd web && npm run dev`

Open `http://localhost:3000/library`. Verify:
- 3 book cards from `books/` directory with real data
- Progress bars fill proportionally
- Status badges show correct colors
- Hover effect (border + shadow + lift) on cards
- Skeleton loaders flash briefly before data loads

**Step 7: Commit**

```bash
git add web/src/
git commit -m "feat(web): add library page with book cards"
```

---

## Task 9: Book Detail Page

**Files:**
- Create: `web/src/app/books/[id]/page.tsx`
- Create: `web/src/components/book/ChapterTable.tsx`

> **Design reference:** MASTER.md → Book Detail wireframe, Status Badges

**Step 1: Create ChapterTable component**

Create `web/src/components/book/ChapterTable.tsx`:
- Container: `bg-[var(--bg-surface)]` card with `rounded-xl`, `border border-[var(--border-default)]`
- Table header: `text-[var(--text-muted)] text-xs uppercase tracking-wider font-['Fira_Code']`
- Columns: `#` (index), `Title`, `Status`, `Actions`
- Row hover: `bg-[var(--bg-elevated)]`, `transition-colors duration-150`
- Status column uses **Lucide icons + status colors** from MASTER.md:
  - `CheckCircle2` (green #10B981) for Translated
  - `Download` (yellow #F59E0B) for Crawled
  - `Clock` (blue #3B82F6) for Pending
  - `AlertCircle` (red #EF4444) for Error
- Translated rows: clicking navigates to `/books/[id]/read?chapter=N`
- `cursor-pointer` on clickable rows
- Scrollable body: `max-h-[60vh] overflow-y-auto`

**Step 2: Create Book Detail page**

Create `web/src/app/books/[id]/page.tsx`:
- Back link: `← Library` using `ChevronLeft` icon, links to `/library`
- Book title: `font-['Fira_Code'] text-2xl font-bold text-[var(--text-primary)]`
- Vietnamese title below in `text-[var(--color-primary)]`
- Author: `text-[var(--text-secondary)]`
- Progress summary bar: wide bar showing `translated/total` with percentage
- Stats row: cards for Translated / Crawled / Pending / Error counts
- ChapterTable below
- Skeleton loading state while fetching

**Step 3: Verify**

Click a book in Library → Book Detail page shows:
- Book header with real data
- Chapter table with colored status icons
- Translated chapters are clickable (cursor-pointer + hover)

**Step 4: Commit**

```bash
git add web/src/
git commit -m "feat(web): add book detail page with chapter table"
```

---

## Task 10: Chapter Reader Page

**Files:**
- Create: `web/src/app/books/[id]/read/page.tsx`
- Create: `web/src/components/reader/ReaderView.tsx`

> **Design reference:** MASTER.md → Chapter Reader wireframe, Typography (Reader font: Noto Serif)

**Step 1: Create ReaderView component**

Create `web/src/components/reader/ReaderView.tsx`:
- Reading text: `font-['Noto_Serif'] text-lg leading-relaxed` (18px, 1.8 line-height)
- Chapter title: `font-['Noto_Serif'] text-xl font-semibold mb-6`
- Text container: `max-w-3xl mx-auto` for optimal reading width
- Side-by-side mode: two columns, left = Chinese (darker bg card), right = Vietnamese
  - Left panel: `bg-[var(--bg-surface)]` with `p-8 rounded-xl`
  - Right panel: `bg-[var(--bg-elevated)]` with `p-8 rounded-xl`
- Toolbar (top): `sticky top-0 bg-[var(--bg-primary)] z-10 py-3 border-b border-[var(--border-default)]`
  - Back link: `ChevronLeft` icon + book title
  - Chapter indicator: "Chapter 47" in `text-[var(--text-secondary)]`
  - Font size controls: `AArrowDown` / `AArrowUp` Lucide icons, `text-[var(--text-muted)]`
  - Side-by-side toggle: `Columns2` Lucide icon, teal when active
- Bottom nav: `flex justify-between items-center mt-8`
  - Prev/Next: `ChevronLeft`/`ChevronRight` + text, styled as ghost buttons
  - Chapter position: `47/320` in `text-[var(--text-muted)]`
- `prefers-reduced-motion`: disable smooth scroll

**Step 2: Create Reader page**

Create `web/src/app/books/[id]/read/page.tsx`:
- Query param `?chapter=N` to select chapter (default to first translated chapter)
- Fetch translated content, optionally raw content when side-by-side is on
- ReaderView component
- Keyboard shortcuts: `ArrowLeft` prev chapter, `ArrowRight` next chapter
- Sidebar hidden on reader page (full-width reading experience)
- Font size persisted in `localStorage`

**Step 3: Verify**

Click a translated chapter in Book Detail → Reader opens:
- Clean Noto Serif text at comfortable reading size
- Side-by-side toggle shows Chinese | Vietnamese split
- Prev/Next navigation works
- Arrow key shortcuts work
- Font size +/- buttons work and persist

**Step 4: Commit**

```bash
git add web/src/
git commit -m "feat(web): add chapter reader with side-by-side view"
```

---

## Task 11: Dashboard Page

**Files:**
- Modify: `web/src/app/page.tsx`
- Create: `web/src/components/dashboard/StatCard.tsx`

> **Design reference:** MASTER.md → Dashboard wireframe, Cards

**Step 1: Create StatCard component**

Create `web/src/components/dashboard/StatCard.tsx`:
- Card: `bg-[var(--bg-surface)]`, `border border-[var(--border-default)]`, `rounded-xl`, `p-6`
- Label: `text-[var(--text-muted)] text-xs uppercase tracking-wider font-['Fira_Code']`
- Value: `text-3xl font-bold text-[var(--text-primary)] font-['Fira_Code']`
- Optional progress ring or accent color strip at top

**Step 2: Build Dashboard page**

Replace placeholder in `web/src/app/page.tsx`:
- Page title: "Dashboard" in Fira Code
- Stats row: 3 StatCards in `grid grid-cols-1 md:grid-cols-3 gap-6`
  - Total Books (icon: `BookOpen`)
  - Total Chapters (icon: `FileText`)
  - Completion % (icon: `CheckCircle2` in teal)
- Recent Books section: `mt-8`, title "Recent Books" in Fira Code
  - Grid of last 3 BookCards (reuse component from Task 8)
- Quick Actions section: `mt-8`
  - "Browse Library" button (secondary, links to `/library`)
  - "Open Settings" button (secondary, links to `/settings`)
- All data fetched from `/api/v1/books`, stats computed client-side
- Skeleton loading state for stat cards and book cards

**Step 3: Verify**

Open `http://localhost:3000/`. Dashboard shows:
- Real stats from your 3 books
- Recent books with progress bars
- Quick action buttons navigate correctly
- Skeleton loaders appear briefly

**Step 4: Commit**

```bash
git add web/src/
git commit -m "feat(web): add dashboard with stats and recent books"
```

## Task 12: Final Integration & Polish

**Step 1: Run all Python tests**

```bash
uv run pytest tests/ -v
```

Expected: ALL pass (existing + new API tests).

**Step 2: Run linting**

```bash
uv run ruff check .
uv run ruff format .
cd web && npx next lint
```

**Step 3: Full integration test**

Run both servers and verify the complete flow:
1. `uv run dich-truyen ui --no-browser` → API starts on `:8000`
2. `cd web && npm run dev` → Frontend on `:3000`
3. Dashboard loads with real stats
4. Library shows all books
5. Click book → detail page with chapters
6. Click translated chapter → reader with text
7. Side-by-side toggle works
8. CLI commands still work: `uv run dich-truyen --help`, `uv run dich-truyen glossary show --book-dir books/<dir>`

**Step 4: Commit**

```bash
git add -A
git commit -m "feat(web): complete Phase 1 — library browser and chapter reader"
```

---

## Verification Plan

### Automated Tests

```bash
# All Python tests (existing + new API tests)
uv run pytest tests/ -v

# Lint check
uv run ruff check .

# Next.js lint
cd web && npx next lint

# Next.js build (verify no type errors)
cd web && npm run build
```

### Manual Verification

1. Start API: `uv run dich-truyen ui --no-browser --port 8000`
2. Start frontend: `cd web && npm run dev`
3. Open `http://localhost:3000` — verify dark theme dashboard with stats
4. Navigate to Library — verify book cards with real data from `books/`
5. Click a book — verify chapter table with status colors
6. Click a translated chapter — verify reader shows Vietnamese text
7. Toggle side-by-side — verify Chinese original appears
8. Verify CLI unchanged: `uv run dich-truyen pipeline --help`
