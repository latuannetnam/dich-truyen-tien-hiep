# Desktop UI Design — Dịch Truyện

> **Date:** 2026-02-24
> **Status:** Approved via brainstorming session
> **Last updated:** 2026-02-25 (synced with implemented code)

## Overview

Add a browser-based desktop UI to the existing CLI tool. Both interfaces coexist, sharing the same backend logic. Users can use either `dich-truyen pipeline ...` (CLI) or `dich-truyen ui` (browser) interchangeably.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UI delivery | Browser-based (`localhost`) | Simplest; upgradeable to Tauri later |
| Frontend | React + Next.js (App Router) | File-based routing, large ecosystem |
| Styling | Tailwind CSS 4 | Utility-first, fast iteration |
| Backend API | FastAPI | Async-native, matches existing codebase |
| Architecture | Monorepo (`web/` at root) | Single repo, separate toolchains |
| Icons | Lucide React | Consistent icon set |
| Phasing | Quick-win first | Visible value from Phase 1 |
| CLI compat | Must not break after any phase | Critical constraint |

## Architecture: Dual UI with Shared Service Layer

```
┌─────────────────┐     ┌─────────────────┐
│    CLI (Click)   │     │  Web UI (React)  │
│  Terminal output │     │  Browser output  │
└────────┬────────┘     └────────┬────────┘
         │                       │ HTTP / WebSocket
         │              ┌────────▼────────┐
         │              │  FastAPI Server  │
         │              │  (port 8000)     │
         │              └────────┬────────┘
         ▼                       ▼
┌─────────────────────────────────────────┐
│          Service Layer (Python)          │
│  PipelineService  · BookService         │
│  GlossaryService  · StyleService        │
│  ExportService    · ConfigService       │
│  EventBus (pub/sub)                     │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│         Core Logic (existing)            │
│  pipeline/ · crawler/ · translator/      │
│  exporter/ · formatter/ · utils/         │
│  config.py                               │
└─────────────────────────────────────────┘
```

### Event System

The service layer uses an `EventBus` (pub/sub) that emits `PipelineEvent` objects:

```python
@dataclass
class PipelineEvent:
    type: str                    # e.g. "chapter_update", "progress", "error", "completed"
    data: dict                   # Payload (varies by type)
    job_id: Optional[str]        # Which pipeline job
    timestamp: float             # Unix timestamp
```

- **CLI** currently calls `StreamingPipeline` directly → Rich console output
- **Web** subscribes via WebSocket → `PipelineEvent.to_dict()` → React state updates

### CLI Backward Compatibility Rule

> [!IMPORTANT]
> The CLI must remain fully functional after every phase. The service layer is **additive** — it wraps existing logic without modifying core behavior. `cli.py` is refactored incrementally: each function is changed from calling core modules directly to calling the equivalent service method, with identical behavior.

## UI Pages

### 🏠 Dashboard (`/`)
- Active pipeline jobs with mini progress bars
- Recent books with progress %, chapter count
- Quick actions: "New Translation", "Settings"
- Stats: total books, chapters translated
- Components: `ActiveJobs`, `StatCard`

### 📚 Library (`/library`)
- Book grid/list view (toggle)
- Cards: title (CN + VI), author, progress bar, status badge
- Filters by status, style, date; search by title/author
- Bulk actions: export, delete, re-translate
- Components: `BookCard`, `BookCardSkeleton`

### 📖 Book Detail (`/books/[id]`)
- Header: title, author, source URL, style, dates
- Chapter table with status icons (Pending / Crawled / Translated / Formatted / Exported / Error)
- Actions: Start/Resume, Export, Edit Glossary, Change Style
- Chapter range selector

### 📝 Chapter Reader (`/books/[id]/read`)
- Clean formatted Vietnamese text
- Side-by-side toggle (Chinese ↔ Vietnamese)
- Chapter navigation (prev/next, dropdown)
- Font size & theme controls

### 🚀 Pipeline Monitor (Real-time)
- Pipeline list page: `/pipeline` — all jobs with status
- Job detail page: `/pipeline/[jobId]` — live monitoring
- Overall progress bar with ETA
- Worker status cards per worker
- Live scrolling event log
- Controls: Cancel (Pause/Resume planned)
- Components: `ProgressPanel`, `WorkerCards`, `EventLog`

### 📖 Glossary Editor (`/books/[id]/glossary`)
- Editable table: Chinese term, Vietnamese translation, category
- Search, filter, add/edit/delete
- Import/Export CSV with file picker
- Auto-generate via LLM button (planned)

