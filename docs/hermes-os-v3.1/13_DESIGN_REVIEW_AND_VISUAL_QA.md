# 13 — Design Review and Visual QA

**Status:** SPECIFICATION (not yet implemented)
**Version:** 3.1
**Date:** 31 July 2026
**Part of:** Hermes Engineering OS v3.1
**Depends on:** 11_DESIGN_STUDIO_OPERATING_MODEL, 12_AVOA_DESIGN_SYSTEM_PLAN, 05_UI_CONTRACT_STANDARD
**Feeds into:** 14_AUTOMATED_QUALITY_GATES, 15_TECHNICAL_REVIEW_AND_FINDINGS_PROTOCOL

---

## 1. Purpose

This document defines the design review protocol — how visual quality is inspected, documented, and triaged. It covers review inputs, required screenshots, review checks, finding severity classification, the structured finding YAML format, Hermes triage procedures, correction workflows, and the Visual QA Agent's review-only role.

---

## 2. Review Inputs

### 2.1 Required Review Package

Before a design review begins, Hermes must assemble the following package:

```yaml
review_package:
  task_id: "TASK-0042"
  review_type: "design"  # design | visual-qa | combined

  # Required inputs
  ui_contract: "docs/tasks/TASK-0042-ui-contract.yaml"
  design_specs:
    ux_spec: "docs/design/TASK-0042-ux-spec.yaml"       # if UX Architect was involved
    visual_spec: "docs/design/TASK-0042-visual-spec.yaml"
    interaction_spec: "docs/design/TASK-0042-interaction-spec.yaml"

  # Implementation evidence
  implementation_branch: "task/0042-quote-redesign"
  implementation_commit: "def5678"
  changed_files:
    - "components/quotes/QuoteReviewHeader.tsx"
    - "components/quotes/QuoteReviewHeader.test.tsx"

  # Automated results
  build_status: "PASS"
  test_status: "12 passed, 0 failed"
  lint_status: "PASS"

  # Required screenshots (provided by UI Implementation Agent)
  screenshots:
    desktop:
      - "screenshots/desktop-default.png"
      - "screenshots/desktop-hover.png"
      - "screenshots/desktop-loading.png"
    tablet:
      - "screenshots/tablet-default.png"
    mobile:
      - "screenshots/mobile-default.png"
      - "screenshots/mobile-expanded.png"

  # Context
  builder_report: "docs/tasks/TASK-0042-builder-report.md"
  design_system_version: "1.0.0"
  relevant_regressions: []  # from regression register
```

### 2.2 Input Completeness Gate

Hermes must verify the review package is complete before dispatching a reviewer:

| Check | Required For |
|---|---|
| UI Contract present | All design reviews |
| Design specs present | All tasks where Design Studio was involved |
| Changed files list present | All reviews |
| Screenshots cover all required breakpoints | All visual reviews |
| Screenshots cover all required states | All interactive component reviews |
| Build passes | All reviews |
| Builder report present | All reviews |

If any required input is missing, Hermes blocks the review and requests the missing item from the responsible agent.

---

## 3. Required Screenshots

### 3.1 Breakpoint Requirements

| Component Type | Desktop (1440px) | Tablet (768px) | Mobile (375px) |
|---|---|---|---|
| Page-level change | **Required** | **Required** | **Required** |
| Shared component | **Required** | **Required** | **Required** |
| Single-use component | Required | Optional | Optional (if responsive) |
| Backend-only change | Not required | Not required | Not required |
| Documentation change | Not required | Not required | Not required |

### 3.2 State Screenshot Requirements

For each breakpoint, screenshots must capture every applicable state:

| State | Required When |
|---|---|
| **Default** | Always |
| **Hover** | Component has hover styles |
| **Focus** | Component is focusable (inputs, buttons, links) |
| **Active** | Component has active/pressed state |
| **Disabled** | Component can be disabled |
| **Loading** | Component has loading state |
| **Empty** | Component displays data that can be empty |
| **Error** | Component can show error state |
| **Success** | Component shows success confirmation |

### 3.3 Screenshot Naming Convention

