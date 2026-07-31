# 04 — Task Contract Standard

**Document ID:** HERMES-OS-V3.1-04
**Status:** SPECIFICATION
**Version:** 3.1
**Date:** 31 July 2026
**Authority:** Hermes Engineering OS v3.1

---

## Purpose

The Task Contract is the single authoritative machine-readable agreement that bounds every Hermes-orchestrated task. It defines **what** is being done, **who** does it, **where** they may work, **how much** change is permitted, **when** success is met, and **why** the task is classified at its risk level.

No task enters execution without an approved contract. No contract may be reinterpreted by any agent other than Hermes.

---

## 1. Complete YAML Schema

```yaml
# === TASK CONTRACT YAML SCHEMA v3.1 ===

# ── Identity ─────────────────────────────────────────────
task_id:            string          # TASK-XXXX-nnn format (e.g. TASK-AVOA-0001)
title:              string          # Human-readable short title
type:               enum            # FEATURE | BUGFIX | MIGRATION | REFACTOR | DOCUMENTATION | CONFIGURATION | VISUAL_ONLY
product:            string          # Product identifier (AVOA | ME | NAUVIS | HERMES)
department:         string          # Owning department (per 02_ORGANIZATIONAL_MODEL)
status:             enum            # DRAFT | PENDING_APPROVAL | APPROVED | ACTIVE | AMENDED | COMPLETED | CANCELLED
parent_task_id:     string|null     # For subtasks; null for top-level tasks
created_at:         datetime        # ISO 8601
created_by:         enum            # HERMES | AMJAD
last_amended_at:    datetime|null   # Updated on amendment

# ── Risk and Classification ──────────────────────────────
risk_level:         enum            # R1 | R2 | R3 | R4 (per 07_RISK_CLASSIFICATION)
primary_class:      enum            # DOCUMENTATION_ONLY | VISUAL_ONLY | INTERACTION_ONLY | BUG_FIX |
                                    # FEATURE | BUSINESS_LOGIC | DATA_MODEL | INFRASTRUCTURE |
                                    # SECURITY | ARCHITECTURE
commercial_impact:  boolean         # true if pricing, financial, or commercial logic is involved
requires_rollback:  boolean         # true if a rollback package must be prepared (R3, R4 default true)
parallel_eligible:  boolean         # true if this task can run concurrently with others (per 07 and 09)

# ── Builder and Reviewer Assignment ──────────────────────
builder:
  primary:          enum            # KIMI_K3 | CODEX | CLAUDE_CODE
  fallback:         enum|null       # CODEX | KIMI_K3 — used if primary fails or repair limit hit
reviewer:
  primary:          enum            # CLAUDE_CODE | HERMES
  review_mode:      enum            # READ_ONLY | WRITE_SUGGESTIONS  (Claude Code mode)

# ── Scope and Boundaries ─────────────────────────────────
scope:
  objective:        string          # Plain-language description of what must be accomplished
  in_scope:         list<string>    # Explicitly permitted work items
  out_of_scope:     list<string>    # Explicitly excluded work items

allowed_files:
  paths:            list<string>    # Glob or explicit file paths the builder may modify
  max_files:        integer         # Hard cap on file count changes
  max_lines:        integer         # Hard cap on total line modifications (adds + deletes)
  max_folders:      integer         # Hard cap on folder count affected

protected_zones_active: boolean     # true enforces protected-zone checks (per 08)

must_remain_unchanged:
  files:            list<string>    # Explicit files builder must not touch
  systems:          list<string>    # Systems/subsystems that must remain unmodified
  locked_decisions: list<string>    # DEC-XXX-NNN locked decisions that must not be violated

# ── Acceptance Criteria ──────────────────────────────────
acceptance_criteria:
  functional:       list<string>    # Behavioural requirements
  visual:           list<string>    # Visual/presentation requirements (for UI contracts)
  quality:          list<string>    # Technical quality requirements
  evidence:         list<string>    # Required evidence items for completion

required_checks:
  build:            boolean         # Build must pass
  lint:             boolean         # Lint must pass
  typecheck:        boolean         # Type-check must pass
  tests_existing:   boolean         # All existing tests must pass
  tests_new:        boolean         # New tests required? Name of test file/module if so
  fixture_check:    boolean         # AVOA fixture validation required
  visual_evidence:  boolean         # Screenshots required (R1, R2 default true)
  scope_check:      boolean         # Scope/protected-zone diff check required

# ── Stop Conditions ──────────────────────────────────────
stop_conditions:
  - condition:      string          # Plain-language stop trigger
    severity:       enum            # IMMEDIATE | AFTER_CURRENT_STEP
  # Standard conditions (always present):
  # - Contract contradictory or incomplete
  # - Locked decision may be affected
  # - Unapproved file or system must change
  # - Production data, secrets, payments, or destructive operations involved unexpectedly
  # - Baseline is dirty or cannot be identified
  # - Automated checks fail for unclear reason
  # - Two repair attempts fail
  # - Requested outcome requires broader redesign
  # - Active branch or commit cannot be confirmed

# ── Task-Specific Stop Conditions ────────────────────────
task_stop_conditions: list<string>  # Additional stop conditions specific to this task

# ── Change Budget ────────────────────────────────────────
change_budget:
  currency:         enum            # USD
  max_spend:        float           # Maximum allowable estimated cost
  actual_spend:     float           # Tracked actual cost (filled during execution)

# ── Baseline ─────────────────────────────────────────────
baseline:
  repository:       string          # Full repository name (e.g. amjadthaufeeg/avoa-connect)
  branch:           string          # Working branch (e.g. feature/TASK-AVOA-0001)
  base_commit:      string          # SHA of the baseline commit
  existing_failures: list<string>   # Known test/check failures at baseline

# ── Rollback Plan ────────────────────────────────────────
rollback:
  strategy:         string          # Plain-language rollback method
  baseline_tag:     string|null     # Git tag of baseline if any
  requires_rehearsal: boolean       # true for R4 tasks

# ── UI Contract (if visual work) ─────────────────────────
ui_contract_id:     string|null     # References 05_UI_CONTRACT_STANDARD contract ID

# ── Approval History ─────────────────────────────────────
approvals:
  - role:           enum            # HERMES | AMJAD
    action:         enum            # APPROVED | REJECTED | AMENDED
    date:           datetime        # ISO 8601
    notes:          string

amendments:
  - amendment_id:   string          # AMND-XXX
    date:           datetime
    reason:         string
    changes:        string          # Summary of changes made
    approved_by:    enum            # HERMES | AMJAD

evidence_package:
  builder_report_id:    string|null
  review_findings_id:   string|null
  test_results_id:      string|null
  visual_evidence_id:   string|null
  scope_check_id:       string|null

# ── Closure ──────────────────────────────────────────────
closure:
  completed_at:     datetime|null
  outcome:          enum|null       # SUCCESS | PARTIAL | FAILED | CANCELLED | SUPERSEDED
  learning_record_id: string|null   # Reference to post-task learning record
  regression_record_ids: list<string>  # Any new regression records created
```

