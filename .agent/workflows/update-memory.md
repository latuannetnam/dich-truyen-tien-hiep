---
description: How to update Agent memory after significant code changes
---

# Update Agent Memory

Run this workflow after completing any significant code change so that memory stays in sync with the codebase.

## When to Run

Trigger after ANY of the following:
- New feature or module added
- Existing component significantly refactored
- CLI command added, removed, or changed
- New config / environment variables added
- File/directory structure changed
- Key patterns, algorithms, or behavior changed

## Steps

1. **Identify affected modules** — compare the changed files against the mapping table below
2. **Open each affected module** in `.agent/memory/`
3. **Rewrite only the changed sections** — keep content factual, use tables and code blocks, no prose
4. **Do NOT touch unrelated modules**
5. **Confirm** by stating: `Memory updated: [module1.md, module2.md]`

## Module → Domain Mapping

| Changed files / area | Update this module |
|---|---|
| `pipeline/streaming.py`, queue design, orchestration | `architecture.md` |
| `crawler/*.py`, pattern discovery, encoding | `crawling.md` |
| `translator/*.py`, glossary, chunking, TF-IDF | `translation.md` |
| `exporter/*.py`, EPUB, Calibre | `export.md` |
| `cli.py` | `cli.md` |
| `config.py`, `.env.example`, env vars | `config.md` |
| `utils/progress.py`, `book.json` schema | `progress.md` |
| `tests/` | `testing.md` |
| `styles/`, `translator/style.py` | `styles.md` |

## Content Rules

- **Concise**: Use tables and code blocks. Avoid long paragraphs.
- **Accurate**: Only document what currently exists — no future/planned items.
- **Structured**: Follow the existing section headings in each module.
- **No duplication**: If something is in `dev.md`, don't repeat it in memory modules.
