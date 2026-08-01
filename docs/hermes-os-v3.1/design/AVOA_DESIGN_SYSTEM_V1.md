# AVOA Design System V1

**Status:** HOS-2 Specification | **Version:** 1.0

---

## Colour Tokens

### Brand Palette (existing in tailwind.config.ts)

| Token | Hex | Usage |
|---|---|---|
| `navy` | #0A1628 | Primary backgrounds, headers |
| `teal` | #0A7E8F | Accents, interactive elements |
| `gold` | #C99A3B | Highlights, premium indicators |
| `coral` | #E8734A | Warnings, attention |
| `cream` | #F5F0E8 | Light backgrounds, cards |

Each colour has 50-900 scale. Use: 50 (lightest) through 900 (darkest).

### Semantic Tokens (to add)

| Token | Colour | Usage |
|---|---|---|
| `success` | #22C55E | Success states, confirmations |
| `error` | #EF4444 | Errors, destructive actions |
| `warning` | #F59E0B | Warnings |
| `info` | #3B82F6 | Information |
| `text-primary` | navy-900 | Primary text |
| `text-secondary` | navy-500 | Secondary text |
| `surface` | cream-50 | Page background |
| `border` | navy-100 | Borders, dividers |

---

## Typography Scale

| Level | Size | Weight | Line Height | Usage |
|---|---|---|---|---|
| h1 | 2.25rem (36px) | 700 | 1.2 | Page titles |
| h2 | 1.875rem (30px) | 600 | 1.25 | Section headers |
| h3 | 1.5rem (24px) | 600 | 1.3 | Card titles |
| h4 | 1.25rem (20px) | 500 | 1.4 | Subsection |
| body | 1rem (16px) | 400 | 1.5 | Body text |
| body-sm | 0.875rem (14px) | 400 | 1.5 | Secondary text |
| caption | 0.75rem (12px) | 400 | 1.4 | Labels, captions |
| overline | 0.625rem (10px) | 600 | 1.2 | Uppercase labels |

Font: System font stack (or Inter for premium feel).

---

## Spacing Scale (4px base)

| Token | Value | Usage |
|---|---|---|
| 1 | 4px | Tight |
| 2 | 8px | Compact |
| 3 | 12px | Default internal |
| 4 | 16px | Standard |
| 5 | 20px | Relaxed |
| 6 | 24px | Section gap |
| 8 | 32px | Major gap |
| 10 | 40px | Section margin |
| 12 | 48px | Page margin |
| 16 | 64px | Large gap |
| 20 | 80px | Hero spacing |
| 24 | 96px | Extra large |
| 32 | 128px | Maximum |

---

## Breakpoints

| Name | Min Width | Target |
|---|---|---|
| Mobile | 375px | Phone |
| Tablet | 768px | iPad portrait |
| Desktop | 1024px | Laptop |
| Wide | 1440px | Desktop monitor |

Mobile-first: design for 375px, enhance upward.

---

## Grid

12-column grid. Container max-width: 1280px. Gutters: 16px mobile, 24px tablet, 32px desktop.

---

## Radius

| Token | Value | Usage |
|---|---|---|
| none | 0 | Tables, data grids |
| sm | 4px | Inputs, small elements |
| md | 8px | Cards, buttons |
| lg | 12px | Modals, dialogs |
| full | 9999px | Pills, badges |

---

## Elevation

| Level | Shadow | Usage |
|---|---|---|
| 0 | none | Flat content |
| 1 | 0 1px 3px rgba(0,0,0,0.1) | Cards |
| 2 | 0 4px 6px rgba(0,0,0,0.1) | Dropdowns |
| 3 | 0 10px 20px rgba(0,0,0,0.15) | Modals |
| 4 | 0 20px 40px rgba(0,0,0,0.2) | Drawers |

---

## Motion

- Duration: 150ms (micro), 250ms (standard), 400ms (entrance)
- Easing: ease-out for entering, ease-in for exiting
- Reduced motion: respect `prefers-reduced-motion`

---

## Accessibility (Minimum)

- WCAG 2.1 AA
- Colour contrast 4.5:1 (normal text), 3:1 (large text)
- Focus indicators visible on all interactive elements
- All images have alt text
- Forms have labels
- Keyboard navigable

---

*Part of Hermes Product OS v3.1 — HOS-2.*