---

## 2. Contract Lifecycle

### 2.1 Creation

Hermes creates the contract from Amjad's request or a system-identified need.

**Creation rules:**
- `task_id` follows `TASK-{PRODUCT}-{NNNN}` format
- `risk_level` is classified per 07_RISK_CLASSIFICATION
- `allowed_files.paths` must be explicit; wildcards discouraged for R3/R4
- `acceptance_criteria` must be testable — no subjective success
- `stop_conditions` include the universal list (from v1.0 STOP_CONDITIONS.md) plus task-specific additions
- `change_budget` is mandatory for R3 and R4 tasks
- `baseline` must be populated with the current state before builder dispatch

**Status on creation:** `DRAFT`

### 2.2 Validation

Hermes validates every contract against the schema before presenting for approval.

**Validation checks:**
1. All required fields present and typed correctly
2. `risk_level` consistent with `primary_class` and `commercial_impact`
3. `allowed_files` does not intersect with `must_remain_unchanged` or protected zones
4. `acceptance_criteria` are specific and testable
5. `stop_conditions` cover the universal set
6. `builder` assignment matches risk-level routing rules
7. `change_budget` present when required by risk level
8. `baseline.commit` is a valid current SHA
9. `parallel_eligible` is consistent with risk-level parallelism rules
10. If `ui_contract_id` is set, the referenced UI contract exists and is approved

### 2.3 Approval

**For R1 tasks:** Hermes may self-approve after validation.

**For R2, R3, R4 tasks:** Contract must be presented to Amjad for explicit approval.

**Approval payload presented to Amjad:**
```
Task: [title]
ID: [task_id]
Risk: [risk_level]
What changes: [in_scope summary]
What stays the same: [out_of_scope summary + must_remain_unchanged]
Files allowed: [allowed_files.paths]
Budget: [change_budget.max_spend]
Builder: [builder.primary]
Reviewer: [reviewer.primary]
Acceptance: [acceptance_criteria summary]
```

**Status on approval:** `APPROVED`

### 2.4 Amendment

Contracts may be amended after approval under strict conditions:

**Amendment triggers:**
- Discovery of a locked decision conflict
- Scope expansion requested by Amjad
- Unforeseen technical dependency discovered
- Budget exceeded preemptively flagged
- Risk reclassification required

**Amendment rules:**
- Only Hermes may amend a contract
- Each amendment gets a unique `AMND-XXX` identifier
- Amendment requires re-approval at the same authority level as original
- Builder must stop work if amendment affects current implementation
- If amendment changes `risk_level` from R1/R2 to R3/R4, full re-approval by Amjad is mandatory

**Status after amendment:** `APPROVED` (with amended field updated)