### 🎨 Style Manager (`/styles`)
- Style cards with preview text (read-only)
- Style detail view
- YAML editor with live preview (planned)
- Generate new style via LLM (planned)

### ⚙️ Settings (`/settings`)
- API config (key, base URL, model) with "Test Connection"
- Crawler, translation, export, pipeline settings
- Task-specific LLM overrides (crawler, glossary, translator)
- Saves to `.env` file (with rotating backups)
- Field descriptions from Pydantic model metadata

### 🆕 New Translation Wizard (`/new`)
- Step 1: Paste URL → configure style, workers, chapter range
- Step 2: Options (crawl-only, translate-only, force, no-glossary)
- Step 3: Confirm & start → redirect to pipeline monitor

## API Design

### REST Endpoints

```
PREFIX: /api/v1

Health:
  GET    /health                                  Health check + version

Books:
  GET    /books                                   List all books
  GET    /books/:id                               Book detail + chapters
  GET    /books/:id/chapters/:num/raw             Raw Chinese text
  GET    /books/:id/chapters/:num/translated      Vietnamese text

Pipeline:
  POST   /pipeline/start                          Start crawl+translate
  GET    /pipeline/jobs                            List all jobs
  GET    /pipeline/jobs/:id                        Job status
  POST   /pipeline/jobs/:id/cancel                Cancel running job

Glossary:
  GET    /books/:id/glossary                      All terms
  POST   /books/:id/glossary                      Add term
  PUT    /books/:id/glossary/:term                Update term
  DELETE /books/:id/glossary/:term                Delete term
  POST   /books/:id/glossary/import               Import CSV
  GET    /books/:id/glossary/export               Export CSV

Styles:
  GET    /styles                                  List styles
  GET    /styles/:name                            Get style detail

Export:
  GET    /export/formats                          List supported formats
  GET    /books/:id/export                        Export status (existing files)
  POST   /books/:id/export                        Start export (?format=epub)
  GET    /books/:id/export/download/:filename     Download ebook file

Settings:
  GET    /settings                                Get all settings
  PUT    /settings                                Update settings
  POST   /settings/test-connection                Test API connection
```

### WebSocket

```
WS /ws/pipeline/:job_id

Server → Client (PipelineEvent.to_dict()):
  {type: "chapter_update",    data: {chapter, status, ...},  job_id, timestamp}
  {type: "progress",          data: {crawled, translated, total, workers, ...}, job_id, timestamp}
  {type: "error",             data: {chapter, message, ...}, job_id, timestamp}
  {type: "completed",         data: {book_id, duration},     job_id, timestamp}
  {type: "heartbeat"}         // Sent every 30s to keep connection alive

Client → Server:
  (Not implemented — cancel via REST POST /pipeline/jobs/:id/cancel)
```

## Project Structure

