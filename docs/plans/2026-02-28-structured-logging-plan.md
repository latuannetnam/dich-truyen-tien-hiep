# Structured Logging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all Rich console output with structlog, remove the `rich` dependency entirely, and wire up `--verbose`/`--quiet`/`--log-file` CLI flags.

**Architecture:** Create a central `log.py` module that configures structlog with stdlib logging integration. All 14 source files replace `console.print()` with `logger.*()`. CLI display commands use `click.echo()`. The Rich Live dashboard in `streaming.py` is replaced with periodic log lines.

**Tech Stack:** `structlog>=24.0.0`, stdlib `logging`, `click.echo()`

---

## Task 1: Add structlog dependency, create `log.py`

**Files:**
- Modify: `pyproject.toml:8-24`
- Create: `src/dich_truyen/log.py`

**Step 1: Add structlog to dependencies**

In `pyproject.toml`, add `structlog` and remove `rich`:

```diff
 dependencies = [
     "openai>=1.0.0",
     "httpx>=0.27.0",
     "beautifulsoup4>=4.12.0",
     "lxml>=5.0.0",
     "playwright>=1.40.0",
     "click>=8.1.0",
-    "rich>=13.0.0",
+    "structlog>=24.0.0",
     "pydantic>=2.0.0",
     "pydantic-settings>=2.0.0",
     "python-dotenv>=1.0.0",
     "chardet>=5.0.0",
     "pyyaml>=6.0.0",
     "fastapi>=0.115.0",
     "uvicorn[standard]>=0.34.0",
     "python-multipart>=0.0.9",
 ]
```

**Step 2: Install dependencies**

Run: `uv sync`

**Step 3: Create `src/dich_truyen/log.py`**

```python
"""Centralized structured logging configuration."""

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog


def configure_logging(
    verbosity: int = 0,
    log_file: Optional[Path] = None,
) -> None:
    """Configure structlog + stdlib logging.

    Args:
        verbosity: -1=quiet (WARNING), 0=normal (INFO), 1=verbose (DEBUG)
        log_file: Optional path to write JSON log lines
    """
    level_map = {-1: logging.WARNING, 0: logging.INFO, 1: logging.DEBUG}
    level = level_map.get(verbosity, logging.INFO)

    # Shared structlog processors
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Configure structlog to wrap stdlib logging
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Console handler — colored, human-readable on stderr
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()),
        ],
    )
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(console_formatter)

    # Root logger setup
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(console_handler)
    root.setLevel(level)

    # JSON file handler (if log_file specified)
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

**Step 4: Verify module imports**

Run: `uv run python -c "from dich_truyen.log import configure_logging; configure_logging(); print('OK')"`
Expected: `OK` printed (with structlog format)

**Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/dich_truyen/log.py
git commit -m "feat: add structlog, create central log.py module"
```

---

## Task 2: Wire up CLI logging flags

**Files:**
- Modify: `src/dich_truyen/cli.py:1-45`

**Step 1: Replace Rich import and wire up logging in CLI group**

Replace lines 1–45 of `cli.py`:

```diff
 """Main CLI entry point for dich-truyen."""

 import asyncio
 from pathlib import Path
 from typing import Optional

 import click
+import structlog
 from dotenv import load_dotenv
-from rich.console import Console

 from dich_truyen import __version__
 from dich_truyen.config import AppConfig, set_config

-console = Console()
+logger = structlog.get_logger()


 def setup_config(env_file: Optional[Path] = None) -> None:
     """Load configuration from environment."""
     if env_file:
         load_dotenv(env_file)
     else:
         load_dotenv()

     config = AppConfig.load(env_file)
     set_config(config)


 @click.group()
 @click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
 @click.option("--quiet", "-q", is_flag=True, help="Minimal output")
+@click.option("--log-file", type=click.Path(), help="Write JSON logs to file")
 @click.option("--env-file", type=click.Path(exists=True), help="Path to .env file")
 @click.version_option(version=__version__)
 @click.pass_context
-def cli(ctx, verbose: bool, quiet: bool, env_file: Optional[str]) -> None:
+def cli(ctx, verbose: bool, quiet: bool, log_file: Optional[str], env_file: Optional[str]) -> None:
     """Chinese novel translation tool.

     Crawl, translate, format, and export Chinese novels to ebooks.
     """
+    from dich_truyen.log import configure_logging
+
     ctx.ensure_object(dict)
     ctx.obj["verbose"] = verbose
     ctx.obj["quiet"] = quiet

+    # Configure structured logging
+    verbosity = 1 if verbose else (-1 if quiet else 0)
+    log_path = Path(log_file) if log_file else None
+    configure_logging(verbosity=verbosity, log_file=log_path)
+
     # Setup configuration
     setup_config(Path(env_file) if env_file else None)
```

