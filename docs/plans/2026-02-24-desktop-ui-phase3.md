# Desktop UI Phase 3: "Edit & Configure" — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Settings editing, glossary management, and enhanced side-by-side reader from the browser.

**Architecture:** Add `ConfigService` and `GlossaryService` to the service layer. New API routes for settings CRUD and glossary CRUD. Three new frontend pages: Settings, Glossary Editor, enhanced Reader. CLI remains unchanged — settings still read from `.env`, glossary uses same CSV format.

**Tech Stack:** Python (FastAPI, Pydantic) · TypeScript (React, Next.js 15) · Tailwind CSS · Lucide React icons

**Design Doc:** [desktop-ui-design.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/docs/plans/2026-02-24-desktop-ui-design.md) → Phase 3

**Phase 2 Plan:** [desktop-ui-phase2.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/docs/plans/2026-02-24-desktop-ui-phase2.md) — Already implemented

### Current State (Phase 2 Complete)

| Component | Status |
|-----------|--------|
| FastAPI server (`api/server.py`) | ✅ Book/chapter + pipeline endpoints |
| Service layer | ✅ `EventBus`, `PipelineService` |
| WebSocket | ✅ Pipeline event streaming |
| Next.js frontend | ✅ Dashboard, Library, Book Detail, Reader, Pipeline Monitor, Wizard |
| Side-by-side Reader | ✅ Toggle exists in `ReaderView.tsx` (basic) |
| Settings page | ❌ Route exists in sidebar, no page |
| Glossary editor | ❌ Does not exist |
| `ConfigService` | ❌ Does not exist |
| `GlossaryService` | ❌ Does not exist |

### Key Constraints

- CLI must remain 100% functional after every task
- Settings reads/writes `.env` file — same file CLI uses
- Glossary uses existing `Glossary` class CSV format
- All tests pass (`uv run pytest tests/ -v`)
- Side-by-side reader enhancement builds on existing `ReaderView.tsx`

> [!IMPORTANT]
> **CLI Compatibility Audit Results:**
> 1. **No existing modules are modified** — all changes are additive (new files + `server.py` router registration)
> 2. **CLI never imports from `services/` or `api/routes/`** — pure isolation
> 3. **Risk 1 (Fixed):** `.env` writer handles quoted values (`KEY="value"`) by stripping quotes on read
> 4. **Risk 2 (Fixed):** Glossary API uses `_load_glossary_quiet()` to bypass `from_csv()`'s Rich console print

### Design System Quick Reference

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0B1120` | Main background |
| `--bg-surface` | `#111827` | Cards, panels |
| `--bg-elevated` | `#1F2937` | Hover states, active items |
| `--color-primary` | `#0D9488` (teal) | Active nav, progress bars |
| `--color-cta` | `#F97316` (orange) | Start/action buttons |
| Status colors | `#10B981` / `#F59E0B` / `#3B82F6` / `#EF4444` | Success / Warning / Info / Error |

---

## UI/UX Design Specifications

> **Source:** [MASTER.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/design-system/dich-truyen/MASTER.md) + ui-ux-pro-max skill research
> **Page overrides:** `design-system/dich-truyen/pages/` — settings.md, glossary-editor.md, reader.md

### Global UX Rules (All Phase 3 Pages)

| Rule | Implementation |
|------|---------------|
| **Loading states** | Show skeleton screens for operations >300ms. Never leave UI frozen. |
| **Form labels** | Every input MUST have a visible `<label>`. No placeholder-only inputs. |
| **Submit feedback** | Show loading spinner on button → then success/error toast. |
| **Toast notifications** | Auto-dismiss success after 3s, error after 5s. `role="alert"` + `aria-live="assertive"`. |
| **Inline validation** | Validate on blur for most fields, not only on submit. |
| **Cursor pointer** | All clickable elements: buttons, cards, table rows, links. |
| **Transitions** | All hover/state changes: `transition-colors duration-150` or `transition-all duration-200`. |
| **No emojis** | All icons from Lucide React. No emoji icons in UI. |
| **Focus states** | Visible `ring-2 ring-[var(--color-primary)]/50` on all interactive elements. |
| **Keyboard support** | Add `onKeyDown` alongside `onClick` on custom interactive elements. `tabIndex={0}` on non-native. |
| **Semantic HTML** | Use `<button>`, `<a>`, `<label>`, `<table>` — no div soup. |
| **Decorative icons** | Add `aria-hidden="true"` to decorative icons. |
| **Motion sensitivity** | `prefers-reduced-motion: reduce` → disable all non-essential animations. |
| **Table responsiveness** | Wrap tables in `overflow-x-auto` for mobile. |

### Page: Settings (`/settings`)