### 2.5 Cancellation

A contract may be cancelled by Amjad or by Hermes (when a stop condition is fatal):

**Cancellation rules:**
- Branch is preserved for reference
- Any work-in-progress is NOT merged
- `closure.outcome` set to `CANCELLED`
- Decision record created if the cancellation reveals architectural or process insight
- All resources (worktree, branch) released

**Status:** `CANCELLED`

---

## 3. Builder Interface

When dispatched, the builder receives a **sanitized contract excerpt**, not the full contract:

```yaml
# BUILDER VIEW (excerpt sent to Kimi K3 / Codex)
task_id:            TASK-AVOA-0001
objective:          Add responsive login form with validation
risk_level:         R2
allowed_files:
  paths:            ["src/components/login/**", "src/pages/login.tsx"]
  max_files:        5
  max_lines:        300
acceptance_criteria:
  functional:
    - "Email field validates format"
    - "Password field minimum 8 characters"
    - "Submit button disabled until form valid"
    - "Error message displayed on invalid submission"
    - "Successful login redirects to /cockpit"
  visual:
    - "Matches approved Figma mockup LOGIN-V2"
    - "Responsive at 320px, 768px, 1024px breakpoints"
stop_conditions:
  - "Contract contradictory or incomplete"
  - "Unapproved file or system must change"
  - "Two repair attempts fail"
  - "Active branch or commit cannot be confirmed"
baseline:
  branch:           feature/TASK-AVOA-0001
  base_commit:      abc123def456
task_stop_conditions:
  - "Login API endpoint returns unexpected response format"
```

Builders do NOT see:
- `change_budget` amounts
- Full `must_remain_unchanged` lists (only filtered to their scope)
- `reviewer` assignment
- Approval history
- Commercial impact classification
- All original stop conditions (only those relevant to their scope)

---

## 4. Examples

### Example 1: R1 Visual Polish (Login Page)

```yaml
task_id: TASK-AVOA-0101
title: "Login page visual polish — spacing and typography"
type: VISUAL_ONLY
product: AVOA
department: DESIGN
status: DRAFT
parent_task_id: null
created_at: "2026-07-31T10:00:00Z"
created_by: HERMES

risk_level: R1
primary_class: VISUAL_ONLY
commercial_impact: false
requires_rollback: false
parallel_eligible: true

builder:
  primary: KIMI_K3
  fallback: null
reviewer:
  primary: HERMES
  review_mode: READ_ONLY

scope:
  objective: "Adjust login page spacing, typography, and color tokens to match AVOA design system v3.1"
  in_scope:
    - "Login form vertical spacing"
    - "Input field padding and border-radius"
    - "Button hover/focus states (visual only)"
    - "Typographic hierarchy (heading, body, label)"
  out_of_scope:
    - "Login logic or validation behaviour"
    - "API endpoint changes"
    - "Route or navigation changes"
    - "Form submission handling"

allowed_files:
  paths: ["src/components/login/*.tsx", "src/styles/login.css"]
  max_files: 3
  max_lines: 150
  max_folders: 2

protected_zones_active: true

must_remain_unchanged:
  files: ["src/lib/auth.ts", "src/api/login.ts", "src/pages/login.tsx"]
  systems: ["Authentication service"]
  locked_decisions: []

acceptance_criteria:
  functional: []
  visual:
    - "Form padding matches AVOA spacing scale (16px/24px)"
    - "Font sizes follow AVOA type scale (14px labels, 16px inputs, 24px heading)"
    - "Color tokens use CSS custom properties from avoa-tokens.css"
    - "Button uses approved navy/gold palette"
    - "No visual regressions at 320px, 768px, 1024px"
  quality: ["No lint errors", "No console warnings"]
  evidence: ["Screenshot at each breakpoint", "Before/after side-by-side comparison"]

required_checks:
  build: true
  lint: true
  typecheck: false
  tests_existing: false
  tests_new: false
  fixture_check: false
  visual_evidence: true
  scope_check: true

stop_conditions:
  - condition: "Contract contradictory or incomplete"
    severity: IMMEDIATE
  - condition: "Unapproved file or system must change"
    severity: IMMEDIATE
  - condition: "Two repair attempts fail"
    severity: AFTER_CURRENT_STEP
  - condition: "Design token referenced is not in avoa-tokens.css"
    severity: IMMEDIATE

task_stop_conditions:
  - "Required design token not found in approved token set"
  - "Visual change unexpectedly affects layout in other components"

change_budget:
  currency: USD
  max_spend: 5.00
  actual_spend: 0.00

baseline:
  repository: amjadthaufeeg/avoa-connect
  branch: feature/TASK-AVOA-0101
  base_commit: abc123def456
  existing_failures: []

rollback:
  strategy: "Revert to baseline commit; git revert"
  baseline_tag: null
  requires_rehearsal: false

ui_contract_id: UI-AVOA-0003
approvals: []
amendments: []
evidence_package: {}
closure: {}
```