**Step 2: Run CLI help to verify flags**

Run: `uv run dich-truyen --help`
Expected: Shows `--verbose`, `--quiet`, `--log-file` options

**Step 3: Test verbose output**

Run: `uv run dich-truyen -v --help`
Expected: No errors, help displayed

**Step 4: Commit**

```bash
git add src/dich_truyen/cli.py
git commit -m "feat: wire up --verbose/--quiet/--log-file CLI flags"
```

---

## Task 3: Migrate CLI commands from console.print to logger/click.echo

**Files:**
- Modify: `src/dich_truyen/cli.py:52-451`

**Step 1: Replace all `console.print()` calls in CLI commands**

Replace every `console.print(f"[color]...[/color]")` with the appropriate `logger.*()` or `click.echo()`:

- Error messages → `logger.error()` then `raise SystemExit(1)`
- Warnings → `logger.warning()`
- Info/status → `logger.info()`
- CLI display output (glossary show, style list) → `click.echo()`
- UI startup messages → `click.echo()` (user-facing startup info)

Key replacements (complete list for the file):

| Line | Old | New |
|------|-----|-----|
| 114 | `console.print("[red]Error: Either --url or --book-dir is required[/red]")` | `logger.error("missing_argument", detail="Either --url or --book-dir is required")` |
| 118 | `console.print("[red]Error: Cannot use both --crawl-only and --translate-only[/red]")` | `logger.error("invalid_flags", detail="Cannot use both --crawl-only and --translate-only")` |
| 126 | `console.print(f"[red]Error: Directory not found: {target_dir}[/red]")` | `logger.error("dir_not_found", path=str(target_dir))` |
| 133 | `console.print(f"[blue]Importing glossary from {glossary}...[/blue]")` | `logger.info("importing_glossary", path=glossary)` |
| 136 | `console.print(f"[green]Imported {len(imported)} glossary entries[/green]")` | `logger.info("glossary_imported", entries=len(imported))` |
| 153 | `console.print(f"[yellow]Warning: ...")` | `logger.warning("pipeline_errors", crawl_errors=result.failed_crawl, translate_errors=result.failed_translate)` |
| 164 | `console.print("\n[bold blue]═══ Exporting ═══[/bold blue]")` | `logger.info("export_started")` |
| 172 | `console.print(f"[red]Export failed: {export_result.error_message}[/red]")` | `logger.error("export_failed", error=export_result.error_message)` |
| 175 | `console.print(f"[green]✓ Exported: {export_result.output_path}[/green]")` | `logger.info("export_complete", path=export_result.output_path)` |
| 177-185 | All `console.print` skip messages | `logger.info()` / `logger.warning()` with structured keys |
| 225 | `console.print(f"[red]Export failed: ...")` | `logger.error("export_failed", error=result.error_message)` |
| 228 | `console.print(f"[green]Book exported: ...")` | `logger.info("export_complete", path=result.output_path)` |
| 251 | `console.print(f"[yellow]No glossary found...")` | `click.echo(f"No glossary found in {book_dir}")` |
| 255 | `console.print(f"[green]Exported {len(g)}...")` | `click.echo(f"Exported {len(g)} entries to {output}")` |
| 273-276 | Glossary import console calls | `click.echo()` equivalents |
| 288-296 | Glossary show display | `click.echo()` equivalents |
| 318-320 | Style list display | `click.echo()` equivalents |
| 333-345 | Style generate status | `logger.info()` equivalents |
| 382-394 | UI errors | `logger.error()` equivalents |
| 415-418 | UI startup messages | `click.echo()` equivalents |
| 440 | Shutdown message | `click.echo("Shutting down...")` |

