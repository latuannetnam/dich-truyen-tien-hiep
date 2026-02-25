---
description: Pipeline overview, component map, data flow, and key design decisions
---

# Architecture

## Pipeline Overview

**StreamingPipeline** = Concurrent CRAWL + TRANSLATE → EXPORT

```
┌─────────────────────────────────────────────────────────────────┐
│                     StreamingPipeline                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐       UNBOUNDED                               │
│  │   Crawler    │──────▶ QUEUE ──────▶ ┌─────────────────┐     │
│  │  (Producer)  │        (∞)           │ Translator W1   │     │
│  │  Downloads   │                      └─────────────────┘     │
│  │  chapters    │                      ┌─────────────────┐     │
│  │  (never      │                      │ Translator W2   │     │
│  │   blocks)    │                      └─────────────────┘     │
│  └──────────────┘                      ┌─────────────────┐     │
│        ↓                               │ Translator W3   │     │
│  Saves to disk immediately             └─────────────────┘     │
│                                                                  │
│            ══════════════════════════════════                   │
│                              ▼                                   │
│                     ┌──────────────┐                            │
│                     │    EXPORT    │  (only when all_done=True) │
│                     │ Direct EPUB  │                            │
│                     │ + Calibre    │                            │
│                     └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

**Unbounded queue** (`maxsize=0`): Crawler never blocks. Translators consume at their own pace.

**Conditional export**: Only triggers when `result.all_done and not result.cancelled`.

## Pipeline Modes

`StreamingPipeline.run()` supports three mutually exclusive modes via `crawl_only` and `translate_only` flags:

| Mode | `to_crawl` | `to_translate` | Behavior |
|------|-----------|----------------|----------|
| **Default** | `PENDING` chapters | `CRAWLED` chapters | Full pipeline: crawl → translate |
| **`crawl_only=True`** | `PENDING` chapters | (skipped) | Early return after crawl, no translation |
| **`translate_only=True`** | `[]` (always empty) | `CRAWLED` chapters | No crawl, only translate existing raw files |

The API route (`api/routes/pipeline.py`) rejects `crawl_only + translate_only` with HTTP 422. The wizard UI enforces mutual exclusivity on the checkboxes.

**`force` flag interaction:**

| Mode | Force resets to | Effect |
|------|----------------|--------|
| `translate_only` | `CRAWLED` | Re-translate all chapters with raw files |
| `crawl_only` | `PENDING` | Re-crawl all chapters |
| Default + URL | `PENDING` | Re-crawl + re-translate |
| Default + no URL | `CRAWLED` | Re-translate only |

## Key Files Map

| Phase | File | Purpose |
|-------|------|---------|
| **Pipeline** | `pipeline/streaming.py` | Orchestration, queue, worker management |
| **Crawl** | `crawler/pattern.py` | LLM CSS selector discovery |
| | `crawler/downloader.py` | Chapter download with resume |
| | `crawler/base.py` | HTTP client, retry, encoding detection |
| **Translate** | `translator/engine.py` | Translation orchestration & chunking |
| | `translator/llm.py` | OpenAI API wrapper, retry logic |
| | `translator/style.py` | Style templates & priority loading |
| | `translator/glossary.py` | Term management & auto-generation |
| | `translator/term_scorer.py` | TF-IDF based glossary selection |
| **Export** | `exporter/epub_assembler.py` | Direct EPUB assembly |
| | `exporter/calibre.py` | Calibre AZW3/MOBI/PDF conversion |
| **Services** | `services/events.py` | EventBus pub/sub for pipeline events |
| | `services/pipeline_service.py` | Job lifecycle management, wraps StreamingPipeline |
| | `services/config_service.py` | Read/write `.env` settings, test LLM connection |
| | `services/glossary_service.py` | Glossary CRUD business logic (testable without HTTP) |
| | `services/export_service.py` | Wraps DirectEPUBAssembler + CalibreExporter |
| | `services/style_service.py` | Wraps StyleManager for style list/load |
| | `services/book_service.py` | Wraps BookProgress for book/chapter queries |
| **CLI** | `cli.py` | All user-facing commands |
| **Config** | `config.py` | Pydantic settings & env vars |
| **Progress** | `utils/progress.py` | BookProgress & chapter status |
| **API** | `api/server.py` | FastAPI app factory with CORS, services init |
| | `api/routes/books.py` | Book list, detail, chapter content endpoints |
| | `api/routes/pipeline.py` | Pipeline start, list, get, cancel endpoints |
| | `api/routes/settings.py` | Settings GET/PUT, test-connection endpoint |
| | `api/routes/glossary.py` | Per-book glossary CRUD, CSV import/export |
| | `api/routes/styles.py` | Style list and detail endpoints |
| | `api/routes/export.py` | Export formats, status, start, download |
| | `api/websocket.py` | WebSocket `/ws/pipeline/{job_id}` for real-time events (graceful disconnect handling) |
| **Web UI** | `web/src/app/` | Next.js App Router pages (dashboard, library, book, reader, new, pipeline, settings, glossary) |
| | `web/src/components/` | React components (Sidebar, BookCard, ChapterTable, ReaderView, ProgressPanel, WorkerCards, EventLog, WizardSteps, ActiveJobs, GlossaryEditor, ToastProvider) |
| | `web/src/hooks/useWebSocket.ts` | React hook for pipeline WebSocket events |
| | `web/src/lib/api.ts` | Frontend API client (books, pipeline, settings, glossary, styles, export) |
| | `web/src/lib/types.ts` | TypeScript interfaces matching Pydantic models |

## Common Modification Points

| Goal | Where |
|------|-------|
| Pipeline behavior | `pipeline/streaming.py:run()` and `_translate_consumer()` |
| Translation logic | `translator/engine.py:translate_chunk_with_context_marker()` |
| Glossary generation | `translator/glossary.py:generate_glossary_from_samples()` |
| CLI commands | `cli.py` with `@cli.command()` |
| Book API endpoints | `api/routes/books.py` with `@router.get()` |
| Pipeline API endpoints | `api/routes/pipeline.py` with `@router.post()` / `@router.get()` |
| WebSocket handler | `api/websocket.py` — subscribes to EventBus, sends JSON |
| Pipeline services | `services/pipeline_service.py` — job creation, status, background tasks |
| Event system | `services/events.py` — subscribe/emit pattern |
| Settings API endpoints | `api/routes/settings.py` with `@router.get()` / `@router.put()` |
| Glossary API endpoints | `api/routes/glossary.py` with CRUD routes |
| Config read/write | `services/config_service.py` — `.env` persistence, key masking |
| Glossary service | `services/glossary_service.py` — CRUD logic without HTTP |
| Export service | `services/export_service.py` — format list, status, run export |
| Style service | `services/style_service.py` — list/load style templates |
| Book service | `services/book_service.py` — list/get books, chapter content |
| Style API endpoints | `api/routes/styles.py` with `@router.get()` |
| Export API endpoints | `api/routes/export.py` with `@router.get()` / `@router.post()` |
| Web UI pages | `web/src/app/*/page.tsx` |
| API proxy config | `web/next.config.ts` rewrites `/api/*` → `:8000` |

