# Settings Page Design Override

> **Inherits from:** [MASTER.md](../MASTER.md) — Only deviations listed here.

## Layout

Single-column form layout. Max width `max-w-3xl` centered. Vertical stack of collapsible section cards.

## Section Cards

Each config group is a `<section>` with card styling:
```
bg-[var(--bg-surface)]
border border-[var(--border-default)]
rounded-xl p-6
```

**Section Header:**
- Icon (Lucide, 18px) + Title in `text-lg font-semibold text-[var(--text-primary)]`
- Collapsible: `ChevronDown`/`ChevronUp` toggle (optional, default expanded)
- Grid layout inside: `grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4`

## Form Inputs

| Element | Spec |
|---------|------|
| **Text input** | `bg-[var(--bg-primary)] border border-[var(--border-default)] rounded-lg px-4 py-2.5 text-sm text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150` |
| **Label** | `text-[var(--text-secondary)] text-sm font-medium mb-1.5 block` |
| **Description** | `text-[var(--text-muted)] text-xs mt-1` (below input, for help text) |
| **Password** | Same as text + `Eye`/`EyeOff` toggle button inside, `font-[var(--font-fira-code)]` |
| **Number** | Same as text + `type="number"` with `font-[var(--font-fira-code)]` |
| **Toggle/Checkbox** | `w-9 h-5 rounded-full` track. On: `bg-[var(--color-primary)]`. Off: `bg-[var(--bg-elevated)]`. Thumb: `w-4 h-4 bg-white rounded-full` with `transition-transform duration-150`. |

> **Rule:** Every input MUST have a visible `<label>`. No placeholder-only inputs.

## Buttons

| Button | Spec |
|--------|------|
| **Save** | `bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg px-6 py-2.5 font-medium text-sm transition-colors duration-150 cursor-pointer`. Icon: `Save` (16px). Loading state: replace icon with `Loader2 animate-spin`. |
| **Reset** | `bg-transparent border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] hover:text-[var(--text-primary)] rounded-lg px-4 py-2.5 text-sm transition-colors duration-150 cursor-pointer`. Icon: `RotateCcw` (16px). |
| **Test Connection** | `bg-[var(--color-primary)]/10 text-[var(--color-primary)] hover:bg-[var(--color-primary)]/20 border border-[var(--color-primary)]/30 rounded-lg px-4 py-2 text-sm font-medium transition-colors duration-150 cursor-pointer`. Icon: `Zap` (16px). |

## Feedback

| State | Spec |
|-------|------|
| **Success toast** | Fixed bottom-right. `bg-[var(--color-success)]/15 border border-[var(--color-success)]/30 text-[var(--color-success)] rounded-lg px-4 py-3 text-sm`. Icon: `CheckCircle2`. Auto-dismiss 3s. `animate-slide-in-right`. |
| **Error toast** | Same position. `bg-[var(--color-error)]/15 border border-[var(--color-error)]/30 text-[var(--color-error)]`. Icon: `AlertCircle`. Auto-dismiss 5s. |
| **Test success** | Inline after button: `text-[var(--color-success)] text-sm` with `CheckCircle2` icon. |
| **Test failure** | Inline: `text-[var(--color-error)] text-sm` with `AlertCircle` icon + error message. |
| **Unsaved changes** | Sticky bottom bar: `bg-[var(--bg-surface)] border-t border-[var(--border-default)] p-4` with Save/Discard buttons. Only appears when form is dirty. |

## Sections

| Section | Icon | Fields |
|---------|------|--------|
| **API Configuration** | `Key` | api_key (password), base_url, model, max_tokens, temperature + Test Connection |
| **Crawler** | `Globe` | delay_ms, max_retries, timeout_seconds |
| **Translation** | `Languages` | chunk_size, chunk_overlap, enable_polish_pass (toggle), progressive_glossary (toggle), polish_temperature |
| **Pipeline** | `Workflow` | translator_workers, queue_size, crawl_delay_ms |
| **Export** | `FileOutput` | parallel_workers, volume_size, fast_mode (toggle) |

## Skeleton Loading

```
3 section cards, each with:
- skeleton h-6 w-48 (title)
- grid of skeleton h-10 (2 columns, 3 rows)
```

## Accessibility

- All inputs: visible `<label>` with `htmlFor`
- Toggle switches: `role="switch"` with `aria-checked`
- Focus: `ring-2 ring-[var(--color-primary)]/50` on all inputs
- Keyboard: `Tab` through inputs, `Enter` to save
- Toast: `role="alert"` with `aria-live="assertive"`