**Step 2: Verify CLI runs without import errors**

Run: `uv run dich-truyen --help`
Expected: Help output, no errors

**Step 3: Commit**

```bash
git add src/dich_truyen/cli.py
git commit -m "refactor: migrate CLI from console.print to logger/click.echo"
```

---

## Task 4: Migrate `config.py` — replace Rich Table with logger

**Files:**
- Modify: `src/dich_truyen/config.py`

**Step 1: Replace Rich imports and console.print calls**

```diff
-from rich.console import Console
-from rich.table import Table
+import structlog
```

In `get_effective_llm_config()` (lines 256-310): Replace the `console = Console()` + `console.print()` block with:

```python
    if task_name:
        logger = structlog.get_logger()
        logger.debug(
            "llm_config",
            task=task_name,
            model=effective.model,
            base_url=effective.base_url,
            max_tokens=effective.max_tokens,
            temperature=effective.temperature,
            api_key=effective.api_key[:8] + "..." if len(effective.api_key) > 8 else "***",
        )
```

In `log_llm_config_summary()` (lines 313-372): Replace the Rich Table with structured log lines:

```python
def log_llm_config_summary() -> None:
    """Log a summary of all LLM configurations."""
    logger = structlog.get_logger()
    app_config = get_config()

    logger.info(
        "llm_config_default",
        model=app_config.llm.model,
        base_url=app_config.llm.base_url,
        max_tokens=app_config.llm.max_tokens,
        temperature=app_config.llm.temperature,
    )

    task_configs: list[tuple[str, TaskLLMConfig]] = [
        ("crawler", app_config.crawler_llm),
        ("glossary", app_config.glossary_llm),
        ("translator", app_config.translator_llm),
    ]

    for task_name, task_cfg in task_configs:
        has_override = bool(task_cfg.model or task_cfg.api_key)
        if has_override:
            effective = get_effective_llm_config(task_cfg, app_config.llm)
            logger.info(
                "llm_config_override",
                task=task_name,
                model=effective.model,
                base_url=effective.base_url,
                max_tokens=effective.max_tokens,
                temperature=effective.temperature,
            )
```

**Step 2: Verify no Rich imports remain**

Run: `uv run python -c "from dich_truyen.config import log_llm_config_summary; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/dich_truyen/config.py
git commit -m "refactor: migrate config.py from Rich Table to structlog"
```

---

## Task 5: Migrate `translator/llm.py`

**Files:**
- Modify: `src/dich_truyen/translator/llm.py`

**Step 1: Replace Rich with structlog**

```diff
-from rich.console import Console
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

All `console.print()` calls → `logger.*()`:

| Line | Old | New |
|------|-----|-----|
| 60-66 | Default LLM Config block | `logger.debug("llm_config_default", model=..., ...)` |
| 120 | `console.print(f"[yellow]LLM attempt {attempt + 1} failed: {e}[/yellow]")` | `logger.warning("llm_retry", attempt=attempt + 1, error=str(e))` |
| 337 | `console.print(f"[red]LLM connection failed: {e}[/red]")` | `logger.error("llm_connection_failed", error=str(e))` |

**Step 2: Commit**

```bash
git add src/dich_truyen/translator/llm.py
git commit -m "refactor: migrate translator/llm.py to structlog"
```

---

## Task 6: Migrate `translator/style.py`

**Files:**
- Modify: `src/dich_truyen/translator/style.py`

**Step 1: Replace Rich with structlog**

```diff
-from rich.console import Console
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

| Line | Old | New |
|------|-----|-----|
| 76 | `console.print(f"[green]Saved style template to {path}[/green]")` | `logger.info("style_saved", path=str(path))` |
| 295 | `console.print(f"[dim]  Using custom style: {yaml_path}[/dim]")` | `logger.debug("style_loaded", name=name, source="custom", path=str(yaml_path))` |
| 302 | `console.print(f"[dim]  Using built-in style: {name}[/dim]")` | `logger.debug("style_loaded", name=name, source="built-in")` |
| 374 | `console.print(f"[red]Failed to parse style response: {e}[/red]")` | `logger.error("style_parse_failed", error=str(e))` |