> **Full design spec:** [settings.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/design-system/dich-truyen/pages/settings.md)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Settings                                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌── API Configuration ────────────────────────────────────────┐   │
│  │  API Key          [••••••••••••••••]                         │   │
│  │  Base URL         [https://api.openai.com/v1]               │   │
│  │  Model            [gpt-4o                   ]               │   │
│  │  Max Tokens       [4096]    Temperature [0.7]               │   │
│  │                                          [Test Connection]  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌── Crawler Settings ─────────────────────────────────────────┐   │
│  │  Delay (ms)       [1000]    Timeout (s)  [30]               │   │
│  │  Max Retries      [3]                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌── Translation Settings ─────────────────────────────────────┐   │
│  │  Chunk Size       [2000]    Overlap      [300]              │   │
│  │  ☑ Polish Pass    ☑ Progressive Glossary                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌── Pipeline Settings ────────────────────────────────────────┐   │
│  │  Workers          [3]       Queue Size   [10]               │   │
│  │  Crawl Delay (ms) [1000]                                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│                              [Save Settings] [Reset to Defaults]   │
└─────────────────────────────────────────────────────────────────────┘
```

**Component Specs:**

| Component | Styling |
|-----------|---------|
| **Section card** | `bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6`. Title: `text-lg font-semibold text-[var(--text-primary)] mb-4`. |
| **Text inputs** | Same base as wizard inputs. `bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150`. Label: `text-[var(--text-secondary)] text-sm font-medium mb-2 block`. |
| **Password input** | Same as text input + toggle visibility button (`Eye` / `EyeOff` icons). |
| **Checkbox** | `w-5 h-5 rounded bg-[var(--bg-surface)] border border-[var(--border-default)]`. Checked: `bg-[var(--color-primary)] border-[var(--color-primary)]` with white check. |
| **Save button** | CTA style: `bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg px-6 py-2.5 font-medium`. Loading spinner during save. |
| **Reset button** | Ghost: `bg-transparent border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] rounded-lg px-6 py-2.5`. |
| **Test Connection** | `bg-[var(--color-primary)]/10 text-[var(--color-primary)] hover:bg-[var(--color-primary)]/20 rounded-lg px-4 py-2 text-sm`. Shows ✓/✗ result inline. |
| **Success toast** | `bg-[var(--color-success)]/15 border border-[var(--color-success)]/30 text-[var(--color-success)] rounded-lg p-3`. Auto-dismiss after 3s. |

**Interactions:**
- Load current config from GET `/api/v1/settings` on mount
- Save: PUT `/api/v1/settings` → writes `.env` file → reloads config
- Test Connection: POST `/api/v1/settings/test-connection` → shows success/error inline
- Reset fills form with defaults from `AppConfig` class defaults
- API key field is password input with toggle visibility

---

### Page: Glossary Editor (`/books/[id]/glossary`)

> **Full design spec:** [glossary-editor.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/design-system/dich-truyen/pages/glossary-editor.md)

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Back to Book Detail                                              │
│                                                                     │
│  Glossary — 仙逆 (Tiên Nghịch)                    42 terms         │
│                                                                     │
│  ┌── Search & Filter ──────────────────────────────────────────┐   │
│  │  🔍 [Search terms...        ]  ▾ [All Categories]           │   │
│  │                          [Import CSV] [Export CSV] [+ Add]  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌── Glossary Table ───────────────────────────────────────────┐   │
│  │  Chinese    │ Vietnamese     │ Category   │ Actions         │   │
│  │─────────────┼────────────────┼────────────┼─────────────────│   │
│  │  王林       │ Vương Lâm      │ character  │  ✏️ 🗑️          │   │
│  │  练气       │ Luyện Khí      │ realm      │  ✏️ 🗑️          │   │
│  │  ...        │ ...            │ ...        │  ...            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌── Add / Edit Form (inline or modal) ────────────────────────┐   │
│  │  Chinese    [王林          ]                                 │   │
│  │  Vietnamese [Vương Lâm     ]                                 │   │
│  │  Category   ▾ [character   ]                                 │   │
│  │  Notes      [Main protagonist]                               │   │
│  │                              [Cancel] [Save]                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Component Specs:**

| Component | Styling |
|-----------|---------|
| **Table** | `w-full`. Header: `bg-[var(--bg-elevated)] text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)]`. Row: `border-b border-[var(--border-default)] hover:bg-[var(--bg-elevated)]/50 transition-colors duration-150`. |
| **Category badge** | `px-2 py-0.5 rounded text-xs font-medium`. Colors per category: character=teal, realm=purple, technique=blue, location=amber, item=emerald, organization=rose, general=gray. |
| **Action buttons** | Icon only: `p-1.5 rounded hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer`. Edit: `Pencil` icon. Delete: `Trash2` icon `text-[var(--color-error)]`. |
| **Search input** | `bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-2.5` with `Search` icon prefix. |
| **Add button** | `bg-[var(--color-primary)] text-white rounded-lg px-4 py-2 text-sm font-medium` with `Plus` icon. |
| **Import/Export** | Ghost buttons: `border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] rounded-lg px-3 py-2 text-sm`. Icons: `Upload` / `Download`. |
| **Inline edit row** | Same row but inputs replace text. `bg-[var(--bg-elevated)]/30` highlight. |
| **Delete confirm** | Inline: row turns `bg-[var(--color-error)]/5`. "Delete this term?" with Cancel/Confirm. |

**Interactions:**
- Table loads all glossary terms from GET `/api/v1/books/:id/glossary`
- Search is client-side, filters as you type on Chinese + Vietnamese columns
- Category filter: dropdown with "All" + each category from `Glossary.CATEGORIES`
- Inline editing: click edit → row becomes input fields → Save/Cancel
- Add: click "+ Add" → empty row appears at top in edit mode
- Delete: click trash → inline confirmation → DELETE api call
- Import CSV: file picker → POST `/api/v1/books/:id/glossary/import`
- Export CSV: GET `/api/v1/books/:id/glossary/export` → downloads file
- Link from Book Detail page "Edit Glossary" button

---

### Enhanced Reader (`/books/[id]/read`)

> **Full design spec:** [reader.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/design-system/dich-truyen/pages/reader.md)

The side-by-side reader already exists in `ReaderView.tsx`. Phase 3 enhancements:

| Enhancement | Implementation |
|-------------|----------------|
| **Synced scrolling** | Both panes scroll together. Use `onScroll` handler to sync `scrollTop` proportionally between panes. |
| **Paragraph alignment** | Split content by `\n\n` and render in a shared grid row, aligning Chinese paragraphs with their Vietnamese translations. |
| **Reading progress** | Save last-read chapter to `localStorage` per book. Show "Continue reading" on Book Detail. |
| **Chapter dropdown** | Add a `<select>` in toolbar to jump directly to any translated chapter. |

---

## Task 1: ConfigService + Settings API

**Files:**
- Create: `src/dich_truyen/services/config_service.py`
- Create: `src/dich_truyen/api/routes/settings.py`
- Modify: `src/dich_truyen/api/server.py`
- Modify: `tests/test_api.py`
- Modify: `pyproject.toml`

**Step 1: Write failing tests**

Add to `tests/test_api.py`:

```python
# --- Settings API tests ---


