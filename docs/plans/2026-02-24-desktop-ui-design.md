# Desktop UI Design — Dịch Truyện

> **Date:** 2026-02-24
> **Status:** Approved via brainstorming session

## Overview

Add a browser-based desktop UI to the existing CLI tool. Both interfaces coexist, sharing the same backend logic. Users can use either `dich-truyen pipeline ...` (CLI) or `dich-truyen ui` (browser) interchangeably.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UI delivery | Browser-based (`localhost`) | Simplest; upgradeable to Tauri later |
| Frontend | React + Next.js | File-based routing, large ecosystem |
| Backend API | FastAPI | Async-native, matches existing codebase |
| Architecture | Monorepo (`web/` at root) | Single repo, separate toolchains |
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
         │              └────────┬────────┘
         ▼                       ▼
┌─────────────────────────────────────────┐
│          Service Layer (Python)          │
│  PipelineService  · BookService         │
│  GlossaryService  · StyleService        │
│  ExportService    · ConfigService       │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│         Core Logic (existing)            │
│  pipeline/ · crawler/ · translator/      │
│  exporter/ · utils/   · config.py        │
└─────────────────────────────────────────┘
```

### Event System

The service layer emits events (`chapter_crawled`, `chapter_translated`, `progress`, `error`, etc.):
- **CLI** subscribes → Rich console output
- **Web** subscribes → WebSocket → React state updates

### CLI Backward Compatibility Rule

> [!IMPORTANT]
> The CLI must remain fully functional after every phase. The service layer is **additive** — it wraps existing logic without modifying core behavior. `cli.py` is refactored incrementally: each function is changed from calling core modules directly to calling the equivalent service method, with identical behavior.

## UI Pages

### 🏠 Dashboard
- Active pipeline jobs with mini progress bars
- Recent books with progress %, chapter count
- Quick actions: "New Translation", "Settings"
- Stats: total books, chapters translated

### 📚 Library
- Book grid/list view (toggle)
- Cards: title (CN + VI), author, progress bar, status badge
- Filters by status, style, date; search by title/author
- Bulk actions: export, delete, re-translate

### 📖 Book Detail
- Header: title, author, source URL, style, dates
- Chapter table with status icons (Pending / Crawled / Translated / Error)
- Actions: Start/Resume, Export, Edit Glossary, Change Style
- Chapter range selector

### 📝 Chapter Reader
- Clean formatted Vietnamese text
- Side-by-side toggle (Chinese ↔ Vietnamese)
- Chapter navigation (prev/next, dropdown)
- Font size & theme controls

### 🚀 Pipeline Monitor (Real-time)
- Overall progress bar with ETA
- Worker status cards per worker
- Live scrolling event log
- Chapter status heatmap grid
- Controls: Pause, Resume, Cancel

### 📖 Glossary Editor
- Editable table: Chinese term, Vietnamese translation, category
- Search, filter, add/edit/delete
- Import/Export CSV with file picker
- Auto-generate via LLM button

### 🎨 Style Manager
- Style cards with preview text
- YAML editor with live preview
- Generate new style via LLM

### ⚙️ Settings
- API config (key, base URL, model) with "Test Connection"
- Crawler, translation, export, pipeline settings
- Saves to `.env` or config file

### 🆕 New Translation Wizard
- Step 1: Paste URL → preview book title & chapter count
- Step 2: Choose style, chapter range
- Step 3: Review glossary (auto-generated or import)
- Step 4: Confirm & start

## API Design

### REST Endpoints

```
PREFIX: /api/v1

Books:
  GET    /books                         List all books
  GET    /books/:id                     Book detail + chapters
  DELETE /books/:id                     Delete book

Pipeline:
  POST   /pipeline/start                Start crawl+translate
  POST   /pipeline/resume/:id           Resume interrupted job
  POST   /pipeline/cancel/:id           Cancel running job
  GET    /pipeline/status/:id           Job status (polling fallback)

Chapters:
  GET    /books/:id/chapters            Chapter list with status
  GET    /books/:id/chapters/:num/raw   Raw Chinese text
  GET    /books/:id/chapters/:num/translated  Vietnamese text

Glossary:
  GET    /books/:id/glossary            All terms
  POST   /books/:id/glossary            Add term
  PUT    /books/:id/glossary/:term      Update term
  DELETE /books/:id/glossary/:term      Delete term
  POST   /books/:id/glossary/import     Import CSV
  GET    /books/:id/glossary/export     Export CSV
  POST   /books/:id/glossary/generate   Auto-generate