```
dich-truyen-tien-hiep/
├── src/dich_truyen/
│   ├── __init__.py                      # Version (__version__)
│   ├── cli.py                           # Existing (refactored incrementally)
│   ├── config.py                        # Existing (SECTIONS registry, Pydantic models)
│   ├── services/                        # Shared service layer
│   │   ├── __init__.py
│   │   ├── pipeline_service.py          # Job management + StreamingPipeline wrapper
│   │   ├── book_service.py              # Book metadata access
│   │   ├── glossary_service.py          # Glossary CRUD
│   │   ├── style_service.py             # Style template management
│   │   ├── export_service.py            # EPUB/Calibre export
│   │   ├── config_service.py            # Settings read/write + .env management
│   │   └── events.py                    # EventBus + PipelineEvent
│   ├── api/                             # FastAPI server
│   │   ├── __init__.py
│   │   ├── server.py                    # App factory (create_app)
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── books.py
│   │   │   ├── pipeline.py
│   │   │   ├── glossary.py
│   │   │   ├── styles.py
│   │   │   ├── export.py
│   │   │   └── settings.py
│   │   └── websocket.py                 # WS /ws/pipeline/{job_id}
│   ├── crawler/                         # Existing
│   │   ├── base.py
│   │   ├── downloader.py
│   │   └── pattern.py
│   ├── translator/                      # Existing
│   │   ├── engine.py
│   │   ├── glossary.py
│   │   ├── llm.py
│   │   ├── style.py
│   │   └── term_scorer.py
│   ├── formatter/                       # Existing (chapter assembly + metadata)
│   │   ├── assembler.py
│   │   └── metadata.py
│   ├── exporter/                        # Existing (EPUB + Calibre)
│   │   ├── calibre.py
│   │   └── epub_assembler.py
│   ├── pipeline/                        # Existing (streaming pipeline)
│   │   ├── __init__.py
│   │   └── streaming.py
│   └── utils/                           # Existing
│       ├── encoding.py
│       └── progress.py
├── web/                                 # Next.js app (App Router)
│   ├── package.json                     # React 19, Next.js 16, lucide-react
│   ├── next.config.ts                   # API rewrite proxy → localhost:8000
│   ├── tsconfig.json
│   ├── postcss.config.mjs
│   ├── eslint.config.mjs
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx               # Root layout (Sidebar, ToastProvider)
│   │   │   ├── globals.css              # Global styles
│   │   │   ├── page.tsx                 # Dashboard
│   │   │   ├── library/page.tsx
│   │   │   ├── books/[id]/page.tsx      # Book detail
│   │   │   ├── books/[id]/read/page.tsx
│   │   │   ├── books/[id]/glossary/page.tsx
│   │   │   ├── pipeline/page.tsx        # Pipeline job list
│   │   │   ├── pipeline/[jobId]/page.tsx
│   │   │   ├── settings/page.tsx
│   │   │   ├── styles/page.tsx
│   │   │   └── new/page.tsx             # Translation wizard
│   │   ├── components/
│   │   │   ├── layout/                  # LayoutWrapper, Sidebar
│   │   │   ├── dashboard/              # ActiveJobs, StatCard
│   │   │   ├── library/                # BookCard, BookCardSkeleton
│   │   │   ├── book/                   # Book detail components
│   │   │   ├── reader/                 # Chapter reader
│   │   │   ├── pipeline/              # ProgressPanel, WorkerCards, EventLog
│   │   │   ├── glossary/              # Glossary editor
│   │   │   ├── wizard/                # New translation wizard
│   │   │   └── ui/                    # EmptyState, ErrorBoundary, ToastProvider
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts
│   │   └── lib/
│   │       ├── api.ts                  # Type-safe API client
│   │       └── types.ts                # TypeScript interfaces
├── design-system/                       # Design tokens & references
├── pyproject.toml
└── tests/
```

## Implementation Phases

### Phase 1 — "See Your Library" ✅ Done

**Goal:** Working web UI that displays existing books and lets you read them.

| Step | What | CLI Impact |
|------|------|------------|
| 1 | Scaffold Next.js app in `web/` with dark theme + sidebar | None |
| 2 | Minimal FastAPI server (read-only file endpoints) | None |
| 3 | Library page — reads `books/*/book.json` | None |
| 4 | Book Detail page — chapter list with status colors | None |
| 5 | Chapter Reader — render translated `.txt` files | None |
| 6 | `dich-truyen ui` command — starts server + opens browser | Additive only |

**CLI remains:** 100% unchanged. Web is read-only, new code only.

---

### Phase 2 — "Monitor Your Work" ✅ Done

**Goal:** Start and monitor translations from the browser.

| Step | What | CLI Impact |
|------|------|------------|
| 1 | Extract `PipelineService` + event system | CLI calls service (same behavior) |
| 2 | Pipeline Monitor page with WebSocket | None |
| 3 | New Translation Wizard | None |
| 4 | Dashboard with active jobs + recent books | None |

**CLI remains:** `cli.py` still calls `StreamingPipeline` directly — service layer is additive.

---

### Phase 3 — "Edit & Configure" ✅ Done

**Goal:** Settings editing, glossary management, side-by-side reader.

| Step | What | CLI Impact |
|------|------|------------|
| 1 | Settings page — edit config in browser | None (reads same `.env`) |
| 2 | Glossary Editor — inline table editing | None |
| 3 | Side-by-side Reader | None |
| 4 | Extract remaining services (Style, Export, Config) | CLI uses same behavior |

**CLI remains:** Settings still read from `.env`. Glossary uses same CSV format.

---

### Phase 4 — "Complete & Polish" 🚧 In Progress

**Goal:** Full feature parity + premium feel.

| Step | What | CLI Impact |
|------|------|------------|
| 1 | Style Manager — view styles, edit YAML (planned) | None |
| 2 | Export controls — format picker, download | None |
| 3 | Animations, transitions, responsive design | None |
| 4 | Error handling, loading states, edge cases | None |

**Planned future additions (not yet implemented):**
- `DELETE /books/:id` — Delete a book
- `POST /pipeline/resume/:id` — Resume interrupted job
- `PUT /styles/:name` — Update style YAML
- `POST /styles/generate` — Generate style via LLM
- `POST /books/:id/glossary/generate` — Auto-generate glossary via LLM
- Client → Server WebSocket commands (pause, resume)
- Chapter status heatmap grid in pipeline monitor

**CLI remains:** Fully functional, all features available via both interfaces.