### Example 2: R2 Dashboard Widget Component

```yaml
task_id: TASK-AVOA-0201
title: "Add occupancy status dashboard widget"
type: FEATURE
product: AVOA
department: FRONTEND
status: DRAFT
parent_task_id: null
created_at: "2026-07-31T11:00:00Z"
created_by: AMJAD

risk_level: R2
primary_class: FEATURE
commercial_impact: false
requires_rollback: true
parallel_eligible: true

builder:
  primary: KIMI_K3
  fallback: CODEX
reviewer:
  primary: CLAUDE_CODE
  review_mode: READ_ONLY

scope:
  objective: "Build a dashboard widget displaying real-time occupancy status with 3 visual states"
  in_scope:
    - "New OccupancyWidget React component"
    - "Widget states: available, limited, sold-out"
    - "Responsive at mobile, tablet, desktop breakpoints"
    - "Integration with existing occupancy API endpoint"
    - "Unit tests for all 3 states"
  out_of_scope:
    - "Occupancy API endpoint changes"
    - "Dashboard layout redesign"
    - "Real-time WebSocket connection"
    - "Pricing logic"

allowed_files:
  paths:
    - "src/components/dashboard/OccupancyWidget.tsx"
    - "src/components/dashboard/OccupancyWidget.test.tsx"
    - "src/types/occupancy.ts"
    - "src/styles/dashboard.css"
  max_files: 5
  max_lines: 400
  max_folders: 2

protected_zones_active: true

must_remain_unchanged:
  files:
    - "src/lib/pricing/**"
    - "src/api/occupancy.ts"
    - "src/pages/cockpit.tsx"
  systems: ["Pricing engine", "Booking service"]
  locked_decisions: ["DEC-AVOA-0003"]

acceptance_criteria:
  functional:
    - "Widget displays 'Available' with green badge when occupancy > 20%"
    - "Widget displays 'Limited' with amber badge when occupancy 5-20%"
    - "Widget displays 'Sold Out' with red badge when occupancy < 5%"
    - "Widget fetches data from GET /api/occupancy/status"
    - "Widget shows loading spinner during fetch"
    - "Widget shows error state on fetch failure with retry button"
  visual:
    - "Matches approved widget component spec"
    - "Responsive layout at 768px and 1024px"
  quality:
    - "Unit tests cover all 3 states + loading + error"
    - "No accessibility violations (WCAG AA contrast)"
  evidence:
    - "Screenshot of each state at desktop breakpoint"
    - "Test results output"

required_checks:
  build: true
  lint: true
  typecheck: true
  tests_existing: true
  tests_new: "OccupancyWidget.test.tsx"
  fixture_check: false
  visual_evidence: true
  scope_check: true

stop_conditions:
  - condition: "Contract contradictory or incomplete"
    severity: IMMEDIATE
  - condition: "Locked decision may be affected"
    severity: IMMEDIATE
  - condition: "Unapproved file or system must change"
    severity: IMMEDIATE
  - condition: "Two repair attempts fail"
    severity: AFTER_CURRENT_STEP
  - condition: "Active branch or commit cannot be confirmed"
    severity: IMMEDIATE

task_stop_conditions:
  - "Occupancy API returns unexpected response shape"
  - "Existing dashboard layout breaks with new widget"

change_budget:
  currency: USD
  max_spend: 15.00
  actual_spend: 0.00

baseline:
  repository: amjadthaufeeg/avoa-connect
  branch: feature/TASK-AVOA-0201
  base_commit: def456abc789
  existing_failures: []

rollback:
  strategy: "Remove component import from dashboard; git revert"
  baseline_tag: null
  requires_rehearsal: false

ui_contract_id: UI-AVOA-0005
approvals: []
amendments: []
evidence_package: {}
closure: {}
```

### Example 3: R2 Feature — Quote Request Form