```
<breakpoint>-<state>-<element>.png

Examples:
  desktop-default-header.png
  desktop-hover-primary-button.png
  tablet-loading-status-badge.png
  mobile-error-form-input.png
  mobile-expanded-navigation.png
```

### 3.4 Screenshot Quality Standards

| Requirement | Specification |
|---|---|
| Resolution | 2x (Retina) for desktop; 1x acceptable for mobile/tablet |
| Format | PNG (lossless) |
| Viewport | Full component in context (not cropped too tightly) |
| Content | Realistic data (not "Lorem ipsum"; use representative sample data) |
| States | Each state in its own screenshot; no composite images |
| Background | Consistent (no dev tools, overlays, or cursor in screenshot) |

---

## 4. Review Checks

### 4.1 Visual Review Checklist

The reviewer must verify each of the following:

```
DESIGN SPEC COMPLIANCE
☐ Colors match design system tokens (not hardcoded values)
☐ Typography matches scale (size, weight, line-height)
☐ Spacing matches grid (padding, margin, gap)
☐ Border radius matches token spec
☐ Shadows/elevation match token spec
☐ Icons use correct library and size

LAYOUT AND RESPONSIVENESS
☐ Layout matches UX spec at desktop
☐ Layout adapts correctly at tablet
☐ Layout adapts correctly at mobile
☐ No horizontal overflow at any breakpoint
☐ Content reflow is logical and readable

INTERACTION STATES
☐ Hover states are present and correct
☐ Focus indicators are visible and consistent
☐ Active states are present
☐ Disabled states are visually distinct
☐ Loading states display correctly
☐ Empty states display correctly
☐ Error states display correctly
☐ State transitions are smooth (no flicker/jump)

ACCESSIBILITY
☐ Color contrast meets WCAG AA (4.5:1 for text, 3:1 for large text)
☐ Focus order is logical
☐ Focus indicators are visible
☐ Touch targets are ≥44px
☐ Alt text is present on images
☐ Form inputs have labels
☐ Error messages are associated with inputs
☐ prefers-reduced-motion is respected

CROSS-BROWSER (if applicable)
☐ Renders correctly in Chrome
☐ Renders correctly in Firefox
☐ Renders correctly in Safari
```

### 4.2 Token Compliance Audit

For each changed component file, the reviewer audits token usage:

```yaml
token_audit:
  file: "components/quotes/QuoteReviewHeader.tsx"
  color_usages:
    - line: 24
      value: "bg-primary"
      token: "--color-primary"
      compliant: true
    - line: 45
      value: "text-green-500"
      token: null
      compliant: false
      expected: "text-success"
  hardcoded_values:
    - line: 67
      value: "#f5f5f5"
      should_be: "var(--color-surface-secondary)"
  summary:
    total_usages: 18
    compliant: 16
    non_compliant: 2
```

---

## 5. Finding Severity Classification

### 5.1 Severity Levels

| Severity | Symbol | Definition | Action Required |
|---|---|---|---|
| **BLOCKER** | 🔴 | Visual or functional defect that prevents task completion; violates a mandatory requirement | Must fix before task can proceed |
| **HIGH** | 🟠 | Significant deviation from approved design spec or design system; visually obvious | Must fix before Amjad approval |
| **MEDIUM** | 🟡 | Noticeable inconsistency; degrades visual quality but does not prevent function | Should fix; may proceed with documented deferral |
| **LOW** | 🟢 | Minor polish issue; barely noticeable | Nice to fix; does not block |
| **OPTIONAL** | ⚪ | Suggestion for improvement; current implementation meets spec | Reviewer recommendation only |

### 5.2 Severity Examples

#### BLOCKER

```yaml
- "Component is completely unstyled / CSS not loaded"
- "Layout is broken at required breakpoint (elements overlap or overflow)"
- "Missing required state (button has no disabled state)"
- "Color contrast fails WCAG AA minimum (below 3:1)"
- "Missing required accessibility (no label on form input)"
- "Wrong component entirely (implemented Card when spec says Table)"
```

#### HIGH

