# Full Style Manager — Design Document

> **Date:** 2026-03-01
> **Approach:** Enhanced Slide-in Panel (Approach 1)
> **Scope:** Full CRUD + LLM generation + shadow/customize built-ins + YAML import/export

## Background

The Web UI Style Manager currently only supports **viewing** styles (card grid + read-only slide-in detail panel). The backend `StyleService` exposes only `list_styles()` and `get_style()` via `GET /api/v1/styles` and `GET /api/v1/styles/{name}`.

This design adds full management capabilities while preserving the existing UI pattern.

### Existing Infrastructure

- **`StyleTemplate`** — Pydantic model with `to_yaml()`/`from_yaml()` serialization
- **`StyleManager`** — Core manager with `load()`, `list_available()`, `get_built_in_names()`, internal `_cache`
- **`generate_style_from_description()`** — LLM-powered style generation (exists but unexposed via API)
- **Priority loading** — Custom `styles/` dir checked first, then built-in fallback (shadow/override mechanism)
- **4 built-in styles** — `tien_hiep`, `kiem_hiep`, `huyen_huyen`, `do_thi`
- **2 custom styles** — YAML files in `styles/` directory

---

## 1. Architecture & API

### New API Endpoints

| Method | Endpoint | Purpose | Notes |
|--------|----------|---------|-------|
| `POST` | `/api/v1/styles` | Create new custom style | Accepts `StyleTemplate` JSON body |
| `PUT` | `/api/v1/styles/{name}` | Update existing custom style | Rejects if built-in |
| `DELETE` | `/api/v1/styles/{name}` | Delete a custom style | Rejects if built-in |
| `POST` | `/api/v1/styles/{name}/duplicate` | Clone a style | Creates shadow or new copy |
| `POST` | `/api/v1/styles/generate` | LLM-generate from description | Returns `StyleTemplate` (not saved) |
| `POST` | `/api/v1/styles/import` | Import YAML as new style | Validates and saves |
| `GET` | `/api/v1/styles/{name}/export` | Export as YAML download | `Content-Disposition` header |

### Service Layer — `StyleService` New Methods

- `create_style(data: dict) → dict` — Validate, save YAML to `styles/` dir, return style dict
- `update_style(name: str, data: dict) → dict` — Validate, overwrite YAML, invalidate cache
- `delete_style(name: str) → None` — Remove YAML file, invalidate cache
- `duplicate_style(name: str, new_name: str | None) → dict` — Load source, save as new file
- `generate_style(description: str) → dict` — Call `generate_style_from_description()`
- `import_style(yaml_content: str) → dict` — Parse YAML, validate, save
- `export_style(name: str) → str` — Return raw YAML content

### Core Layer — `StyleManager` New Methods

- `save(template: StyleTemplate) → None` — Save to custom `styles/` dir as YAML
- `delete(name: str) → None` — Remove YAML file from `styles/` dir
- `invalidate_cache(name: str) → None` — Remove entry from `_cache`

### Overwrite Logic

| Operation | Rule |
|-----------|------|
| Create new | Reject if `name` exists (built-in or custom) — **409 Conflict** |
| Edit custom | `PUT` replaces YAML, invalidates cache. Rejects built-in — **403 Forbidden** |
| Shadow built-in | "Customize" copies built-in data into `styles/{same_name}.yaml` |
| Delete shadow | Removes YAML, built-in reappears automatically |
| Import | Same rules as Create (reject on name collision) |

### Frontend API Functions — `web/src/lib/api.ts`

- `createStyle(data)`, `updateStyle(name, data)`, `deleteStyle(name)`
- `duplicateStyle(name)`, `generateStyle(description)`
- `importStyle(yamlContent)`, `exportStyle(name)`

---

## 2. Panel UI States & UX Flow

### Two Distinct Entry Points (Top of Page)

| Button | Label | Action |
|--------|-------|--------|
| ➕ | **"New Style"** | Opens panel in CREATE mode (empty form) |
| 📥 | **"Import YAML"** | File picker → validates → opens panel in CREATE mode pre-filled |

Built-in style cards get a dedicated action:

| Button | Location | Label | Action |
|--------|----------|-------|--------|
| 🔧 | On each **built-in** card | **"Customize"** | Opens panel in SHADOW-EDIT mode pre-filled with built-in data |

### Four Panel Modes

| Mode | Triggered By | Name Field | Header Actions |
|------|-------------|------------|----------------|
| **VIEW** | Click any card | Read-only | Varies by type (see below) |
| **CREATE** | "New Style" / Import | Editable (validated) | `[Save]` `[Cancel]` |
| **SHADOW-EDIT** | "Customize" on built-in | Locked (same name) | `[Save Customization]` `[Cancel]` |
| **EDIT** | "Edit" on custom/shadow | Locked | `[Save]` `[Cancel]` |

