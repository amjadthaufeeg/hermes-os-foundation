# 05 — UI Contract Standard

**Document ID:** HERMES-OS-V3.1-05
**Status:** SPECIFICATION
**Version:** 3.1
**Date:** 31 July 2026
**Authority:** Hermes Engineering OS v3.1

---

## Purpose

The UI Contract is a visual-governance agreement that sits alongside the Task Contract (04) when a task involves user-facing interface work. It defines who owns the design, what visual standards apply, which states and breakpoints must be evidenced, and what constitutes acceptable visual delivery.

A UI Contract is **required** whenever a task's `primary_class` is `VISUAL_ONLY`, or when a `FEATURE` / `INTERACTION_ONLY` task produces user-visible output.

---

## 1. Complete YAML Schema

```yaml
# === UI CONTRACT YAML SCHEMA v3.1 ===

# ── Identity ─────────────────────────────────────────────
ui_contract_id:     string          # UI-{PRODUCT}-{NNNN} format (e.g. UI-AVOA-0003)
task_contract_id:   string          # References parent 04_TASK_CONTRACT_STANDARD contract
title:              string          # Human-readable title
status:             enum            # DRAFT | APPROVED | ACTIVE | COMPLETED

# ── Design Authority ─────────────────────────────────────
design_owner:       enum            # AMJAD | DESIGN_DEPARTMENT | HERMES
                                    # Who owns the final visual sign-off
design_reference:   string          # URL or file path to approved design (Figma, prototype, spec)
design_system_version: string       # Design system version (e.g. avoa-design-system-v3.1)

# ── Required States ──────────────────────────────────────
# Every interactive state the builder must implement AND evidence
required_states:
  - state:          string          # State name (e.g. DEFAULT, LOADING, EMPTY, ERROR, SUCCESS, ACTIVE, HOVER, FOCUS, DISABLED)
    description:    string          # What this state represents
    screenshot_required: boolean   # Must evidence be collected for this state?
    notes:          string|null     # Additional visual guidance
  # Common state catalog:
  # DEFAULT, LOADING, EMPTY, ERROR, SUCCESS, HOVER, FOCUS, ACTIVE, DISABLED,
  # EXPANDED, COLLAPSED, VALIDATION_ERROR, SUBMITTING, CONFIRMED, PARTIAL_DATA

# ── Required Breakpoints ─────────────────────────────────
required_breakpoints:
  - width:          integer         # Pixel width (e.g. 320)
    label:          string          # Human label (e.g. "Mobile S")
    orientation:    enum            # PORTRAIT | LANDSCAPE
    required:       boolean         # Must screenshots be taken at this breakpoint?
  # Standard AVOA breakpoints:
  # 320 (Mobile S), 375 (Mobile M), 414 (Mobile L), 768 (Tablet),
  # 1024 (Tablet Landscape/Desktop S), 1280 (Desktop M), 1440 (Desktop L)

# ── Approved Tokens ──────────────────────────────────────
approved_tokens:
  colors:
    source:         string          # CSS file or config (e.g. "src/styles/avoa-tokens.css")
    palette:        list<string>    # Allowed color token namespace prefixes (e.g. ["navy", "teal", "gold", "coral", "cream"])
  typography:
    source:         string          # CSS file or config
    scale:          list<string>    # Allowed type scale tokens (e.g. ["text-xs", "text-sm", "text-base", "text-lg", "text-xl", "text-2xl", "text-3xl"])
    families:       list<string>    # Allowed font families (e.g. ["Inter", "system-ui"])
  spacing:
    source:         string          # CSS file or config
    scale:          list<integer>   # Allowed spacing values in px (e.g. [4, 8, 12, 16, 20, 24, 32, 40, 48, 64])
  breakpoints:
    source:         string          # CSS file or config
    values:         list<string>    # Allowed breakpoint names (e.g. ["sm", "md", "lg", "xl"])
  border_radius:
    scale:          list<string>    # Allowed radius tokens (e.g. ["none", "sm", "md", "lg", "full"])
  shadows:
    scale:          list<string>    # Allowed shadow tokens (e.g. ["none", "sm", "md", "lg", "xl"])

# ── Component-Level Requirements ─────────────────────────
component_requirements:
  - component:      string          # Component name
    states:         list<string>    # Required states for this component
    breakpoints:    list<integer>   # Required breakpoints (overrides global if specified)
    accessibility:
      wcag_level:   enum            # A | AA | AAA
      keyboard:     boolean         # Full keyboard navigation required
      screenreader: boolean         # Screen-reader tested
    animation:
      allowed:      boolean         # Animations permitted
      max_duration_ms: integer|null # Maximum animation duration
      spec:         string|null     # Reference to animation spec

# ── Visual Acceptance Criteria ───────────────────────────
visual_acceptance_criteria:
  layout:
    - description:  string          # e.g. "Form fields stack vertically at mobile breakpoints"
  alignment:
    - description:  string          # e.g. "All form labels left-aligned with consistent 8px gutter"
  color:
    - description:  string          # e.g. "Error messages use coral-600 on cream-50 background"
  typography:
    - description:  string          # e.g. "Section headings use font-size text-xl font-weight semibold"
  spacing:
    - description:  string          # e.g. "24px vertical gap between form sections"
  responsive:
    - description:  string          # e.g. "Sidebar collapses to hamburger menu below 768px"

# ── Required Visual Evidence ─────────────────────────────
required_visual_evidence:
  screenshot_evidence: boolean      # Screenshots required?
  screenshot_count_min: integer     # Minimum number of screenshots
  comparison_evidence: boolean      # Side-by-side before/after required?
  video_evidence: boolean           # Screen recording required?
  video_duration_max_seconds: integer|null  # Max recording length
  browser_testing:
    required:     boolean           # Multi-browser testing required?
    browsers:     list<string>      # e.g. ["Chrome", "Firefox", "Safari"]

# ── Design Review Gates ──────────────────────────────────
design_review_gates:
  gates:
    - gate:         string          # Gate name
      required:     boolean         # Must pass
      reviewer:     enum            # AMJAD | HERMES | DESIGN_DEPARTMENT
      description:  string
  # Standard gates:
  # token_compliance, layout_accuracy, responsive_accuracy,
  # state_completeness, accessibility_check, visual_regression

# ── Anti-Patterns (Forbidden) ────────────────────────────
forbidden_patterns:
  - pattern:        string          # Description of forbidden visual pattern
    reason:         string          # Why forbidden
  # Examples:
  # - "Hardcoded color values (hex/rgb) outside approved tokens"
  # - "Inline styles not extractable to design system"
  # - "Fixed pixel dimensions for text containers"
  # - "Images without alt text"

# ── Evidence Record ──────────────────────────────────────
evidence_record:
  screenshots:      list<string>    # File paths or URLs
  videos:           list<string>    # File paths or URLs
  comparison_images: list<string>   # Before/after comparison file paths
  browser_results:  object          # { browser_name: "pass"|"fail"|"not_tested" }
  visual_regression_results: string|null  # Path to diff report

# ── Approval ─────────────────────────────────────────────
approvals:
  - role:           enum            # DESIGN_DEPARTMENT | HERMES | AMJAD
    action:         enum            # APPROVED | REJECTED | CONDITIONALLY_APPROVED
    date:           datetime
    notes:          string
```

