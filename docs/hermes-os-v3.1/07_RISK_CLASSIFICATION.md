# 07 — Risk Classification

**Document ID:** HERMES-OS-V3.1-07
**Status:** SPECIFICATION
**Version:** 3.1
**Date:** 31 July 2026
**Authority:** Hermes Engineering OS v3.1

---

## Purpose

This document defines the Hermes OS v3.1 4-tier risk classification system (R1-R4). It maps from the v1.0 6-tier system (R0-R5), establishes per-tier requirements, governs parallelism eligibility, and defines the rule-set for commercial logic serialization.

**Rule:** When uncertain between two risk levels, classify one level higher.

---

## 1. Risk Tier Definitions

### R1 — Presentation and Documentation

**Category:** Low-risk changes with no runtime behavior impact.

**Scope:**
- Visual/presentation-only changes (CSS, spacing, typography, color, layout)
- Documentation updates (README, comments, inline docs, markdown)
- Static content changes (copy text, labels, help text)
- Design token application (applying existing tokens, not creating them)
- Configuration comments or non-functional config

**What R1 does NOT authorize:**
- Any logic, state management, or behavior change
- API endpoint modification
- New components with interactive behavior
- Database or schema changes
- Package dependency changes

**Requirements:**

| Requirement | Mandatory |
|---|---|
| Task contract | Yes |
| UI contract (if visual) | Yes |
| Hermes self-approval | Yes (no Amjad required) |
| Builder self-check (build + lint) | Yes |
| Automated gates (basic) | Build, lint, scope check |
| Visual evidence (screenshots) | Yes (if visual) |
| Claude Code review | No |
| Amjad preview approval | Optional (delegated to Hermes for purely typographic/token work) |
| Rollback package | No |
| Change budget tracking | Optional |
| CI gates | Build + lint + scope check |

**Builder routing:** Kimi K3 (primary), Codex (fallback)

**Parallelism:** R1 tasks are parallel-eligible by default, provided they do not touch the same files. Multiple R1 visual tasks may run concurrently.

**Examples:**
- Login page spacing and typography alignment
- Color token migration (hex → CSS custom properties)
- README updates
- JSDoc comment additions
- Form label text correction

---

### R2 — Interaction and Contained Features

**Category:** Moderate-risk changes affecting UI behavior, bounded features, or localized defect fixes.

**Scope:**
- New interactive UI components (forms, widgets, modals, tooltips)
- Frontend feature implementation (bounded to specific components/pages)
- Contained bug fixes (single system, known root cause)
- Accessibility improvements (ARIA, keyboard nav, screen-reader)
- Unit/integration test additions
- Non-commercial API consumption (read-only display endpoints)

**What R2 does NOT authorize:**
- Backend business logic changes
- Commercial/pricing logic modifications
- Database schema changes
- Authentication or authorization changes
- Cross-system architectural changes
- API endpoint signature changes (consuming existing endpoints is R2; modifying them is R3)

**Requirements:**

| Requirement | Mandatory |
|---|---|
| Task contract | Yes |
| UI contract (if visual) | Yes |
| Amjad contract approval | Yes |
| Builder self-check (build + lint + typecheck) | Yes |
| Automated gates (full) | Build, lint, typecheck, existing tests, new tests, scope check |
| Visual evidence (screenshots) | Yes (if visual) |
| Claude Code review | Yes (read-only mode) |
| Amjad preview approval | Yes |
| Rollback package | Yes |
| Change budget tracking | Yes |
| CI gates | Full suite |

**Builder routing:** Kimi K3 (primary), Codex (fallback)

**Reviewer routing:** Claude Code (read-only review mode)

**Parallelism:** R2 tasks are parallel-eligible if they:
- Do not touch the same files as any in-flight task
- Are not in the same component/page domain as an in-flight task
- Do not share protected zone areas

Two R2 tasks in the same component area must be serialized.

**Examples:**
- Occupancy status dashboard widget
- Quote request form with validation
- Toggle-based settings panel
- Bug fix for broken dropdown in navigation
- Adding keyboard navigation to an existing table

---

### R3 — Business Logic and Cross-System Changes

**Category:** High-risk changes affecting business logic, data models, APIs, or cross-system behavior.

**Scope:**
- Backend business logic changes (non-commercial)
- API endpoint creation or modification
- Database schema changes (additive columns, new tables)
- Cross-system integration changes
- Workflow/state machine changes
- Permission or role logic (non-auth infrastructure)
- Non-commercial data migration
- Configuration that changes runtime behavior
- Multi-domain changes (frontend + backend + data)

