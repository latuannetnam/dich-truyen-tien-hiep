---
description: How to update Agent memory after significant code changes
---

# Update Agent Memory & READMEs

Run this workflow after completing any significant code change so that memory and documentation stay in sync with the codebase.

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
5. **Update READMEs if needed** — see README mapping below
6. **Confirm** by stating: `Memory updated: [module1.md, module2.md]. READMEs updated: [file1, file2]` (omit READMEs section if none changed)

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

## README → Domain Mapping

Three-tier README system: master READMEs link to `web/README.md` for UI detail.

| Changed files / area | Update this README |
|---|---|
| CLI commands added/changed, new config vars, installation, styles | `README.md` + `README.en.md` (both languages) |
| New web pages, components, API endpoints, UI features | `web/README.md` (features, structure, API table) |
| New API endpoints (backend) | `web/README.md` API table |
| Major new feature (CLI + Web) | All three READMEs |

### README Update Rules

- `README.md` and `README.en.md` must stay in sync (same structure, different language)
- `web/README.md` features section: each feature gets its own `###` heading with screenshot placeholder
- Screenshot placeholder format: `<!-- TODO: Add screenshot -->` followed by `<!-- ![Name](docs/screenshots/name.png) -->`
- Keep the `web/README.md` directory structure tree and API endpoint table up to date
- Master READMEs reference Web UI via `[Giao Diện Web](web/README.md)` / `[Web UI](web/README.md)` link

## Content Rules

- **Concise**: Use tables and code blocks. Avoid long paragraphs.
- **Accurate**: Only document what currently exists — no future/planned items.
- **Structured**: Follow the existing section headings in each module.
- **No duplication**: If something is in `dev.md`, don't repeat it in memory modules.
- **READMEs**: Keep bilingual master READMEs identical in structure. Web README owns UI detail.