---

## 2. Relationship to Task Contract (04)

The UI Contract is a **companion document** to the Task Contract. They are linked via `ui_contract_id` in the Task Contract and `task_contract_id` in the UI Contract.

### Overlap and Boundaries

| Concern | Task Contract (04) | UI Contract (05) |
|---|---|---|
| What must be built | `scope.objective`, `acceptance_criteria.functional` | — |
| How it must look | `acceptance_criteria.visual` (summary) | `visual_acceptance_criteria` (detailed) |
| What states to handle | — | `required_states` (full catalog) |
| Which breakpoints | — | `required_breakpoints` (per-component) |
| What tokens to use | — | `approved_tokens` |
| What evidence to provide | `acceptance_criteria.evidence` (summary) | `required_visual_evidence` (detailed) |
| What files to touch | `allowed_files` | — |
| Risk and gates | `risk_level`, `required_checks` | `design_review_gates` |
| Approval authority | Amjad (contract approval) | Design owner (visual approval) |

### Rule: No UI Contract Without Task Contract

Every UI Contract must reference a valid, approved Task Contract. A UI Contract may NOT authorize work beyond the parent Task Contract's scope.

### Rule: R1 Visual-Only Tasks

For `VISUAL_ONLY` tasks (R1), the UI Contract effectively defines the primary scope. The Task Contract exists to bound the code changes; the UI Contract defines the visual target.

---

## 3. Design-Review Hierarchy

```
AMJAD (final visual authority)
  │
  ├── DESIGN_DEPARTMENT (when delegated)
  │     Can pre-approve visual assets before Amjad review
  │
  └── HERMES (visual QA gatekeeper)
        Validates token compliance, state coverage, breakpoint evidence
        Does NOT approve aesthetics — only checks contract compliance
```

- **Amjad** always has final visual sign-off on production-facing UI.
- **Design Department** (when established) can pre-approve for Amjad.
- **Hermes** validates compliance with the UI Contract but does not judge aesthetic quality.
- **Builders** must follow the UI Contract exactly; they may not interpret or deviate from visual specs.

