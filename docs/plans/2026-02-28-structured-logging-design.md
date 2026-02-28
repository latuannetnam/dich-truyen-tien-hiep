# Structured Logging: Replace Rich with structlog

## Summary

Replace all `rich.console.Console.print()` usage and Rich UI components (Live dashboard, Progress bars, Tables) with **structlog** for structured, leveled logging. Remove the `rich` dependency entirely.

## Motivation

- **Debugging**: Leveled logging (`DEBUG`/`INFO`/`WARNING`/`ERROR`) enables filtering noise via `--verbose`/`--quiet`
- **Analytics**: JSON log files enable post-mortem debugging of long pipeline runs
- **Simplicity**: Web UI already provides interactive dashboards; CLI doesn't need Rich UI
- **Consistency**: Single output system instead of scattered `console.print()` calls

## Design

### 1. Central Logging Module — `src/dich_truyen/log.py`

```python
import logging
import sys
from pathlib import Path

import structlog


def configure_logging(
    verbosity: int = 0,       # -1=quiet, 0=normal, 1=verbose
    log_file: Path | None = None,
) -> None:
    """Configure structlog + stdlib logging."""
    
    # Map verbosity to level
    level = {-1: logging.WARNING, 0: logging.INFO, 1: logging.DEBUG}.get(verbosity, logging.INFO)
    
    # Shared processors (structlog pipeline)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Terminal handler — colored, human-readable
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()),
        ],
    )
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(console_formatter)
    
    # Root logger
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(console_handler)
    root.setLevel(level)
    
    # File handler — JSON lines (if log_file specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        json_formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(json_formatter)
        file_handler.setLevel(logging.DEBUG)  # Always capture everything to file
        root.addHandler(file_handler)
    
    # Quiet noisy third-party loggers
    for name in ("httpx", "httpcore", "openai", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)
```

**Usage in any module:**
```python
import structlog
logger = structlog.get_logger()

# Simple
logger.info("pipeline_started", book="my-novel", chapters=100)
logger.warning("crawl_retry", chapter=5, attempt=2, error="timeout")

# With bound context (carries through all subsequent calls)
log = logger.bind(worker=2)
log.info("translating_chapter", chapter=5, chunks=3)
```

### 2. CLI Integration

Wire up existing `--verbose`/`--quiet` flags (currently unused) + add `--log-file`:

```python
@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Show debug-level output")
@click.option("--quiet", "-q", is_flag=True, help="Only show warnings and errors")
@click.option("--log-file", type=click.Path(), help="Write JSON logs to file")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, verbose, quiet, log_file):
    from dich_truyen.log import configure_logging
    
    verbosity = 1 if verbose else (-1 if quiet else 0)
    log_path = Path(log_file) if log_file else None
    configure_logging(verbosity=verbosity, log_file=log_path)
```

For CLI display commands (`glossary show`, `style list`), use `click.echo()` instead of Rich tables.

### 3. Pipeline Dashboard Replacement

The Rich `Live` + `Table` dashboard in `streaming.py` gets replaced with periodic log lines:

```python
# Instead of Live table, log progress periodically
logger.info("pipeline_progress",
    crawled=f"{stats.chapters_crawled}/{len(to_crawl)}",
    translated=f"{stats.chapters_translated}/{total_target}",
    queue=stats.chapters_in_queue,
    glossary=stats.glossary_count,
    errors=stats.crawl_errors + stats.translate_errors,
)
```

The `build_status_table()`, `update_display()`, and entire `with Live(...)` block get removed. A simple periodic logging task replaces them.

### 4. Migration Mapping

Each Rich pattern maps to a structlog call:

| Rich pattern | structlog replacement |
|---|---|
| `console.print(f"[green]Success: {x}[/green]")` | `logger.info("success", detail=x)` |
| `console.print(f"[yellow]Warning: {x}[/yellow]")` | `logger.warning("warning_msg", detail=x)` |
| `console.print(f"[red]Error: {x}[/red]")` | `logger.error("error_msg", detail=x)` |
| `console.print(f"[dim]Debug info: {x}[/dim]")` | `logger.debug("debug_info", detail=x)` |
| `console.print(f"[blue]Status: {x}[/blue]")` | `logger.info("status", detail=x)` |
| `console.print(f"[bold]Title[/bold]")` | `logger.info("title")` |