```yaml
task_id: TASK-AVOA-0202
title: "Quote request form with validation and API integration"
type: FEATURE
product: AVOA
department: FRONTEND
status: DRAFT
parent_task_id: null
created_at: "2026-07-31T12:00:00Z"
created_by: AMJAD

risk_level: R2
primary_class: FEATURE
commercial_impact: false
requires_rollback: true
parallel_eligible: false    # Conflicts with occupancy widget if same dashboard

builder:
  primary: KIMI_K3
  fallback: CODEX
reviewer:
  primary: CLAUDE_CODE
  review_mode: READ_ONLY

scope:
  objective: "Implement quote request form with client-side validation and API submission"
  in_scope:
    - "QuoteRequestForm React component with all fields"
    - "Client-side validation (required fields, email format, date ranges)"
    - "POST to /api/quotes/request"
    - "Success state with confirmation message"
    - "Error state with inline field errors"
    - "Form accessibility (labels, aria attributes, keyboard navigation)"
  out_of_scope:
    - "Backend quote calculation logic"
    - "Email notification system"
    - "Quote status tracking page"
    - "Multi-step form wizard"

allowed_files:
  paths:
    - "src/components/quote/QuoteRequestForm.tsx"
    - "src/components/quote/QuoteRequestForm.test.tsx"
    - "src/types/quote.ts"
    - "src/styles/quote.css"
  max_files: 5
  max_lines: 500
  max_folders: 2

protected_zones_active: true

must_remain_unchanged:
  files:
    - "src/lib/pricing/**"
    - "src/api/quotes.ts"
  systems: ["Pricing engine"]
  locked_decisions: ["DEC-AVOA-0004"]

acceptance_criteria:
  functional:
    - "Full name field validates non-empty"
    - "Email field validates RFC 5322 format"
    - "Check-in/check-out dates validate: check-out > check-in"
    - "Guest count validates: 1-20"
    - "Submit sends correctly structured JSON to POST /api/quotes/request"
    - "Form shows loading state during submission"
    - "Success response shows confirmation with reference number"
    - "Error response highlights invalid fields"
  visual:
    - "Matches approved quote form design"
    - "Error states use approved AVOA error color (coral-600)"
  quality:
    - "All fields have associated labels"
    - "Tab order follows visual order"
    - "Error messages announced by screen reader"
    - "Unit tests for validation logic and submission states"
  evidence:
    - "Screenshot: form empty, filled, submitting, success, error"
    - "Test results output"

required_checks:
  build: true
  lint: true
  typecheck: true
  tests_existing: true
  tests_new: "QuoteRequestForm.test.tsx"
  fixture_check: false
  visual_evidence: true
  scope_check: true

stop_conditions:
  - condition: "Contract contradictory or incomplete"
    severity: IMMEDIATE
  - condition: "Unapproved file or system must change"
    severity: IMMEDIATE
  - condition: "Two repair attempts fail"
    severity: AFTER_CURRENT_STEP

task_stop_conditions:
  - "Quote API endpoint returns status not documented in spec"
  - "Validation library incompatible with form patterns"

change_budget:
  currency: USD
  max_spend: 20.00
  actual_spend: 0.00

baseline:
  repository: amjadthaufeeg/avoa-connect
  branch: feature/TASK-AVOA-0202
  base_commit: ghi789jkl012
  existing_failures: []

rollback:
  strategy: "Remove form route from router; git revert"
  baseline_tag: null
  requires_rehearsal: false

ui_contract_id: UI-AVOA-0006
approvals: []
amendments: []
evidence_package: {}
closure: {}
```

### Example 4: R3 Migration — Database Schema Change

```yaml
task_id: TASK-AVOA-0301
title: "Migrate booking table to include cancellation reason codes"
type: MIGRATION
product: AVOA
department: BACKEND
status: DRAFT
parent_task_id: null
created_at: "2026-07-31T13:00:00Z"
created_by: AMJAD

risk_level: R3
primary_class: DATA_MODEL
commercial_impact: false
requires_rollback: true
parallel_eligible: false    # Database migrations are serial

builder:
  primary: KIMI_K3
  fallback: CODEX
reviewer:
  primary: CLAUDE_CODE
  review_mode: READ_ONLY

scope:
  objective: "Add cancellation_reason_code column to booking table with migration, backfill, and API updates"
  in_scope:
    - "Database migration script (add column + index)"
    - "Backfill script for historical records (default: 'UNSPECIFIED')"
    - "Update booking model to include new field"
    - "Update booking API response schema"
    - "Update cancellation endpoint to accept/return reason codes"
    - "Migration test that validates schema change on staging"
    - "Rollback migration script"
  out_of_scope:
    - "Cancellation reason code taxonomy/UI"
    - "Reporting dashboard changes"
    - "Pricing logic modifications"

allowed_files:
  paths:
    - "backend/migrations/004_add_cancellation_reason.sql"
    - "backend/migrations/004_rollback.sql"
    - "backend/src/models/booking.ts"
    - "backend/src/api/bookings.ts"
    - "backend/tests/test_booking_migration.py"
    - "backend/src/types/booking.ts"
  max_files: 8
  max_lines: 600
  max_folders: 4

protected_zones_active: true

must_remain_unchanged:
  files:
    - "backend/src/lib/pricing_engine.py"
    - "backend/src/lib/occupancy_calculator.py"
    - "backend/migrations/001_initial_schema.sql"
    - "backend/migrations/002_*.sql"
    - "backend/migrations/003_*.sql"
  systems: ["Pricing engine", "Occupancy calculator"]
  locked_decisions: ["DEC-AVOA-0001", "DEC-AVOA-0002"]

acceptance_criteria:
  functional:
    - "Migration adds nullable VARCHAR(50) column"
    - "Column has index for filtering"
    - "Backfill sets all existing rows to 'UNSPECIFIED'"
    - "Booking API returns cancellation_reason_code in response"
    - "Cancellation endpoint accepts reason_code parameter"
    - "Rollback migration removes column cleanly"
  visual: []
  quality:
    - "Migration passes on staging database copy"
    - "Rollback verified on staging database copy"
    - "Existing booking queries continue to work (backward compatible)"
    - "API response schema updated in documentation"
  evidence:
    - "Migration output (before/after schema diff)"
    - "Rollback verification output"
    - "Test results: all existing + new migration test"

required_checks:
  build: true
  lint: true
  typecheck: true
  tests_existing: true
  tests_new: "test_booking_migration.py"
  fixture_check: true
  visual_evidence: false
  scope_check: true

stop_conditions:
  - condition: "Contract contradictory or incomplete"
    severity: IMMEDIATE
  - condition: "Locked decision may be affected"
    severity: IMMEDIATE
  - condition: "Production data, secrets, payments, or destructive operations involved unexpectedly"
    severity: IMMEDIATE
  - condition: "Baseline is dirty or cannot be identified"
    severity: IMMEDIATE
  - condition: "Automated checks fail for unclear reason"
    severity: AFTER_CURRENT_STEP
  - condition: "Two repair attempts fail"
    severity: AFTER_CURRENT_STEP
  - condition: "Requested outcome requires broader redesign"
    severity: IMMEDIATE

task_stop_conditions:
  - "Existing booking data contains values incompatible with new column"
  - "Migration runs longer than 30 seconds on staging"
  - "Rollback fails on staging verification"

change_budget:
  currency: USD
  max_spend: 35.00
  actual_spend: 0.00

baseline:
  repository: amjadthaufeeg/avoa-connect
  branch: feature/TASK-AVOA-0301
  base_commit: jkl012mno345
  existing_failures: []

rollback:
  strategy: "Execute rollback migration script; git revert if migration already applied"
  baseline_tag: null
  requires_rehearsal: true    # R3 with rollback rehearsal

ui_contract_id: null
approvals: []
amendments: []
evidence_package: {}
closure: {}
```

