# 18 — Evidence and Completion Standard

**Status:** SPECIFICATION
**Version:** 3.1

---

## Purpose

No task is complete because an agent says it is complete. Completion requires structured, verifiable evidence across all required gates. Hermes is the sole authority to declare a task READY_FOR_AMJAD.

---

## Evidence Package Schema

```yaml
evidence_package:
  task_id:
  timestamp:
  compiled_by: hermes

  acceptance:
    criteria_met: true|false|partial
    unmet_criteria:
      - criterion: "Description of unmet criterion"

  scope:
    allowed_files_respected: true|false
    protected_zones_untouched: true|false
    change_budget_respected: true|false
    violations:
      - description:
        severity:

  automated_gates:
    build:
      status: passed|failed|skipped
      evidence: "Build output or link"
    type_check:
      status: passed|failed|skipped
      evidence:
    lint:
      status: passed|failed|skipped
      evidence:
    tests:
      status: passed|failed|skipped
      evidence:
      total: N
      passed: N
      failed: N
    business_fixtures:
      status: passed|failed|skipped
      evidence:
    scope_check:
      status: passed|failed
      evidence:
    protected_zone_check:
      status: passed|failed
      evidence:

  visual:
    screenshots_provided: true|false
    desktop_screenshot:
    tablet_screenshot:
    mobile_screenshot:
    state_screenshots:
      - state: loading|empty|error|success
        path:
    visual_qa_passed: true|false

  review:
    independent_review_completed: true|false
    blocker_findings: N
    high_findings: N
    accepted_findings_resolved: true|false
    findings_summary:

  readiness:
    preview_available: true|false
    preview_url:
    rollback_ready: true|false
    baseline_commit:
    candidate_commit:
    known_limitations:
      - description:

  amjad_approval:
    required: true|false
    status: pending|approved|rejected
```

---

## Completion States and Meanings

| State | Meaning |
|---|---|
| **IMPLEMENTATION_SUBMITTED** | Builder has written code. No gates have run. |
| **AUTOMATED_VALIDATION** | Build, lint, tests, fixtures have run. Results recorded. |
| **VISUAL_QA** | Screenshots captured, visual review performed. |
| **FINDINGS_TRIAGE** | Hermes has adjudicated review findings. |
| **FINAL_VALIDATION** | All gates pass, all accepted findings resolved. |
| **READY_FOR_AMJAD** | Hermes declares: all required evidence collected, all gates green, ready for human approval. |
| **APPROVED** | Amjad has reviewed and approved. |
| **MERGED** | Code is in the protected branch. |
| **DEPLOYED** | Code is running in production. |
| **MONITORED** | Post-deployment observation period complete. |
| **CLOSED** | Task record archived. |

---

## Evidence Requirements by Risk Level

| Evidence | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| Build passes | ✓ | ✓ | ✓ | ✓ |
| Type check passes | ✓ | ✓ | ✓ | ✓ |
| Lint passes | ✓ | ✓ | ✓ | ✓ |
| Tests pass | ✓ | ✓ | ✓ | ✓ |
| Scope check | ✓ | ✓ | ✓ | ✓ |
| Protected zone check | ✓ | ✓ | ✓ | ✓ |
| Change budget check | — | ✓ | ✓ | ✓ |
| Screenshots (visual) | ✓ | ✓ | ✓ | ✓ |
| Accessibility baseline | — | ✓ | ✓ | ✓ |
| Business fixtures | — | — | — | ✓ |
| Independent review | ✓ | ✓ | ✓ | ✓ |
| Rollback package | — | ✓ | ✓ | ✓ |
| Amjad approval | ✓ | ✓ | ✓ | ✓ |

---

## What Hermes Must NOT Do

- Mark a task complete with missing evidence
- Fabricate gate results for unimplemented checks
- Claim Claude Code review occurred when not authenticated
- Declare READY_FOR_AMJAD without all required evidence
- Skip Amjad approval when required

---

*Part of Hermes OS v3.1 — Specification. Awaiting implementation.*