---

## 4. Examples

### Example 1: R1 Visual-Only — Login Page Polish

```yaml
ui_contract_id: UI-AVOA-0003
task_contract_id: TASK-AVOA-0101
title: "Login page visual polish — spacing and typography"
status: DRAFT

design_owner: AMJAD
design_reference: "docs/design/approved/login.html"
design_system_version: avoa-design-system-v3.1

required_states:
  - state: DEFAULT
    description: "Login form as rendered on page load"
    screenshot_required: true
  - state: HOVER
    description: "Submit button hover state with navy-700 background"
    screenshot_required: true
  - state: FOCUS
    description: "Input focus ring (teal-400, 2px)"
    screenshot_required: true
  - state: VALIDATION_ERROR
    description: "Inline error below email field (coral-600)"
    screenshot_required: true

required_breakpoints:
  - width: 320
    label: "Mobile S"
    orientation: PORTRAIT
    required: true
  - width: 768
    label: "Tablet"
    orientation: PORTRAIT
    required: true
  - width: 1024
    label: "Desktop S"
    orientation: LANDSCAPE
    required: true

approved_tokens:
  colors:
    source: "src/styles/avoa-tokens.css"
    palette: ["navy", "teal", "gold", "coral", "cream"]
  typography:
    source: "src/styles/avoa-tokens.css"
    scale: ["text-sm", "text-base", "text-lg", "text-xl", "text-2xl"]
    families: ["Inter", "system-ui"]
  spacing:
    source: "src/styles/avoa-tokens.css"
    scale: [4, 8, 12, 16, 20, 24, 32, 40, 48]
  breakpoints:
    source: "tailwind.config.ts"
    values: ["sm", "md", "lg", "xl"]
  border_radius:
    scale: ["none", "sm", "md", "lg"]
  shadows:
    scale: ["none", "sm", "md"]

component_requirements:
  - component: "LoginForm"
    states: ["DEFAULT", "HOVER", "FOCUS", "VALIDATION_ERROR"]
    breakpoints: [320, 768, 1024]
    accessibility:
      wcag_level: AA
      keyboard: true
      screenreader: true
    animation:
      allowed: true
      max_duration_ms: 200
      spec: "ease-in-out transitions for hover/focus states"

visual_acceptance_criteria:
  layout:
    - "Form centered vertically and horizontally on viewport"
    - "Single-column layout at all breakpoints"
  alignment:
    - "Logo centered above form with 32px gap"
    - "Input labels left-aligned with 8px gap to input"
    - "Submit button full-width matching input width"
  color:
    - "Background: cream-50"
    - "Form card: white with navy-100 border"
    - "Input borders: navy-300 (default), teal-400 (focus), coral-500 (error)"
    - "Submit button: navy-600 background, white text, navy-700 hover"
    - "Error text: coral-600 on cream-50"
  typography:
    - "Logo text: text-2xl, font-bold, navy-900"
    - "Labels: text-sm, font-medium, navy-700"
    - "Input text: text-base, navy-900"
    - "Error text: text-sm, coral-600"
  spacing:
    - "24px padding inside form card"
    - "16px gap between form fields"
    - "24px gap between last field and submit button"
  responsive:
    - "Form card max-width: 400px at all breakpoints"
    - "Horizontal padding: 16px at mobile, 32px at tablet+"

required_visual_evidence:
  screenshot_evidence: true
  screenshot_count_min: 12
  comparison_evidence: true
  video_evidence: false
  video_duration_max_seconds: null
  browser_testing:
    required: false
    browsers: []

design_review_gates:
  gates:
    - gate: token_compliance
      required: true
      reviewer: HERMES
      description: "All colors, fonts, spacing use approved tokens"
    - gate: layout_accuracy
      required: true
      reviewer: AMJAD
      description: "Layout matches approved login.html reference"
    - gate: responsive_accuracy
      required: true
      reviewer: HERMES
      description: "No layout breakage at 320px, 768px, 1024px"
    - gate: state_completeness
      required: true
      reviewer: HERMES
      description: "All 4 states evidenced with screenshots"

forbidden_patterns:
  - pattern: "Hardcoded color hex values outside approved tokens"
    reason: "Must use CSS custom properties from avoa-tokens.css"
  - pattern: "Font-size declarations outside approved scale"
    reason: "Must use type scale tokens"
  - pattern: "Fixed pixel widths on text containers"
    reason: "Must support responsive text flow"

evidence_record:
  screenshots: []
  videos: []
  comparison_images: []
  browser_results: {}
  visual_regression_results: null

approvals: []
```

### Example 2: R2 Feature — Occupancy Widget