```yaml
- "Wrong design token used (text-green-500 instead of text-success)"
- "Spacing deviates from grid by 8px or more"
- "Typography weight is wrong (font-normal instead of font-semibold on heading)"
- "Hover state missing on primary action button"
- "Focus ring invisible (same color as background)"
- "Component breaks at tablet breakpoint (not mobile or desktop)"
```

#### MEDIUM

```yaml
- "Spacing deviates from grid by 4px"
- "Border radius uses rounded-md instead of rounded-lg per design system"
- "Shadow is slightly too heavy (shadow-md when spec says shadow-sm)"
- "Animation duration is 300ms instead of specified 200ms"
- "Icon size is w-5 h-5 instead of specified w-4 h-4"
```

#### LOW

```yaml
- "1px alignment issue at edge case viewport"
- "Subtle color difference that passes contrast check (e.g., #f5f5f5 vs #f4f4f4)"
- "Transition easing curve differs slightly from spec"
- "Optional decorative element alignment"
```

#### OPTIONAL

```yaml
- "Consider adding a micro-interaction on status change"
- "Suggestion: increase section padding from py-8 to py-10 for better breathing room"
- "Would benefit from a subtle entrance animation"
- "Alternative icon suggestion"
```

### 5.3 Severity Decision Flow

```
Reviewer observes issue
        │
        ▼
Does it prevent task completion?
  YES → BLOCKER
  NO  ↓
Is it a significant deviation from approved spec?
  YES → HIGH
  NO  ↓
Is it a noticeable inconsistency?
  YES → MEDIUM
  NO  ↓
Is it a minor polish issue?
  YES → LOW
  NO  ↓
OPTIONAL (suggestion only)
```

---

## 6. Finding YAML Format

### 6.1 Full Finding Schema

Every finding must use this structured format:

```yaml
finding_id: "DR-0042-001"           # DR = Design Review, task ID, sequential
review_id: "REV-2026-0731-001"
task_id: "TASK-0042"
review_type: "visual-qa"            # visual-qa | design-review | combined
reviewer: "visual-qa-agent"         # agent role

severity: "HIGH"                    # BLOCKER | HIGH | MEDIUM | LOW | OPTIONAL
category: "color-token"             # See category list below
element: "status_badge"             # Specific UI element
file: "components/quotes/QuoteReviewHeader.tsx"
line: 45

title: "Status badge uses wrong color token"
description: >
  The status badge for 'Confirmed' reservations uses text-green-500
  instead of the design system token text-success. This causes a
  visible color mismatch with other status badges in the application.

expected:
  value: "text-success (--color-success: #16a34a)"
  reference: "AVOA Design System v1.0.0, Section 3.1.2"

actual:
  value: "text-green-500 (#22c55e)"
  screenshot: "screenshots/findings/DR-0042-001-actual.png"

evidence:
  screenshots:
    - "screenshots/findings/DR-0042-001-actual.png"
    - "screenshots/findings/DR-0042-001-expected-comparison.png"
  code_snippet: |
    // Line 45 — current
    <span className="text-green-500 font-medium">{status}</span>

    // Should be
    <span className="text-success font-medium">{status}</span>

recommendation: >
  Replace text-green-500 with text-success. Verify the Tailwind config
  maps text-success to var(--color-success).

wcag_impact: null                   # null if no accessibility impact
design_system_rule: "DS-COLOR-001"  # Reference to design system rule violated
```

### 6.2 Finding Categories

```yaml
categories:
  color-token: "Color does not match design system token"
  typography: "Font size, weight, line-height, or family mismatch"
  spacing: "Padding, margin, or gap deviation from grid"
  layout: "Layout structure, grid, or positioning issue"
  radius-border: "Border radius or border style deviation"
  elevation-shadow: "Shadow or elevation mismatch"
  icon: "Icon library, size, or style deviation"
  responsive: "Layout breaks or degrades at specific breakpoint"
  animation-motion: "Animation duration, easing, or behavior issue"
  state-missing: "Required state not implemented"
  state-incorrect: "State implemented but visually wrong"
  accessibility: "WCAG violation or accessibility concern"
  cross-browser: "Rendering difference between browsers"
  token-hardcoded: "Hardcoded value where token should be used"
  consistency: "Inconsistency with other instances of same component"
  interaction: "Interactive behavior not matching spec"
```