def test_get_settings(tmp_path):
    """GET /settings returns current config."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()
    assert "llm" in data
    assert "crawler" in data
    assert "translation" in data
    assert "pipeline" in data


def test_update_settings(tmp_path):
    """PUT /settings updates config values."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.put("/api/v1/settings", json={
        "llm": {"model": "gpt-4o-mini"},
    })
    assert response.status_code == 200
    # Verify updated
    response = client.get("/api/v1/settings")
    assert response.json()["llm"]["model"] == "gpt-4o-mini"


def test_test_connection_no_key(tmp_path):
    """POST /settings/test-connection with empty key fails."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.post("/api/v1/settings/test-connection")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
```

**Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/test_api.py::test_get_settings tests/test_api.py::test_update_settings tests/test_api.py::test_test_connection_no_key -v
```

Expected: FAIL — 404 Not Found

**Step 3: Implement ConfigService**

Create `src/dich_truyen/services/config_service.py`:

```python
"""Configuration service for web UI.

Provides read/write access to app configuration. Reads from the in-memory
AppConfig and writes changes back to the .env file so CLI picks them up too.
"""

import os
from pathlib import Path
from typing import Any, Optional

from dich_truyen.config import AppConfig, get_config, set_config


class ConfigService:
    """Read and update application configuration.

    Updates are written to .env for persistence. The in-memory config
    is also refreshed so the running server picks up changes immediately.
    """

    def __init__(self, env_file: Optional[Path] = None) -> None:
        self._env_file = env_file or Path(".env")

    def get_settings(self) -> dict[str, Any]:
        """Get current configuration as a nested dict.

        Returns:
            Dict with sections: llm, crawler, translation, pipeline, export.
            API keys are masked for security.
        """
        config = get_config()
        return {
            "llm": {
                "api_key": self._mask_key(config.llm.api_key),
                "base_url": config.llm.base_url,
                "model": config.llm.model,
                "max_tokens": config.llm.max_tokens,
                "temperature": config.llm.temperature,
            },
            "crawler": {
                "delay_ms": config.crawler.delay_ms,
                "max_retries": config.crawler.max_retries,
                "timeout_seconds": config.crawler.timeout_seconds,
            },
            "translation": {
                "chunk_size": config.translation.chunk_size,
                "chunk_overlap": config.translation.chunk_overlap,
                "enable_polish_pass": config.translation.enable_polish_pass,
                "progressive_glossary": config.translation.progressive_glossary,
                "polish_temperature": config.translation.polish_temperature,
            },
            "pipeline": {
                "translator_workers": config.pipeline.translator_workers,
                "queue_size": config.pipeline.queue_size,
                "crawl_delay_ms": config.pipeline.crawl_delay_ms,
            },
            "export": {
                "parallel_workers": config.export.parallel_workers,
                "volume_size": config.export.volume_size,
                "fast_mode": config.export.fast_mode,
            },
        }

    def update_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Update configuration from a partial dict.

        Args:
            updates: Nested dict matching get_settings() structure.
                     Only provided keys are updated.

        Returns:
            Updated full settings dict.
        """
        env_vars: dict[str, str] = {}

        # Map nested dict keys to env var names
        section_prefix_map = {
            "llm": "OPENAI_",
            "crawler": "CRAWLER_",
            "translation": "TRANSLATION_",
            "pipeline": "PIPELINE_",
            "export": "EXPORT_",
        }

        for section, values in updates.items():
            if not isinstance(values, dict):
                continue
            prefix = section_prefix_map.get(section, "")
            for key, value in values.items():
                # Skip masked API keys (user didn't change them)
                if key == "api_key" and isinstance(value, str) and "••" in value:
                    continue
                env_name = f"{prefix}{key.upper()}"
                env_vars[env_name] = str(value)

        # Write to .env file
        self._update_env_file(env_vars)

        # Update environment and reload config
        for name, value in env_vars.items():
            os.environ[name] = value
        set_config(AppConfig.load(self._env_file))

        return self.get_settings()

    def test_connection(self) -> dict[str, Any]:
        """Test LLM API connection.

        Returns:
            Dict with 'success' bool and 'message' string.
        """
        config = get_config()
        if not config.llm.api_key:
            return {"success": False, "message": "API key is not configured"}

        try:
            import httpx

            response = httpx.get(
                f"{config.llm.base_url}/models",
                headers={"Authorization": f"Bearer {config.llm.api_key}"},
                timeout=10,
            )
            if response.status_code == 200:
                return {"success": True, "message": "Connection successful"}
            return {
                "success": False,
                "message": f"API returned {response.status_code}",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _mask_key(self, key: str) -> str:
        """Mask API key for display."""
        if not key or len(key) < 8:
            return "••••••••"
        return key[:4] + "••••" + key[-4:]

    def _update_env_file(self, env_vars: dict[str, str]) -> None:
        """Update .env file, preserving existing entries.

        Handles quoted values (KEY="value" or KEY='value') correctly.
        Preserves comments and blank lines.
        """
        lines: list[str] = []
        existing_keys: set[str] = set()

        if self._env_file.exists():
            for line in self._env_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    if key in env_vars:
                        lines.append(f"{key}={env_vars[key]}")
                        existing_keys.add(key)
                        continue
                lines.append(line)

        # Add new keys
        for key, value in env_vars.items():
            if key not in existing_keys:
                lines.append(f"{key}={value}")

        self._env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _strip_quotes(value: str) -> str:
        """Strip surrounding quotes from .env values."""
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            return value[1:-1]
        return value
```

**Step 4: Add python-multipart dependency**

Modify `pyproject.toml` to add `python-multipart` to dependencies (required by FastAPI for file uploads in Glossary API).

```toml
    "python-multipart>=0.0.9",
```

**Step 5: Implement settings routes**

Create `src/dich_truyen/api/routes/settings.py`:

```python
"""Settings API routes — read and update configuration."""

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

_config_service = None


def set_config_service(service) -> None:
    """Set the ConfigService instance."""
    global _config_service
    _config_service = service


@router.get("")
async def get_settings() -> dict[str, Any]:
    """Get current application settings."""
    return _config_service.get_settings()


@router.put("")
async def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Update application settings."""
    return _config_service.update_settings(updates)


@router.post("/test-connection")
async def test_connection() -> dict[str, Any]:
    """Test LLM API connection."""
    return _config_service.test_connection()
```

**Step 6: Wire up in server.py**

Modify `src/dich_truyen/api/server.py` — add imports and router registration:

```diff
 from dich_truyen.api.routes import books, pipeline
+from dich_truyen.api.routes import settings
 from dich_truyen.services.events import EventBus
 from dich_truyen.services.pipeline_service import PipelineService
+from dich_truyen.services.config_service import ConfigService
```

In `create_app()`, after pipeline router:

```diff
+    # Settings service
+    config_service = ConfigService()
+    settings.set_config_service(config_service)
+    app.include_router(settings.router)
```

**Step 7: Run tests — verify they pass**

```bash
uv run pytest tests/test_api.py -v
```

Expected: All tests pass including 3 new settings tests.

**Step 8: Run full test suite**

```bash
uv run pytest tests/ -v 2>&1 | Select-Object -Last 5
```

Expected: All tests pass.

**Step 9: Commit**

```bash
git add src/dich_truyen/services/config_service.py src/dich_truyen/api/routes/settings.py src/dich_truyen/api/server.py tests/test_api.py pyproject.toml
git commit -m "feat(api): add settings API and python-multipart dependency"
```

---

## Task 2: Glossary API Endpoints

**Files:**
- Create: `src/dich_truyen/api/routes/glossary.py`
- Modify: `src/dich_truyen/api/server.py`
- Modify: `tests/test_api.py`

**Step 1: Write failing tests**

Add to `tests/test_api.py`:

```python
# --- Glossary API tests ---


@pytest.fixture
def books_dir_with_glossary(books_dir):
    """Extend books_dir with a glossary CSV file."""
    import csv

    book_dir = books_dir / "test-book-1"
    glossary_path = book_dir / "glossary.csv"
    with open(glossary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["chinese", "vietnamese", "category", "notes"])
        writer.writerow(["王林", "Vương Lâm", "character", "Main character"])
        writer.writerow(["练气", "Luyện Khí", "realm", ""])
    return books_dir


def test_get_glossary(books_dir_with_glossary):
    """GET /books/:id/glossary returns glossary entries."""
    app = create_app(books_dir=books_dir_with_glossary)
    client = TestClient(app)
    response = client.get("/api/v1/books/test-book-1/glossary")
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 2
    assert data["entries"][0]["chinese"] == "王林"


def test_add_glossary_entry(books_dir_with_glossary):
    """POST /books/:id/glossary adds a new entry."""
    app = create_app(books_dir=books_dir_with_glossary)
    client = TestClient(app)
    response = client.post("/api/v1/books/test-book-1/glossary", json={
        "chinese": "筑基", "vietnamese": "Trúc Cơ", "category": "realm",
    })
    assert response.status_code == 200
    # Verify it was added
    response = client.get("/api/v1/books/test-book-1/glossary")
    assert len(response.json()["entries"]) == 3


def test_delete_glossary_entry(books_dir_with_glossary):
    """DELETE /books/:id/glossary/:term removes an entry."""
    app = create_app(books_dir=books_dir_with_glossary)
    client = TestClient(app)
    response = client.delete("/api/v1/books/test-book-1/glossary/王林")
    assert response.status_code == 200
    response = client.get("/api/v1/books/test-book-1/glossary")
    assert len(response.json()["entries"]) == 1


def test_get_glossary_book_not_found(tmp_path):
    """GET /books/:id/glossary returns 404 for unknown book."""
    app = create_app(books_dir=tmp_path)
    client = TestClient(app)
    response = client.get("/api/v1/books/nonexistent/glossary")
    assert response.status_code == 404


def test_export_glossary_csv(books_dir_with_glossary):
    """GET /books/:id/glossary/export returns CSV file."""
    app = create_app(books_dir=books_dir_with_glossary)
    client = TestClient(app)
    response = client.get("/api/v1/books/test-book-1/glossary/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "王林" in response.text
```

**Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/test_api.py::test_get_glossary -v
```

Expected: FAIL — 404

**Step 3: Implement glossary routes**

Create `src/dich_truyen/api/routes/glossary.py`:

```python
"""Glossary API routes — CRUD for book glossaries.

Note: Uses _load_glossary_quiet() instead of Glossary.load_or_create()
to avoid Glossary.from_csv()'s Rich console.print() spam on every request.
This ensures the server stdout stays clean while CLI behavior is unchanged.
"""

import csv
import io
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from dich_truyen.translator.glossary import Glossary, GlossaryEntry

router = APIRouter(prefix="/api/v1/books/{book_id}/glossary", tags=["glossary"])

_books_dir: Path = Path("books")


def set_books_dir(books_dir: Path) -> None:
    """Set the books directory path."""
    global _books_dir
    _books_dir = books_dir


def _get_book_dir(book_id: str) -> Path:
    """Get book directory, raising 404 if not found."""
    book_dir = _books_dir / book_id
    if not book_dir.exists():
        raise HTTPException(status_code=404, detail="Book not found")
    return book_dir


def _load_glossary_quiet(book_dir: Path) -> Glossary:
    """Load glossary without Rich console output.

    Glossary.from_csv() prints "Imported N entries" to stdout,
    which is fine for CLI but spams the API server log. This
    reads the CSV directly and constructs a Glossary silently.
    """
    glossary_path = book_dir / "glossary.csv"
    if not glossary_path.exists():
        return Glossary()

    entries: list[GlossaryEntry] = []
    with open(glossary_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append(
                GlossaryEntry(
                    chinese=row["chinese"],
                    vietnamese=row["vietnamese"],
                    category=row.get("category", "general"),
                    notes=row.get("notes") or None,
                )
            )
    return Glossary(entries)


class GlossaryEntryRequest(BaseModel):
    """Request body for adding/updating a glossary entry."""

    chinese: str
    vietnamese: str
    category: str = "general"
    notes: Optional[str] = None


class GlossaryResponse(BaseModel):
    """Response with glossary entries."""

    entries: list[dict[str, Any]]
    total: int
    categories: list[str]


@router.get("", response_model=GlossaryResponse)
async def get_glossary(book_id: str) -> GlossaryResponse:
    """Get all glossary entries for a book."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)
    entries = [
        {
            "chinese": e.chinese,
            "vietnamese": e.vietnamese,
            "category": e.category,
            "notes": e.notes,
        }
        for e in glossary.entries
    ]
    return GlossaryResponse(
        entries=entries,
        total=len(entries),
        categories=Glossary.CATEGORIES,
    )


@router.post("")
async def add_glossary_entry(
    book_id: str, entry: GlossaryEntryRequest
) -> dict[str, str]:
    """Add or update a glossary entry."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)
    glossary.add(GlossaryEntry(
        chinese=entry.chinese,
        vietnamese=entry.vietnamese,
        category=entry.category,
        notes=entry.notes,
    ))
    glossary.save(book_dir)
    return {"status": "ok"}


@router.put("/{term}")
async def update_glossary_entry(
    book_id: str, term: str, entry: GlossaryEntryRequest
) -> dict[str, str]:
    """Update an existing glossary entry."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)

    # Remove old entry if Chinese term changed
    if term != entry.chinese:
        glossary.remove(term)

    glossary.add(GlossaryEntry(
        chinese=entry.chinese,
        vietnamese=entry.vietnamese,
        category=entry.category,
        notes=entry.notes,
    ))
    glossary.save(book_dir)
    return {"status": "ok"}


@router.delete("/{term}")
async def delete_glossary_entry(book_id: str, term: str) -> dict[str, str]:
    """Delete a glossary entry by Chinese term."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)
    if not glossary.remove(term):
        raise HTTPException(status_code=404, detail="Term not found")
    glossary.save(book_dir)
    return {"status": "ok"}


@router.get("/export")
async def export_glossary_csv(book_id: str) -> StreamingResponse:
    """Export glossary as CSV download."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["chinese", "vietnamese", "category", "notes"])
    for entry in glossary.entries:
        writer.writerow([entry.chinese, entry.vietnamese, entry.category, entry.notes or ""])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={book_id}_glossary.csv"},
    )