```yaml
ui_contract_id: UI-AVOA-0005
task_contract_id: TASK-AVOA-0201
title: "Occupancy status dashboard widget"
status: DRAFT

design_owner: AMJAD
design_reference: "docs/design/approved/cockpit.html#occupancy-widget"
design_system_version: avoa-design-system-v3.1

required_states:
  - state: LOADING
    description: "Skeleton/shimmer placeholder while data loads"
    screenshot_required: true
  - state: AVAILABLE
    description: "Green badge with occupancy percentage and rooms count"
    screenshot_required: true
  - state: LIMITED
    description: "Amber badge with urgency indicator"
    screenshot_required: true
  - state: SOLD_OUT
    description: "Red badge with 'contact us' message"
    screenshot_required: true
  - state: ERROR
    description: "Error message with retry button"
    screenshot_required: true
  - state: EMPTY
    description: "No occupancy data available state"
    screenshot_required: true

required_breakpoints:
  - width: 375
    label: "Mobile M"
    orientation: PORTRAIT
    required: true
  - width: 768
    label: "Tablet"
    orientation: PORTRAIT
    required: true
  - width: 1280
    label: "Desktop M"
    orientation: LANDSCAPE
    required: true

approved_tokens:
  colors:
    source: "src/styles/avoa-tokens.css"
    palette: ["navy", "teal", "gold", "coral", "cream"]
  typography:
    source: "src/styles/avoa-tokens.css"
    scale: ["text-xs", "text-sm", "text-base", "text-lg", "text-xl"]
    families: ["Inter", "system-ui"]
  spacing:
    source: "src/styles/avoa-tokens.css"
    scale: [4, 8, 12, 16, 20, 24, 32]
  breakpoints:
    source: "tailwind.config.ts"
    values: ["sm", "md", "lg", "xl"]
  border_radius:
    scale: ["sm", "md", "lg"]
  shadows:
    scale: ["sm", "md"]

component_requirements:
  - component: "OccupancyWidget"
    states: ["LOADING", "AVAILABLE", "LIMITED", "SOLD_OUT", "ERROR", "EMPTY"]
    breakpoints: [375, 768, 1280]
    accessibility:
      wcag_level: AA
      keyboard: true
      screenreader: true
    animation:
      allowed: true
      max_duration_ms: 300
      spec: "Fade transition between states; smooth badge color transition"

visual_acceptance_criteria:
  layout:
    - "Card component with header, body, and footer sections"
    - "Status badge positioned top-right"
    - "Fills available grid column width"
  alignment:
    - "Widget title left-aligned in header"
    - "Percentage value centered in body"
    - "Rooms count centered below percentage"
  color:
    - "AVAILABLE: green-500 badge"
    - "LIMITED: amber-500 badge with amber-100 background pulse"
    - "SOLD_OUT: coral-600 badge"
    - "Card background: white with navy-50 border"
  typography:
    - "Title: text-base, font-semibold, navy-900"
    - "Percentage: text-3xl, font-bold, navy-900"
    - "Rooms count: text-sm, navy-600"
    - "Badge text: text-xs, font-medium"
  spacing:
    - "16px card padding"
    - "12px gap between header and body"
    - "8px gap between percentage and rooms count"
  responsive:
    - "Full width at mobile"
    - "Half width at tablet (2-column grid)"
    - "Quarter width at desktop (4-column grid)"

required_visual_evidence:
  screenshot_evidence: true
  screenshot_count_min: 18
  comparison_evidence: false
  video_evidence: false
  video_duration_max_seconds: null
  browser_testing:
    required: true
    browsers: ["Chrome", "Safari"]

design_review_gates:
  gates:
    - gate: token_compliance
      required: true
      reviewer: HERMES
      description: "All visual tokens match approved design system"
    - gate: state_completeness
      required: true
      reviewer: HERMES
      description: "All 6 states evidenced at each breakpoint"
    - gate: responsive_accuracy
      required: true
      reviewer: HERMES
      description: "Grid layout adapts correctly at all breakpoints"
    - gate: visual_regression
      required: true
      reviewer: HERMES
      description: "No visual regressions against baseline dashboard"

forbidden_patterns:
  - pattern: "Hardcoded status colors outside approved palette"
    reason: "Status colors must use approved token values"
  - pattern: "Text truncation with ellipsis on critical numbers"
    reason: "Occupancy percentage must always be fully visible"
  - pattern: "Auto-refresh without visual indicator"
    reason: "Users must know when data updates"

evidence_record:
  screenshots: []
  videos: []
  comparison_images: []
  browser_results: {}
  visual_regression_results: null

approvals: []
```

### Example 3: R2 Feature — Quote Request Form

