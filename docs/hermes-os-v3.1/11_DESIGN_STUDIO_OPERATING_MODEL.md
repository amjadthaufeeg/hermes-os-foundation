# 11 — Design Studio Operating Model

**Status:** SPECIFICATION (not yet implemented)
**Version:** 3.1
**Date:** 31 July 2026
**Part of:** Hermes Engineering OS v3.1
**Depends on:** 05_UI_CONTRACT_STANDARD, 04_TASK_CONTRACT_STANDARD, 07_RISK_CLASSIFICATION
**Feeds into:** 12_AVOA_DESIGN_SYSTEM_PLAN, 13_DESIGN_REVIEW_AND_VISUAL_QA

---

## 1. Purpose

This document defines the Design Studio — a specialized subsystem within Hermes Engineering OS for visual and interaction design tasks. It establishes five design roles, their responsibilities, the standard design workflow, a shortened R1-only path, boundaries with the Engineering workflow, and the protocol for submitting design findings to Hermes.

---

## 2. Design Studio Architecture

### 2.1 Position Within Hermes OS

```
                              HERMES
                   Sole Orchestrator
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
   Engineering        Design Studio     Command Center
   Workflow           (this doc)        (Doc 21-23)
         │                 │
         │    ┌────────────┼────────────┐
         │    │            │            │
         │    ▼            ▼            ▼
         │  UX Arch    Visual Des   Interaction Des
         │    │            │            │
         │    └────────────┼────────────┘
         │                 │
         │                 ▼
         │          UI Implementation
         │                 │
         │                 ▼
         │           Visual QA
         │                 │
         └─────────┬───────┘
                   ▼
              Hermes Triage
```

### 2.2 Design Studio vs. Engineering

| Dimension | Design Studio | Engineering |
|---|---|---|
| Primary concern | Visual quality, usability, consistency | Functional correctness, architecture, performance |
| Output | Design specs, prototypes, visual QA reports | Code, tests, builds, deployments |
| Risk range | R1 (presentation) to R2 (interaction) | R1 through R5 |
| Agent specialization | UX, visual, interaction design | Implementation, review, precision repair |
| Key contract | UI Contract (Doc 05) | Task Contract (Doc 04) |
| Evidence | Screenshots, prototypes, design tokens | Diffs, test results, build logs |
| Gate | Visual approval (Amjad) | Automated gates + Claude review |

### 2.3 Boundaries

Design Studio must not:

- Modify business logic, APIs, database schemas, or infrastructure
- Change authentication, permissions, or security rules
- Alter navigation structure without explicit Amjad approval
- Deploy to production independently
- Override engineering decisions about implementation approach

Engineering must not:

- Override approved design tokens, spacing, or typography
- Change visual layout without a UI contract
- Skip visual QA for presentation-layer changes
- Merge UI changes without design review for R1+ tasks

---

## 3. Five Design Roles

### 3.1 Role Overview

| # | Role | Responsibility | Agent Assignment | Write Access |
|---|---|---|---|---|
| 1 | UX Architect | Information architecture, user flows, component hierarchy | Hermes or designated UX agent | Design docs only |
| 2 | Visual Designer | Color, typography, spacing, design tokens, visual language | Design-capable agent (Kimi/Claude) | Design tokens, style files |
| 3 | Interaction Designer | Micro-interactions, animations, state transitions, responsive behavior | Design-capable agent | Interaction specs only |
| 4 | UI Implementation Agent | Translate design specs into code | Kimi K3 (primary) or Codex | UI component files only |
| 5 | Visual QA Agent | Capture screenshots, verify visual fidelity, detect regressions | Visual QA pilot agent | Read-only |

### 3.2 UX Architect

**Responsibilities:**

- Audit existing information architecture
- Define or refine user flows for the task
- Establish component hierarchy and page structure
- Identify reusable vs. one-off components
- Document layout constraints (breakpoints, content priority)
- Produce UX specification document

**Deliverables:**

```yaml
ux_spec:
  task_id: "TASK-0042"
  component_tree: [...]
  user_flows: [...]
  layout_grid: "12-column, 1440px max-width"
  breakpoints: [desktop, tablet, mobile]
  content_priority: [primary_action, key_metrics, supporting_data]
  reusable_components: ["QuoteCard", "StatusBadge"]
  new_components: ["QuoteReviewHeader"]
```

**Boundary:** UX Architect defines structure and flow, not visual style. Colors, typography, and spacing belong to the Visual Designer.

### 3.3 Visual Designer

**Responsibilities:**