@router.post("/import")
async def import_glossary_csv(
    book_id: str, file: UploadFile = File(...)
) -> dict[str, Any]:
    """Import glossary entries from uploaded CSV."""
    book_dir = _get_book_dir(book_id)
    glossary = _load_glossary_quiet(book_dir)

    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    for row in reader:
        if "chinese" in row and "vietnamese" in row:
            glossary.add(GlossaryEntry(
                chinese=row["chinese"],
                vietnamese=row["vietnamese"],
                category=row.get("category", "general"),
                notes=row.get("notes"),
            ))
            imported += 1

    glossary.save(book_dir)
    return {"status": "ok", "imported": imported, "total": len(glossary)}
```

**Step 4: Wire up in server.py**

```diff
 from dich_truyen.api.routes import books, pipeline
-from dich_truyen.api.routes import settings
+from dich_truyen.api.routes import settings, glossary
```

In `create_app()`:

```diff
+    # Glossary routes
+    glossary.set_books_dir(books_dir or Path("books"))
+    app.include_router(glossary.router)
```

**Step 5: Run tests — verify they pass**

```bash
uv run pytest tests/test_api.py -v
```

**Step 6: Run full test suite**

```bash
uv run pytest tests/ -v 2>&1 | Select-Object -Last 5
```

**Step 7: Commit**

```bash
git add src/dich_truyen/api/routes/glossary.py src/dich_truyen/api/server.py tests/test_api.py
git commit -m "feat(api): add glossary CRUD endpoints"
```

---

## Task 3: Settings Frontend Page

**Files:**
- Create: `web/src/app/settings/page.tsx`
- Create: `web/src/components/ui/ToastProvider.tsx` (or similar custom global toast system)
- Modify: `web/src/app/layout.tsx` (wrap with ToastProvider)
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/lib/types.ts`