```yaml
ui_contract_id: UI-AVOA-0006
task_contract_id: TASK-AVOA-0202
title: "Quote request form"
status: DRAFT

design_owner: AMJAD
design_reference: "docs/design/approved/request-form.html"
design_system_version: avoa-design-system-v3.1

required_states:
  - state: DEFAULT
    description: "Empty form ready for input"
    screenshot_required: true
  - state: FOCUS
    description: "Active field with focus ring"
    screenshot_required: true
  - state: VALIDATION_ERROR
    description: "Inline field errors displayed"
    screenshot_required: true
  - state: SUBMITTING
    description: "Form disabled with loading spinner on button"
    screenshot_required: true
  - state: SUCCESS
    description: "Confirmation message with reference number"
    screenshot_required: true
  - state: ERROR
    description: "Server error with retry option"
    screenshot_required: true

required_breakpoints:
  - width: 375
    label: "Mobile M"
    orientation: PORTRAIT
    required: true
  - width: 768
    label: "Tablet"
    orientation: PORTRAIT
    required: true
  - width: 1024
    label: "Desktop S"
    orientation: LANDSCAPE
    required: true

approved_tokens:
  colors:
    source: "src/styles/avoa-tokens.css"
    palette: ["navy", "teal", "gold", "coral", "cream"]
  typography:
    source: "src/styles/avoa-tokens.css"
    scale: ["text-xs", "text-sm", "text-base", "text-lg", "text-xl", "text-2xl"]
    families: ["Inter", "system-ui"]
  spacing:
    source: "src/styles/avoa-tokens.css"
    scale: [4, 8, 12, 16, 20, 24, 32, 40, 48]
  breakpoints:
    source: "tailwind.config.ts"
    values: ["sm", "md", "lg", "xl"]
  border_radius:
    scale: ["sm", "md", "lg"]
  shadows:
    scale: ["sm", "md", "lg"]

component_requirements:
  - component: "QuoteRequestForm"
    states: ["DEFAULT", "FOCUS", "VALIDATION_ERROR", "SUBMITTING", "SUCCESS", "ERROR"]
    breakpoints: [375, 768, 1024]
    accessibility:
      wcag_level: AA
      keyboard: true
      screenreader: true
    animation:
      allowed: true
      max_duration_ms: 300
      spec: "Smooth error message appear/disappear; button loading spinner fade in"

visual_acceptance_criteria:
  layout:
    - "Two-column layout at tablet+: name/email left, dates/guests right"
    - "Single-column stacked at mobile"
    - "Submit button full-width below fields"
  alignment:
    - "Labels above inputs with 4px gap"
    - "Error messages below inputs with 4px gap"
    - "Confirmation message centered"
  color:
    - "Form background: cream-50 with 1px navy-200 border"
    - "Valid input border: navy-300"
    - "Error input border: coral-500"
    - "Success banner: teal-100 background, teal-800 text"
    - "Error banner: coral-100 background, coral-800 text"
  typography:
    - "Title: text-2xl, font-bold, navy-900"
    - "Labels: text-sm, font-medium, navy-700"
    - "Input text: text-base, navy-900"
    - "Error text: text-sm, coral-600"
    - "Confirmation: text-base, teal-800"
  spacing:
    - "32px padding inside form container"
    - "20px gap between form sections"
    - "16px gap between fields"
    - "24px gap between last field and submit button"
  responsive:
    - "Form container max-width: 720px, centered"
    - "Full-width inputs at mobile; two-column grid at tablet+"

required_visual_evidence:
  screenshot_evidence: true
  screenshot_count_min: 18
  comparison_evidence: true
  video_evidence: false
  video_duration_max_seconds: null
  browser_testing:
    required: true
    browsers: ["Chrome", "Firefox", "Safari"]

design_review_gates:
  gates:
    - gate: token_compliance
      required: true
      reviewer: HERMES
      description: "All tokens match approved design system"
    - gate: state_completeness
      required: true
      reviewer: HERMES
      description: "All 6 states evidenced"
    - gate: layout_accuracy
      required: true
      reviewer: AMJAD
      description: "Layout matches approved request-form.html"
    - gate: accessibility_check
      required: true
      reviewer: HERMES
      description: "Labels, keyboard nav, screen-reader announcements verified"

forbidden_patterns:
  - pattern: "Placeholder text as the only label"
    reason: "Must have visible <label> elements for accessibility"
  - pattern: "Client-side validation as sole validation"
    reason: "Server-side errors must be displayed in the same error pattern"
  - pattern: "Form reset on error"
    reason: "User input must be preserved on validation failure"

evidence_record:
  screenshots: []
  videos: []
  comparison_images: []
  browser_results: {}
  visual_regression_results: null

approvals: []
```

