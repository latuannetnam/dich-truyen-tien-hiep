---
trigger: always_on
---

# Development Rules

Always use uv for project management and unit testing.

## App Architecture Quick Reference

**Pipeline:** `CRAWL -> TRANSLATE -> FORMAT -> EXPORT`

### Key Files by Phase

| Phase | Key Files | Purpose |
|-------|-----------|---------|
| **Crawl** | `crawler/pattern.py` | LLM pattern discovery for CSS selectors |
| | `crawler/downloader.py` | Chapter download with resume support |
| | `crawler/base.py` | HTTP client with retry & encoding detection |
| **Translate** | `translator/engine.py` | Main translation orchestration & chunking |
| | `translator/llm.py` | OpenAI API wrapper with retry logic |
| | `translator/style.py` | Style templates (tien_hiep, kiem_hiep, custom via yaml) |
| | `translator/glossary.py` | Term management & auto-generation from samples |
| **Format** | `formatter/assembler.py` | HTML book assembly with TOC generation |
| | `formatter/metadata.py` | Book metadata handling |
| **Export** | `exporter/calibre.py` | Calibre ebook-convert integration |
| **CLI** | `cli.py` | All CLI commands (crawl, translate, format, export, pipeline) |
| **Config** | `config.py` | Pydantic settings, env vars management |
| **Progress** | `utils/progress.py` | BookProgress, Chapter models & status tracking |

### Key Logic Patterns

1. **Translation flow:** `engine.py:translate_book()` loops chapters → `translate_chapter()` splits into chunks → `translate_chunk()` calls LLM
   - Uses context from previous chunk (last 500 chars) for continuity.
   - Updates progress via callback after each chunk completes.

2. **Style loading priority:** Custom styles in `styles/` directory are checked **BEFORE** built-in styles. This allows users to override default styles by creating a YAML file with the same name.

3. **Progress tracking:** `BookProgress.load(book_dir)` loads state from `book.json`. Chapters have status flow: PENDING → CRAWLED → TRANSLATED.

4. **Chunk progress:** `translate_chapter()` accepts `progress_callback(chunk_idx, total_chunks)` for fine-grained UI updates in the CLI.

5. **Glossary Generation:** Randomly samples text from chapters (configurable via env vars) to generate domain-specific terms using LLM before translation starts.

### Common Modification Points

- **Add new CLI command:** Add to `cli.py` with `@cli.command()` decorator.
- **Change translation behavior:** Modify `translator/engine.py:translate_chunk()` logic or update prompts in `translator/llm.py`.
- **Add new style:** Create YAML in `styles/` or add defaults to `BUILT_IN_STYLES` in `translator/style.py`.
- **Change glossary generation:** Modify `glossary.py:generate_glossary_from_samples()` and the `GLOSSARY_GENERATION_PROMPT`.
- **Change progress display:** Modify the Progress bar logic in `engine.py:translate_book()` (look for chunk progress calculation).

### Environment Variables

| Prefix | Purpose |
|--------|---------|
| `OPENAI_*` | LLM API configuration (API_KEY, BASE_URL, MODEL) |
| `TRANSLATION_GLOSSARY_*` | Glossary generation settings (samples, size, etc.) |
| `CRAWLER_*` | HTTP client settings (delay, retries) |
| `CALIBRE_*` | Path to Calibre executable |

### Full Architecture Doc
See `docs/ARCHITECTURE.md` for detailed diagrams, flowcharts, and in-depth explanations of mechanisms.