**What R3 does NOT authorize:**
- Pricing engine modifications (→ R4)
- Financial calculation changes (→ R4)
- Authentication infrastructure changes (→ R4)
- Production data destruction (→ R4)
- Major architectural replacement (→ R4)

**Requirements:**

| Requirement | Mandatory |
|---|---|
| Task contract | Yes |
| UI contract (if visual) | Yes |
| Amjad contract approval | Yes |
| Builder self-check (Build + lint + typecheck + tests) | Yes |
| Automated gates (full + fixtures) | Build, lint, typecheck, existing tests, new tests, fixtures, scope check |
| Visual evidence (screenshots) | Yes (if visual) |
| Claude Code review | Yes (read-only mode) |
| Amjad preview approval | Yes |
| Rollback package | Yes |
| Rollback rehearsal | Yes (verify on staging) |
| Change budget tracking | Yes (mandatory) |
| CI gates | Full suite + fixtures |
| Feature flags (if applicable) | Must be considered |

**Builder routing:** Kimi K3 (primary), Codex (fallback)

**Reviewer routing:** Claude Code (read-only review mode; extended review scope)

**Parallelism:** R3 tasks are NOT parallel-eligible by default. They must run serially. Exceptions:
- Two R3 tasks in completely disjoint domains (different products, different repositories) may run in parallel if both contracts explicitly set `parallel_eligible: true` AND Amjad approves.
- An R3 task may NOT run in parallel with any R4 task.

**Examples:**
- Database migration: add cancellation reason column
- New API endpoint for booking history
- Permission system refactor (non-auth infrastructure)
- Workflow engine: add quote-to-booking conversion
- Cross-service integration: occupancy service ↔ pricing service

---

### R4 — Critical Commercial, Security, or Infrastructure

**Category:** Critical-risk changes involving commercial logic, security, authentication, financial calculations, pricing, destructive operations, or major architecture changes.

**Scope:**
- **Pricing engine** modifications (calculation logic, rate structures, multipliers, discounts)
- **Financial calculations** (tax, commission, fees, totals, invoices)
- **Authentication and authorization** infrastructure
- **Secrets management** changes
- **Database schema** destructive changes (column drops, table drops)
- **Production data** operations (migrations affecting live data)
- **Security** vulnerability fixes or security infrastructure
- **Infrastructure** changes (deployment config, CI/CD, hosting)
- **Major architecture** replacement or refactor
- **Commercial logic** that directly affects revenue

**Requirements:**

| Requirement | Mandatory |
|---|---|
| Task contract | Yes (extended review) |
| UI contract (if visual) | Yes |
| Amjad contract approval | Yes (must sign off explicitly) |
| Amjad explicit acknowledgment of commercial impact | Yes |
| Independent challenge (second opinion) | Yes (Claude Code as critic, not just reviewer) |
| Builder self-check | Yes |
| Automated gates (full + fixtures + deterministic tests) | Yes — all gates must pass |
| Visual evidence | Yes (if visual) |
| Claude Code review | Yes (read-only; extended security + regression scope) |
| Claude Code "challenge" review | Yes (separate from standard review) |
| Amjad preview approval | Yes (mandatory; cannot be delegated) |
| Rollback package | Yes (mandatory) |
| Rollback rehearsal | Yes (must pass on staging before production) |
| Change budget tracking | Yes (mandatory; hard cap enforced) |
| CI gates | Full suite + fixtures + deterministic test verification |
| Feature flags | Yes (required for deployment) |
| Backup verification | Yes (database backup before migration) |
| Deployment window | Yes (low-traffic period) |

**Builder routing:** Kimi K3 (primary), NO fallback. If Kimi fails, escalate to Amjad for decision (re-scope, different approach, or external developer).

**Reviewer routing:** Claude Code (extended review: security, regression, architectural criticism). Additional independent challenge review required.

**Parallelism:** R4 tasks MUST run serially. NO exceptions. No other task (of any risk level) may be in-flight while an R4 task is active. This serialization is automatic and enforced by Hermes.

**Examples:**
- Seasonal pricing multiplier logic update
- Tax calculation engine modification
- Authentication system migration (JWT → OAuth)
- Production database destructive migration
- Commission calculation rule change
- Deployment infrastructure reconfiguration

---

## 2. Classification Decision Matrix