### Example 4: Dashboard v2 — Multi-Component Page

```yaml
ui_contract_id: UI-AVOA-0010
task_contract_id: TASK-AVOA-0500
title: "Dashboard v2 — multi-component page redesign"
status: DRAFT

design_owner: AMJAD
design_reference: "docs/design/approved/cockpit.html"
design_system_version: avoa-design-system-v3.1

required_states:
  - state: DEFAULT
    description: "Full dashboard with all widgets loaded"
    screenshot_required: true
  - state: LOADING
    description: "Skeleton placeholders for each widget during initial load"
    screenshot_required: true
  - state: PARTIAL_DATA
    description: "Some widgets loaded, others still loading"
    screenshot_required: true
  - state: EMPTY
    description: "Dashboard with no data (first-time user)"
    screenshot_required: true
  - state: ERROR
    description: "Global error state with retry"
    screenshot_required: true

required_breakpoints:
  - width: 375
    label: "Mobile M"
    orientation: PORTRAIT
    required: true
  - width: 768
    label: "Tablet"
    orientation: PORTRAIT
    required: true
  - width: 1024
    label: "Desktop S"
    orientation: LANDSCAPE
    required: true
  - width: 1440
    label: "Desktop L"
    orientation: LANDSCAPE
    required: true

approved_tokens:
  colors:
    source: "src/styles/avoa-tokens.css"
    palette: ["navy", "teal", "gold", "coral", "cream"]
  typography:
    source: "src/styles/avoa-tokens.css"
    scale: ["text-xs", "text-sm", "text-base", "text-lg", "text-xl", "text-2xl", "text-3xl"]
    families: ["Inter", "system-ui"]
  spacing:
    source: "src/styles/avoa-tokens.css"
    scale: [4, 8, 12, 16, 20, 24, 32, 40, 48, 64]
  breakpoints:
    source: "tailwind.config.ts"
    values: ["sm", "md", "lg", "xl"]
  border_radius:
    scale: ["sm", "md", "lg"]
  shadows:
    scale: ["sm", "md", "lg", "xl"]

component_requirements:
  - component: "DashboardLayout"
    states: ["DEFAULT", "LOADING", "EMPTY", "ERROR"]
    breakpoints: [375, 768, 1024, 1440]
    accessibility:
      wcag_level: AA
      keyboard: true
      screenreader: true
    animation:
      allowed: true
      max_duration_ms: 300
      spec: "Grid reflow animation on breakpoint change"
  - component: "OccupancySummaryCard"
    states: ["DEFAULT", "LOADING", "ERROR"]
    breakpoints: [375, 768, 1024, 1440]
    accessibility:
      wcag_level: AA
      keyboard: true
      screenreader: true
    animation:
      allowed: true
      max_duration_ms: 200
      spec: null
  - component: "RevenueOverviewCard"
    states: ["DEFAULT", "LOADING", "ERROR"]
    breakpoints: [375, 768, 1024, 1440]
    accessibility:
      wcag_level: AA
      keyboard: true
      screenreader: true
    animation:
      allowed: false
      max_duration_ms: null
      spec: null
  - component: "RecentBookingsTable"
    states: ["DEFAULT", "LOADING", "EMPTY", "ERROR"]
    breakpoints: [375, 768, 1024, 1440]
    accessibility:
      wcag_level: AA
      keyboard: true
      screenreader: true
    animation:
      allowed: false
      max_duration_ms: null
      spec: null

visual_acceptance_criteria:
  layout:
    - "4-column grid at desktop L (1440px)"
    - "3-column grid at desktop S (1024px)"
    - "2-column grid at tablet (768px)"
    - "Single-column at mobile (375px)"
    - "OccupancySummaryCard: spans 1 column"
    - "RevenueOverviewCard: spans 1 column"
    - "RecentBookingsTable: spans full width below cards"
  alignment:
    - "Cards aligned to grid with consistent gutter (16px)"
    - "Table full-width below card row with 24px gap"
  color:
    - "Page background: cream-50"
    - "Cards: white background with 1px navy-100 border, md shadow"
    - "Navigation: navy-900 background, white text"
  typography:
    - "Page title: text-3xl, font-bold, navy-900"
    - "Card titles: text-lg, font-semibold, navy-800"
    - "Card body: text-base, navy-700"
    - "Table headers: text-sm, font-medium, navy-600"
  spacing:
    - "48px page padding on desktop"
    - "24px page padding on tablet"
    - "16px page padding on mobile"
    - "16px card padding"
    - "24px gap between card row and table"
  responsive:
    - "Sidebar collapses to bottom navigation bar below 768px"
    - "Table switches to card layout below 768px"

required_visual_evidence:
  screenshot_evidence: true
  screenshot_count_min: 20
  comparison_evidence: true
  video_evidence: false
  video_duration_max_seconds: null
  browser_testing:
    required: true
    browsers: ["Chrome", "Firefox", "Safari"]

design_review_gates:
  gates:
    - gate: token_compliance
      required: true
      reviewer: HERMES
      description: "All tokens drawn from approved set"
    - gate: layout_accuracy
      required: true
      reviewer: AMJAD
      description: "Dashboard matches approved cockpit.html reference"
    - gate: responsive_accuracy
      required: true
      reviewer: HERMES
      description: "Grid layout adapts correctly at all 4 breakpoints"
    - gate: state_completeness
      required: true
      reviewer: HERMES
      description: "All states evidenced for all components"
    - gate: visual_regression
      required: true
      reviewer: HERMES
      description: "No regression against v1 dashboard at matching breakpoints"
    - gate: accessibility_check
      required: true
      reviewer: HERMES
      description: "Full page passes WCAG AA checks"

forbidden_patterns:
  - pattern: "Hardcoded grid breakpoints in component code"
    reason: "Must use design system breakpoint tokens"
  - pattern: "Scrollable cards with internal overflow:hidden"
    reason: "Cards should grow to fit content"
  - pattern: "Text contrast below WCAG AA ratio"
    reason: "Minimum 4.5:1 for body text, 3:1 for large text"

evidence_record:
  screenshots: []
  videos: []
  comparison_images: []
  browser_results: {}
  visual_regression_results: null

approvals: []
```

