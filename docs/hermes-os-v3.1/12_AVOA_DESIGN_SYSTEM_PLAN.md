# 12 — AVOA Design System Plan

**Status:** SPECIFICATION (not yet implemented)
**Version:** 3.1
**Date:** 31 July 2026
**Part of:** Hermes Engineering OS v3.1
**Depends on:** 11_DESIGN_STUDIO_OPERATING_MODEL, 05_UI_CONTRACT_STANDARD
**Feeds into:** 13_DESIGN_REVIEW_AND_VISUAL_QA, 14_AUTOMATED_QUALITY_GATES

---

## 1. Purpose

This document defines the plan to audit, standardize, and maintain the AVOA design system. It covers the current-state audit methodology, a comprehensive token and component plan, component state definitions, recurring UI patterns, ownership and governance, versioning, and a migration pathway from ad-hoc styling to token-driven design.

---

## 2. Current-State Audit

### 2.1 Audit Scope

The design system audit must inspect:

| Audit Area | What to Discover | Method |
|---|---|---|
| Tailwind color usage | All color classes used in the codebase | Static analysis: grep for `bg-`, `text-`, `border-`, `ring-`, `shadow-` color classes |
| Typography patterns | Font sizes, weights, line heights in use | Static analysis: grep for `text-`, `font-`, `leading-`, `tracking-` |
| Spacing values | Padding, margin, gap patterns | Static analysis: grep for `p-`, `m-`, `gap-`, `space-` |
| Layout patterns | Grid and flexbox usage | Static analysis + visual inspection |
| Component inventory | All React/Vue components and their variants | File-system scan of component directories |
| Hardcoded values | Non-token colors, magic numbers | Static analysis for hex codes, raw px values, inline styles |

### 2.2 Audit Deliverables

```yaml
audit_results:
  color_audit:
    total_color_usages: "<count>"
    unique_colors_used: "<count>"
    tailwind_classes_found: ["bg-blue-600", "text-gray-900", ...]
    hardcoded_colors: ["#1a1a2e", "rgb(255,255,255)", ...]
    inconsistencies: ["blue-500 vs blue-600 for primary buttons", ...]

  typography_audit:
    font_sizes_in_use: ["text-xs", "text-sm", "text-base", "text-lg", "text-xl", "text-2xl", "text-3xl"]
    font_weights_in_use: ["font-normal", "font-medium", "font-semibold", "font-bold"]
    inconsistent_pairings: ["heading uses text-2xl/font-bold in header, text-xl/font-semibold in card"]

  spacing_audit:
    padding_values: ["p-2", "p-4", "p-6", "p-8"]
    inconsistent_spacing: ["card padding: p-6 in dashboard, p-4 in settings"]

  component_inventory:
    total_components: "<count>"
    without_design_tokens: ["<component names>"]
    with_variants: ["<component: variant count>"]

  html_prototype_inventory:
    count: "<number of standalone HTML files>"
    design_inconsistencies: ["<file: issue>"]
```

### 2.3 Three HTML Prototypes to Build

As a validation step, three representative HTML prototypes must be built using the proposed design tokens:

| # | Prototype | Purpose | Tests |
|---|---|---|---|
| 1 | **Quote Review Page** | Primary user-facing page; verifies data display, status badges, action buttons | Color tokens, typography hierarchy, table patterns, responsive layout |
| 2 | **Admin Dashboard** | Data-heavy internal page; verifies card patterns, stat displays, navigation | Spacing grid, card consistency, sidebar layout, dark-mode readiness |
| 3 | **Settings/Form Page** | Form-heavy page; verifies input states, validation, accessibility | Form patterns, focus states, error states, keyboard navigation |

### 2.4 Four Components to Standardize First

| # | Component | Rationale |
|---|---|---|
| 1 | **Button** | Highest reuse; multiple variants (primary, secondary, ghost, destructive); many hardcoded instances |
| 2 | **Card** | Second-highest reuse; inconsistent padding, shadow, and border across the app |
| 3 | **StatusBadge** | Business-critical (reservation status, quote status); multiple color variants; accessibility requirement |
| 4 | **FormInput** | Used in all forms; needs consistent states (default, focus, error, disabled); accessibility critical |

---

## 3. Design Token Plan

### 3.1 Color System

#### 3.1.1 Semantic Color Tokens

All UI code must reference semantic tokens, never raw Tailwind color values directly:

```css
:root {
  /* === Brand === */
  --color-brand-50: #eff6ff;
  --color-brand-100: #dbeafe;
  --color-brand-200: #bfdbfe;
  --color-brand-300: #93c5fd;
  --color-brand-400: #60a5fa;
  --color-brand-500: #3b82f6;
  --color-brand-600: #2563eb;
  --color-brand-700: #1d4ed8;
  --color-brand-800: #1e40af;
  --color-brand-900: #1e3a8a;

  /* === Neutral === */
  --color-neutral-50: #fafafa;
  --color-neutral-100: #f5f5f5;
  --color-neutral-200: #e5e5e5;
  --color-neutral-300: #d4d4d4;
  --color-neutral-400: #a3a3a3;
  --color-neutral-500: #737373;
  --color-neutral-600: #525252;
  --color-neutral-700: #404040;
  --color-neutral-800: #262626;
  --color-neutral-900: #171717;

  /* === Semantic Mappings === */
  --color-primary: var(--color-brand-600);
  --color-primary-hover: var(--color-brand-700);
  --color-primary-light: var(--color-brand-100);

  --color-surface: #ffffff;
  --color-surface-secondary: var(--color-neutral-50);
  --color-surface-tertiary: var(--color-neutral-100);

  --color-text-primary: var(--color-neutral-900);
  --color-text-secondary: var(--color-neutral-600);
  --color-text-tertiary: var(--color-neutral-400);
  --color-text-inverse: #ffffff;

  --color-border: var(--color-neutral-200);
  --color-border-focus: var(--color-brand-500);

  /* === Functional === */
  --color-success: #16a34a;
  --color-success-light: #dcfce7;
  --color-warning: #d97706;
  --color-warning-light: #fef3c7;
  --color-error: #dc2626;
  --color-error-light: #fee2e2;
  --color-info: #2563eb;
  --color-info-light: #dbeafe;
}
```

#### 3.1.2 Token Usage Rules

| Rule | Correct | Incorrect |
|---|---|---|
| Use semantic tokens in component styles | `color: var(--color-primary)` | `color: #2563eb` |
| Tailwind classes reference tokens via config | `bg-primary` (with Tailwind config extending colors) | `bg-blue-600` |
| Functional colors use semantic names | `var(--color-success)` | `bg-green-600` |
| Never hardcode hex values in components | ❌ | `style="color: #2563eb"` |

#### 3.1.3 Tailwind Configuration

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'var(--color-primary)',
          hover: 'var(--color-primary-hover)',
          light: 'var(--color-primary-light)',
        },
        surface: {
          DEFAULT: 'var(--color-surface)',
          secondary: 'var(--color-surface-secondary)',
          tertiary: 'var(--color-surface-tertiary)',
        },
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        border: {
          DEFAULT: 'var(--color-border)',
          focus: 'var(--color-border-focus)',
        },
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
        error: 'var(--color-error)',
        info: 'var(--color-info)',
      },
    },
  },
};
```

### 3.2 Typography Scale

```yaml
typography:
  scale:
    xs:
      size: "0.75rem"     # text-xs
      line_height: "1rem"  # leading-4
      usage: "captions, helper text, legal"
    sm:
      size: "0.875rem"    # text-sm
      line_height: "1.25rem"  # leading-5
      usage: "body-small, labels, secondary text"
    base:
      size: "1rem"          # text-base
      line_height: "1.5rem"   # leading-6
      usage: "body, form inputs, table cells"
    lg:
      size: "1.125rem"     # text-lg
      line_height: "1.75rem"  # leading-7
      usage: "large body, card titles"
    xl:
      size: "1.25rem"      # text-xl
      line_height: "1.75rem"  # leading-7
      usage: "section headers, modal titles"
    2xl:
      size: "1.5rem"        # text-2xl
      line_height: "2rem"     # leading-8
      usage: "page titles"
    3xl:
      size: "1.875rem"     # text-3xl
      line_height: "2.25rem"  # leading-9
      usage: "hero headings, dashboard titles"
    4xl:
      size: "2.25rem"       # text-4xl
      line_height: "2.5rem"   # leading-10
      usage: "landing page headlines only"

  weights:
    normal: 400     # font-normal — body text
    medium: 500     # font-medium — emphasized body, labels
    semibold: 600   # font-semibold — headings, button text
    bold: 700       # font-bold — hero text, key metrics

  font_families:
    sans: "'Inter', system-ui, -apple-system, sans-serif"
    mono: "'JetBrains Mono', 'Fira Code', monospace"