**Step 2: Commit**

```bash
git add src/dich_truyen/translator/style.py
git commit -m "refactor: migrate translator/style.py to structlog"
```

---

## Task 7: Migrate `translator/engine.py`

**Files:**
- Modify: `src/dich_truyen/translator/engine.py`

**Step 1: Replace Rich imports with structlog**

```diff
-from rich.console import Console
-from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

Key replacements:

| Line | Old | New |
|------|-----|-----|
| 394 | `console.print(f"[yellow]Polish attempt...")` | `logger.warning("polish_retry", attempt=attempt + 1, error=str(e))` |
| 398 | `console.print(f"[yellow]Polish failed...")` | `logger.warning("polish_failed", attempts=max_retries + 1, error=str(last_error))` |
| 602 | `console.print("[green]All chapters already translated![/green]")` | `logger.info("all_chapters_translated")` |
| 610 | `console.print(f"[blue]Translating {len(chapters_to_translate)}...")` | `logger.info("translation_started", chapters=len(chapters_to_translate))` |
| 620 | Calculating total chunks | `logger.debug("calculating_chunks")` |
| 631-637 | `with Progress(...)` block | Remove entirely — use simple loop with periodic logging |
| 682 | Progressive glossary | `logger.debug("glossary_terms_added", count=len(new_terms))` |
| 695 | Error | `logger.error("chapter_translation_error", chapter=chapter.index, error=str(e))` |
| 707-710 | Final summary | `logger.info("translation_complete", translated=result.translated, skipped=result.skipped, failed=result.failed)` |
| 743-745 | Style loaded/not found | `logger.info()`/`logger.warning()` |
| 756 | Generating glossary | `logger.info("generating_glossary")` |
| 774-777 | Sample selection | `logger.debug("glossary_sampling", ...)` |
| 795 | Generated entries | `logger.info("glossary_generated", entries=len(glossary))` |
| 800+ | Metadata translation | `logger.info("translating_metadata")` |

The `translate_book()` method's `with Progress(...)` block needs to be replaced with a simple for-loop. Remove the Rich Progress bar and just log each chapter:

```python
        for chapter in chapters_to_translate:
            chapter_desc = f"Ch.{chapter.index}"
            logger.info("translating_chapter", chapter=chapter.index, title=(chapter.title_cn or "")[:20])

            try:
                # ... existing logic stays the same ...
                await self.translate_chapter(source_path, output_path, progress_callback)
                # ...
            except Exception as e:
                # ...

            progress.save(book_dir)
```

**Step 2: Commit**

```bash
git add src/dich_truyen/translator/engine.py
git commit -m "refactor: migrate translator/engine.py to structlog, remove Rich Progress"
```

---

## Task 8: Migrate `translator/glossary.py`

**Files:**
- Modify: `src/dich_truyen/translator/glossary.py`

**Step 1: Replace Rich with structlog**

```diff
-from rich.console import Console
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

Key replacements:

| Line | Old | New |
|------|-----|-----|
| 300 | `console.print(f"[green]Imported {len(entries)} entries from {path}[/green]")` | `logger.info("glossary_imported", entries=len(entries), path=str(path))` |
| 414 | Batch processing message | `logger.info("glossary_batch_start", samples=len(sample_texts), batches=num_batches)` |
| 420 | Batch N message | `logger.debug("glossary_batch", batch=batch_num, total=num_batches, samples=len(batch))` |
| 445 | Found terms | `logger.debug("glossary_batch_terms", batch=batch_num, terms=len(batch_entries))` |
| 447 | Parse failed | `logger.warning("glossary_batch_parse_error", batch=batch_num, error=str(e))` |
| 449 | No JSON found | `logger.warning("glossary_batch_no_json", batch=batch_num)` |
| 451 | Batch failed | `logger.error("glossary_batch_failed", batch=batch_num, error=str(e))` |
| 462 | Generated entries | `logger.info("glossary_generated", unique_entries=len(unique_entries))` |
| 467 | Limited entries | `logger.debug("glossary_limited", max_entries=max_entries)` |

**Step 2: Commit**

```bash
git add src/dich_truyen/translator/glossary.py
git commit -m "refactor: migrate translator/glossary.py to structlog"
```