### Example 5: R1 Visual-Only — Typography Scale Alignment

```yaml
ui_contract_id: UI-AVOA-0012
task_contract_id: TASK-AVOA-0103
title: "Global typography scale alignment"
status: DRAFT

design_owner: HERMES
design_reference: "src/styles/avoa-tokens.css#typography"
design_system_version: avoa-design-system-v3.1

required_states:
  - state: DEFAULT
    description: "Page rendered with updated typography"
    screenshot_required: true

required_breakpoints:
  - width: 375
    label: "Mobile M"
    orientation: PORTRAIT
    required: true
  - width: 1024
    label: "Desktop S"
    orientation: LANDSCAPE
    required: true

approved_tokens:
  colors:
    source: "src/styles/avoa-tokens.css"
    palette: ["navy", "teal", "gold", "coral", "cream"]
  typography:
    source: "src/styles/avoa-tokens.css"
    scale: ["text-xs", "text-sm", "text-base", "text-lg", "text-xl", "text-2xl", "text-3xl"]
    families: ["Inter", "system-ui"]
  spacing:
    source: "src/styles/avoa-tokens.css"
    scale: [4, 8, 12, 16, 20, 24, 32, 40, 48, 64]
  breakpoints:
    source: "tailwind.config.ts"
    values: ["sm", "md", "lg", "xl"]
  border_radius:
    scale: ["sm", "md", "lg"]
  shadows:
    scale: ["sm", "md"]

component_requirements: []

visual_acceptance_criteria:
  layout:
    - "No layout shifts from typography changes"
  alignment:
    - "Text alignment preserved throughout"
  color:
    - "Text colors must remain within navy-500 to navy-900 range"
  typography:
    - "All body text: text-base (16px)"
    - "All labels: text-sm (14px)"
    - "All section headings: text-lg (18px)"
    - "All page titles: text-2xl (24px)"
    - "Line-height: 1.5 for body, 1.25 for headings"
    - "Letter-spacing: -0.01em for headings"
  spacing:
    - "No spacing changes — typography only"
  responsive:
    - "Text scales proportionally at all breakpoints"

required_visual_evidence:
  screenshot_evidence: true
  screenshot_count_min: 6
  comparison_evidence: true
  video_evidence: false
  video_duration_max_seconds: null
  browser_testing:
    required: false
    browsers: []

design_review_gates:
  gates:
    - gate: token_compliance
      required: true
      reviewer: HERMES
      description: "Only approved type scale tokens used"
    - gate: visual_regression
      required: true
      reviewer: HERMES
      description: "No text clipping, overflow, or spacing regressions"
    - gate: layout_accuracy
      required: true
      reviewer: AMJAD
      description: "Overall visual harmony with updated typography"

forbidden_patterns:
  - pattern: "Arbitrary font-size values outside approved scale"
    reason: "Must use token scale only"
  - pattern: "Multiple font families in single component"
    reason: "Consistency: Inter only except for system-ui fallback"

evidence_record:
  screenshots: []
  videos: []
  comparison_images: []
  browser_results: {}
  visual_regression_results: null

approvals: []
```

### Example 6: R1 Visual-Only — Color Token Migration