### 6.3 Finding Collection Format

All findings for a review are collected into a single YAML document:

```yaml
review_id: "REV-2026-0731-001"
task_id: "TASK-0042"
review_type: "visual-qa"
reviewer: "visual-qa-agent"
reviewed_at: "2026-07-31T14:30:00Z"
design_system_version: "1.0.0"

summary:
  total_findings: 5
  blocker: 0
  high: 1
  medium: 2
  low: 1
  optional: 1
  verdict: "CONDITIONAL_PASS"  # PASS | CONDITIONAL_PASS | FAIL

findings:
  - finding_id: "DR-0042-001"
    severity: "HIGH"
    category: "color-token"
    title: "Status badge uses wrong color token"
    # ... full finding

  - finding_id: "DR-0042-002"
    severity: "MEDIUM"
    category: "spacing"
    title: "Header padding deviates from grid by 4px"
    # ... full finding

  - finding_id: "DR-0042-003"
    severity: "MEDIUM"
    category: "state-missing"
    title: "Loading state not implemented for action buttons"
    # ... full finding

  - finding_id: "DR-0042-004"
    severity: "LOW"
    category: "animation-motion"
    title: "Hover transition duration is 300ms instead of 150ms"
    # ... full finding

  - finding_id: "DR-0042-005"
    severity: "OPTIONAL"
    category: "animation-motion"
    title: "Consider entrance animation for status badge"
    # ... full finding
```

---

## 7. Hermes Triage

### 7.1 Triage Decision Types

For every finding with severity ≥ LOW, Hermes must make a decision:

```yaml
triage:
  finding_id: "DR-0042-001"

  decision: "accepted"  # accepted | rejected | deferred

  reason: >
    Design system compliance is mandatory. The token text-success is
    the canonical color for success states. No reason to deviate.

  approved_correction: >
    Replace text-green-500 with text-success in QuoteReviewHeader.tsx line 45.
    Verify no other instances of text-green-500 exist in the changed files.

  routed_to: "kimi-k3"    # agent assigned to fix
  priority: "high"         # high | normal | low
  deadline: null           # null = before task closure
```

### 7.2 Triage Rules

| Finding Severity | Default Decision | Can Defer? |
|---|---|---|
| BLOCKER | **Must accept** | No |
| HIGH | Accept unless design spec allows alternative | Only with Amjad approval |
| MEDIUM | Accept unless documented rationale for deviation | Yes, with recorded reason |
| LOW | Hermes discretion | Yes |
| OPTIONAL | Hermes discretion (usually deferred) | Yes |

### 7.3 Triage Outcome

```yaml
triage_outcome:
  review_id: "REV-2026-0731-001"
  triaged_by: "hermes"
  triaged_at: "2026-07-31T15:00:00Z"

  accepted: 3   # DR-0042-001, DR-0042-002, DR-0042-003
  rejected: 1   # DR-0042-004 (deviation documented: animation library limitation)
  deferred: 1   # DR-0042-005 (optional enhancement, separate task)

  corrections_required: 3
  assigned_to: "kimi-k3"

  post_correction_verdict: "RE_REVIEW_REQUIRED"
```

### 7.4 Deferred Findings

Deferred findings must be tracked:

```yaml
deferred_finding:
  finding_id: "DR-0042-005"
  deferred_reason: "Enhancement, not required for current task"
  deferral_approved_by: "hermes"
  follow_up_task: "TASK-0047"  # Separate task created, or null if backlog
  revisit_at: null              # or specific date/milestone
```

---

## 8. Corrections Flow

### 8.1 Correction Cycle