Use this matrix to classify any incoming task. Start from the top; first match determines the level.

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLASSIFICATION MATRIX                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Does the task involve PRICING, FINANCIAL CALCS, or REVENUE?    │
│    ├── YES → R4                                                 │
│    └── NO  → continue                                            │
│                                                                 │
│  Does the task involve AUTH, SECRETS, or SECURITY INFRA?        │
│    ├── YES → R4                                                 │
│    └── NO  → continue                                            │
│                                                                 │
│  Does the task involve PRODUCTION DATA DESTRUCTION?             │
│    ├── YES → R4                                                 │
│    └── NO  → continue                                            │
│                                                                 │
│  Does the task involve MAJOR ARCHITECTURE REPLACEMENT?          │
│    ├── YES → R4                                                 │
│    └── NO  → continue                                            │
│                                                                 │
│  Does the task change BUSINESS LOGIC, APIs, or DB SCHEMA?       │
│    ├── YES → R3                                                 │
│    └── NO  → continue                                            │
│                                                                 │
│  Does the task change UI BEHAVIOR, add features, or fix bugs?   │
│    ├── YES → R2                                                 │
│    └── NO  → continue                                            │
│                                                                 │
│  Is the task purely visual, docs, or config comments?           │
│    ├── YES → R1                                                 │
│    └── NO  → escalate to R2 (default)                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Mapping: v1.0 (R0-R5) → v3.1 (R1-R4)

| v1.0 Level | v1.0 Name | v3.1 Level | Notes |
|---|---|---|---|
| R0 | Documentation only | R1 | Merged into R1 — documentation and presentation share the same risk profile |
| R1 | Presentation-only | R1 | Direct map |
| R2 | Interaction or contained bug fix | R2 | Direct map |
| R3 | Business logic or cross-system | R3 | Direct map |
| R4 | Data, security, infrastructure | R4 | Direct map |
| R5 | Critical commercial or irreversible | R4 | **MERGED** — R4 now encompasses both v1.0 R4 and R5. Commercial/irreversible gets additional R4 requirements (independent challenge, backup verify, feature flags) rather than a separate tier |

**Rationale for R4+R5 merge:**
- v1.0 R4 and R5 both required Amjad approval, Claude review, rollback rehearsal, and backup verification
- The distinction between "data/security/infra" and "critical commercial" was sometimes ambiguous
- v3.1 R4 now triggers the full suite of protections: all v1.0 R4 requirements PLUS the R5 requirements (independent challenge, feature flags, backup verification)
- The classification matrix now routes pricing/financial → R4 directly (no separate tier needed)
- This simplifies the taxonomy while maintaining or strengthening protections

---

## 4. Commercial Logic Serialization

**Rule:** Any task touching commercial logic (pricing, financial calculations, tax, commission, fees, revenue-affecting code) is classified R4 and MUST be serialized.

### What Qualifies as "Commercial Logic"

Files and functions that directly compute or affect:
- **Pricing:** base rate, seasonal multipliers, discounts, package pricing, offer pricing
- **Financial:** tax calculation, commission calculation, fee calculation, totals, subtotals
- **Revenue:** any calculation whose output is a price, cost, or revenue figure presented to customers
- **Payment:** payment amount calculation, refund amount calculation

### Serialization Enforcement

1. When an R4 commercial task is ACTIVE (between `APPROVED` and `CLOSED`), no other task of any risk level may enter `IN_PROGRESS`.
2. Hermes enforces this automatically — `parallel_eligible` is forced to `false` for all tasks during R4 commercial execution.
3. If an R2 or R3 task is already `IN_PROGRESS` when an R4 commercial task is `APPROVED`:
   - Hermes evaluates: can the in-progress task complete safely before R4 starts?
   - If yes: let it finish, then start R4
   - If no: pause (BLOCKED_BY_DEPENDENCY) the in-progress task until R4 is `CLOSED`

### Overlap Detection

Commercial logic files are registered as protected zones (per 08_PROTECTED_ZONES_AND_SCOPE_CONTROL.md). Any task whose `allowed_files` intersects with a commercial-logic protected zone is automatically elevated to R4.

---

## 5. Risk-Level Gate Requirements

```
┌──────────────────────────────────────────────────────────────────┐
│                       GATE REQUIREMENTS                          │
├────────────┬──────────┬──────────┬──────────┬───────────────────┤
│ Gate       │ R1       │ R2       │ R3       │ R4                │
├────────────┼──────────┼──────────┼──────────┼───────────────────┤
│ Build      │ REQUIRED │ REQUIRED │ REQUIRED │ REQUIRED          │
│ Lint       │ REQUIRED │ REQUIRED │ REQUIRED │ REQUIRED          │
│ Typecheck  │ OPTIONAL │ REQUIRED │ REQUIRED │ REQUIRED          │
│ Exst Tests │ OPTIONAL │ REQUIRED │ REQUIRED │ REQUIRED          │
│ New Tests  │ OPTIONAL │ REQUIRED │ REQUIRED │ REQUIRED          │
│ Fixtures   │ OPTIONAL │ OPTIONAL │ REQUIRED │ REQUIRED          │
│ Scope Ck   │ REQUIRED │ REQUIRED │ REQUIRED │ REQUIRED          │
│ Visual Evd │ IF VIS.  │ IF VIS.  │ IF VIS.  │ IF VIS.           │
│ Rollback   │ OPTIONAL │ REQUIRED │ REQUIRED │ REQUIRED          │
│ RB Rehrsl  │ —        │ —        │ REQUIRED │ REQUIRED          │
│ Feat Flags │ —        │ —        │ OPTIONAL │ REQUIRED          │
│ Backup Vfy │ —        │ —        │ —        │ REQUIRED          │
│ Ind.Chall. │ —        │ —        │ —        │ REQUIRED          │
│ Amjad Appr │ OPTIONAL │ REQUIRED │ REQUIRED │ REQUIRED          │
└────────────┴──────────┴──────────┴──────────┴───────────────────┘
```