**Step 1: Add TypeScript types**

Add to `web/src/lib/types.ts`:

```typescript
/** Application settings. */
export interface AppSettings {
  llm: {
    api_key: string;
    base_url: string;
    model: string;
    max_tokens: number;
    temperature: number;
  };
  crawler: {
    delay_ms: number;
    max_retries: number;
    timeout_seconds: number;
  };
  translation: {
    chunk_size: number;
    chunk_overlap: number;
    enable_polish_pass: boolean;
    progressive_glossary: boolean;
    polish_temperature: number;
  };
  pipeline: {
    translator_workers: number;
    queue_size: number;
    crawl_delay_ms: number;
  };
  export: {
    parallel_workers: number;
    volume_size: number;
    fast_mode: boolean;
  };
}

/** Test connection result. */
export interface TestConnectionResult {
  success: boolean;
  message: string;
}
```

**Step 2: Add API functions**

Add to `web/src/lib/api.ts`:

```typescript
export async function getSettings(): Promise<AppSettings> {
  return fetchJson<AppSettings>(`${API_BASE}/settings`);
}

export async function updateSettings(
  settings: Partial<AppSettings>
): Promise<AppSettings> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function testConnection(): Promise<TestConnectionResult> {
  return fetchJson<TestConnectionResult>(`${API_BASE}/settings/test-connection`);
}
```