Styles:
  GET    /styles                        List styles
  GET    /styles/:name                  Get style YAML
  PUT    /styles/:name                  Update style
  POST   /styles/generate              Generate via LLM

Export:
  POST   /books/:id/export              Start export
  GET    /books/:id/export/download     Download ebook

Settings:
  GET    /settings                      Get all settings
  PUT    /settings                      Update settings
  POST   /settings/test-connection      Test API connection
```

### WebSocket

```
WS /ws/pipeline/:job_id

Server → Client:
  {type: "chapter_crawled",    chapter, total}
  {type: "chapter_translated", chapter, worker, total}
  {type: "progress",           crawled, translated, total, eta}
  {type: "worker_status",      workers: [{id, status, chapter}]}
  {type: "error",              chapter, message}
  {type: "glossary_updated",   new_terms, total}
  {type: "completed",          book_id, duration}

Client → Server:
  {type: "pause"}
  {type: "resume"}
  {type: "cancel"}
```

## Project Structure

```
dich-truyen-tien-hiep/
├── src/dich_truyen/
│   ├── cli.py                        # Existing (refactored incrementally)
│   ├── config.py                     # Existing
│   ├── services/                     # NEW: shared service layer
│   │   ├── __init__.py
│   │   ├── pipeline_service.py
│   │   ├── book_service.py
│   │   ├── glossary_service.py
│   │   ├── style_service.py
│   │   ├── export_service.py
│   │   ├── config_service.py
│   │   └── events.py                 # Event pub/sub system
│   ├── api/                          # NEW: FastAPI server
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── routes/
│   │   │   ├── books.py
│   │   │   ├── pipeline.py
│   │   │   ├── glossary.py
│   │   │   ├── styles.py
│   │   │   ├── export.py
│   │   │   └── settings.py
│   │   └── websocket.py
│   ├── crawler/                      # Existing (unchanged)
│   ├── translator/                   # Existing (unchanged)
│   ├── exporter/                     # Existing (unchanged)
│   ├── pipeline/                     # Existing (unchanged)
│   └── utils/                        # Existing (unchanged)
├── web/                              # NEW: Next.js app
│   ├── package.json
│   ├── next.config.js
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                  # Dashboard
│   │   ├── library/page.tsx
│   │   ├── books/[id]/page.tsx
│   │   ├── books/[id]/read/page.tsx
│   │   ├── books/[id]/glossary/page.tsx
│   │   ├── pipeline/[jobId]/page.tsx
│   │   ├── styles/page.tsx
│   │   ├── settings/page.tsx
│   │   └── new/page.tsx
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── styles/
├── pyproject.toml
└── tests/
```

## Implementation Phases

### Phase 1 — "See Your Library" 🎯

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

### Phase 2 — "Monitor Your Work" 🚀

**Goal:** Start and monitor translations from the browser.

| Step | What | CLI Impact |
|------|------|------------|
| 1 | Extract `PipelineService` + event system | CLI calls service (same behavior) |
| 2 | Pipeline Monitor page with WebSocket | None |
| 3 | New Translation Wizard | None |
| 4 | Dashboard with active jobs + recent books | None |

**CLI remains:** `cli.py` refactored to call `PipelineService` — same inputs, same outputs.

---

### Phase 3 — "Edit & Configure" ⚙️

**Goal:** Settings editing, glossary management, side-by-side reader.

| Step | What | CLI Impact |
|------|------|------------|
| 1 | Settings page — edit config in browser | None (reads same `.env`) |
| 2 | Glossary Editor — inline table editing | None |
| 3 | Side-by-side Reader | None |
| 4 | Extract remaining services | CLI calls services (same behavior) |

**CLI remains:** Settings still read from `.env`. Glossary uses same CSV format.

---

### Phase 4 — "Complete & Polish" ✨

**Goal:** Full feature parity + premium feel.

| Step | What | CLI Impact |
|------|------|------------|
| 1 | Style Manager — edit YAML, generate styles | None |
| 2 | Export controls — format picker, download | None |
| 3 | Animations, transitions, responsive design | None |
| 4 | Error handling, loading states, edge cases | None |

**CLI remains:** Fully functional, all features available via both interfaces.
