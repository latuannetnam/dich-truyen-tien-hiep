# Reader Page Design Override

> **Inherits from:** [MASTER.md](../MASTER.md) — Only deviations listed here.
> **Enhances:** Existing `ReaderView.tsx` from Phase 1.

## New Features (Phase 3)

1. **Paragraph-aligned side-by-side** — paragraphs rendered in shared grid rows
2. **Synced scrolling** — both panes scroll together proportionally
3. **Chapter dropdown** — jump to any translated chapter from toolbar
4. **Reading progress** — persist last-read chapter per book

## Enhanced Toolbar

```
← Book Title    ▾ [Chapter 47 ▾]    Chapter 47/320    [A-] [A+] [⫼]
```

| Element | Spec |
|---------|------|
| **Chapter dropdown** | `<select>` styled: `bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-3 py-1.5 text-sm text-[var(--text-primary)] font-[var(--font-fira-code)]`. Shows chapter index + truncated title. `ChevronDown` indicator. `cursor-pointer`. |
| **Current position** | `text-[var(--text-secondary)] text-sm font-[var(--font-fira-code)]` — e.g., "47/320" |
| **Toggle active state** | Side-by-side button when active: `text-[var(--color-primary)] bg-[var(--color-primary-subtle)]` with `ring-1 ring-[var(--color-primary)]/30` |

## Paragraph-Aligned Side-by-Side

Replace the current 2-column grid with a **shared-row grid**:

```
┌───────────────────────────────┬───────────────────────────────┐
│ (paragraph 1 原文)            │ (paragraph 1 bản dịch)        │
├───────────────────────────────┼───────────────────────────────┤
│ (paragraph 2 原文)            │ (paragraph 2 bản dịch)        │
├───────────────────────────────┼───────────────────────────────┤
│ (paragraph 3 原文)            │ (paragraph 3 bản dịch)        │
└───────────────────────────────┴───────────────────────────────┘
```

**Implementation:**

```
split Chinese text by \n\n → chinese_paragraphs[]
split Vietnamese text by \n\n → vietnamese_paragraphs[]
max_rows = max(chinese_paragraphs.length, vietnamese_paragraphs.length)

render in <div class="grid grid-cols-2 gap-0">:
  for i in 0..max_rows:
    <div class="border-b border-[var(--border-default)]/30 p-4 bg-[var(--bg-surface)]">
      chinese_paragraphs[i] || ""
    </div>
    <div class="border-b border-[var(--border-default)]/30 p-4 bg-[var(--bg-elevated)]">
      vietnamese_paragraphs[i] || ""
    </div>
```

| Part | Spec |
|------|------|
| **Chinese column** | `bg-[var(--bg-surface)]` background. Font: `font-[var(--font-noto-serif)]`. Color: `text-[var(--text-secondary)]`. |
| **Vietnamese column** | `bg-[var(--bg-elevated)]` background. Font: `font-[var(--font-noto-serif)]`. Color: `text-[var(--text-primary)]`. |
| **Column headers** | `text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)] py-2 px-4 bg-[var(--bg-elevated)]/50`. Sticky at top of each column. Chinese: "原文 (Chinese)". Vietnamese: "Bản dịch (Vietnamese)". |
| **Row divider** | `border-b border-[var(--border-default)]/30` — subtle, don't dominate |
| **Paragraph text** | Both: `leading-relaxed` with `fontSize` from user preference |

## Synced Scrolling

When side-by-side is active:

```typescript
// On scroll of either pane:
const scrollPercent = source.scrollTop / (source.scrollHeight - source.clientHeight);
target.scrollTop = scrollPercent * (target.scrollHeight - target.clientHeight);
```

- Use `useRef` for both panes
- Add `onScroll` handler that sets the other pane's `scrollTop`
- Use a `scrollingRef` flag to prevent infinite scroll loops
- Respect `prefers-reduced-motion`: if reduced, disable smooth scroll behavior

## Reading Progress

| Feature | Spec |
|---------|------|
| **Storage key** | `dich-truyen-last-read-{bookId}` in `localStorage` |
| **Stored value** | `{ chapterIndex: number, timestamp: number }` |
| **Save triggers** | On chapter load (after content renders) |
| **Book Detail CTA** | On the Book Detail page, show "Continue Reading → Chapter 47" badge below the book header if last-read data exists. Style: `bg-[var(--color-primary-subtle)] text-[var(--color-primary)] rounded-lg px-4 py-2 text-sm font-medium inline-flex items-center gap-2 cursor-pointer`. Icon: `BookOpen` (16px). |

## Responsive Behavior

- Side-by-side: only available on `md:` breakpoint and above
- On mobile: side-by-side button hidden (`hidden md:inline-flex`)
- Single column mode always fills `max-w-3xl`

## Skeleton Loading (already exists)

No changes — existing skeleton pattern is sufficient.

## Accessibility

- Chapter dropdown: `<label>` with `aria-label="Jump to chapter"`
- Side-by-side columns: `aria-label="Chinese original"` and `aria-label="Vietnamese translation"`
- Synced scrolling: `prefers-reduced-motion: reduce` → disable smooth scroll
- Keyboard shortcuts already exist: `ArrowLeft`/`ArrowRight` for prev/next
- Focus: visible ring on all interactive toolbar elements
