# Design System Master File — Dịch Truyện

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** Dịch Truyện
**Generated:** 2026-02-24
**Category:** Productivity Tool — Translation Dashboard
**Theme:** Dark Mode Primary

---

## Global Rules

### Color Palette — Dark Mode

| Role | Hex | CSS Variable | Usage |
|------|-----|--------------|-------|
| Background | `#0B1120` | `--bg-primary` | Main background |
| Surface | `#111827` | `--bg-surface` | Cards, panels |
| Surface Elevated | `#1F2937` | `--bg-elevated` | Hover states, active items |
| Border | `#1F2937` | `--border-default` | Card borders, dividers |
| Border Hover | `#374151` | `--border-hover` | Hover state borders |
| Text Primary | `#F9FAFB` | `--text-primary` | Headings, main content |
| Text Secondary | `#9CA3AF` | `--text-secondary` | Descriptions, labels |
| Text Muted | `#6B7280` | `--text-muted` | Timestamps, hints |
| Primary / Teal | `#0D9488` | `--color-primary` | Active nav, progress bars, links |
| Primary Hover | `#14B8A6` | `--color-primary-hover` | Hover on primary elements |
| Primary Subtle | `#0D948820` | `--color-primary-subtle` | Active nav background |
| CTA / Orange | `#F97316` | `--color-cta` | Action buttons, alerts |
| CTA Hover | `#FB923C` | `--color-cta-hover` | Hover on CTA elements |
| Success | `#10B981` | `--color-success` | Translated status, success |
| Warning | `#F59E0B` | `--color-warning` | Crawled status, in-progress |
| Error | `#EF4444` | `--color-error` | Error status, failures |
| Info | `#3B82F6` | `--color-info` | Pending status, tips |

### Typography

- **Heading Font:** Fira Code (monospace — technical, precise feel)
- **Body Font:** Fira Sans (clean readability for Vietnamese + Chinese)
- **Reading Font:** Noto Serif (for chapter reader — optimal CJK + Vietnamese rendering)

```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&family=Noto+Serif:wght@400;500;600;700&display=swap');
```

| Element | Font | Weight | Size | Line Height |
|---------|------|--------|------|-------------|
| Page title | Fira Code | 700 | 24px | 1.3 |
| Card title | Fira Code | 600 | 16px | 1.4 |
| Body text | Fira Sans | 400 | 14px | 1.6 |
| Small/label | Fira Sans | 500 | 12px | 1.4 |
| Reader text | Noto Serif | 400 | 18px | 1.8 |
| Chapter title (reader) | Noto Serif | 600 | 22px | 1.4 |

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px | Tight gaps, inline padding |
| `--space-sm` | 8px | Icon gaps, badge padding |
| `--space-md` | 16px | Card padding, input padding |
| `--space-lg` | 24px | Section gaps, card padding |
| `--space-xl` | 32px | Page margin, between sections |
| `--space-2xl` | 48px | Top-level spacing |

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Badges, small buttons |
| `--radius-md` | 8px | Inputs, buttons |
| `--radius-lg` | 12px | Cards, panels |
| `--radius-xl` | 16px | Modals, large containers |

### Shadows (Dark Mode)

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.3)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.4)` | Cards |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.5)` | Dropdowns, popovers |
| `--shadow-glow` | `0 0 20px rgba(13,148,136,0.15)` | Active/focused elements |

---

## Component Specs

### Sidebar Navigation

```
Width: 240px (expanded) / 64px (collapsed)
Background: var(--bg-surface)
Border right: 1px solid var(--border-default)

Logo area: 64px height, centered
Nav items: 48px height, 16px horizontal padding
  - Default: text-secondary, no background
  - Hover: bg-elevated, text-primary
  - Active: primary-subtle bg, primary text, left 3px border

Transition: width 200ms ease
```

### Cards

```css
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 24px;
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  border-color: var(--border-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
```

### Status Badges

| Status | Background | Text | Dot Color |
|--------|-----------|------|-----------|
| Pending | `#3B82F620` | `#3B82F6` | `#3B82F6` |
| Crawled | `#F59E0B20` | `#F59E0B` | `#F59E0B` |
| Translated | `#10B98120` | `#10B981` | `#10B981` |
| Error | `#EF444420` | `#EF4444` | `#EF4444` |

### Progress Bars

```css
.progress-bar {
  background: var(--bg-elevated);
  border-radius: 4px;
  height: 6px;
  overflow: hidden;
}

.progress-fill {
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-hover));
  border-radius: 4px;
  height: 100%;
  transition: width 500ms ease;
}
```

### Buttons

```css
.btn-primary {
  background: var(--color-cta);
  color: white;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 600;
  font-family: 'Fira Sans', sans-serif;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  background: var(--color-cta-hover);
  transform: translateY(-1px);
}

.btn-secondary {
  background: transparent;
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}
```

---

## Icons

Use **Lucide React** (`lucide-react` npm package). Consistent 20px size for nav, 16px for inline.

| Context | Icons |
|---------|-------|
| Dashboard | `LayoutDashboard` |
| Library | `BookOpen` |
| Settings | `Settings` |
| Reading | `BookText` |
| Search | `Search` |
| Status: Translated | `CheckCircle2` |
| Status: Crawled | `Download` |
| Status: Error | `AlertCircle` |
| Status: Pending | `Clock` |
| Navigation | `ChevronLeft`, `ChevronRight` |
| Font Size | `AArrowUp`, `AArrowDown` |
| Side-by-side | `Columns2` |
| Close | `X` |

---

## Page Layouts

### Dashboard