```

#### 3.2.1 Typography Rules

| Rule | Example |
|---|---|
| Page titles: `text-2xl font-semibold` | "Quote Review" |
| Section headers: `text-xl font-semibold` | "Booking Details" |
| Card titles: `text-lg font-medium` | "Reservation #1234" |
| Body text: `text-base font-normal` | All paragraph and description text |
| Labels: `text-sm font-medium` | Form labels, table headers |
| Captions: `text-xs font-normal` | Timestamps, metadata |
| Consistent line heights per size | Never mix leading-tight with text-base |

### 3.3 Spacing Grid

```yaml
spacing:
  base_unit: 0.25rem  # 4px
  scale:
    0: "0"
    px: "1px"
    0.5: "0.125rem"   # 2px
    1: "0.25rem"       # 4px
    1.5: "0.375rem"    # 6px
    2: "0.5rem"        # 8px
    2.5: "0.625rem"    # 10px
    3: "0.75rem"       # 12px
    3.5: "0.875rem"    # 14px
    4: "1rem"          # 16px
    5: "1.25rem"       # 20px
    6: "1.5rem"        # 24px
    7: "1.75rem"       # 28px
    8: "2rem"          # 32px
    9: "2.25rem"       # 36px
    10: "2.5rem"       # 40px
    11: "2.75rem"      # 44px
    12: "3rem"         # 48px
    14: "3.5rem"       # 56px
    16: "4rem"         # 64px
    20: "5rem"         # 80px
    24: "6rem"         # 96px

  presets:
    section_padding_y: "py-8"      # 32px vertical
    section_padding_x: "px-6"      # 24px horizontal
    card_padding: "p-6"            # 24px all sides
    card_gap: "gap-4"              # 16px between cards
    form_field_gap: "gap-2"        # 8px between label and input
    inline_gap: "gap-3"            # 12px between inline elements
    page_margin: "mx-auto max-w-7xl px-6"  # centered, max 1280px
```

#### 3.3.1 Spacing Rules

| Context | Spacing |
|---|---|
| Between sections | `py-8` or `py-12` |
| Between cards in a grid | `gap-4` or `gap-6` |
| Card internal padding | `p-6` |
| Form field groups | `gap-4` between fields |
| Label-to-input spacing | `gap-2` |
| Button groups | `gap-3` |
| Inline icon + text | `gap-2` |

### 3.4 Breakpoints

```yaml
breakpoints:
  mobile: "max-width: 639px"         # sm: and below
  tablet: "min-width: 640px"         # sm: and md:
  desktop: "min-width: 1024px"       # lg: and above
  wide: "min-width: 1280px"          # xl: and above

  design_at:
    - 375px   # mobile (iPhone SE)
    - 768px   # tablet (iPad Mini)
    - 1440px  # desktop (standard laptop)
```

#### 3.4.1 Responsive Rules

| Breakpoint | Layout Behavior |
|---|---|
| Mobile (< 640px) | Single column; navigation collapses to hamburger; tables become cards |
| Tablet (640-1023px) | Two-column grid; side navigation visible; compact tables |
| Desktop (≥ 1024px) | Multi-column; full navigation; data tables; side panels |
| Wide (≥ 1280px) | Maximum content width; additional whitespace |

### 3.5 Radius, Border, and Elevation

```yaml
radius:
  none: "rounded-none"       # 0px
  sm: "rounded-sm"           # 2px — inputs, small elements
  DEFAULT: "rounded-lg"      # 8px — cards, modals, buttons
  md: "rounded-md"           # 6px — dropdowns, tooltips
  lg: "rounded-lg"           # 8px — cards, modals
  xl: "rounded-xl"           # 12px — large cards, hero sections
  full: "rounded-full"       # circular — avatars, badges

borders:
  default: "border border-[var(--color-border)]"
  focus: "border-2 border-[var(--color-border-focus)]"
  error: "border border-[var(--color-error)]"
  none: "border-0"

elevation:
  none: "shadow-none"
  sm: "shadow-sm"           # subtle card elevation
  DEFAULT: "shadow"          # standard card/dropdown elevation
  md: "shadow-md"            # raised element (modal, drawer)
  lg: "shadow-lg"            # prominent modal, dialog
  xl: "shadow-xl"            # full-screen overlay