**Step 3: Create Toast System**

Create a global Toast context (`ToastProvider.tsx`) and wrap `layout.tsx` with it, allowing any page to trigger success/error toasts.

**Step 4: Create Settings page**

Create `web/src/app/settings/page.tsx` — a form page with sections for each config group (API, Crawler, Translation, Pipeline, Export). Uses the design specs from the wireframe above. Key behaviors:

- Loads settings on mount via `getSettings()`
- Save button calls `updateSettings()` with changed values
- Test Connection button calls `testConnection()` and shows inline result
- Reset button reloads from server
- Success/error feedback via the global Toast system
- Password toggle for API key field

> **Note:** Full component code will be written during execution. The page follows the same patterns as existing pages (e.g., `/new/page.tsx` for form inputs, card-based sections).

**Step 5: Verify in browser**

Start dev servers and verify:
```bash
uv run dich-truyen ui
```
Navigate to `http://localhost:3000/settings` and verify:
- Settings load and display
- Save updates config
- Test Connection shows result
- Global toasts appear correctly

**Step 6: Commit**

```bash
git add web/src/app/settings/ web/src/lib/api.ts web/src/lib/types.ts web/src/app/layout.tsx web/src/components/ui/
git commit -m "feat(web): add global Toast system and Settings page"
```