---

## Task 9: Migrate `crawler/base.py`

**Files:**
- Modify: `src/dich_truyen/crawler/base.py`

**Step 1: Replace Rich with structlog**

```diff
-from rich.console import Console
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

| Line | Old | New |
|------|-----|-----|
| 68 | `console.print(f"[yellow]HTTP {e.response.status_code}...")` | `logger.warning("http_error", status=e.response.status_code, url=url)` |
| 74 | `console.print(f"[yellow]Attempt {attempt + 1}...")` | `logger.warning("fetch_retry", attempt=attempt + 1, error=str(e), url=url)` |

**Step 2: Commit**

```bash
git add src/dich_truyen/crawler/base.py
git commit -m "refactor: migrate crawler/base.py to structlog"
```

---

## Task 10: Migrate `crawler/downloader.py`

**Files:**
- Modify: `src/dich_truyen/crawler/downloader.py`

**Step 1: Replace Rich with structlog**

```diff
-from rich.console import Console
-from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

Replace the Rich Progress bar in `download_chapters()` with a simple loop + logging:

```python
        logger.info("download_started", chapters=len(chapters_to_download), skipped=skipped)

        async with BaseCrawler(self.config) as crawler:
            for i, chapter in enumerate(chapters_to_download, 1):
                logger.debug("downloading_chapter", chapter=chapter.index, title=(chapter.title_cn or "")[:20])

                try:
                    # ... existing download logic stays the same ...
                except Exception as e:
                    error_msg = f"Chapter {chapter.index}: {str(e)}"
                    result.errors.append(error_msg)
                    result.failed += 1
                    progress.update_chapter_status(chapter.index, ChapterStatus.ERROR, str(e))
                    logger.error("download_error", chapter=chapter.index, error=str(e))

                progress.save(self.book_dir)
                await crawler.delay()

                if i % 10 == 0:
                    logger.info("download_progress", completed=i, total=len(chapters_to_download))
```

All other `console.print()` calls in this file → appropriate `logger.*()`.

**Step 2: Commit**

```bash
git add src/dich_truyen/crawler/downloader.py
git commit -m "refactor: migrate crawler/downloader.py to structlog, remove Rich Progress"
```

---

## Task 11: Migrate `crawler/pattern.py`

**Files:**
- Modify: `src/dich_truyen/crawler/pattern.py`

**Step 1: Replace Rich with structlog**

```diff
-from rich.console import Console
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

All `console.print(f"[dim]...")` debug messages → `logger.debug(...)` with structured keys.
All `console.print(f"[yellow]Warning:...")` → `logger.warning(...)`.

**Step 2: Commit**

```bash
git add src/dich_truyen/crawler/pattern.py
git commit -m "refactor: migrate crawler/pattern.py to structlog"
```

---

## Task 12: Migrate `exporter/epub_assembler.py`

**Files:**
- Modify: `src/dich_truyen/exporter/epub_assembler.py`

**Step 1: Replace Rich with structlog**

```diff
-from rich.console import Console
-from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

Replace Rich Progress bar in `assemble()` with simple logging:

| Line | Old | New |
|------|-----|-----|
| 134 | `console.print(f"[blue]Assembling EPUB...")` | `logger.info("epub_assembling", chapters=len(translated_chapters))` |
| 137-196 | `with Progress(...) as prog:` block | Remove Progress wrapper; keep the parallel write logic. Add periodic logs. |
| 198 | `console.print(f"[green]✓ Created {epub_path}[/green]")` | `logger.info("epub_created", path=str(epub_path))` |

**Step 2: Commit**

```bash
git add src/dich_truyen/exporter/epub_assembler.py
git commit -m "refactor: migrate exporter/epub_assembler.py to structlog"
```

---

## Task 13: Migrate `exporter/calibre.py`

**Files:**
- Modify: `src/dich_truyen/exporter/calibre.py`

**Step 1: Replace Rich with structlog**

