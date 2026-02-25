---
description: Pydantic settings, environment variables, and configuration hierarchy
---

# Configuration

## Key File

`config.py` — Pydantic `BaseSettings` classes, loaded from env vars and `.env` file.

## Settings Hierarchy

```python
AppConfig(BaseSettings)
├── llm: LLMConfig           # OPENAI_* vars
├── crawler: CrawlerConfig   # CRAWLER_* vars
├── translation: TranslationConfig  # TRANSLATION_* vars
├── pipeline: PipelineConfig  # PIPELINE_* vars
├── calibre: CalibreConfig   # CALIBRE_* vars
├── export: ExportConfig     # EXPORT_* vars
├── crawler_llm: CrawlerLLMConfig     # Task-specific LLM overrides
├── glossary_llm: GlossaryLLMConfig   # Task-specific LLM overrides
└── translator_llm: TranslatorLLMConfig # Task-specific LLM overrides
```

## Environment Variables Reference

### LLM / API

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | API key |
| `OPENAI_BASE_URL` | API base URL (for proxies / local models) |
| `OPENAI_MODEL` | Model name (e.g., `gpt-4o-mini`) |

### Crawler

| Variable | Default | Purpose |
|----------|---------|---------|
| `CRAWLER_DELAY` | `1.0` | Seconds between requests |
| `CRAWLER_RETRIES` | `3` | Max retry attempts |
| `CRAWLER_TIMEOUT` | `30` | Request timeout (seconds) |

### Translation

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRANSLATION_CHUNK_SIZE` | 2000 | Chars per translation chunk |
| `TRANSLATION_CHUNK_OVERLAP` | 300 | Context chars from previous chunk |
| `TRANSLATION_CONCURRENT_REQUESTS` | 3 | Max parallel API calls per worker |
| `TRANSLATION_PROGRESSIVE_GLOSSARY` | `true` | Extract new terms during translation |
| `TRANSLATION_GLOSSARY_SAMPLE_CHAPTERS` | 5 | Chapters sampled for initial glossary |
| `TRANSLATION_GLOSSARY_SAMPLE_SIZE` | 3000 | Chars per sample chapter |

### Pipeline

| Variable | Default | Purpose |
|----------|---------|---------|
| `PIPELINE_WORKERS` | 3 | Number of translator worker processes |
| `PIPELINE_QUEUE_SIZE` | 0 | Queue max size (0 = unbounded) |
| `PIPELINE_CRAWL_DELAY_MS` | 500 | Crawl delay within pipeline (ms) |

### Export / Calibre

| Variable | Default | Purpose |
|----------|---------|---------|
| `EXPORT_PARALLEL_WORKERS` | 8 | Threads for parallel chapter writing |
| `EXPORT_VOLUME_SIZE` | 0 | Chapters per volume (0 = single file) |
| `EXPORT_FAST_MODE` | `true` | Use direct EPUB assembly |
| `CALIBRE_EXECUTABLE` | `ebook-convert` | Path to Calibre converter |

## Usage Pattern

```python
from dich_truyen.config import get_config

config = get_config()
model = config.llm.model
delay = config.crawler.delay
```

### ConfigService (API settings management)

```python
from dich_truyen.services.config_service import ConfigService

svc = ConfigService()           # Uses .env in CWD
settings = svc.get_settings()   # Returns dict with masked API keys
svc.update_settings({"llm": {"model": "gpt-4o"}})  # Writes to .env + reloads
result = svc.test_connection()  # Returns {"success": bool, "message": str}
```
