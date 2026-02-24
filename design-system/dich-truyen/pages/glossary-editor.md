# Glossary Editor Page Design Override

> **Inherits from:** [MASTER.md](../MASTER.md) — Only deviations listed here.

## Layout

Full-width inside content area. Header with back link + title + term count. Toolbar row. Scrollable table. Inline edit form.

## Page Header

```
← Back to Book Detail                    42 terms
Glossary — 仙逆 (Tiên Nghịch)
```

- Back link: `ChevronLeft` (16px) + book title, `text-[var(--text-secondary)] hover:text-[var(--text-primary)]`
- Page title: `text-xl font-semibold text-[var(--text-primary)] font-[var(--font-fira-code)]`
- Term count: `text-[var(--text-muted)] text-sm font-[var(--font-fira-code)]`

## Toolbar

```
🔍 [Search terms...         ]  ▾ [All Categories]    [Import CSV] [Export CSV] [+ Add Term]
```

`flex items-center gap-3 mb-4 flex-wrap`

| Element | Spec |
|---------|------|
| **Search** | `bg-[var(--bg-primary)] border border-[var(--border-default)] rounded-lg pl-10 pr-4 py-2.5 text-sm flex-1 min-w-[200px]`. `Search` icon (16px) positioned `absolute left-3 text-[var(--text-muted)]`. |
| **Category filter** | `<select>` styled: `bg-[var(--bg-primary)] border border-[var(--border-default)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)]` + `ChevronDown` indicator. |
| **Import CSV** | Ghost button: `border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] rounded-lg px-3 py-2 text-sm`. Icon: `Upload` (16px). |
| **Export CSV** | Same ghost style. Icon: `Download` (16px). |
| **Add Term** | `bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg px-4 py-2 text-sm font-medium`. Icon: `Plus` (16px). |

## Table

Wrapped in `overflow-x-auto` for responsive mobile support.

| Part | Spec |
|------|------|
| **Container** | `bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl overflow-hidden` |
| **Header row** | `bg-[var(--bg-elevated)] px-4 py-3`. Text: `text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)]` |
| **Body row** | `px-4 py-3 border-b border-[var(--border-default)] hover:bg-[var(--bg-elevated)]/30 transition-colors duration-150` |
| **Chinese text** | `text-[var(--text-primary)] text-sm font-medium` — Noto Serif for CJK characters |
| **Vietnamese text** | `text-[var(--text-primary)] text-sm` |
| **Empty state** | Centered in table body: `text-[var(--text-muted)] text-sm py-12`. Icon: `BookOpen` (40px) above text. |

**Column widths:** Chinese 25%, Vietnamese 30%, Category 15%, Notes 20%, Actions 10%

## Category Badges

| Category | Background | Text |
|----------|-----------|------|
| `character` | `bg-teal-500/15` | `text-teal-400` |
| `realm` | `bg-purple-500/15` | `text-purple-400` |
| `technique` | `bg-blue-500/15` | `text-blue-400` |
| `location` | `bg-amber-500/15` | `text-amber-400` |
| `item` | `bg-emerald-500/15` | `text-emerald-400` |
| `organization` | `bg-rose-500/15` | `text-rose-400` |
| `general` | `bg-gray-500/15` | `text-gray-400` |

Style: `px-2 py-0.5 rounded-md text-xs font-medium inline-flex items-center`

## Action Buttons (per row)

| Button | Spec |
|--------|------|
| **Edit** | `p-1.5 rounded-md text-[var(--text-muted)] hover:text-[var(--color-primary)] hover:bg-[var(--bg-elevated)] transition-colors duration-150 cursor-pointer`. Icon: `Pencil` (14px). |
| **Delete** | Same base. `hover:text-[var(--color-error)] hover:bg-[var(--color-error)]/10`. Icon: `Trash2` (14px). |

## Inline Edit Mode

When editing a row, the row transforms into input fields:

```
Row background: bg-[var(--color-primary)]/5 border-l-2 border-l-[var(--color-primary)]
Inputs: same as Settings page inputs but compact (py-1.5 text-sm)
Actions: [Cancel] (ghost) [Save] (primary, small)
```

- Cancel: `text-[var(--text-muted)] hover:text-[var(--text-primary)] text-sm cursor-pointer`
- Save: `bg-[var(--color-primary)] text-white rounded px-3 py-1 text-sm cursor-pointer`
- New row (Add): appears at top of table in edit mode, auto-focus on Chinese input

## Delete Confirmation

Inline, NOT modal. Row changes to:

```
bg-[var(--color-error)]/5 border-l-2 border-l-[var(--color-error)]
```

Text: `"Delete 王林 → Vương Lâm?"` + `[Cancel] [Delete]`

Delete button: `bg-[var(--color-error)] text-white rounded px-3 py-1 text-sm`

## Import CSV Dialog

Simple file upload area:
```
bg-[var(--bg-surface)] border-2 border-dashed border-[var(--border-default)]
rounded-xl p-8 text-center
```

- Icon: `Upload` (32px) `text-[var(--text-muted)]`
- Text: "Drop CSV file here or click to browse"
- On import: show count of imported terms in success toast

## Skeleton Loading

```
Toolbar skeleton: search + 3 buttons (rounded rectangles)
Table skeleton: 8 rows of alternating-width skeleton bars in 4 columns
```

## Accessibility

- Table: `<table>` with `<thead>`, `<tbody>` semantic markup
- Sort columns: `aria-sort="ascending"` / `aria-sort="descending"` (if adding sort later)
- Inline edit: manage focus — auto-focus first input when entering edit mode
- Delete confirmation: `role="alert"` on the confirmation row
- Search: `aria-label="Search glossary terms"`
- Category filter: `<label>` associated with `<select>`
- Keyboard: `Escape` to cancel edit, `Enter` to save edit
