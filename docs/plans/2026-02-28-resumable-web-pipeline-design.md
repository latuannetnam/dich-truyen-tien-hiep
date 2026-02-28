# Resumable Web UI Pipeline

## Problem

The CLI pipeline is fully resumable across restarts: `StreamingPipeline.run()` reads `BookProgress` from `books/<slug>/book.json` and skips chapters already in `CRAWLED` or `TRANSLATED` status. Each chapter's status is saved to disk immediately after processing.

The Web UI loses all pipeline jobs on restart because `PipelineService._jobs` is a pure in-memory Python `dict`. The underlying `book.json` still has per-chapter progress, but the UI has no way to surface it or restart from it.

## Design Decisions

- **Manual resume** — user clicks a "Resume" button (no auto-resume on startup)
- **Both surfaces** — pipeline page shows all resumable books; book detail page shows contextual banner
- **Quick + configurable** — "Resume" for one-click start with defaults; "Resume with options" for tweaking style/workers
- **Hybrid approach** — detect incomplete books from existing `book.json`; save `last_pipeline_settings.json` per book for pre-filling the options form

## Backend

### Save pipeline settings per book

In `PipelineService._run_pipeline()`, after determining `book_dir`, write `last_pipeline_settings.json`:

```json
{
  "style": "tien_hiep",
  "workers": 3,
  "chapters": null,
  "crawl_only": false,
  "translate_only": false,
  "no_glossary": false,
  "last_run_at": "2026-02-28T16:00:00"
}
```

Best-effort convenience data. If missing, UI uses defaults.

### New endpoint: `GET /api/v1/pipeline/resumable`

Returns books with incomplete chapters plus their last pipeline settings.

Existing `GET /api/v1/books` already returns `pending_chapters`, `crawled_chapters`, `error_chapters` — so detection is possible from frontend alone. This endpoint adds the `last_settings` data and avoids duplicating detection logic across surfaces.

Response:

```json
[
  {
    "book_dir": "books/1234-my-novel",
    "book_id": "1234-my-novel",
    "title": "Original Title",
    "title_vi": "Vietnamese Title",
    "total_chapters": 200,
    "translated": 50,
    "crawled": 30,
    "pending": 100,
    "errors": 20,
    "last_settings": { "style": "tien_hiep", "workers": 3 },
    "last_run_at": "2026-02-28T16:00:00"
  }
]
```

### Resume action

No new endpoint. Existing `POST /api/v1/pipeline/start` with `book_dir` already works — `StreamingPipeline.run()` handles resume logic.

## Frontend

### Pipeline page (`/pipeline`)

New **"Resumable Books"** section above Active/History. Each card:
- Book title (Vietnamese → Chinese fallback)
- Progress bar with chapter counts
- "Resume" button — calls `POST /pipeline/start` with `book_dir`, redirects to `/pipeline/[jobId]`
- "⚙ Options" — inline form pre-filled from `last_settings` (style, workers, chapters, translate_only, force)

### Book detail page (`/library/[slug]`)

Banner at top when book has incomplete chapters:
```
⚠ Translation incomplete — 150 chapters remaining
[▶ Resume]  [⚙ Resume with options...]
```

### Post-resume navigation

Both surfaces redirect to `/pipeline/[jobId]` for real-time monitoring after starting.

### New TypeScript types

```typescript
interface ResumableBook {
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

### New API client function

```typescript
export async function getResumableBooks(): Promise<ResumableBook[]> {
  return fetchJson<ResumableBook[]>(`${API_BASE}/pipeline/resumable`);
}
```