```

### 3.6 Icons

```yaml
icons:
  library: "lucide-react"  # preferred
  fallback: "heroicons"

  sizes:
    sm: "w-4 h-4"          # inline with text-sm
    DEFAULT: "w-5 h-5"      # inline with text-base
    lg: "w-6 h-6"           # standalone, buttons
    xl: "w-8 h-8"           # feature icons, empty states
    2xl: "w-12 h-12"        # hero icons, large empty states

  usage:
    - Icons must use currentColor for fill/stroke
    - Icon color inherits from parent text color
    - Paired icon+text must use gap-2
    - Decorative icons must have aria-hidden="true"
    - Semantic icons must have aria-label
```

### 3.7 Motion

```yaml
motion:
  durations:
    instant: "75ms"      # micro-interactions (hover, focus)
    fast: "150ms"         # transitions, color changes
    normal: "200ms"       # standard animations
    slow: "300ms"         # page transitions, modal open/close
    deliberate: "500ms"   # hero animations, onboarding

  easings:
    default: "cubic-bezier(0.4, 0, 0.2, 1)"   # ease-in-out
    enter: "cubic-bezier(0, 0, 0.2, 1)"        # ease-out (appearing)
    exit: "cubic-bezier(0.4, 0, 1, 1)"          # ease-in (disappearing)

  reduced_motion:
    prefer_reduced: >
      All animations must respect prefers-reduced-motion.
      When reduced motion is preferred, transitions should be instant (0ms)
      and animations should be disabled.
```

### 3.8 Accessibility (WCAG AA)

```yaml
accessibility:
  standard: "WCAG 2.1 Level AA"

  color_contrast:
    normal_text: "4.5:1 minimum"
    large_text: "3:1 minimum"      # ≥18px or ≥14px bold
    ui_components: "3:1 minimum"    # borders, icons, controls

  focus_indicators:
    default: "ring-2 ring-offset-2 ring-[var(--color-border-focus)]"
    visible: "Focus ring must be visible on all interactive elements"
    keyboard_only: "Use :focus-visible for keyboard focus, not mouse"

  touch_targets:
    minimum: "44x44px"             # WCAG 2.5.5
    preferred: "48x48px"

  semantic_html:
    - Use <button> for actions, not <div onclick>
    - Use <nav> for navigation
    - Use <main> for primary content
    - Use heading hierarchy (h1 → h2 → h3) without skipping levels

  screen_reader:
    - All images must have alt text (decorative: alt="")
    - Form inputs must have associated <label>
    - Error messages must be announced via aria-live
    - Dynamic content changes must use aria-live regions
```

---

## 4. Component States

### 4.1 Standard State Set

Every interactive component must implement these states:

| State | Required For | Example |
|---|---|---|
| **Default** | All components | Normal resting appearance |
| **Hover** | All interactive (buttons, links, cards with actions) | Cursor over element |
| **Focus** | All focusable (inputs, buttons, links) | Keyboard tab or click focus |
| **Active** | Buttons, toggles, selectable items | Being pressed/selected |
| **Disabled** | All interactive | Greyed out, no interaction |
| **Loading** | Buttons, data containers | Spinner, skeleton, or shimmer |
| **Empty** | Lists, tables, data displays | "No results" message with icon |
| **Error** | Inputs, data containers | Validation error, fetch failure |

### 4.2 Button States

```yaml
button:
  variants: [primary, secondary, ghost, destructive, link]
  sizes: [sm, DEFAULT, lg, icon]

  states:
    default:
      primary: "bg-primary text-white rounded-lg px-4 py-2"
      secondary: "bg-surface-secondary text-text-primary border rounded-lg px-4 py-2"
      ghost: "text-text-secondary hover:bg-surface-tertiary rounded-lg px-4 py-2"
      destructive: "bg-error text-white rounded-lg px-4 py-2"
      link: "text-primary hover:underline px-0 py-0"

    hover:
      primary: "bg-primary-hover"
      secondary: "bg-surface-tertiary"
      ghost: "bg-surface-tertiary"
      destructive: "bg-red-700"
      link: "underline"

    focus:
      all: "ring-2 ring-offset-2 ring-primary outline-none"

    active:
      all: "scale-[0.98] transition-transform duration-75"

    disabled:
      all: "opacity-50 cursor-not-allowed pointer-events-none"

    loading:
      all: "cursor-wait"
      content: "Spinner icon + 'Loading...' text (or icon-only for icon buttons)"