- Select or define color palette from design system
- Establish typography scale and hierarchy
- Define spacing grid (padding, margin, gap)
- Specify border radius, shadows, elevation
- Produce or reference design tokens
- Create visual mockups or references

**Deliverables:**

```yaml
visual_spec:
  task_id: "TASK-0042"
  color_tokens:
    primary: "var(--color-primary-600)"
    surface: "var(--color-surface-50)"
    text_primary: "var(--color-neutral-900)"
  typography:
    heading_lg: "text-2xl font-semibold tracking-tight"
    body: "text-base font-normal leading-relaxed"
  spacing:
    section_padding: "py-8 px-6"
    card_gap: "gap-4"
  radius: "rounded-xl"
  shadow: "shadow-sm"
  mockup_reference: "designs/quote-review-header-v2.fig"  # or URL
```

**Boundary:** Visual Designer defines tokens and style, not implementation. Code generation belongs to the UI Implementation Agent.

### 3.4 Interaction Designer

**Responsibilities:**

- Define hover, focus, active, disabled states
- Specify transitions and animations
- Define loading, empty, error states
- Document responsive behavior changes
- Specify keyboard and accessibility interactions

**Deliverables:**

```yaml
interaction_spec:
  task_id: "TASK-0042"
  states:
    - name: "default"
      description: "Header displays quote ID, status badge, action buttons"
    - name: "loading"
      description: "Skeleton placeholder for status badge; buttons disabled"
    - name: "empty"
      description: "N/A for header component"
    - name: "error"
      description: "Status badge shows error icon; retry button appears"
  animations:
    - element: "status_badge"
      trigger: "status_change"
      animation: "fade + scale, 200ms ease-out"
  transitions:
    - element: "action_buttons"
      trigger: "hover"
      animation: "background-color 150ms ease"
  responsive:
    mobile: "Header stacks vertically; actions collapse to overflow menu"
    tablet: "Header side-by-side; actions inline"
    desktop: "Full layout with expanded metadata"
  accessibility:
    focus_order: "status → title → primary action → secondary actions"
    aria_labels: ["Status: {status}", "Quote reference: {id}"]
```

**Boundary:** Interaction Designer defines behavior, not visual appearance. The visual style of states is owned by the Visual Designer.

### 3.5 UI Implementation Agent

**Responsibilities:**

- Translate UX, visual, and interaction specs into code
- Implement components with correct design tokens
- Ensure responsive behavior matches spec
- Write or update component tests
- Produce implementation evidence

**Deliverables:**

- Working component code in assigned files
- Component test updates
- Screenshots at required breakpoints
- Builder report

**Constraints:**

- Must not deviate from design specs without Hermes approval
- Must not change business logic while implementing UI
- Must respect file ownership and change budgets
- Must implement all specified states (loading, empty, error, etc.)

### 3.6 Visual QA Agent

**Responsibilities:**

- Capture screenshots at all required breakpoints
- Compare implementation against design specs
- Detect visual regressions (pixel-level comparison where applicable)
- Verify design token usage in code
- Report findings to Hermes (not to the builder)

**Deliverables:**

```yaml
visual_qa_report:
  task_id: "TASK-0042"
  screenshots:
    desktop: ["header-default.png", "header-loading.png", "header-error.png"]
    tablet: ["header-default-tablet.png"]
    mobile: ["header-default-mobile.png", "header-actions-expanded.png"]
  findings:
    - severity: "MEDIUM"
      element: "status_badge"
      issue: "Badge color deviates from token --color-status-active"
      expected: "#16a34a (green-600)"
      actual: "#22c55e (green-500)"
      screenshot: "status-badge-comparison.png"
  token_compliance:
    passed: 24
    failed: 1
    unchecked: 0
  verdict: "CONDITIONAL_PASS"  # PASS | CONDITIONAL_PASS | FAIL
```

**Boundary:** Visual QA Agent is **review-only**. It must not modify code, even for trivial fixes. All findings flow to Hermes, who triages and routes approved corrections to the UI Implementation Agent.

---

## 4. Standard Design Workflow

### 4.1 Full Flow

```
DESIGN_REQUESTED
        │
        ▼
  Hermes creates UI Contract (Doc 05)
        │
        ▼
  UX Architect → UX Specification
        │
        ▼
  Visual Designer → Visual Specification
        │
        ▼
  Interaction Designer → Interaction Specification
        │
        ▼
  Hermes reviews and approves design specs
        │
        ▼
  UI Implementation Agent → Code + evidence
        │
        ▼
  Visual QA Agent → Screenshots + findings report
        │
        ▼
  Hermes triages findings
        │
   ┌────┴────┐
   ▼         ▼
PASS      FINDINGS
   │         │
   │         ▼
   │    UI Impl Agent → Corrections
   │         │
   │         ▼
   │    Visual QA Agent → Re-check
   │         │
   └────┬────┘
        ▼
  Hermes readiness assessment
        │
        ▼
  Amjad visual approval
        │
        ▼
  DESIGN_APPROVED → Engineering merge
```