### Example 5: R4 Critical — Pricing Engine Update

```yaml
task_id: TASK-AVOA-0401
title: "Update seasonal pricing multiplier logic for peak periods"
type: FEATURE
product: AVOA
department: BACKEND
status: DRAFT
parent_task_id: null
created_at: "2026-07-31T14:00:00Z"
created_by: AMJAD

risk_level: R4
primary_class: BUSINESS_LOGIC
commercial_impact: true     # PRICING ENGINE
requires_rollback: true
parallel_eligible: false    # Must be serial — commercial logic

builder:
  primary: KIMI_K3
  fallback: null             # R4: no fallback; if primary fails, escalate to Amjad
reviewer:
  primary: CLAUDE_CODE
  review_mode: READ_ONLY

scope:
  objective: "Implement configurable seasonal pricing multipliers for peak periods (Eid, Christmas, New Year)"
  in_scope:
    - "New seasonal_pricing_config table/collection"
    - "Multiplier calculation logic in pricing engine"
    - "Integration with existing base rate calculation"
    - "Configuration admin endpoint (read + upsert)"
    - "Pricing fixture updates for all seasonal scenarios"
    - "Comprehensive deterministic tests"
    - "Rollback strategy with baseline pricing restoration"
  out_of_scope:
    - "Dynamic date-range selection UI"
    - "Customer-facing pricing display changes"
    - "Booking flow modifications"
    - "Any changes to booking or availability logic"

allowed_files:
  paths:
    - "backend/src/lib/pricing_engine.py"
    - "backend/src/models/seasonal_config.py"
    - "backend/src/api/admin/pricing.py"
    - "backend/src/types/pricing.py"
    - "backend/tests/test_pricing_v4_fixtures.py"
    - "backend/tests/test_seasonal_pricing.py"
    - "backend/migrations/005_seasonal_pricing.sql"
  max_files: 10
  max_lines: 800
  max_folders: 5

protected_zones_active: true

must_remain_unchanged:
  files:
    - "backend/src/lib/occupancy_calculator.py"
    - "backend/src/lib/tax_calculator.py"
    - "backend/src/lib/commission_calculator.py"
    - "backend/src/models/booking.py"
  systems:
    - "Occupancy calculator"
    - "Tax calculator"
    - "Commission calculator"
    - "Booking service"
  locked_decisions:
    - "DEC-AVOA-0001"
    - "DEC-AVOA-0002"
    - "DEC-AVOA-0003"
    - "DEC-AVOA-0005"

acceptance_criteria:
  functional:
    - "Seasonal multiplier applied when booking date falls within configured peak period"
    - "Multiplier defaults to 1.0 when no seasonal config matches"
    - "Multiple overlapping seasonal periods resolved by highest-priority rule"
    - "Admin endpoint: GET returns current seasonal configuration"
    - "Admin endpoint: PUT replaces seasonal configuration"
    - "Config changes take effect immediately (no cache delay > 1s)"
  visual: []
  quality:
    - "All 78 existing pricing tests pass without modification"
    - "New deterministic tests cover: single period, overlapping periods, edge of period, empty config, priority ordering"
    - "Pricing fixture validation passes"
    - "No floating-point rounding errors beyond 2 decimal places"
    - "Rollback script restores exact previous pricing calculations"
  evidence:
    - "Test results: all existing + seasonal tests"
    - "Fixture validation output"
    - "Manual calculation verification for 5 test scenarios"
    - "Rollback rehearsal verification"

required_checks:
  build: true
  lint: true
  typecheck: true
  tests_existing: true
  tests_new: "test_seasonal_pricing.py"
  fixture_check: true
  visual_evidence: false
  scope_check: true

stop_conditions:
  - condition: "Contract contradictory or incomplete"
    severity: IMMEDIATE
  - condition: "Locked decision may be affected"
    severity: IMMEDIATE
  - condition: "Unapproved file or system must change"
    severity: IMMEDIATE
  - condition: "Production data, secrets, payments, or destructive operations involved unexpectedly"
    severity: IMMEDIATE
  - condition: "Baseline is dirty or cannot be identified"
    severity: IMMEDIATE
  - condition: "Automated checks fail for unclear reason"
    severity: AFTER_CURRENT_STEP
  - condition: "Two repair attempts fail"
    severity: AFTER_CURRENT_STEP
  - condition: "Requested outcome requires broader redesign"
    severity: IMMEDIATE
  - condition: "Active branch or commit cannot be confirmed"
    severity: IMMEDIATE

task_stop_conditions:
  - "Existing pricing fixture calculations change unexpectedly"
  - "Seasonal config schema conflicts with existing pricing models"
  - "Rollback rehearsal fails on staging"
  - "Multiplier calculation produces NaN or Infinity"

change_budget:
  currency: USD
  max_spend: 60.00
  actual_spend: 0.00

baseline:
  repository: amjadthaufeeg/avoa-connect
  branch: feature/TASK-AVOA-0401
  base_commit: mno345pqr678
  existing_failures:
    - "test_kvm_me_packages: missing fixture file kvm_me_packages.json"

rollback:
  strategy: "Execute rollback migration; restore pricing_engine.py from baseline; rerun full pricing fixture suite"
  baseline_tag: "baseline-TASK-AVOA-0401"
  requires_rehearsal: true

ui_contract_id: null
approvals: []
amendments: []
evidence_package: {}
closure: {}
```