```

### 4.3 Input States

```yaml
input:
  variants: [text, textarea, select, checkbox, radio, toggle]

  states:
    default: "border rounded-lg px-3 py-2 text-base bg-surface"
    hover: "border-neutral-300"
    focus: "border-focus ring-2 ring-primary/20 outline-none"
    error: "border-error ring-2 ring-error/20"
    disabled: "bg-surface-tertiary text-text-tertiary cursor-not-allowed"
    readonly: "bg-surface-secondary cursor-default"
    placeholder: "text-text-tertiary"

  with_label: "flex flex-col gap-2"
  with_error_message: "text-sm text-error mt-1"
  with_helper_text: "text-sm text-text-tertiary mt-1"
```

### 4.4 Card States

```yaml
card:
  states:
    default: "bg-surface rounded-xl shadow-sm border p-6"
    hover: "shadow-md"  # only for interactive cards
    selected: "border-primary ring-2 ring-primary/20"
    disabled: "opacity-60 pointer-events-none"
    loading: "animate-pulse bg-surface-tertiary"  # skeleton variant
```

---

## 5. Recurring UI Patterns

### 5.1 Form Patterns

```yaml
form_layout:
  stack: "flex flex-col gap-4"              # vertical form
  inline: "flex items-end gap-3"            # horizontal compact form
  two_column: "grid grid-cols-1 md:grid-cols-2 gap-4"  # responsive grid

  field_group:
    structure: "label + input + (error | helper)"
    spacing: "gap-2"

  actions:
    placement: "flex justify-end gap-3 mt-6"  # right-aligned
    primary_first: true                          # primary action on the right

  validation:
    inline: "error message below field"
    summary: "Error banner at top of form with count"
```

### 5.2 Table Patterns

```yaml
table:
  container: "overflow-x-auto rounded-lg border"
  header: "bg-surface-secondary text-sm font-medium text-text-secondary"
  row: "border-t hover:bg-surface-secondary/50 transition-colors"
  cell: "px-4 py-3 text-sm"
  empty: "text-center py-12 text-text-tertiary"

  responsive:
    mobile: "Table becomes stacked cards; each row is a card"
    tablet_plus: "Standard table layout"

  sortable_headers: "cursor-pointer hover:text-text-primary flex items-center gap-1"
  selectable_rows: "checkbox column + selected state with bg-primary-light"
```

### 5.3 Card Grid Patterns

```yaml
card_grid:
  two_column: "grid grid-cols-1 md:grid-cols-2 gap-4"
  three_column: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
  four_column: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"

  stat_card:
    structure: "icon + label + value + (delta)"
    spacing: "p-6"
    icon: "w-8 h-8 text-primary bg-primary-light rounded-lg p-1.5"
    label: "text-sm text-text-secondary"
    value: "text-2xl font-bold text-text-primary"
    delta: "text-sm font-medium text-success or text-error"
```

### 5.4 Data Display Patterns

```yaml
key_value_list:
  structure: "grid grid-cols-1 sm:grid-cols-2 gap-4"
  item: "flex flex-col gap-1"
  label: "text-sm text-text-secondary"
  value: "text-base font-medium text-text-primary"

detail_section:
  structure: "flex flex-col gap-4"
  header: "text-lg font-semibold pb-2 border-b"
  content: "prose or structured data"
```

### 5.5 Pricing Display Patterns

```yaml
price_display:
  large: "text-3xl font-bold"
  currency: "text-lg font-normal text-text-secondary align-top"
  period: "text-sm text-text-secondary"
  original_price: "line-through text-text-tertiary mr-2"
  discount_badge: "bg-success-light text-success text-sm font-medium rounded-full px-2 py-0.5"
```

### 5.6 Status Display Patterns

```yaml
status_badge:
  variants: [success, warning, error, info, neutral]
  structure: "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
  colors:
    success: "bg-success-light text-success"
    warning: "bg-warning-light text-warning"
    error: "bg-error-light text-error"
    info: "bg-info-light text-info"
    neutral: "bg-surface-tertiary text-text-secondary"
  with_dot: "w-1.5 h-1.5 rounded-full bg-current"
```

---

## 6. Ownership and Governance

### 6.1 Ownership Model

```yaml
design_system_ownership:
  design_tokens: "Visual Designer role (Design Studio)"
  component_library: "UI Implementation Agent + Hermes review"
  documentation: "Doc Agent (pilot) + Visual Designer"
  accessibility_compliance: "All design roles; Visual QA verifies"
  version_control: "Hermes (tokens file in repo)"