---

## Task 4: Glossary Editor Frontend

**Files:**
- Create: `web/src/app/books/[id]/glossary/page.tsx`
- Create: `web/src/components/glossary/GlossaryEditor.tsx`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/lib/types.ts`
- Modify: `web/src/components/book/BookDetailView.tsx` (add "Edit Glossary" button)

**Step 1: Add TypeScript types**

Add to `web/src/lib/types.ts`:

```typescript
/** Glossary entry. */
export interface GlossaryEntryType {
  chinese: string;
  vietnamese: string;
  category: string;
  notes: string | null;
}

/** Glossary response. */
export interface GlossaryResponseType {
  entries: GlossaryEntryType[];
  total: number;
  categories: string[];
}
```

**Step 2: Add API functions**

Add to `web/src/lib/api.ts`:

```typescript
export async function getGlossary(bookId: string): Promise<GlossaryResponseType> {
  return fetchJson<GlossaryResponseType>(`${API_BASE}/books/${bookId}/glossary`);
}

export async function addGlossaryEntry(
  bookId: string,
  entry: Omit<GlossaryEntryType, "notes"> & { notes?: string }
): Promise<void> {
  const res = await fetch(`${API_BASE}/books/${bookId}/glossary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function updateGlossaryEntry(
  bookId: string,
  term: string,
  entry: Omit<GlossaryEntryType, "notes"> & { notes?: string }
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/books/${bookId}/glossary/${encodeURIComponent(term)}`,
    { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(entry) }
  );
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function deleteGlossaryEntry(bookId: string, term: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/books/${bookId}/glossary/${encodeURIComponent(term)}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function importGlossaryCsv(bookId: string, file: File): Promise<{imported: number}> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/books/${bookId}/glossary/import`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// For export, we just use the raw URL: `${API_BASE}/books/${bookId}/glossary/export`
```

**Step 3: Create GlossaryEditor component and page**

Create `web/src/components/glossary/GlossaryEditor.tsx` — an editable table with:
- Search + category filter toolbar
- Import/Export CSV buttons
- Inline add/edit/delete rows
- Category badges with distinct colors

Create `web/src/app/books/[id]/glossary/page.tsx` — wrapper that loads glossary data.

> **Note:** Full component code will be written during execution. Uses patterns from existing table components and the wireframe above.

**Step 4: Add "Edit Glossary" link to Book Detail**

Modify the Book Detail page/component to include an "Edit Glossary" button that links to `/books/[id]/glossary`.

**Step 5: Verify in browser**

Navigate to a book's glossary page and verify CRUD operations.

**Step 6: Commit**

```bash
git add web/src/app/books/*/glossary/ web/src/components/glossary/ web/src/lib/ web/src/components/book/
git commit -m "feat(web): add Glossary Editor page"
```

---

## Task 5: Enhanced Side-by-Side Reader

**Files:**
- Modify: `web/src/components/reader/ReaderView.tsx`
- Modify: `web/src/app/books/[id]/read/page.tsx`
- Modify: `web/src/components/book/BookDetailView.tsx`

**Step 1: Add paragraph-aligned side-by-side mode**

Current implementation uses a simple 2-column grid rendering full text blocks. Enhance to:

1. **Paragraph alignment**: Split both Chinese and Vietnamese by double newlines. Render as rows in a table/grid so paragraph N in Chinese aligns with paragraph N in Vietnamese.

2. **Synced scrolling**: When side-by-side is active, add `onScroll` handler that proportionally syncs `scrollTop` between panes.

3. **Chapter dropdown**: Add a `<select>` element in the toolbar between the back button and chapter indicator, allowing direct jump to any translated chapter.

**Step 2: Add reading progress persistence**

Save last-read chapter index to `localStorage` key `dich-truyen-last-read-{bookId}`. On Book Detail page, show "Continue Reading" button if a last-read chapter exists.

**Step 3: Verify in browser**

- Open a book with translated chapters
- Toggle side-by-side mode — verify paragraphs align
- Scroll one pane — verify other pane scrolls too
- Use chapter dropdown to jump
- Close and reopen — verify "Continue Reading" appears

**Step 4: Commit**

```bash
git add web/src/components/reader/ web/src/app/books/
git commit -m "feat(web): enhanced reader with paragraph alignment and reading progress"
```

---

## Task 6: Extract Remaining Services

**Files:**
- Create: `src/dich_truyen/services/glossary_service.py`
- Create: `src/dich_truyen/services/export_service.py`
- Create: `src/dich_truyen/services/style_service.py`
- Create: `src/dich_truyen/services/book_service.py`
- Modify: `src/dich_truyen/services/__init__.py`

These services wrap existing modules for future CLI refactoring. They are thin wrappers that don't change behavior — they just provide a clean API boundary.

**Step 1: Write tests for GlossaryService**

Create `tests/test_glossary_service.py`:

```python
"""Tests for GlossaryService."""

from pathlib import Path

import pytest

from dich_truyen.services.glossary_service import GlossaryService


@pytest.fixture
def glossary_service(tmp_path):
    """Create a GlossaryService with a temp book dir."""
    book_dir = tmp_path / "test-book"
    book_dir.mkdir()
    return GlossaryService(), book_dir


def test_glossary_service_list_empty(glossary_service):
    """Empty book dir returns empty glossary."""
    service, book_dir = glossary_service
    result = service.list_entries(book_dir)
    assert result == []


def test_glossary_service_add_and_list(glossary_service):
    """Add entry and list returns it."""
    service, book_dir = glossary_service
    service.add_entry(book_dir, "王林", "Vương Lâm", "character")
    entries = service.list_entries(book_dir)
    assert len(entries) == 1
    assert entries[0]["chinese"] == "王林"


def test_glossary_service_remove(glossary_service):
    """Remove entry."""
    service, book_dir = glossary_service
    service.add_entry(book_dir, "王林", "Vương Lâm", "character")
    assert service.remove_entry(book_dir, "王林") is True
    assert service.list_entries(book_dir) == []
```

**Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/test_glossary_service.py -v
```

**Step 3: Implement services**

Create each service as a thin wrapper around the existing module:

- `GlossaryService`: wraps `Glossary` class
- `ExportService`: wraps `DirectEPUBAssembler` + `CalibreConverter`
- `StyleService`: wraps `StyleManager`
- `BookService`: wraps `BookProgress` file operations

Each service follows the same pattern:

```python
class GlossaryService:
    """Glossary management service.

    Wraps the existing Glossary class with a dict-based API
    suitable for REST endpoints.
    """

    def list_entries(self, book_dir: Path) -> list[dict]:
        glossary = Glossary.load_or_create(book_dir)
        return [
            {"chinese": e.chinese, "vietnamese": e.vietnamese,
             "category": e.category, "notes": e.notes}
            for e in glossary.entries
        ]

    def add_entry(self, book_dir: Path, chinese: str,
                  vietnamese: str, category: str = "general",
                  notes: str | None = None) -> None:
        glossary = Glossary.load_or_create(book_dir)
        glossary.add(GlossaryEntry(
            chinese=chinese, vietnamese=vietnamese,
            category=category, notes=notes,
        ))
        glossary.save(book_dir)

    def remove_entry(self, book_dir: Path, chinese: str) -> bool:
        glossary = Glossary.load_or_create(book_dir)
        result = glossary.remove(chinese)
        if result:
            glossary.save(book_dir)
        return result
```

**Step 4: Run tests — verify they pass**

```bash
uv run pytest tests/test_glossary_service.py -v
```

**Step 5: Run full test suite**

```bash
uv run pytest tests/ -v 2>&1 | Select-Object -Last 5
```

**Step 6: Commit**

```bash
git add src/dich_truyen/services/ tests/test_glossary_service.py
git commit -m "feat(services): extract GlossaryService, ExportService, StyleService, BookService"
```

---

## Verification Plan

### Automated Tests

```bash
# Run all tests (should include new settings + glossary API tests)
uv run pytest tests/ -v

# Run only Phase 3 tests
uv run pytest tests/test_api.py -v -k "settings or glossary"
uv run pytest tests/test_glossary_service.py -v

# Lint and format
uv run ruff check .
uv run ruff format --check .
```

### Browser Verification

Start the app and manually verify each page:

```bash
uv run dich-truyen ui
```

1. **Settings page** (`/settings`): loads config, saves changes, test connection works
2. **Glossary editor** (`/books/{id}/glossary`): CRUD operations, search/filter, CSV import/export
3. **Enhanced reader**: paragraph alignment in side-by-side, chapter dropdown, reading progress
4. **CLI unchanged**: Run `uv run dich-truyen pipeline --help` to verify CLI still works