```yaml
ui_contract_id: UI-AVOA-0015
task_contract_id: TASK-AVOA-0104
title: "Migrate hardcoded colors to design tokens"
status: DRAFT

design_owner: HERMES
design_reference: "src/styles/avoa-tokens.css"
design_system_version: avoa-design-system-v3.1

required_states:
  - state: DEFAULT
    description: "All pages rendered with token-based colors"
    screenshot_required: true

required_breakpoints:
  - width: 375
    label: "Mobile M"
    orientation: PORTRAIT
    required: true
  - width: 768
    label: "Tablet"
    orientation: PORTRAIT
    required: true
  - width: 1024
    label: "Desktop S"
    orientation: LANDSCAPE
    required: true

approved_tokens:
  colors:
    source: "src/styles/avoa-tokens.css"
    palette: ["navy", "teal", "gold", "coral", "cream"]
  typography:
    source: "src/styles/avoa-tokens.css"
    scale: ["text-xs", "text-sm", "text-base", "text-lg", "text-xl", "text-2xl"]
    families: ["Inter", "system-ui"]
  spacing:
    source: "src/styles/avoa-tokens.css"
    scale: [4, 8, 12, 16, 20, 24, 32]
  breakpoints:
    source: "tailwind.config.ts"
    values: ["sm", "md", "lg", "xl"]
  border_radius:
    scale: ["sm", "md", "lg"]
  shadows:
    scale: ["sm", "md"]

component_requirements: []

visual_acceptance_criteria:
  layout:
    - "No layout changes — color-only migration"
  alignment:
    - "No alignment changes"
  color:
    - "All hex/rgb values replaced with CSS custom properties from avoa-tokens.css"
    - "No hardcoded colors remain in any TSX/CSS file"
    - "Visual output must be pixel-identical to baseline"
  typography:
    - "No typography changes"
  spacing:
    - "No spacing changes"
  responsive:
    - "Color rendering must be identical at all breakpoints"

required_visual_evidence:
  screenshot_evidence: true
  screenshot_count_min: 15
  comparison_evidence: true
  video_evidence: false
  video_duration_max_seconds: null
  browser_testing:
    required: true
    browsers: ["Chrome", "Safari"]

design_review_gates:
  gates:
    - gate: token_compliance
      required: true
      reviewer: HERMES
      description: "No hardcoded colors remain; grep for hex/rgb confirms zero matches"
    - gate: visual_regression
      required: true
      reviewer: HERMES
      description: "Pixel-identical comparison against baseline screenshots"
    - gate: layout_accuracy
      required: true
      reviewer: AMJAD
      description: "No visual difference from baseline"

forbidden_patterns:
  - pattern: "Any hex color (#xxx or #xxxxxx) in component files"
    reason: "All colors must be CSS custom properties"
  - pattern: "Any rgb/rgba/hsl/hsla in component files"
    reason: "All colors must be CSS custom properties"
  - pattern: "Tailwind arbitrary color values (e.g. bg-[#123456])"
    reason: "Must use design token classes only"

evidence_record:
  screenshots: []
  videos: []
  comparison_images: []
  browser_results: {}
  visual_regression_results: null

approvals: []
```

---

## 5. UI Contract Lifecycle

```
CREATED → VALIDATED → APPROVED → ACTIVE → EVIDENCED → COMPLETED
```

1. **CREATED** — Hermes drafts UI Contract alongside Task Contract when visual work is detected
2. **VALIDATED** — Hermes validates against schema, checks token consistency, confirms breakpoints match design system
3. **APPROVED** — Design owner (Amjad or delegated) approves visual criteria
4. **ACTIVE** — Builder begins implementation; UI Contract is active constraint
5. **EVIDENCED** — Builder submits screenshots and visual evidence; Hermes validates against contract
6. **COMPLETED** — All gates pass; visual evidence archived

---

## 6. Relationship to Other Documents

| Document | Relationship |
|---|---|
| 04_TASK_CONTRACT_STANDARD | Parent contract; UI Contract is companion document |
| 06_TASK_LIFECYCLE | UI Contract lifecycle maps to task lifecycle states |
| 07_RISK_CLASSIFICATION | Risk level determines review gate stringency |
| 08_PROTECTED_ZONES | Design token files may be in protected zones |
| 12_AVOA_DESIGN_SYSTEM_PLAN | Source of approved tokens, breakpoints, and component specs |
| 13_DESIGN_REVIEW_AND_VISUAL_QA | Review protocol for visual evidence validation |
| 18_EVIDENCE_AND_COMPLETION | Evidence requirements flow into completion criteria |

---

*Document 05 of 26. See 00_HERMES_OS_V3_1_INDEX.md for the full package.*