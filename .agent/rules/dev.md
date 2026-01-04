---
trigger: always_on
---

# Development Rules

Always use uv for project management and unit testing.

## App Architecture Quick Reference

**Pipeline:** `StreamingPipeline` = Concurrent CRAWL + TRANSLATE → EXPORT

### Key Files

| Component | Key Files | Purpose |
|-----------|-----------|---------|
| **Pipeline** | `pipeline/streaming.py` | Concurrent crawl/translate with queue |
| **Crawl** | `crawler/pattern.py` | LLM CSS selector discovery |
| | `crawler/downloader.py` | Chapter download with resume |
| **Translate** | `translator/engine.py` | Translation orchestration & chunking |
| | `translator/glossary.py` | Term management & auto-generation |
| | `translator/style.py` | Style templates (custom YAML in `styles/`) |
| **Export** | `exporter/epub_assembler.py` | Direct EPUB assembly |
| | `exporter/calibre.py` | Calibre AZW3/MOBI/PDF conversion |
| **CLI** | `cli.py` | Commands: pipeline, export, glossary, style |
| **Config** | `config.py` | Pydantic settings & env vars |
| **Progress** | `utils/progress.py` | BookProgress & Chapter status tracking |

### CLI Commands

```
dich-truyen
├── pipeline      # Main workflow (--crawl-only, --translate-only, --skip-export)
├── export        # Standalone ebook export
├── glossary      # show, export, import
└── style         # list, generate
```

### Key Patterns

1. **Streaming Pipeline:** `StreamingPipeline.run()` creates crawler producer + N translator workers with shared queue. Glossary generated after first chapters crawled.

2. **Glossary Sharing:** All workers share same `Glossary` object. Progressive extraction adds terms with `_glossary_lock`.

3. **Progress Tracking:** `BookProgress.load(book_dir)` → chapters have status: PENDING → CRAWLED → TRANSLATED.

4. **Style Priority:** `styles/` directory checked BEFORE built-in styles.

### Common Modification Points

- **Pipeline behavior:** `pipeline/streaming.py:run()` and `_translate_consumer()`
- **Translation logic:** `translator/engine.py:translate_chunk_with_context_marker()`
- **Glossary generation:** `glossary.py:generate_glossary_from_samples()`
- **CLI commands:** `cli.py` with `@cli.command()` decorator

### Environment Variables

| Prefix | Purpose |
|--------|---------|
| `OPENAI_*` | LLM API (API_KEY, BASE_URL, MODEL) |
| `TRANSLATION_GLOSSARY_*` | Glossary settings (samples, size) |
| `PIPELINE_*` | Worker count, queue size |
| `CALIBRE_*` | Calibre executable path |

### Full Architecture
See `docs/ARCHITECTURE.md` for detailed diagrams.