```
Hermes triages findings
        │
        ▼
  Accepted findings → Correction contract
        │
        ▼
  UI Implementation Agent receives:
    - List of accepted findings with approved corrections
    - Original task contract (for context + boundaries)
    - Current implementation commit
        │
        ▼
  Agent implements corrections
        │
        ▼
  Agent submits corrected implementation
        │
        ▼
  Visual QA re-reviews:
    - Verify each accepted finding is resolved
    - Check for new issues introduced by corrections
    - Report re-review findings
        │
        ▼
  Hermes re-triages (if new findings)
        │
   ┌────┴────┐
   ▼         ▼
PASS      MORE FINDINGS
   │         │
   │         ▼
   │    Correction cycle repeats (max 2 cycles)
   │         │
   │         ▼
   │    After 2 cycles → Hermes escalation
   │         │
   └────┬────┘
        ▼
  Final verdict → PASS
```

### 8.2 Correction Contract

Hermes creates a correction contract from accepted findings:

```yaml
correction_contract:
  parent_task_id: "TASK-0042"
  correction_cycle: 1
  max_cycles: 2

  findings_to_resolve:
    - finding_id: "DR-0042-001"
      approved_correction: "Replace text-green-500 with text-success"
    - finding_id: "DR-0042-002"
      approved_correction: "Adjust header padding from py-3 (12px) to py-4 (16px)"
    - finding_id: "DR-0042-003"
      approved_correction: "Add loading state with spinner to action buttons"

  scope: "Only resolve listed findings. Do not introduce unrelated changes."
  allowed_files:  # same as original task contract
    - "components/quotes/QuoteReviewHeader.tsx"

  stop_conditions:
    - "Any change beyond listed findings"
    - "Correction introduces new visual issue"
    - "Correction requires change to file outside allowed set"
```

### 8.3 Re-Review Protocol

After corrections, the reviewer checks:

```
☐ Each accepted finding is resolved
☐ Resolution matches the approved correction
☐ No new visual issues introduced
☐ No regression in previously passing checks
☐ No scope expansion beyond approved corrections
```

Re-review findings are numbered sequentially (DR-0042-006, DR-0042-007, ...) to distinguish from initial review findings.

### 8.4 Escalation After 2 Correction Cycles

If two correction cycles do not resolve all BLOCKER or HIGH findings:

1. Hermes pauses the task
2. Hermes records the unresolved findings and correction history
3. Hermes evaluates whether to:
   - Switch builder (Kimi → Codex for precision fix)
   - Re-scope the task (accept remaining deviations with Amjad approval)
   - Restart with narrower scope
4. Hermes presents escalation to Amjad with evidence

---

## 9. Visual QA Agent — Review-Only Role

### 9.1 Mandate

The Visual QA Agent is **strictly review-only**:

| Permitted | Prohibited |
|---|---|
| Capture screenshots | Modify any source code |
| Inspect HTML/CSS output | Edit style files |
| Compare against design specs | Change design tokens |
| Report token compliance | Regenerate screenshots with altered code |
| Identify visual regressions | "Quick-fix" any issue, however trivial |
| Suggest corrections | Implement corrections |

### 9.2 Output

Visual QA Agent produces exactly:

1. **Screenshots** — at all required breakpoints and states
2. **Findings YAML** — structured per Section 6
3. **Token compliance audit** — per changed file
4. **Summary verdict** — PASS | CONDITIONAL_PASS | FAIL

The Visual QA Agent reports to Hermes, never directly to the builder.

### 9.3 Prohibited Messages

The Visual QA Agent must not send:

```
❌ "I fixed the color token on line 45."
❌ "Here's the corrected component."
❌ "I adjusted the spacing to match the grid."
❌ "Minor issue — I went ahead and fixed it."
```

Only:

```
✅ "Review completed. 5 findings submitted to Hermes."
✅ "Screenshots captured at desktop, tablet, and mobile breakpoints."
✅ "Token compliance audit: 16/18 usages compliant."
```

---

## 10. Design Review Schema (Machine-Readable)

