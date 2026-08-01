# Loop Engineering — Schemas, Policies, Pilots, and Risk Assessment

**Status:** Planning | **Release:** Loop Engineering

---

## Loop Contract JSON Schema

Required fields: `loop_id`, `name`, `owner`, `status`, `version`, `trigger`, `objective`, `success_condition`, `terminal_states`, `task_template`, `risk_ceiling`, `protected_zones`, `execution`, `verification`, `stop_conditions`, `rollback`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://hermes-os.local/schemas/loop-contract.schema.json",
  "type": "object",
  "required": ["loop_id", "name", "owner", "status", "trigger", "objective", "risk_ceiling", "execution", "stop_conditions"],
  "properties": {
    "loop_id": {"type": "string", "pattern": "^LOOP-[A-Z]+-\\d{3}$"},
    "name": {"type": "string", "minLength": 5},
    "owner": {"enum": ["hermes"]},
    "status": {"enum": ["proposed", "approved", "active", "paused", "deprecated"]},
    "version": {"type": "string"},
    "trigger": {"type": "object", "required": ["type"], "properties": {
      "type": {"enum": ["cron", "webhook", "manual", "event"]},
      "source": {"type": "string"},
      "schedule_or_condition": {"type": "string"}
    }},
    "objective": {"type": "string", "minLength": 10},
    "success_condition": {"type": "string"},
    "terminal_states": {"type": "array", "items": {"type": "string"}},
    "discovery": {"type": "object", "properties": {
      "source": {"type": "string"},
      "eligibility_rules": {"type": "array", "items": {"type": "string"}},
      "priority_rules": {"type": "array", "items": {"type": "string"}},
      "max_items_per_run": {"type": "integer", "minimum": 1}
    }},
    "task_template": {"type": "object"},
    "risk_ceiling": {"enum": ["R1", "R2", "R3", "R4"]},
    "protected_zones": {"type": "array", "items": {"type": "string"}},
    "authorized_protected_changes": {"type": "array", "items": {"type": "object"}},
    "execution": {"type": "object", "required": ["builder", "isolated_workspace"], "properties": {
      "builder": {"enum": ["kimi-k3", "codex", "hermes"]},
      "reviewer": {"enum": ["claude-code", "none"]},
      "isolated_workspace": {"type": "string"},
      "max_runtime_minutes": {"type": "integer", "default": 30},
      "heartbeat_interval_minutes": {"type": "integer", "default": 2},
      "max_repair_cycles": {"type": "integer", "default": 3},
      "max_validation_cycles": {"type": "integer", "default": 4},
      "provider_timeout_minutes": {"type": "integer", "default": 8}
    }},
    "verification": {"type": "object", "properties": {
      "deterministic_checks": {"type": "array", "items": {"type": "string"}},
      "independent_evaluator": {"enum": ["claude-code", "none"]},
      "required_evidence": {"type": "array", "items": {"enum": ["build", "type_check", "lint", "unit_tests", "integration_tests", "business_fixtures", "screenshots", "scope_check", "protected_zone_check", "rollback_package"]}},
      "freshness_requirements": {"type": "string"},
      "source_commit_binding": {"type": "boolean", "default": true}
    }},
    "human_gates": {"type": "object", "properties": {
      "before_scope_change": {"type": "boolean"},
      "before_protected_change": {"type": "boolean"},
      "before_merge": {"type": "boolean"},
      "before_deploy": {"type": "boolean"},
      "before_irreversible_action": {"type": "boolean"}
    }},
    "stop_conditions": {"type": "object", "properties": {
      "success": {"type": "string"},
      "budget_exceeded": {"type": "string"},
      "scope_exceeded": {"type": "string"},
      "protected_change_required": {"type": "string"},
      "repeated_failure": {"type": "string"},
      "provider_timeout": {"type": "string"},
      "evidence_failure": {"type": "string"},
      "human_decision_required": {"type": "string"},
      "cancelled": {"type": "string"}
    }},
    "rollback": {"type": "string"},
    "audit_requirements": {"type": "array", "items": {"type": "string"}}
  }
}
```

---

## Loop State Event Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://hermes-os.local/schemas/loop-state-event.schema.json",
  "type": "object",
  "required": ["event_id", "loop_id", "run_id", "timestamp", "from_state", "to_state", "actor"],
  "properties": {
    "event_id": {"type": "string", "pattern": "^LEVT-\\d{3}$"},
    "loop_id": {"type": "string"},
    "run_id": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"},
    "from_state": {"enum": ["LOOP_PROPOSED", "LOOP_APPROVED", "DISCOVERING", "TASK_SELECTED", "CONTRACT_DRAFTED", "AWAITING_CONTRACT_APPROVAL", "EXECUTING", "VALIDATING", "EVALUATING", "CORRECTING", "AWAITING_HUMAN_GATE", "SUCCEEDED", "FAILED", "BUDGET_EXCEEDED", "SCOPE_EXCEEDED", "PROVIDER_TIMEOUT", "EVIDENCE_REJECTED", "CANCELLED", "ARCHIVED"]},
    "to_state": {"type": "string"},
    "actor": {"enum": ["hermes", "loop-controller", "amjad"]},
    "reason": {"type": "string"},
    "evidence_ref": {"type": "string"}
  }
}
```

---

## Loop Budget Policy

Default values:

| Budget | Value | Enforced By |
|---|---|---|
| heartbeat_interval_minutes | 2 | Loop Controller |
| silent_warning_minutes | 5 | Loop Controller |
| checkpoint_interval_minutes | 15 | Loop Controller |
| provider_timeout_minutes | 8 | Loop Controller |
| max_provider_retries | 1 | Loop Controller |
| max_repair_cycles | 3 | Loop Controller |
| max_validation_cycles | 4 | Loop Controller |
| max_external_retries | 5 | Loop Controller |
| max_runtime_minutes | 30 | Loop Controller |

When a budget is exceeded, the Loop Controller must: stop safely, save state, record `EXECUTION_BUDGET_EXCEEDED`, preserve evidence, report to Hermes, and not retry.

---

## Human-Gate Policy

All human gates are mandatory for the following loop states:

| Gate | Required Before |
|---|---|
| Contract approval | CONTRACT_DRAFTED → AWAITING_CONTRACT_APPROVAL |
| Scope change | Any scope expansion beyond approved contract |
| Protected change | Any write to authorized_protected_changes |
| Merge | Any merge to protected branches |
| Deploy | Any production deployment |
| Irreversible action | Any delete, destroy, or non-reversible mutation |

Each gate: pauses the loop, presents the proposed action with evidence, and awaits explicit approval. No timeout override.

---

## Proof-or-Stop Evidence Policy

Required evidence by gate:

| Gate | Evidence |
|---|---|
| Build check | Build output |
| Scope check | Changed-file report + scope result |
| Protected zone | Protected-zone check output |
| Test gate | Test results |
| Fixture gate | Fixture pass/fail |
| Review gate | Independent review findings |
| Deployment | Rollback package + deployment record |

Evidence is **commit-bound**: every evidence item must reference the exact commit it was generated from. Stale evidence (different commit) → EVIDENCE_REJECTED.

---

## Loop Memory Specification

```yaml
run_id: LOOP-RUN-XXX
loop_id: LOOP-XXX-XXX
state: EXECUTING
started_at: "2026-08-01T00:00:00Z"
branch: "feature/LOOP-RUN-XXX"
commit: "abc123"
prior_runs: []
task_contracts_created: []
evidence_collected: {}
decisions: []
regressions_encountered: []
unresolved_findings: []
budget_remaining: {}
current_repair_cycle: 0
last_checkpoint_commit: ""
```

---

## Audit Event Schema

```yaml
event_id: AEVT-XXX
loop_id: LOOP-XXX-XXX
run_id: LOOP-RUN-XXX
timestamp: "2026-08-01T00:00:00Z"
event_type: state_transition | budget_exceeded | scope_exceeded | human_gate | evidence_rejected | error
actor: loop-controller | hermes | amjad
detail: "state transition from EXECUTING to VALIDATING"
evidence_ref: ""
```

---

## Initial Pilot Contracts

### LOOP-PILOT-001: CI Failure Triage

```yaml
loop_id: LOOP-PILOT-001
name: "CI Failure Triage Pilot"
risk_ceiling: R1
trigger:
  type: event
  source: "GitHub Actions failure notification"
  schedule_or_condition: "on workflow_run failure"
objective: "Inspect failed GitHub Actions check logs, classify likely cause, and propose a task contract for resolution."
discovery:
  source: "GitHub Actions API"
  eligibility_rules: ["Workflow run failure", "Not already triaged in prior 24h"]
  max_items_per_run: 1
execution:
  builder: kimi-k3
  reviewer: claude-code
  isolated_workspace: "feature/loop-pilot-001-run-*"
task_template:
  task_type: bug_fix
  risk_level: R1
verification:
  deterministic_checks: ["schema_validate", "scope_check"]
  independent_evaluator: claude-code
human_gates:
  before_merge: true
stop_conditions:
  success: "Triage report and proposed task contract created"
```

### LOOP-PILOT-002 through LOOP-PILOT-004

Similarly structured with appropriate risk ceilings, read-only scope, and human gates. Full specifications deferred to implementation authorization.

---

## Risk Assessment

| Pilot | Risk | Mitigation |
|---|---|---|
| CI Triage | R1 | Read-only, no code changes, human gate before any action |
| Governance Drift | R1 | Read-only, proposes corrections only |
| Regression Verify | R1-R2 | Runs approved fixtures only, no production code |
| Documentation Drift | R1 | Read-only, proposes corrections only |

Zero production impact. All loops require explicit approval before scope changes, protected changes, or merges. No autonomous code modifications authorized.

---

## File Manifest

| File | Purpose |
|---|---|
| `LOOP_ENGINEERING_ARCHITECTURE.md` | Architecture + lifecycle |
| `LOOP_CONTROLLER_SPEC.md` | Controller responsibilities |
| `LOOP_ENGINEERING.md` | Schemas, policies, pilots (this file) |
| `.hermes/schemas/loop-contract.schema.json` | Contract schema |
| `.hermes/schemas/loop-state-event.schema.json` | State event schema |

## Change Budget

| Budget | Value |
|---|---|
| max_files | 10 |
| max_folders | 3 |
| max_lines | 2,000 |

## Rollback

```bash
git revert <merge-commit>  # Governance docs only, no production impact
```

## Recommended Implementation Release

**HOS-3 or HOS-4** — after Design Studio is operational and design direction is established. Loop engineering is independent of AVOA visual implementation.

---

*Part of Hermes Product OS v3.1 — Loop Engineering Planning.*