---
description: BookProgress model, chapter status flow, resume logic, and Rich Live display
---

# Progress Tracking

## Key File

`utils/progress.py` — `BookProgress`, `Chapter`, and status enums.  
Serialized to `books/<slug>/book.json`.

## BookProgress Model

```python
class BookProgress(BaseModel):
    url: str                    # Source URL
    title: str                  # Original Chinese title
    title_vi: str               # Vietnamese title
    author: str                 # Original author
    author_vi: str              # Vietnamese author
    encoding: str               # Content encoding
    patterns: BookPatterns      # Discovered CSS selectors
    chapters: list[Chapter]     # All chapters with status
```

## Chapter Status Flow

```
PENDING ──▶ CRAWLED ──▶ TRANSLATED
    │           │            │
    └───────────┴────────────┴──▶ ERROR (if failed)
```

## Resume vs Force

```python
# Resume (default): skip completed chapters
chapters_to_process = [c for c in chapters if c.status == PENDING]

# Force mode (--force): re-process all
chapters_to_process = all_chapters

# Progress saved after EACH chapter (interrupt-safe)
progress.save(book_dir)
```

## Book Directory Structure

```
books/
└── <slug>/          # e.g., 8717-indexhtml
    ├── book.json    # BookProgress serialized
    ├── glossary.csv
    ├── raw/         # Downloaded .txt chapters
    ├── translated/  # Translated .txt chapters
    ├── epub_build/  # Build artifacts (auto-generated)
    └── output/      # Final ebook files
```

## Rich Live Table Display

```python
from rich.live import Live
from rich.table import Table

with Live(build_table(), console=console, transient=True) as live:
    while running:
        live.update(build_table())  # Rebuild with current stats
        await asyncio.sleep(1)
```

**Rules:**
- `transient=True` → table disappears cleanly when done
- Progress % in `table.title`, status messages in `table.caption`
- **NO `console.print()` inside Live** → causes scroll
- Store messages in `PipelineStats.status_message` instead

## Loading Progress

```python
progress = BookProgress.load(book_dir)   # Load existing or create new
progress.save(book_dir)                   # Persist after each chapter
```
