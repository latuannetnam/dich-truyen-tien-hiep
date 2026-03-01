---
description: Translation style templates, YAML schema, priority loading, CRUD API, and how to create new styles
---

# Translation Styles

## Key Files

| File | Purpose |
|------|---------|
| `translator/style.py` | `StyleTemplate`, `StyleManager`, `generate_style_from_description()` |
| `services/style_service.py` | Service wrapper for API routes (dict-based API) |
| `api/routes/styles.py` | REST endpoints for style CRUD |
| `styles/` | Custom user styles directory |
| `web/src/app/styles/page.tsx` | Style Manager UI page |
| `web/src/components/styles/StyleEditorForm.tsx` | Create/edit form component |

## Priority Loading

1. **Custom styles** in `styles/` directory — checked **first**
2. **Built-in styles** — fallback if custom not found

Custom files with the same name as a built-in create a **shadow** (override).

## Style Types

| Type | Condition | Badge |
|------|-----------|-------|
| `builtin` | Name in `BUILT_IN_STYLES`, no custom file | Blue |
| `custom` | Only exists in `styles/` dir | Green |
| `shadow` | Built-in name AND custom file exists | Orange |

## Built-in Styles

`tien_hiep`, `kiem_hiep`, `huyen_huyen`, `do_thi` — defined in `BUILT_IN_STYLES` dict.

## StyleManager Methods

| Method | Purpose |
|--------|---------|
| `list_available()` | All style names (built-in + custom) |
| `load(name)` | Load by name (custom first, then built-in) |
| `save(template)` | Save to `styles/` dir, overwrites existing |
| `delete(name)` | Delete custom file, rejects built-in |
| `invalidate_cache(name)` | Remove from `_cache` |
| `is_builtin(name)` | Check if name in `BUILT_IN_STYLES` |
| `is_shadow(name)` | Check if built-in AND custom file exists |

## StyleService Methods

| Method | Purpose |
|--------|---------|
| `list_styles()` | All styles with metadata (`style_type`, `is_builtin`) |
| `get_style(name)` | Full template as dict |
| `create_style(data)` | Validate + save new style (rejects name collision) |
| `update_style(name, data)` | Update custom/shadow (rejects pure built-in) |
| `delete_style(name)` | Delete custom file |
| `duplicate_style(name, new_name)` | Clone style (shadow if no new_name) |
| `generate_style(description)` | LLM generation (async, not saved) |
| `import_style(yaml_content)` | **Validate-only** — parses YAML, returns dict, does NOT save |
| `export_style(name)` | Returns raw YAML string |
| `get_style_type(name)` | Returns `builtin`, `custom`, or `shadow` |

> **Note:** `import_style` validates and returns parsed data without saving. The frontend then opens CREATE mode for user review, and the normal `create_style` flow persists.

## Style YAML Schema

```yaml
name: tien_hiep            # snake_case, 3-50 chars
description: "Tiên hiệp"  # 5-200 chars
guidelines:
  - "Guideline 1"          # At least 1 required
vocabulary:
  我: ta                   # Optional key-value map
tone: archaic              # formal | casual | archaic | poetic | literary
examples:                  # Optional
  - chinese: "你是谁？"
    vietnamese: "Ngươi là ai?"
```

## CLI Usage

```bash
uv run dich-truyen style list
uv run dich-truyen style generate my_style_name
uv run dich-truyen pipeline "https://..." --style tien_hiep
```