### Example 6: Parent Task with Subtasks

```yaml
# PARENT CONTRACT
task_id: TASK-AVOA-0500
title: "Dashboard v2 redesign — parent orchestration task"
type: FEATURE
product: AVOA
department: FRONTEND
status: DRAFT
parent_task_id: null
created_at: "2026-07-31T15:00:00Z"
created_by: AMJAD

risk_level: R2
primary_class: FEATURE
commercial_impact: false
requires_rollback: true
parallel_eligible: true     # Parent splits into parallel subtasks

builder:
  primary: KIMI_K3
  fallback: CODEX
reviewer:
  primary: CLAUDE_CODE
  review_mode: READ_ONLY

scope:
  objective: "Orchestrate Dashboard v2 redesign across 3 subtasks"
  in_scope:
    - "Subtask coordination and integration"
    - "Final integration validation"
    - "Overall evidence package assembly"
  out_of_scope:
    - "Individual component implementation (delegated to subtasks)"

allowed_files:
  paths: ["src/pages/cockpit.tsx"]    # Integration file only
  max_files: 2
  max_lines: 100
  max_folders: 1

protected_zones_active: true

must_remain_unchanged:
  files: ["src/lib/pricing/**"]
  systems: ["Pricing engine"]
  locked_decisions: ["DEC-AVOA-0003"]

acceptance_criteria:
  functional:
    - "All 3 subtask components render correctly in dashboard layout"
    - "No layout regressions at any breakpoint"
    - "Integration tests pass"
  visual:
    - "Dashboard matches approved v2 design at all breakpoints"
  quality:
    - "All subtask test suites pass"
    - "No console errors on dashboard load"
  evidence:
    - "Full dashboard screenshot at each breakpoint"
    - "Integration test results"

required_checks:
  build: true
  lint: true
  typecheck: true
  tests_existing: true
  tests_new: "test_dashboard_integration.py"
  fixture_check: false
  visual_evidence: true
  scope_check: true

stop_conditions:
  - condition: "Any subtask fails or is cancelled"
    severity: AFTER_CURRENT_STEP
  - condition: "Two repair attempts fail"
    severity: AFTER_CURRENT_STEP

task_stop_conditions:
  - "Subtask components have CSS conflicts"
  - "Integration test reveals incompatible component APIs"

change_budget:
  currency: USD
  max_spend: 50.00
  actual_spend: 0.00

baseline:
  repository: amjadthaufeeg/avoa-connect
  branch: feature/TASK-AVOA-0500
  base_commit: pqr678stu901
  existing_failures: []

rollback:
  strategy: "Revert dashboard page to v1; git revert all subtask branches"
  baseline_tag: null
  requires_rehearsal: false

ui_contract_id: UI-AVOA-0010
approvals: []
amendments: []
evidence_package: {}
closure: {}

# ── CHILD SUBTASK 1 ──
---
task_id: TASK-AVOA-0501
title: "Dashboard v2 — Occupancy summary card"
type: FEATURE
product: AVOA
department: FRONTEND
status: DRAFT
parent_task_id: TASK-AVOA-0500
created_at: "2026-07-31T15:30:00Z"
created_by: HERMES

risk_level: R2
primary_class: FEATURE
commercial_impact: false
requires_rollback: true
parallel_eligible: true     # Eligible to run in parallel with 0502, 0503

builder:
  primary: KIMI_K3
  fallback: CODEX
reviewer:
  primary: CLAUDE_CODE
  review_mode: READ_ONLY

scope:
  objective: "Build occupancy summary card component for Dashboard v2"
  in_scope:
    - "OccupancySummaryCard component"
    - "Loading/error/empty states"
    - "Unit tests"
  out_of_scope:
    - "Dashboard layout integration (handled by parent)"

allowed_files:
  paths:
    - "src/components/dashboard/OccupancySummaryCard.tsx"
    - "src/components/dashboard/OccupancySummaryCard.test.tsx"
    - "src/types/occupancy.ts"
  max_files: 4
  max_lines: 300
  max_folders: 1

protected_zones_active: true
must_remain_unchanged:
  files: ["src/lib/pricing/**"]
  systems: ["Pricing engine"]
  locked_decisions: ["DEC-AVOA-0003"]

acceptance_criteria:
  functional:
    - "Displays occupancy percentage, rooms available, rooms total"
    - "Updates on data refresh"
    - "Error state with retry on fetch failure"
  visual:
    - "Matches approved card component in UI contract UI-AVOA-0010"
  quality:
    - "Unit tests for all states"
  evidence:
    - "Screenshot of card in each state"

required_checks:
  build: true
  lint: true
  typecheck: true
  tests_existing: true
  tests_new: "OccupancySummaryCard.test.tsx"
  fixture_check: false
  visual_evidence: true
  scope_check: true

stop_conditions:
  - condition: "Contract contradictory or incomplete"
    severity: IMMEDIATE
  - condition: "Two repair attempts fail"
    severity: AFTER_CURRENT_STEP

task_stop_conditions:
  - "Occupancy API data shape incompatible with component"

change_budget:
  currency: USD
  max_spend: 15.00
  actual_spend: 0.00

baseline:
  repository: amjadthaufeeg/avoa-connect
  branch: feature/TASK-AVOA-0501
  base_commit: pqr678stu901
  existing_failures: []

rollback:
  strategy: "Delete component file; git revert"
  baseline_tag: null
  requires_rehearsal: false

ui_contract_id: UI-AVOA-0010
approvals: []
amendments: []
evidence_package: {}
closure: {}
```