### 4.2 Step Details

**Step 1 — UI Contract Creation:**
Hermes creates a UI Contract documenting the objective, visual scope, constraints, and acceptance criteria. The contract must explicitly state: "This is a presentation-layer change. Do not modify business logic, workflow, APIs, or data model."

**Step 2 — UX Architecture:**
UX Architect audits the existing component tree, user flows, and layout. Produces a structured UX spec. If the task is a modification of existing UI, the UX Architect documents what changes and what stays.

**Step 3 — Visual Design:**
Visual Designer translates the UX spec into concrete visual attributes. All values must reference design system tokens where they exist. New tokens must be proposed through the design system plan (Doc 12).

**Step 4 — Interaction Design:**
Interaction Designer defines state transitions, animations, and responsive behavior. Must document all states: default, hover, focus, active, disabled, loading, empty, error.

**Step 5 — Hermes Design Review:**
Hermes reviews the combined design specs against the UI Contract. Hermes checks for:
- Alignment with existing design system
- Complete state coverage
- Responsive breakpoint coverage
- Accessibility requirements (WCAG AA minimum)
- No scope creep into non-visual areas

**Step 6 — UI Implementation:**
UI Implementation Agent receives the approved design specs and implements them in code. The agent must reference design tokens, not hardcoded values. Implementation evidence includes screenshots, test results, and a builder report.

**Step 7 — Visual QA:**
Visual QA Agent captures screenshots at all specified breakpoints and states. Compares against design specs. Produces a structured findings report.

**Step 8 — Hermes Triage:**
Hermes reviews Visual QA findings and decides: accept, reject, or defer each finding. Only accepted findings become correction tasks for the UI Implementation Agent.

**Step 9 — Amjad Approval:**
Hermes presents final screenshots and the Visual QA report to Amjad for visual acceptance. Amjad may approve, request changes, or reject.

---

## 5. Shortened R1 Path

### 5.1 When to Use

The shortened path applies when:

- Risk level is R1 (presentation-only)
- The change is limited to a single component or small component group
- No new interaction patterns are introduced
- The design system already covers all needed tokens
- Amjad has pre-approved the visual direction

### 5.2 Shortened Flow

```
DESIGN_REQUESTED (R1, pre-approved direction)
        │
        ▼
  Hermes creates UI Contract
        │
        ▼
  Visual Designer → Quick visual spec (skip UX + Interaction)
        │
        ▼
  UI Implementation Agent → Code + screenshots
        │
        ▼
  Visual QA Agent → Screenshots + findings
        │
        ▼
  Hermes triage → Amjad approval
```

### 5.3 Shortened Path Rules

- UX Architect and Interaction Designer roles are skipped
- Visual Designer produces a lightweight spec (no full UX audit)
- UI Implementation Agent handles basic interaction states implicitly
- The shortened path is a **convenience**, not a loophole — scope and quality standards are unchanged
- If the UI Implementation Agent discovers the task is more complex than anticipated, it must stop and request full workflow

---

## 6. Findings Submission Protocol

### 6.1 All Findings Flow to Hermes

Design Studio agents submit findings to Hermes using the following schema:

```yaml
finding_id: "DS-0042-001"
task_id: "TASK-0042"
role: "visual-qa"  # ux-architect | visual-designer | interaction-designer | visual-qa
severity: "MEDIUM"  # BLOCKER | HIGH | MEDIUM | LOW | OPTIONAL
category: "color-token"  # spacing | typography | animation | responsive | accessibility | state-missing
element: "status_badge"
description: "Status badge uses color green-500 instead of design token --color-status-active (green-600)"
expected: "#16a34a"
actual: "#22c55e"
evidence: "screenshots/status-badge-diff.png"
recommendation: "Replace hardcoded color with var(--color-status-active)"
```

### 6.2 Finding Severity in Design Context

| Severity | Definition | Example |
|---|---|---|
| BLOCKER | Visual outcome contradicts approved spec; cannot proceed | Wrong component entirely; missing critical state |
| HIGH | Significant deviation from design system; visually obvious | Wrong color token; broken layout at standard breakpoint |
| MEDIUM | Noticeable inconsistency; degrades visual quality | Spacing off by 4px+; font weight mismatch |
| LOW | Minor polish issue; barely noticeable | 1px alignment; subtle shadow difference |
| OPTIONAL | Suggestion for improvement; spec-compliant but could be better | Alternative animation curve; optional micro-interaction |