---

## 6. Parallelism Rules by Risk Level

| Risk Level | Default Parallel | Conditions for Parallel |
|---|---|---|
| R1 | YES | Must not touch same files as any in-flight task |
| R2 | CONDITIONAL | Must not share component domain or protected zones with in-flight tasks |
| R3 | NO (default) | Only if: disjoint domains, Amjad-approved, no R4 active |
| R4 | NO (enforced) | Never. All other tasks serialized behind R4. |

### Conflict Detection for Parallel R1/R2

Before a parallel `DISPATCHING` transition, Hermes checks:
1. Does this task's `allowed_files.paths` intersect with any in-flight task's paths?
2. Does this task's `must_remain_unchanged.files` intersect with any in-flight task's `allowed_files.paths`?
3. Are both tasks in the same product and department with overlapping domains?

If any check returns YES → task is NOT parallel-eligible; must wait.

---

## 7. Examples by Risk Level

### R1 Example: Update README with setup instructions

```yaml
risk_level: R1
primary_class: DOCUMENTATION_ONLY
commercial_impact: false
parallel_eligible: true
```

**Why R1:** Documentation only. No runtime behavior change. No logic.

---

### R1 Example: Adjust button border-radius to match design system

```yaml
risk_level: R1
primary_class: VISUAL_ONLY
commercial_impact: false
parallel_eligible: true
```

**Why R1:** Pure CSS change. No interaction or logic. Token application.

---

### R2 Example: Add search filter to bookings table

```yaml
risk_level: R2
primary_class: FEATURE
commercial_impact: false
parallel_eligible: true
```

**Why R2:** New interactive UI component. Consumes existing API. No backend changes.

---

### R2 Example: Fix broken date-picker in quote form

```yaml
risk_level: R2
primary_class: BUG_FIX
commercial_impact: false
parallel_eligible: true
```

**Why R2:** Bug fix. Known root cause. Contained to date-picker component.

---

### R3 Example: Add new booking history API endpoint

```yaml
risk_level: R3
primary_class: FEATURE
commercial_impact: false
parallel_eligible: false
```

**Why R3:** New API endpoint. Backend logic. Database query changes. Cross-system (API + DB).

---

### R3 Example: Migrate user preferences to new schema

```yaml
risk_level: R3
primary_class: DATA_MODEL
commercial_impact: false
parallel_eligible: false
```

**Why R3:** Database migration. New schema. Data backfill. But not commercial pricing.

---

### R4 Example: Implement dynamic seasonal pricing

```yaml
risk_level: R4
primary_class: BUSINESS_LOGIC
commercial_impact: true
parallel_eligible: false
```

**Why R4:** Pricing engine modification. Direct revenue impact. Commercial logic. R4 with all protections including independent challenge and feature flags.

---

### R4 Example: Fix tax calculation rounding error

```yaml
risk_level: R4
primary_class: BUG_FIX
commercial_impact: true
parallel_eligible: false
```

**Why R4:** Even though it's a bug fix, it touches financial calculation (tax). Commercial impact. R4 protections apply.

---

## 8. Relationship to Other Documents

| Document | Relationship |
|---|---|
| 04_TASK_CONTRACT_STANDARD | `risk_level` field enforces these classifications |
| 06_TASK_LIFECYCLE | Risk level determines which gates are required and approval path |
| 08_PROTECTED_ZONES | Commercial logic zones trigger automatic R4 classification |
| 09_PARALLEL_EXECUTION | Parallelism rules defined by risk level |
| 14_AUTOMATED_QUALITY_GATES | Gate matrix per risk level |
| 15_TECHNICAL_REVIEW | Review scope expands with risk level |
| 20_ROLLBACK_AND_DEPLOYMENT_SAFETY | Rollback rehearsal required at R3, R4 |

---

*Document 07 of 26. See 00_HERMES_OS_V3_1_INDEX.md for the full package.*