```diff
-from rich.console import Console
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

| Line | Old | New |
|------|-----|-----|
| 167 | `console.print(f"[blue]Exporting to...")` | `logger.info("calibre_exporting", format=output_format.upper())` |
| 181 | `console.print(f"[green]Export successful...")` | `logger.info("calibre_export_success", path=str(output_path))` |
| 185 | `console.print(f"[red]Export failed...")` | `logger.error("calibre_export_failed", error=error_msg)` |
| 228 | `console.print(f"[blue]Converting EPUB...")` | `logger.info("calibre_converting", format=output_format.upper())` |

**Step 2: Commit**

```bash
git add src/dich_truyen/exporter/calibre.py
git commit -m "refactor: migrate exporter/calibre.py to structlog"
```

---

## Task 14: Migrate `formatter/metadata.py` and `formatter/assembler.py`

**Files:**
- Modify: `src/dich_truyen/formatter/metadata.py`
- Modify: `src/dich_truyen/formatter/assembler.py`

**Step 1: Migrate metadata.py**

```diff
-from rich.console import Console
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

Note: `metadata.py` imports Console but doesn't actually call `console.print()` in any of its methods. Just remove the import and the `console = Console()` line.

**Step 2: Migrate assembler.py**

```diff
-from rich.console import Console
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

| Line | Old | New |
|------|-----|-----|
| 287 | `console.print(f"[blue]Assembling {len(chapters)} chapters...")` | `logger.info("html_assembling", chapters=len(chapters))` |
| 322 | `console.print(f"[green]Book assembled: {output_path}[/green]")` | `logger.info("html_assembled", path=str(output_path))` |

**Step 3: Commit**

```bash
git add src/dich_truyen/formatter/metadata.py src/dich_truyen/formatter/assembler.py
git commit -m "refactor: migrate formatter modules to structlog"
```

---

## Task 15: Migrate `pipeline/streaming.py` — the big one

**Files:**
- Modify: `src/dich_truyen/pipeline/streaming.py`

This is the largest migration. The entire Rich Live/Table/Progress dashboard needs removal.

**Step 1: Replace Rich imports with structlog**

```diff
-from rich.console import Console
-from rich.live import Live
-from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn
-from rich.table import Table
+import structlog
...
-console = Console()
+logger = structlog.get_logger()
```

**Step 2: Replace all console.print() calls with logger**

Lines 206-211 (pipeline status):
```python
        logger.info("pipeline_started",
            book=self.progress.title,
            total_chapters=len(chapters),
            to_crawl=len(to_crawl),
            to_translate=len(to_translate),
            already_done=len(already_done),
        )
```

Lines 214-221 (all completed):
```python
        if not to_crawl and not to_translate:
            logger.info("all_chapters_completed")
            return PipelineResult(...)
```

Lines 224, 259, 262, 275-278, 291 — all simple replacements.

**Step 3: Replace Live dashboard with periodic logging task**

Remove the entire `build_status_table()` function (lines 353-398) and the `with Live(...)` block (lines 400-440).

Replace with:

```python
        try:
            async def log_progress():
                """Log pipeline progress periodically."""
                try:
                    while not self._stop_requested and not self._shutdown_event.is_set():
                        total_target = len(to_crawl) + len(to_translate)
                        logger.info("pipeline_progress",
                            crawled=f"{self.stats.chapters_crawled}/{len(to_crawl)}",
                            translated=f"{self.stats.chapters_translated}/{total_target}",
                            queue=self.stats.chapters_in_queue,
                            glossary=self.stats.glossary_count,
                            errors=self.stats.crawl_errors + self.stats.translate_errors,
                        )
                        await asyncio.sleep(10)  # Log every 10 seconds
                except asyncio.CancelledError:
                    pass

            progress_task = asyncio.create_task(log_progress())

            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                logger.warning("shutdown_requested")
                self._shutdown_event.set()
                self._cancelled = True

                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=30
                    )
                except asyncio.TimeoutError:
                    logger.warning("shutdown_timeout")
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
            finally:
                self._stop_requested = True
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logger.error("pipeline_error", error=str(e))
            self._cancelled = True
```

Also remove the `from rich.live import Live` and `from rich.box import SIMPLE` imports on lines 350-351.

Lines 471-484 (final summary):
```python
        if was_cancelled:
            logger.warning("pipeline_interrupted",
                crawled=self.stats.chapters_crawled,
                translated=self.stats.chapters_translated,
            )
        else:
            logger.info("pipeline_complete",
                crawled=self.stats.chapters_crawled,
                translated=self.stats.chapters_translated,
                crawl_errors=self.stats.crawl_errors,
                translate_errors=self.stats.translate_errors,
                glossary=len(self.glossary) if self.glossary else 0,
            )