### VIEW Mode Header Actions (by Style Type)

| Style Type | Actions |
|-----------|---------|
| Built-in (no shadow) | `[Customize]` `[Export YAML]` |
| Custom (new) | `[Edit]` `[Delete]` `[Export YAML]` |
| Shadow (custom overriding built-in) | `[Edit]` `[Reset to Default]` `[Export YAML]` |

### SHADOW-EDIT Banner

Panel header shows: *"✏️ Customizing built-in style — your changes will override the default"*

### Card Badge System

| Type | Badge | Color |
|------|-------|-------|
| Built-in (no shadow) | `built-in` | Primary blue |
| Custom (new) | `custom` | Green |
| Shadow (overriding built-in) | `customized` | Orange/warning |

### Delete / Reset Flows

- **Delete custom:** Confirmation dialog → *"Delete 'my_style'? This cannot be undone."*
- **Reset shadow:** Confirmation dialog → *"Reset 'tien_hiep' to default? Your customizations will be removed."* → Deletes YAML, built-in reappears

---

## 3. LLM Generation & Import/Export

### LLM Generation Flow

Entry point: **"✨ Generate with AI"** button inside CREATE mode panel.

```
"New Style" → Panel opens (empty form)
  → "✨ Generate with AI" → expands inline section
  → [Description textarea (Vietnamese)] + [Generate] button
  → User types description → clicks [Generate]
  → Button: spinner + disabled (prevent double-click)
  → API: POST /api/v1/styles/generate {description: "..."}
  → Success: form fields auto-fill with LLM result
  → User reviews/tweaks → [Save] to persist
```

**Key decisions:**
- Generation **does NOT auto-save** — only fills the form for review
- The `name` from LLM fills the name input but remains editable
- On failure: inline error *"Generation failed. Try again or fill manually."*
- No streaming — show spinner for ~3-5 second wait

### YAML Export

Entry point: `[Export YAML]` in VIEW mode panel header.

- `GET /api/v1/styles/{name}/export` → browser downloads `{name}.yaml`
- Works for all style types (built-in, custom, shadow)
- No modal needed

### YAML Import

Entry point: `[📥 Import YAML]` button at top of styles page.

```
[Import YAML] → file picker (.yaml, .yml)
  → Frontend reads file as text
  → API: POST /api/v1/styles/import {yaml_content: "..."}
  → Validates: YAML syntax, StyleTemplate schema, name uniqueness
  → Success: panel opens in CREATE mode pre-filled (user reviews before save)
  → Name collision: error with guidance
  → Invalid YAML/schema: error listing issues
```

Import opens panel in **CREATE mode pre-filled** (not auto-saved) so user can review/adjust.

---

## 4. Error Handling & Validation

### Frontend Validation (on blur)

| Field | Rules | Error Message |
|-------|-------|--------------|
| `name` | Required, snake_case (`/^[a-z][a-z0-9_]*$/`), 3-50 chars, unique | "Name must be lowercase with underscores" / "Style 'x' already exists" |
| `description` | Required, 5-200 chars | "Description is required" |
| `guidelines` | ≥1 entry, each non-empty | "Add at least one guideline" |
| `vocabulary` | Optional; if present, both key & value non-empty | "Both Chinese and Vietnamese required" |
| `tone` | Required, dropdown: `formal`, `casual`, `archaic`, `poetic`, `literary` | (can't be invalid) |
| `examples` | Optional; if present, both `chinese` & `vietnamese` non-empty | "Both fields required" |

### Backend Validation

Same checks plus:
- **Name collision:** 409 Conflict
- **Built-in protection:** 403 Forbidden
- **YAML parsing:** 422 Unprocessable Entity

### HTTP Error Codes

| Scenario | Code | Frontend Behavior |
|----------|------|-------------------|
| Style not found | 404 | Toast: "Style not found" |
| Name collision on create | 409 | Inline error on name field |
| Edit/delete built-in | 403 | Toast: "Built-in styles cannot be modified" |
| Invalid YAML import | 422 | Error detail in import dialog |
| LLM generation failed | 500 | Inline error in form |
| Successful save/delete | 200 | Toast + refresh card grid |

### Unsaved Changes Guard

In CREATE, EDIT, or SHADOW-EDIT mode:
- Clicking backdrop or `X` with dirty form → *"Discard unsaved changes?"* dialog
- Track dirty state by comparing current form values to initial values

### Cache Invalidation

After any write operation:
1. **Backend:** `StyleManager._cache` evicts the affected entry
2. **Frontend:** re-fetches style list to refresh card grid
