---
trigger: always_on
---

# Development Rules

> **Note:** This file is gitignored. Use PowerShell to update it:
> ```powershell
> $content = Get-Content ".agent\rules\dev.md" -Raw
> # ... modify $content ...
> Set-Content ".agent\rules\dev.md" $content -NoNewline
> ```

Always use `uv` for project management and unit testing.

## Build & Test Commands

```bash
uv run pytest                          # All tests
uv run pytest tests/test_crawler.py    # Single file
uv run pytest -m "requires_network"    # Integration tests
uv run ruff check .                    # Lint
uv run ruff format .                   # Format
uv run dich-truyen [command] [options] # Run CLI
```

## Code Style Essentials

- **Python:** 3.11+, line length 100 (Ruff enforced)
- **Type hints:** Required on all functions
- **Docstrings:** Google-style
- **Naming:** `PascalCase` classes, `snake_case` functions/vars, `UPPER_CASE` constants, `_prefix` private
- **Imports:** stdlib → third-party → local, absolute imports only
- **Async:** Use `asyncio` + `httpx`; `async` fixtures with `@pytest.mark.asyncio`
- **Errors:** Catch specific exceptions; use `rich.console` not `print()`
- **Paths:** Always `pathlib.Path`, never `os.path`
- **Config:** Pydantic models
- **CLI:** Click with `@cli.command()`
- **Output:** Rich for formatted terminal output

## Memory Update Rule

> **After any significant change, run the `/update-memory` workflow** to keep memory in sync.

## Memory Modules

Detailed knowledge is split into focused modules in `.agent/memory/`:

| Module | Topic |
|--------|-------|
| [`architecture.md`](.agent/memory/architecture.md) | Pipeline overview, key files map, modification points |
| [`crawling.md`](.agent/memory/crawling.md) | LLM pattern discovery, encoding, resume logic |
| [`translation.md`](.agent/memory/translation.md) | Engine, glossary, chunking, TF-IDF, prompt structure |
| [`export.md`](.agent/memory/export.md) | EPUB assembly, Calibre, output formats |
| [`cli.md`](.agent/memory/cli.md) | CLI command tree, options, adding new commands |
| [`config.md`](.agent/memory/config.md) | All env vars, Pydantic settings hierarchy |
| [`progress.md`](.agent/memory/progress.md) | BookProgress, chapter status flow, Rich Live rules |
| [`testing.md`](.agent/memory/testing.md) | Test commands, fixtures, async patterns |
| [`styles.md`](.agent/memory/styles.md) | Style YAML schema, priority loading, creating styles |