```

### 6.2 Change Process

```
1. Design token change request → Visual Designer
2. Visual Designer assesses impact on all components
3. Visual Designer proposes token changes to Hermes
4. Hermes approves or requests revision
5. Visual Designer updates token file
6. Hermes creates audit task: "Update all components using changed tokens"
7. UI Implementation Agent updates affected components
8. Visual QA runs token-compliance audit
9. Hermes merges token changes
```

### 6.3 Token File Location

```
/avoa-connect/
├── styles/
│   └── tokens.css              # All design tokens
├── tailwind.config.js           # Tailwind config referencing tokens
└── docs/
    └── design/
        └── DESIGN_SYSTEM.md     # Human-readable design system docs
```

---

## 7. Versioning

### 7.1 Semantic Versioning for Design Tokens

```yaml
versioning:
  schema: "MAJOR.MINOR.PATCH"

  major:
    trigger: "Breaking visual change (color palette redesign, spacing scale change)"
    example: "Primary brand color changes from blue to teal"

  minor:
    trigger: "New tokens added, new component variants, new patterns"
    example: "New success-light token added; new 'link' button variant"

  patch:
    trigger: "Token value tweaks, bug fixes, accessibility improvements"
    example: "Increased contrast ratio on text-secondary from 3.8:1 to 4.6:1"
```

### 7.2 Token Changelog

```yaml
changelog:
  - version: "1.0.0"
    date: "TBD"
    changes:
      - "Initial token set established from audit"
      - "All hardcoded values migrated to tokens"
  - version: "1.1.0"
    date: "TBD"
    changes:
      - "Added dark mode token variants"
      - "Added motion tokens"
```

---

## 8. Migration Plan

### 8.1 Migration Phases

| Phase | Activity | Success Criteria |
|---|---|---|
| **Phase 0 — Audit** | Run static analysis; catalog all colors, typography, spacing | Complete audit report with counts and inconsistencies |
| **Phase 1 — Tokens** | Create `tokens.css` file with all design tokens | Token file exists; Tailwind config references tokens |
| **Phase 2 — Core Components** | Migrate Button, Card, StatusBadge, FormInput to tokens | 4 components use only tokens; 0 hardcoded values |
| **Phase 3 — Prototypes** | Build 3 HTML prototypes using tokens only | Prototypes visually match design intent; 0 hardcoded values |
| **Phase 4 — Full Migration** | Migrate all remaining components to tokens | 0 hardcoded hex/rgb values in component code |
| **Phase 5 — Enforcement** | Add CI check that rejects hardcoded color/spacing values | CI fails on `#[0-9a-fA-F]{6}` or `rgb(` in component files |

### 8.2 Migration Rules

1. **Never break existing UI during migration.** Each component is migrated and verified before moving to the next.
2. **New components must use tokens from Day 1.** No new hardcoded values.
3. **Migration tasks are R1.** Token swaps are presentation-only changes.
4. **Visual QA verifies every migrated component.** Screenshots before/after migration must match.
5. **CI enforcement is gradual.** Warning first, then error after full migration.

### 8.3 Hardcoded Value Detection Pattern

```regex
# Detect hardcoded colors in component files
#[0-9a-fA-F]{3,8}(?!\s*;)           # hex colors not followed by CSS comment
rgb\(\s*\d+                            # rgb() values
rgba\(\s*\d+                           # rgba() values
(?<!var\(--)hsl\(                     # hsl() values not inside var()
```

---

## 9. Design System Checklist

Before any UI task begins, Hermes must verify:

```
☐ Design tokens file exists and is up to date
☐ Required component tokens are defined
☐ Component has all required states documented
☐ Breakpoints are specified for responsive behavior
☐ Color contrast meets WCAG AA at all breakpoints
☐ Focus indicators are visible and consistent
☐ Touch targets meet minimum size (44px)
☐ All images have alt text specified
☐ Form inputs have associated labels
☐ Animation respects prefers-reduced-motion
☐ No hardcoded values in the implementation
```

---

## 10. Cross-References

| Reference | Document |
|---|---|
| Design Studio Operating Model | `11_DESIGN_STUDIO_OPERATING_MODEL.md` |
| Design Review and Visual QA | `13_DESIGN_REVIEW_AND_VISUAL_QA.md` |
| UI Contract Standard | `05_UI_CONTRACT_STANDARD.md` |
| Automated Quality Gates | `14_AUTOMATED_QUALITY_GATES.md` |
| Evidence Standards | `18_EVIDENCE_AND_COMPLETION_STANDARD.md` |

---

*Version 3.1 — Specification. Part of Hermes Engineering OS v3.1. Awaiting implementation authorization.*