```

Lines 731, 747 (glossary generation):
```python
        logger.debug("glossary_exists", entries=len(self.glossary))
        # ...
        logger.info("generating_glossary_from_crawled")
```

**Step 4: Commit**

```bash
git add src/dich_truyen/pipeline/streaming.py
git commit -m "refactor: migrate streaming pipeline to structlog, remove Live dashboard"
```

---

## Task 16: Update services comments, verify no Rich references remain

**Files:**
- Modify: `src/dich_truyen/services/events.py` (update comment)
- Modify: `src/dich_truyen/services/glossary_service.py` (update comment)

**Step 1: Update comments referencing Rich**

In `services/events.py` line 4, update comment:
```diff
-- CLI subscribes → Rich console output (future refactor)
+- CLI subscribes → structlog output
```

In `services/glossary_service.py` lines 18 and 32, update comments:
```diff
-    Uses quiet loading to avoid Rich console output on every API request.
+    Uses quiet loading to avoid console output on every API request.
```
```diff
-        """Load glossary from CSV without Rich console output."""
+        """Load glossary from CSV without console output."""
```

**Step 2: Verify no Rich imports remain**

Run: `uv run python -c "import ast, pathlib; files = pathlib.Path('src/dich_truyen').rglob('*.py'); [print(f) for f in files if 'rich' in f.read_text(encoding='utf-8').lower() and 'rich' in [n.module for n in ast.parse(f.read_text(encoding='utf-8')).body if isinstance(n, ast.Import) or isinstance(n, ast.ImportFrom) and n.module and 'rich' in n.module]]"`

Or simpler manual check:

Run: `findstr /s /i "from rich" src\dich_truyen\*.py`
Expected: No results

**Step 3: Commit**

```bash
git add src/dich_truyen/services/events.py src/dich_truyen/services/glossary_service.py
git commit -m "chore: remove Rich references from comments"
```

---

## Task 17: Run existing tests

**Step 1: Run all tests**

Run: `uv run pytest -x -v`
Expected: All tests pass. The tests don't reference `console` directly, so they should be unaffected.

**Step 2: Run linter**

Run: `uv run ruff check .`
Expected: No lint errors (or only pre-existing ones)

**Step 3: Fix any test failures**

If tests import `console` indirectly through modules, mock `structlog.get_logger()` instead.

---

## Task 18: Integration smoke test

**Step 1: Test normal mode**

Run: `uv run dich-truyen --help`
Expected: Help with `--verbose`, `--quiet`, `--log-file` options

**Step 2: Test verbose mode**

Run: `uv run dich-truyen -v glossary show --book-dir books/some-book 2>nul`
Expected: DEBUG-level log lines visible (or "No glossary found" message)

**Step 3: Test quiet mode**

Run: `uv run dich-truyen -q --help`
Expected: Only help output, no extra log lines

**Step 4: Test log file**

Run: `uv run dich-truyen --log-file test.log --help`
Expected: `test.log` file created (possibly empty if no logging during --help)

**Step 5: Clean up**

```bash
del test.log 2>nul
```

**Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete Rich → structlog migration"
```

---

## Verification Plan

### Automated Tests

Run existing test suite to verify no regressions:

```bash
uv run pytest -x -v
```

Expected: All existing tests pass without modification (tests don't reference `console`).

### Lint Check

```bash
uv run ruff check .
```

Expected: No new lint errors.

### Manual Verification

1. **No Rich imports**: `findstr /s /i "from rich" src\dich_truyen\*.py` → no results
2. **CLI --help**: `uv run dich-truyen --help` → shows `--verbose`, `--quiet`, `--log-file`
3. **Style list**: `uv run dich-truyen style list` → shows styles via click.echo
4. **Verbose mode**: `uv run dich-truyen -v style list` → shows DEBUG-level structlog output
5. **(Optional) Full pipeline**: If API key is configured, run a small pipeline to verify structured log output
