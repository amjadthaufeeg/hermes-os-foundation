# Component Library Specification

**Status:** HOS-2 Spec | **Version:** 1.0

---

## Foundational Components

### Button
- **Variants:** Primary (navy), Secondary (outline), Tertiary (text), Danger (coral)
- **States:** Default, Hover, Focus, Active, Disabled, Loading
- **Sizes:** sm (32px), md (40px), lg (48px)
- **Accessibility:** Focus visible, aria-label when icon-only, min 44px touch target
- **Disallowed:** Inline links styled as buttons; buttons without labels

### Input / TextArea
- **Variants:** Default, Error, Disabled, Read-only
- **States:** Empty, Filled, Focus, Error, Disabled
- **Accessibility:** Associated label, error message linked via aria-describedby
- **Disallowed:** Placeholder as sole label

### Checkbox / Radio / Switch
- **Variants:** Default, Disabled, Error
- **Accessibility:** Group label, keyboard navigable
- **Disallowed:** Custom styling without native input preservation

### Dropdown / Select
- **Variants:** Native, Searchable
- **States:** Closed, Open, Selected, Disabled, Error
- **Accessibility:** Keyboard navigable, aria-expanded

### DatePicker / Search / Filter
- Spec deferred to HOS-3 (needs UX research first)

### Card
- **Variants:** Default, Interactive (hover), Selected
- **Content zones:** Header, Body, Footer, Media
- **Usage:** Lists, grids, dashboards
- **Disallowed:** Nesting more than 2 levels

### Table
- **Variants:** Default, Striped, Compact
- **Features:** Sortable headers, Pagination, Row selection
- **States:** Loading, Empty, Error
- **Responsive:** Horizontal scroll on mobile

### Pagination / Tabs / Navigation
- **Pagination:** Prev/Next + page numbers, compact on mobile
- **Tabs:** Horizontal, scrollable overflow on mobile
- **Navigation:** Top bar (desktop), Bottom bar (mobile), Sidebar (admin)

### Dialog / Drawer
- **Dialog:** Modal overlay, title + body + actions, Escape to close
- **Drawer:** Slide from right, for detail panels, configurable width
- **Accessibility:** Focus trap, aria-modal, Escape key

### Alert / Badge / Tooltip
- **Alert:** Info, Success, Warning, Error; dismissible option
- **Badge:** Count, Status dot, Label
- **Tooltip:** On hover/focus, short text only, 200ms delay

### Timeline
- Vertical timeline with dots and connectors
- Used for reservation history, audit trails, approval flows

### Domain Components (AVOA-specific)
- **PricingSummary:** Rate breakdown, taxes, totals, validity
- **ReservationTimeline:** Villa, dates, status transitions
- **ApprovalPanel:** Accept/Reject/Comment, multi-step
- **DashboardWidgets:** Charts, KPIs, status cards

---

## Component States Standard

Every interactive component must support: **default, hover, focus, active, disabled, loading**.
Every data component must support: **loading, empty, error, success**.

---

*Part of Hermes Product OS v3.1 — HOS-2.*