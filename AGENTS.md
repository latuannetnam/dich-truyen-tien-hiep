# Agentic Coding Guide

This repository contains a Python CLI tool for crawling, translating, and exporting Chinese novels. It uses `uv` for dependency management and follows modern Python practices.

## 1. Build & Test Commands

Use `uv` to run commands in the project environment.

### Testing
- **Run all tests:**
  ```bash
  uv run pytest
  ```
- **Run a specific test file:**
  ```bash
  uv run pytest tests/test_crawler.py
  ```
- **Run a specific test case:**
  ```bash
  uv run pytest tests/test_crawler.py::TestEncoding::test_detect_gbk_encoding
  ```
- **Run integration tests (requires network/API):**
  ```bash
  uv run pytest -m "requires_network"
  ```

### Linting & Formatting
- **Lint code:**
  ```bash
  uv run ruff check .
  ```
- **Format code:**
  ```bash
  uv run ruff format .
  ```

### Running the CLI
- **Execute the tool:**
  ```bash
  uv run dich-truyen [command] [options]
  ```
  Example: `uv run dich-truyen crawl --url "https://site.com/novel"`

## 2. Code Style & Conventions

### General
- **Python Version:** 3.11+
- **Line Length:** 100 characters (enforced by Ruff).
- **Type Hints:** REQUIRED for all function arguments and return values.
  ```python
  def process_text(content: str, max_length: int = 100) -> Optional[str]:
      ...
  ```
- **Docstrings:** Use Google-style docstrings for classes and functions.
  ```python
  """Short summary.

  Args:
      param_name: Description.

  Returns:
      Description of return value.
  """
  ```

### Naming
- **Classes:** `PascalCase` (e.g., `BaseCrawler`, `ChapterDownloader`).
- **Functions/Variables:** `snake_case` (e.g., `fetch_page`, `chapter_id`).
- **Constants:** `UPPER_CASE` (e.g., `DEFAULT_TIMEOUT`).
- **Private Members:** Prefix with `_` (e.g., `_client`, `_parse_json`).

### Imports
- Group imports: Standard Library -> Third Party -> Local Application.
- Use absolute imports for project modules (e.g., `from dich_truyen.utils import ...`).

### Asynchronous Programming
- Use `asyncio` and `httpx` for network I/O.
- Implement `__aenter__` and `__aexit__` for resources requiring cleanup (like HTTP clients).
- Use `async` fixtures in tests (`@pytest.mark.asyncio`).

### Error Handling
- Catch specific exceptions (e.g., `httpx.HTTPStatusError`) rather than bare `Exception`.
- Use `rich.console` for user-facing logs/errors, not `print()`.
- Implement retry logic for network operations using loops or decorators.

### Libraries & Patterns
- **Config:** Use `pydantic` models for configuration.
- **CLI:** Use `click` for command definitions.
- **Output:** Use `rich` for formatted terminal output.
- **Paths:** Always use `pathlib.Path` instead of `os.path`.
