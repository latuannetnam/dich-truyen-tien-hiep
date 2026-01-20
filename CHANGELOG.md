# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-01-20

### Added
- **Multi-Model LLM Configuration**: Implemented granular control over LLM settings for different tasks. Users can now configure distinct models, API keys, and parameters for Crawler, Glossary, and Translator components via `CRAWLER_LLM_*`, `GLOSSARY_LLM_*`, and `TRANSLATOR_LLM_*` environment variables.
- **Two-Pass Translation (Polishing)**: Introduced an "Editor-in-Chief" workflow. Added `enable_polish_pass` configuration to perform a second refinement pass on translations, improving literary quality.
- **Streaming Pipeline**: Implemented a concurrent producer-consumer pipeline (`StreamPipeline`) that allows crawling and translating chapters in parallel. This significantly speeds up processing for large novels.
- **Direct EPUB Assembly**: Added a native Python EPUB generator (`epub_assembler.py`) to construct EPUB files directly, improving export performance and reducing dependency on external tools for intermediate steps.
- **Glossary Management**:
    - Added TF-IDF term scoring (`TermScorer`) for more intelligent glossary extraction.
    - Added automatic glossary annotation in source text to help the LLM use correct terms.
    - Added state tracking to maintain narrative consistency across chunks.
- **CLI Improvements**:
    - Added `log_llm_config_summary` to display the effective configuration table on startup.
    - Unified CLI commands for `crawl`, `translate`, `export`, and `pipeline`.

### Changed
- **Architecture**: Refactored the core engine to support asynchronous processing and better modularity using `uv` and `asyncio`.
- **Configuration**: Migrated to Pydantic-based `AppConfig` with nested configuration classes (`LLMConfig`, `TranslationConfig`, etc.) for better type safety and validation.
- **Documentation**: Added comprehensive guides:
    - `AGENTS.md` for agentic coding standards.
    - `ARCHITECTURE.md` for system design.
    - `MULTI_MODEL_CONFIG_PLAN.md` and `POLISH_PASS_IMPLEMENTATION.md` for feature specifications.

### Fixed
- Fixed race conditions in the glossary update mechanism during parallel processing.
- Fixed `Ctrl+C` interrupt handling to ensure graceful shutdown and auto-export of progress.
- Fixed re-crawling bug when using `--translate-only --force`.