### 6.3 Hermes Triage

For each finding, Hermes records:

```yaml
finding_id: "DS-0042-001"
decision: "accepted"  # accepted | rejected | deferred
reason: "Color token compliance is mandatory per design system"
approved_correction: "Replace green-500 with var(--color-status-active)"
routed_to: "kimi-k3"  # which agent performs the correction
```

---

## 7. Role Assignment Rules

### 7.1 Default Assignments

| Role | Default Agent | Alternative |
|---|---|---|
| UX Architect | Hermes (orchestrator analysis) | Claude Code (read-only analysis) |
| Visual Designer | Kimi K3 | Claude Code |
| Interaction Designer | Kimi K3 | Claude Code |
| UI Implementation Agent | Kimi K3 | Codex (precision work) |
| Visual QA Agent | Visual QA pilot agent | Claude Code (review capability) |

### 7.2 Combined Roles

For small tasks, Hermes may combine roles:

| Combination | When Allowed |
|---|---|
| Visual Designer + Interaction Designer | R1 tasks with simple interactions |
| UX Architect + Visual Designer | Greenfield component with no existing patterns |
| Visual QA Agent only | Pre-approved visual change needing only verification |

UX Architect must never be combined with UI Implementation Agent (designer reviewing their own implementation).

---

## 8. Design-to-Engineering Handoff

### 8.1 When Design Studio Hands Off

The Design Studio workflow completes when:

1. Amjad approves the visual outcome
2. All accepted findings are resolved
3. Visual QA returns `PASS` or `CONDITIONAL_PASS` with all conditions accepted by Hermes
4. Task state transitions to `DESIGN_APPROVED`

### 8.2 Handoff Package

Design Studio delivers to Engineering:

```yaml
handoff_package:
  task_id: "TASK-0042"
  design_approved: true
  ux_spec: "docs/design/TASK-0042-ux-spec.yaml"
  visual_spec: "docs/design/TASK-0042-visual-spec.yaml"
  interaction_spec: "docs/design/TASK-0042-interaction-spec.yaml"
  visual_qa_report: "docs/design/TASK-0042-visual-qa.yaml"
  amjad_approval: "2026-07-31T14:00:00Z"
  screenshots:
    desktop: ["final-desktop.png"]
    tablet: ["final-tablet.png"]
    mobile: ["final-mobile.png"]
  implementation_branch: "task/0042-quote-redesign"
  implementation_commit: "def5678"
```

### 8.3 Engineering Receives

Engineering (Claude Code review, automated gates) receives the design-approved implementation and validates:

- Code quality and architecture compliance
- Test coverage and correctness
- No regression in protected zones
- Build and type-check pass

Engineering must not re-litigate visual decisions already approved by Amjad through Design Studio.

---

## 9. Prohibited Actions

| Prohibition | Applies To |
|---|---|
| UI Implementation Agent skipping Visual QA | All R1+ tasks |
| Visual QA Agent modifying code directly | Visual QA Agent |
| Design agents changing business logic | All Design Studio roles |
| Skipping UX Architecture for new components | R2+ tasks with new UX patterns |
| Visual Designer using non-token values | All visual specs |
| Interaction Designer ignoring accessibility | All interaction specs |
| Designer reviewing their own implementation | Combined-role tasks |

---

## 10. Release Mapping

| Release | Design Studio Capability |
|---|---|
| HOS-1 | Manual design review (Claude Code) |
| HOS-2 | Design Studio operating model activated; UI Contracts |
| HOS-3 | Design tokens and specs stored as structured records |
| HOS-4 | Visual QA pilot agent available |
| HOS-5 | Parallel design + implementation pilots |
| HOS-6 | Full Design Studio workflow for UI tasks |

---

## 11. Cross-References

| Reference | Document |
|---|---|
| UI Contract standard | `05_UI_CONTRACT_STANDARD.md` |
| Task Contract standard | `04_TASK_CONTRACT_STANDARD.md` |
| Risk classification | `07_RISK_CLASSIFICATION.md` |
| AVOA Design System Plan | `12_AVOA_DESIGN_SYSTEM_PLAN.md` |
| Design Review and Visual QA | `13_DESIGN_REVIEW_AND_VISUAL_QA.md` |
| Evidence standards | `18_EVIDENCE_AND_COMPLETION_STANDARD.md` |

---

*Version 3.1 — Specification. Part of Hermes Engineering OS v3.1. Awaiting implementation authorization.*