### 10.1 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://hermes-os.nousresearch.com/schemas/design-review-v1.json",
  "title": "Design Review",
  "type": "object",
  "required": ["review_id", "task_id", "review_type", "reviewer", "findings", "summary"],
  "properties": {
    "review_id": {
      "type": "string",
      "pattern": "^REV-\\d{4}-\\d{4}-\\d{3}$",
      "description": "Unique review identifier"
    },
    "task_id": {
      "type": "string",
      "pattern": "^TASK-\\d{4}$"
    },
    "review_type": {
      "type": "string",
      "enum": ["visual-qa", "design-review", "combined"]
    },
    "reviewer": {
      "type": "string",
      "enum": ["visual-qa-agent", "claude-code", "hermes"]
    },
    "reviewed_at": {
      "type": "string",
      "format": "date-time"
    },
    "design_system_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "summary": {
      "type": "object",
      "required": ["total_findings", "blocker", "high", "medium", "low", "optional", "verdict"],
      "properties": {
        "total_findings": {"type": "integer", "minimum": 0},
        "blocker": {"type": "integer", "minimum": 0},
        "high": {"type": "integer", "minimum": 0},
        "medium": {"type": "integer", "minimum": 0},
        "low": {"type": "integer", "minimum": 0},
        "optional": {"type": "integer", "minimum": 0},
        "verdict": {
          "type": "string",
          "enum": ["PASS", "CONDITIONAL_PASS", "FAIL"]
        }
      }
    },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["finding_id", "severity", "category", "title", "description"],
        "properties": {
          "finding_id": {
            "type": "string",
            "pattern": "^DR-\\d{4}-\\d{3}$"
          },
          "severity": {
            "type": "string",
            "enum": ["BLOCKER", "HIGH", "MEDIUM", "LOW", "OPTIONAL"]
          },
          "category": {
            "type": "string",
            "enum": [
              "color-token", "typography", "spacing", "layout",
              "radius-border", "elevation-shadow", "icon", "responsive",
              "animation-motion", "state-missing", "state-incorrect",
              "accessibility", "cross-browser", "token-hardcoded",
              "consistency", "interaction"
            ]
          },
          "element": {"type": "string"},
          "file": {"type": "string"},
          "line": {"type": "integer"},
          "title": {"type": "string"},
          "description": {"type": "string"},
          "expected": {
            "type": "object",
            "properties": {
              "value": {"type": "string"},
              "reference": {"type": "string"}
            }
          },
          "actual": {
            "type": "object",
            "properties": {
              "value": {"type": "string"},
              "screenshot": {"type": "string"}
            }
          },
          "evidence": {
            "type": "object",
            "properties": {
              "screenshots": {
                "type": "array",
                "items": {"type": "string"}
              },
              "code_snippet": {"type": "string"}
            }
          },
          "recommendation": {"type": "string"},
          "wcag_impact": {"type": "string"},
          "design_system_rule": {"type": "string"}
        }
      }
    }
  }
}
```

---

## 11. Verdict Definitions

| Verdict | Criteria | Next Step |
|---|---|---|
| **PASS** | 0 BLOCKER, 0 HIGH. All mandatory checks pass. | Proceed to Hermes readiness assessment |
| **CONDITIONAL_PASS** | 0 BLOCKER. HIGH findings exist but Hermes accepts with documented rationale. | Corrections for HIGH findings; re-review optional per Hermes |
| **FAIL** | ≥1 BLOCKER, or ≥3 HIGH, or mandatory check fails. | Corrections required; full re-review mandatory |

---

## 12. Cross-References

| Reference | Document |
|---|---|
| Design Studio Operating Model | `11_DESIGN_STUDIO_OPERATING_MODEL.md` |
| AVOA Design System Plan | `12_AVOA_DESIGN_SYSTEM_PLAN.md` |
| UI Contract Standard | `05_UI_CONTRACT_STANDARD.md` |
| Technical Review Protocol | `15_TECHNICAL_REVIEW_AND_FINDINGS_PROTOCOL.md` |
| Evidence Standards | `18_EVIDENCE_AND_COMPLETION_STANDARD.md` |
| Automated Quality Gates | `14_AUTOMATED_QUALITY_GATES.md` |

---

*Version 3.1 — Specification. Part of Hermes Engineering OS v3.1. Awaiting implementation authorization.*