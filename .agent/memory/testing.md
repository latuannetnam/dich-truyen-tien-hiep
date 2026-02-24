---
description: Test commands, test structure, fixtures, and patterns
---

# Testing

## Commands

```bash
# Run all tests
uv run pytest

# Run specific file
uv run pytest tests/test_crawler.py

# Run specific test case
uv run pytest tests/test_crawler.py::TestEncoding::test_detect_gbk_encoding

# Run integration tests (requires network/API)
uv run pytest -m "requires_network"

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src
```

## Linting & Formatting

```bash
uv run ruff check .     # Lint
uv run ruff format .    # Format

# Frontend lint
cd web && npm run lint
```

## Test Directory

```
tests/
├── test_api.py        # FastAPI endpoint tests (httpx TestClient)
├── test_crawler.py
├── test_translator.py
├── test_glossary.py
├── test_progress.py
├── test_export.py
├── test_pipeline.py
└── conftest.py        # Shared fixtures
```

## Key Patterns

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_async_function()
    assert result == expected
```

### Integration Test Marker

```python
@pytest.mark.requires_network
async def test_real_api_call():
    ...
```

### Fixtures (conftest.py)

```python
@pytest.fixture
def sample_book_dir(tmp_path):
    # Creates a temporary book directory for testing
    ...

@pytest.fixture
def mock_llm_client():
    # Returns a mock LLM client that doesn't make real API calls
    ...
```
