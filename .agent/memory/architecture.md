---
description: Pipeline overview, component map, data flow, and key design decisions
---

# Architecture

## Pipeline Overview

**StreamingPipeline** = Concurrent CRAWL + TRANSLATE → EXPORT

```
┌─────────────────────────────────────────────────────────────────┐
│                     StreamingPipeline                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐       UNBOUNDED                               │
│  │   Crawler    │──────▶ QUEUE ──────▶ ┌─────────────────┐     │
│  │  (Producer)  │        (∞)           │ Translator W1   │     │
│  │  Downloads   │                      └─────────────────┘     │
│  │  chapters    │                      ┌─────────────────┐     │
│  │  (never      │                      │ Translator W2   │     │
│  │   blocks)    │                      └─────────────────┘     │
│  └──────────────┘                      ┌─────────────────┐     │
│        ↓                               │ Translator W3   │     │
│  Saves to disk immediately             └─────────────────┘     │
│                                                                  │
│            ══════════════════════════════════                   │
│                              ▼                                   │
│                     ┌──────────────┐                            │
│                     │    EXPORT    │  (only when all_done=True) │
│                     │ Direct EPUB  │                            │
│                     │ + Calibre    │                            │
│                     └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

**Unbounded queue** (`maxsize=0`): Crawler never blocks. Translators consume at their own pace.

**Conditional export**: Only triggers when `result.all_done and not result.cancelled`.

## Key Files Map

| Phase | File | Purpose |
|-------|------|---------|
| **Pipeline** | `pipeline/streaming.py` | Orchestration, queue, worker management |
| **Crawl** | `crawler/pattern.py` | LLM CSS selector discovery |
| | `crawler/downloader.py` | Chapter download with resume |
| | `crawler/base.py` | HTTP client, retry, encoding detection |
| **Translate** | `translator/engine.py` | Translation orchestration & chunking |
| | `translator/llm.py` | OpenAI API wrapper, retry logic |
| | `translator/style.py` | Style templates & priority loading |
| | `translator/glossary.py` | Term management & auto-generation |
| | `translator/term_scorer.py` | TF-IDF based glossary selection |
| **Export** | `exporter/epub_assembler.py` | Direct EPUB assembly |
| | `exporter/calibre.py` | Calibre AZW3/MOBI/PDF conversion |
| **CLI** | `cli.py` | All user-facing commands |
| **Config** | `config.py` | Pydantic settings & env vars |
| **Progress** | `utils/progress.py` | BookProgress & chapter status |

## Common Modification Points

| Goal | Where |
|------|-------|
| Pipeline behavior | `pipeline/streaming.py:run()` and `_translate_consumer()` |
| Translation logic | `translator/engine.py:translate_chunk_with_context_marker()` |
| Glossary generation | `translator/glossary.py:generate_glossary_from_samples()` |
| CLI commands | `cli.py` with `@cli.command()` |