---

## 5. Contract Enforcement

### 5.1 Automated Enforcement

The task contract schema is enforced at multiple layers:

1. **Schema validation** — CI gate validates every contract YAML against the JSON Schema at `.hermes/schemas/task-contract.schema.json`
2. **Scope check** — `scope-check.sh` diff analysis verifies actual file changes match `allowed_files.paths` and do not touch `must_remain_unchanged` files
3. **Budget tracking** — Agent run costs tracked against `change_budget.max_spend`
4. **Evidence validation** — Required evidence items must be present before status advances to `COMPLETED`

### 5.2 Human Enforcement

Amjad approves R2+ contracts before execution. No agent override. Hermes may approve R1 contracts autonomously.

---

## 6. Relationship to Other Documents

| Document | Relationship |
|---|---|
| 05_UI_CONTRACT_STANDARD | Referenced via `ui_contract_id` when visual work is involved |
| 06_TASK_LIFECYCLE | Task state machine; contract status field tracks lifecycle state |
| 07_RISK_CLASSIFICATION | Risk level determines contract fields, routing, and gates |
| 08_PROTECTED_ZONES | `protected_zones_active` flag triggers scope enforcement |
| 09_PARALLEL_EXECUTION | `parallel_eligible` determines concurrent execution eligibility |
| 15_TECHNICAL_REVIEW | `reviewer` assignment and `evidence_package.review_findings_id` |
| 16_DECISION_MEMORY | `must_remain_unchanged.locked_decisions` references decision register |

---

*Document 04 of 26. See 00_HERMES_OS_V3_1_INDEX.md for the full package.*