### 5. Files to Migrate

| File | What changes |
|------|-------------|
| **`log.py`** | **NEW** — Central config |
| **`cli.py`** | Wire up `configure_logging()`, replace `console` → `logger` + `click.echo()` |
| **`pipeline/streaming.py`** | Remove Rich Live/Table/Progress, replace with periodic `logger.info()` |
| **`translator/engine.py`** | Replace `console.print()` → `logger.*()`, remove Rich Progress |
| **`translator/glossary.py`** | Replace `console.print()` → `logger.*()` |
| **`translator/llm.py`** | Replace `console.print()` → `logger.*()` |
| **`translator/style.py`** | Replace `console.print()` → `logger.*()` |
| **`crawler/pattern.py`** | Replace → `logger.*()` |
| **`crawler/downloader.py`** | Replace → `logger.*()`, remove Rich Progress |
| **`crawler/base.py`** | Replace → `logger.*()` |
| **`exporter/epub_assembler.py`** | Replace → `logger.*()`, remove Rich Progress |
| **`exporter/calibre.py`** | Replace → `logger.*()` |
| **`formatter/metadata.py`** | Replace → `logger.*()` |
| **`formatter/assembler.py`** | Replace → `logger.*()` |
| **`config.py`** | Replace → `logger.*()`, remove Rich Table |
| **`pyproject.toml`** | Remove `rich>=13.0.0`, add `structlog>=24.0.0` |

### 6. What Stays / What Goes

| Component | Status |
|-----------|--------|
| `rich` dependency | **REMOVED** from `pyproject.toml` |
| `Live` dashboard | **REMOVED** → periodic log lines |
| `Progress` bars | **REMOVED** → `logger.info("progress", ...)` |
| `Rich.Table` | **REMOVED** → `click.echo()` for CLI display |
| `console.print()` | **REMOVED** → `logger.*()` everywhere |
| `--verbose`/`--quiet` flags | **WIRED UP** (currently unused) |
| `--log-file` flag | **NEW** |
| EventBus (services/events.py) | **UNCHANGED** — not a logging concern |
| Web UI | **UNCHANGED** — uses API/WebSocket, not console |

## Terminal Output Examples

**Normal mode** (`dich-truyen pipeline --url ...`):
```
2026-02-28T14:30:00 [info     ] pipeline_started               book=my-novel chapters=100
2026-02-28T14:30:01 [info     ] setup_translation              style=tien_hiep
2026-02-28T14:30:05 [info     ] glossary_generated             entries=42
2026-02-28T14:30:06 [info     ] pipeline_progress              crawled=5/80 translated=2/100
2026-02-28T14:30:10 [info     ] pipeline_progress              crawled=12/80 translated=8/100
2026-02-28T14:30:15 [warning  ] crawl_error                    chapter=15 error=timeout
2026-02-28T14:31:00 [info     ] pipeline_complete              crawled=80 translated=98 errors=2
```

**Verbose mode** (`dich-truyen -v pipeline --url ...`):
```
2026-02-28T14:30:00 [debug    ] llm_config                     model=gpt-4o base_url=https://...
2026-02-28T14:30:00 [info     ] pipeline_started               book=my-novel chapters=100
2026-02-28T14:30:01 [debug    ] style_loaded                   name=tien_hiep source=built-in
2026-02-28T14:30:02 [debug    ] chapter_crawled                chapter=1 title=第一章...
```

**Quiet mode** (`dich-truyen -q pipeline --url ...`):
```
2026-02-28T14:30:15 [warning  ] crawl_error                    chapter=15 error=timeout
```

**JSON log file** (`--log-file pipeline.log`):
```json
{"event": "pipeline_started", "book": "my-novel", "chapters": 100, "level": "info", "timestamp": "2026-02-28T14:30:00"}
{"event": "chapter_crawled", "chapter": 1, "level": "debug", "timestamp": "2026-02-28T14:30:02"}
```
