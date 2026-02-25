# Desktop UI Phase 4: "Complete & Polish" — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Full feature parity with premium feel — Style Manager, Export controls, animations, error handling, plus user-requested i18n and theme toggle.

**Architecture:** Add `styles` and `export` API routes using existing service wrappers. Two new frontend pages. Add CSS animation system and comprehensive error/loading states across all existing pages. Finally, add i18n and light/dark theme support.

**Tech Stack:** Python (FastAPI, Pydantic) · TypeScript (React, Next.js 15) · Vanilla CSS with design tokens · Lucide React icons

**Design Doc:** [desktop-ui-design.md](file:///d:/latuan/Programming/dich-truyen-tien-hiep/docs/plans/2026-02-24-desktop-ui-design.md) → Phase 4

---

### Current State (Phase 3 Complete)

| Component | Status |
|-----------|--------|
| API routes | ✅ books, pipeline, settings, glossary (5 route files) |
| Services | ✅ EventBus, PipelineService, ConfigService, GlossaryService, ExportService, StyleService, BookService |
| Frontend pages | ✅ Dashboard, Library, Book Detail, Reader, Pipeline Monitor, Wizard, Settings, Glossary Editor (10 pages) |
| Styles API | ❌ No route file, no frontend page |
| Export API | ❌ No route file, no frontend controls |
| CSS animations | ❌ No `@keyframes`, no `prefers-reduced-motion` |
| Error boundaries | ❌ No global error handling |
| i18n | ❌ English only |
| Theme toggle | ❌ Dark mode only |

### Key Constraints

- CLI must remain 100% functional
- All tests pass (`uv run pytest tests/ -v`)
- Frontend builds cleanly (`npx next build`)
- Existing CSS design token system (`var(--xxx)`) must be preserved
- Animation timing: 150–300ms for micro-interactions, `ease-out` for enter, `ease-in` for exit

---

## Task 1: Styles API Routes

**Files:**
- Create: `src/dich_truyen/api/routes/styles.py`
- Modify: `src/dich_truyen/api/server.py`
- Modify: `tests/test_api.py`

**Step 1: Write tests**

Add to `tests/test_api.py`:

```python
def test_list_styles(client):
    """List styles returns available styles."""
    response = client.get("/api/v1/styles")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "name" in data[0]


def test_get_style(client):
    """Get style by name returns full template."""
    # First get list to find a valid name
    styles = client.get("/api/v1/styles").json()
    name = styles[0]["name"]
    response = client.get(f"/api/v1/styles/{name}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == name
    assert "guidelines" in data


def test_get_style_not_found(client):
    """Get nonexistent style returns 404."""
    response = client.get("/api/v1/styles/nonexistent-style-xyz")
    assert response.status_code == 404
```

**Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/test_api.py -k "style" -v
```

**Step 3: Implement routes**

Create `src/dich_truyen/api/routes/styles.py`:

```python
"""Style API routes — CRUD for translation styles."""

from typing import Any

from fastapi import APIRouter, HTTPException

from dich_truyen.services.style_service import StyleService

router = APIRouter(prefix="/api/v1/styles", tags=["styles"])

_style_service: StyleService | None = None


def set_style_service(service: StyleService) -> None:
    """Set the style service instance."""
    global _style_service
    _style_service = service


def _get_service() -> StyleService:
    if _style_service is None:
        return StyleService()
    return _style_service


@router.get("")
async def list_styles() -> list[dict[str, Any]]:
    """List all available style templates."""
    return _get_service().list_styles()


@router.get("/{name}")
async def get_style(name: str) -> dict[str, Any]:
    """Get a style template by name."""
    try:
        return _get_service().get_style(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

**Step 4: Wire up in server.py**

```diff
-from dich_truyen.api.routes import books, glossary, pipeline, settings
+from dich_truyen.api.routes import books, glossary, pipeline, settings, styles
+from dich_truyen.services.style_service import StyleService
```

In `create_app()`:

```diff
+    # Style routes
+    style_service = StyleService()
+    styles.set_style_service(style_service)
+    app.include_router(styles.router)
```

**Step 5: Run tests — verify they pass**

```bash
uv run pytest tests/test_api.py -k "style" -v
```

**Step 6: Run full test suite**

```bash
uv run pytest tests/ -v 2>&1 | Select-Object -Last 5
```

**Step 7: Commit**

```bash
git add src/dich_truyen/api/routes/styles.py src/dich_truyen/api/server.py tests/test_api.py
git commit -m "feat(api): add styles API endpoints"
```

---

## Task 2: Style Manager Frontend Page

**Files:**
- Create: `web/src/app/styles/page.tsx`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/lib/types.ts`

**Step 1: Add TypeScript types**

Add to `web/src/lib/types.ts`:

```typescript
/** Style template summary. */
export interface StyleSummary {
  name: string;
  description: string;
  tone: string;
  is_builtin: boolean;
}

/** Full style template. */
export interface StyleDetail {
  name: string;
  description: string;
  guidelines: string[];
  vocabulary: Record<string, string>;
  tone: string;
  examples: { chinese: string; vietnamese: string }[];
}
```

**Step 2: Add API functions**

Add to `web/src/lib/api.ts`:

```typescript
// --- Styles API ---

export async function getStyles(): Promise<StyleSummary[]> {
  return fetchJson<StyleSummary[]>(`${API_BASE}/styles`);
}

export async function getStyle(name: string): Promise<StyleDetail> {
  return fetchJson<StyleDetail>(`${API_BASE}/styles/${name}`);
}
```

**Step 3: Create Style Manager page**

Create `web/src/app/styles/page.tsx` — a card-based page showing:
- Grid of style cards with name, description, tone badge (`is_builtin` indicated)
- Click card → detail panel slides in from right (or modal) showing:
  - Guidelines list
  - Vocabulary table (Chinese → Vietnamese)
  - Tone indicator
  - Translation examples
- Search/filter bar at top

Key design patterns:
- Cards use `bg-[var(--bg-surface)]` with `border border-[var(--border-default)]`
- Built-in badge: `bg-[var(--color-primary-subtle)] text-[var(--color-primary)]`
- Tone badges with category colors (same as glossary categories)
- Slide-in detail panel with `transition: transform 300ms ease-out`
- `cursor-pointer` on all card elements

**Step 4: Verify build**

```bash
cd web && npx next build
```

**Step 5: Commit**

```bash
git add web/src/app/styles/ web/src/lib/api.ts web/src/lib/types.ts
git commit -m "feat(web): add Style Manager page"
```

---

## Task 3: Export API Routes

**Files:**
- Create: `src/dich_truyen/api/routes/export.py`
- Modify: `src/dich_truyen/api/server.py`
- Modify: `tests/test_api.py`

**Step 1: Write tests**

Add to `tests/test_api.py`:

```python
def test_get_export_status(client, sample_book):
    """Get export status for a book."""
    response = client.get(f"/api/v1/books/{sample_book}/export")
    assert response.status_code == 200
    data = response.json()
    assert "formats" in data


def test_get_supported_formats(client):
    """Get supported export formats."""
    response = client.get("/api/v1/export/formats")
    assert response.status_code == 200
    data = response.json()
    assert "epub" in data
```

**Step 2: Implement routes**

Create `src/dich_truyen/api/routes/export.py`:

```python
"""Export API routes — book export and download."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from dich_truyen.services.export_service import ExportService

router = APIRouter(prefix="/api/v1", tags=["export"])

_export_service: ExportService | None = None


def set_export_service(service: ExportService) -> None:
    """Set the export service instance."""
    global _export_service
    _export_service = service


def _get_service() -> ExportService:
    if _export_service is None:
        raise RuntimeError("ExportService not initialized")
    return _export_service


@router.get("/export/formats")
async def get_supported_formats() -> list[str]:
    """Get list of supported export formats."""
    return _get_service().get_supported_formats()


@router.get("/books/{book_id}/export")
async def get_export_status(book_id: str) -> dict[str, Any]:
    """Get export status for a book."""
    try:
        return _get_service().get_export_status(book_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/books/{book_id}/export")
async def start_export(book_id: str, format: str = "epub") -> dict[str, Any]:
    """Start export for a book."""
    try:
        return await _get_service().export(book_id, format)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/books/{book_id}/export/download/{filename}")
async def download_export(book_id: str, filename: str) -> FileResponse:
    """Download exported ebook file."""
    service = _get_service()
    try:
        status = service.get_export_status(book_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Find matching file
    for fmt, path in status["formats"].items():
        if Path(path).name == filename:
            return FileResponse(path, filename=filename)

    raise HTTPException(status_code=404, detail="File not found")
```

**Step 3: Wire up in server.py**

```diff
-from dich_truyen.api.routes import books, glossary, pipeline, settings, styles
+from dich_truyen.api.routes import books, export, glossary, pipeline, settings, styles
+from dich_truyen.services.export_service import ExportService
```

In `create_app()`:

```diff
+    # Export routes
+    export_service = ExportService(books_dir or Path("books"))
+    export.set_export_service(export_service)
+    app.include_router(export.router)
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_api.py -k "export" -v
```

**Step 5: Commit**

```bash
git add src/dich_truyen/api/routes/export.py src/dich_truyen/api/server.py tests/test_api.py
git commit -m "feat(api): add export API endpoints"
```

---

## Task 4: Export Controls on Book Detail

**Files:**
- Modify: `web/src/app/books/[id]/page.tsx`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/lib/types.ts`

**Step 1: Add types and API**

Add to `types.ts`:

```typescript
/** Export status for a book. */
export interface ExportStatus {
  formats: Record<string, string>;
}
```

Add to `api.ts`:

```typescript
// --- Export API ---

export async function getExportStatus(bookId: string): Promise<ExportStatus> {
  return fetchJson<ExportStatus>(`${API_BASE}/books/${bookId}/export`);
}

export async function startExport(
  bookId: string,
  format: string
): Promise<{ success: boolean; output_path?: string; error_message?: string }> {
  const res = await fetch(`${API_BASE}/books/${bookId}/export?format=${format}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function getExportDownloadUrl(bookId: string, filename: string): string {
  return `${API_BASE}/books/${bookId}/export/download/${filename}`;
}
```

**Step 2: Add export panel to Book Detail page**

Below the stats cards, add an **Export** section:
- Format selector (dropdown: epub, azw3, mobi, pdf)
- "Export" button that calls `startExport()`
- Existing files listed with download links
- Loading spinner during export
- Success/error toast feedback

Design:
- Use `<Section>` card component (like settings page)
- Format badges: `bg-[var(--bg-elevated)]` rounded pills
- Download links with `Download` icon from Lucide
- Progress: `Loader2` spinner with `animate-spin`

**Step 3: Verify build**

```bash
cd web && npx next build
```

**Step 4: Commit**

```bash
git add web/src/app/books/[id]/page.tsx web/src/lib/api.ts web/src/lib/types.ts
git commit -m "feat(web): add export controls to Book Detail page"
```

---

## Task 5: CSS Animations & Transitions

**Files:**
- Modify: `web/src/app/globals.css`

**Step 1: Add animation system**

Add to `globals.css`:

```css
/* ─── Animations ──────────────────────────────────────────── */

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeOut {
  from { opacity: 1; }
  to { opacity: 0; }
}

@keyframes slideInRight {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

@keyframes slideInUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.animate-fade-in {
  animation: fadeIn 200ms ease-out both;
}

.animate-slide-in-right {
  animation: slideInRight 300ms ease-out both;
}

.animate-slide-in-up {
  animation: slideInUp 250ms ease-out both;
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

/* Staggered children: apply to parent */
.stagger-children > * {
  animation: fadeIn 200ms ease-out both;
}
.stagger-children > *:nth-child(1) { animation-delay: 0ms; }
.stagger-children > *:nth-child(2) { animation-delay: 50ms; }
.stagger-children > *:nth-child(3) { animation-delay: 100ms; }
.stagger-children > *:nth-child(4) { animation-delay: 150ms; }
.stagger-children > *:nth-child(5) { animation-delay: 200ms; }
.stagger-children > *:nth-child(6) { animation-delay: 250ms; }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Step 2: Update existing skeleton class**

Ensure the `.skeleton` class uses the new `animate-pulse`:

```css
.skeleton {
  background: var(--bg-elevated);
  border-radius: 8px;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
```

**Step 3: Apply animations to pages**

Add `animate-fade-in` to main content containers, `stagger-children` to card grids (Library, Dashboard stats), `animate-slide-in-up` to modals/toasts.

**Step 4: Verify build**

```bash
cd web && npx next build
```

**Step 5: Commit**

```bash
git add web/src/app/globals.css
git commit -m "feat(web): add CSS animation system with reduced motion support"
```

---

## Task 6: Error Handling & Loading States

**Files:**
- Create: `web/src/components/ui/ErrorBoundary.tsx`
- Create: `web/src/components/ui/EmptyState.tsx`
- Modify: `web/src/app/layout.tsx`
- Modify: multiple page files (apply error/loading patterns)

**Step 1: Create ErrorBoundary component**

```tsx
"use client";

import { Component, ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

interface Props { children: ReactNode; fallback?: ReactNode; }
interface State { hasError: boolean; error: Error | null; }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="flex flex-col items-center justify-center p-12 text-center">
          <AlertTriangle size={48} className="text-[var(--color-warning)] mb-4" />
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
            Something went wrong
          </h2>
          <p className="text-[var(--text-secondary)] text-sm mb-4 max-w-md">
            {this.state.error?.message || "An unexpected error occurred"}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg
              bg-[var(--color-primary)] text-white text-sm cursor-pointer
              hover:bg-[var(--color-primary-hover)] transition-colors"
          >
            <RotateCcw size={14} /> Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

**Step 2: Create EmptyState component**

```tsx
import { type LucideIcon } from "lucide-react";

export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: { label: string; href: string };
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center animate-fade-in">
      <div className="p-4 rounded-2xl bg-[var(--bg-elevated)] mb-4">
        <Icon size={32} className="text-[var(--text-muted)]" />
      </div>
      <h3 className="text-lg font-medium text-[var(--text-primary)] mb-1">{title}</h3>
      <p className="text-[var(--text-secondary)] text-sm max-w-sm">{description}</p>
      {action && (
        <a href={action.href}
           className="mt-4 px-4 py-2 rounded-lg bg-[var(--color-primary)]
             text-white text-sm cursor-pointer hover:bg-[var(--color-primary-hover)]
             transition-colors">
          {action.label}
        </a>
      )}
    </div>
  );
}
```

**Step 3: Wrap layout with ErrorBoundary**

In `layout.tsx`, wrap `{children}` with `<ErrorBoundary>`.

**Step 4: Add EmptyState to pages**

- **Library**: "No books yet" with link to /new when `books.length === 0`
- **Book Detail chapters**: "No chapters found" when `chapters.length === 0`
- **Glossary**: "No glossary entries" with button to add first entry
- **Pipeline**: "No pipeline jobs" with link to /new

**Step 5: Verify build**

```bash
cd web && npx next build
```

**Step 6: Commit**

```bash
git add web/src/components/ui/ web/src/app/
git commit -m "feat(web): add ErrorBoundary, EmptyState, and loading improvements"
```

---

## Task 7: Translation Pipeline Resume (from TODO)

> [!IMPORTANT]
> User requirement: "Translation pipeline: continue pending translations (the same as CLI pipeline)"

**Files:**
- Modify: `web/src/app/books/[id]/page.tsx`
- The pipeline resume API already exists at `POST /api/v1/pipeline/start` with `book_dir` and `translate_only` options.

**Step 1: Add "Resume Translation" button to Book Detail**

When a book has chapters with `status === "crawled"` (crawled but not translated), show a prominent "Resume Translation" button in the action bar alongside "Continue Reading" and "Edit Glossary". Clicking it calls `startPipeline({ book_dir: book.id, translate_only: true })` and navigates to the pipeline monitor.

**Step 2: Verify in browser**

Start the app and verify the button appears for books with crawled-only chapters.

**Step 3: Commit**

```bash
git add web/src/app/books/[id]/page.tsx
git commit -m "feat(web): add Resume Translation button to Book Detail"
```

---

## Task 8: Light/Dark Theme Toggle (from TODO)

**Files:**
- Modify: `web/src/app/globals.css` (add light theme tokens)
- Create: `web/src/components/ui/ThemeToggle.tsx`
- Modify: `web/src/app/layout.tsx` (add theme provider)

**Step 1: Add light mode CSS variables**

Currently all CSS tokens are dark-mode values. Add a data attribute toggle:

```css
:root[data-theme="light"] {
  --bg-primary: #FAFAFA;
  --bg-surface: #FFFFFF;
  --bg-elevated: #F5F5F5;
  --text-primary: #0F172A;
  --text-secondary: #475569;
  --text-muted: #94A3B8;
  --text-tertiary: #64748B;
  --border-default: #E2E8F0;
  /* ... all tokens with light values */
}
```

**Step 2: Create ThemeToggle component**

A button that toggles `data-theme` on `<html>` and persists to localStorage:

```tsx
"use client";
import { useState, useEffect } from "react";
import { Sun, Moon } from "lucide-react";

export default function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const saved = localStorage.getItem("dich-truyen-theme") as "dark" | "light" | null;
    if (saved) {
      setTheme(saved);
      document.documentElement.setAttribute("data-theme", saved);
    }
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("dich-truyen-theme", next);
  };

  return (
    <button onClick={toggle} className="p-2 rounded-lg cursor-pointer ..." title="Toggle theme">
      {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}
```

**Step 3: Add to sidebar**

Place `<ThemeToggle />` at the bottom of the sidebar in `layout.tsx`.

**Step 4: Verify both themes**

Start the app, toggle theme, verify:
- All text contrast meets 4.5:1 minimum
- Borders visible in both modes
- Cards/surfaces distinguishable from background
- No invisible elements

**Step 5: Commit**

```bash
git add web/src/app/globals.css web/src/components/ui/ThemeToggle.tsx web/src/app/layout.tsx
git commit -m "feat(web): add light/dark theme toggle"
```

---

## Verification Plan

### Automated Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run Phase 4 specific tests
uv run pytest tests/test_api.py -k "style or export" -v
uv run pytest tests/test_services.py -v

# Lint and format
uv run ruff check .
uv run ruff format --check .

# Frontend build
cd web && npx next build
```

### Browser Verification

Start the app and manually verify:

```bash
uv run dich-truyen ui
```

1. **Style Manager** (`/styles`): style cards load, click shows detail, built-in badge
2. **Export controls** (`/books/{id}`): format picker, export button, download link
3. **Animations**: fade-in on page load, stagger on card grids, skeleton loading
4. **Error handling**: ErrorBoundary on API failure, EmptyState on empty lists
5. **Resume Translation**: button appears for books with crawled chapters
6. **Theme toggle**: dark ↔ light, persists on reload, all tokens update
7. **CLI unchanged**: `uv run dich-truyen pipeline --help` still works