```
┌──────────┬──────────────────────────────────────────┐
│          │  Dashboard                                │
│  SIDEBAR │  ┌──────────┬──────────┬──────────┐      │
│          │  │ 3 Books  │ 450 Ch.  │ 78% Done │      │
│  ■ Dash  │  │ ──────── │ ──────── │ ●●●●○○○  │      │
│  □ Lib   │  └──────────┴──────────┴──────────┘      │
│  □ Set   │                                           │
│          │  Recent Books                             │
│          │  ┌──────────┬──────────┬──────────┐      │
│          │  │ Book 1   │ Book 2   │ Book 3   │      │
│          │  │ ████░░░  │ ██████░  │ ████████ │      │
│          │  │ 45/120   │ 89/100   │ 200/200  │      │
│          │  └──────────┴──────────┴──────────┘      │
│          │                                           │
│          │  ┌── Quick Actions ──────────────────┐   │
│          │  │ [Browse Library]  [Open Settings]  │   │
│          │  └────────────────────────────────────┘   │
└──────────┴──────────────────────────────────────────┘
```

### Library

```
┌──────────┬──────────────────────────────────────────┐
│          │  Library              [Search...] [Filter]│
│  SIDEBAR │  ┌──────────┬──────────┬──────────┐      │
│          │  │  遮天     │  凡人修仙 │  斗破苍穹 │      │
│  □ Dash  │  │ Già Thiên│ Phàm Nhân│ Đấu Phá  │      │
│  ■ Lib   │  │ Author   │ Author   │ Author   │      │
│  □ Set   │  │ ████░░░  │ ██████░  │ ████████ │      │
│          │  │ 45/120   │ 89/100   │ 200/200  │      │
│          │  │ ●Trans.  │ ●Trans.  │ ●Done    │      │
│          │  └──────────┴──────────┴──────────┘      │
│          │  ┌──────────┬──────────┬──────────┐      │
│          │  │  ...      │  ...      │  ...      │      │
│          │  └──────────┴──────────┴──────────┘      │
└──────────┴──────────────────────────────────────────┘
```

### Book Detail

```
┌──────────┬──────────────────────────────────────────┐
│          │  ← Library / 遮天 (Già Thiên Cổ Đế)      │
│  SIDEBAR │  Author: 辰东 (Thần Đông)                │
│          │  145/320 chapters translated  ████░░ 45%  │
│          │  ┌──────────────────────────────────────┐ │
│          │  │ #  │ Title          │ Status         │ │
│          │  │ 1  │ 第一章 飞来横祸 │ ✓ Translated   │ │
│          │  │ 2  │ 第二章 天命之子 │ ✓ Translated   │ │
│          │  │ 3  │ 第三章 万道归一 │ ● Crawled      │ │
│          │  │ 4  │ 第四章 ...     │ ○ Pending      │ │
│          │  │... │                │                 │ │
│          │  └──────────────────────────────────────┘ │
└──────────┴──────────────────────────────────────────┘
```

### Chapter Reader (Side-by-side)

```
┌──────────┬──────────────────────────────────────────┐
│          │  ← Book / Chapter 47   [A-][A+] [⫼ Split]│
│  SIDEBAR │  ┌──────────────────┬─────────────────┐  │
│ (hidden) │  │ 第四十七章        │ Chương 47       │  │
│          │  │ 飞来横祸          │ Tai Họa Từ Trên │  │
│          │  │                   │ Trời Rơi Xuống  │  │
│          │  │ 天空中忽然出现了    │                 │  │
│          │  │ 一道巨大的裂缝...  │ Trên bầu trời   │  │
│          │  │                   │ bỗng nhiên xuất │  │
│          │  │ "你是谁？"         │ hiện một vết    │  │
│          │  │ 少年开口问道。     │ nứt khổng lồ...│  │
│          │  │                   │                 │  │
│          │  │                   │ "Ngươi là ai?"  │  │
│          │  │                   │ Thiếu niên mở   │  │
│          │  │                   │ miệng hỏi.     │  │
│          │  └──────────────────┴─────────────────┘  │
│          │          [← Prev]  47/320  [Next →]       │
└──────────┴──────────────────────────────────────────┘
```

---

## Animations & Transitions

| Element | Property | Duration | Easing |
|---------|----------|----------|--------|
| Card hover | transform, shadow, border | 200ms | ease |
| Nav item hover | background, color | 150ms | ease |
| Progress bar | width | 500ms | ease |
| Page transition | opacity | 200ms | ease-in-out |
| Sidebar collapse | width | 200ms | ease |
| Skeleton pulse | opacity | 1.5s | ease-in-out (infinite) |

### Loading Skeletons

Show skeleton placeholders for all async content (books, chapters, reader text). Use `animate-pulse` with `bg-elevated` color. Reserve exact dimensions to prevent layout shift.

---

## Anti-Patterns

- ❌ **No emojis as icons** — Use Lucide React SVG icons exclusively
- ❌ **No layout-shifting hovers** — Use translateY(-1px) max, no scale
- ❌ **No missing cursor:pointer** — All clickable elements must have it
- ❌ **No instant state changes** — Always 150-300ms transitions
- ❌ **No low contrast text** — Minimum #6B7280 on #0B1120 background
- ❌ **No content behind fixed elements** — Account for sidebar width
- ❌ **No infinite decorative animations** — Pulse only for loading
- ❌ **No blank loading screens** — Always show skeletons

## Pre-Delivery Checklist

- [ ] All icons from Lucide React (no emojis)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with 150-300ms transitions
- [ ] Text contrast minimum 4.5:1 on dark background
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Skeleton loaders for all async content
- [ ] No content hidden behind sidebar
- [ ] Font loading with `display=swap`
