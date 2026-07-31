# 15 — Technical Review and Findings Protocol

**Status:** SPECIFICATION
**Version:** 3.1

---

## Purpose

Claude Code is the independent technical reviewer. It operates review-only on the initial pass. All findings flow through Hermes for adjudication before any builder sees them.

---

## Review Package

Claude receives a structured review package:

```yaml
review_package:
  review_id:
  task_id:
  timestamp:
  
  original_request:
  task_contract:
  ui_contract:  # when applicable
  acceptance_criteria:
  relevant_decisions:  # DEC-XXX-NNN records
  relevant_regressions:  # REG-XXX-NNN records
  
  git_diff:
  changed_files:
  builder_report:
  builder_evidence:
  validation_results:
  visual_qa_results:  # when applicable
  
  known_assumptions:
  known_limitations:
```

---

## Review Scope

Claude checks:

1. **Objective completion** — does the implementation achieve the stated objective?
2. **Scope compliance** — are changes within allowed_files and change_budget?
3. **Architecture compliance** — do changes respect architecture decisions?
4. **Business-rule compliance** — are locked decisions respected?
5. **Regression risk** — could this reintroduce known regressions?
6. **Maintainability** — is the code clear, well-structured, documented?
7. **Security** — are there injection, auth, data-exposure, or secret risks?
8. **Test adequacy** — are new code paths tested? Edge cases covered?
9. **Accessibility** — does UI meet baseline accessibility?
10. **Builder-report accuracy** — does the builder's explanation match the actual diff?

---

## Findings Schema

```yaml
review_report:
  review_id:
  task_id:
  reviewer: claude-code
  timestamp:
  
  summary:
    objective_achieved: true|false|partial
    scope_respected: true|false
    tests_sufficient: true|false
    ready_for_correction: true|false
    ready_for_final_validation: true|false
  
  findings:
    - finding_id:
      severity: BLOCKER|HIGH|MEDIUM|LOW|OPTIONAL
      category: security|correctness|scope|architecture|maintainability|testing|accessibility|performance|documentation
      file:
      location:  # line number or range
      description:
      evidence:
      recommendation:
```

### Severity Definitions

| Severity | Meaning | Action |
|---|---|---|
| BLOCKER | Must fix before merge; breaks functionality/security/compliance | Stop, return to builder immediately |
| HIGH | Significant risk or deviation; should fix before merge | Fix in this correction cycle |
| MEDIUM | Noticeable issue; improvement recommended | Fix if correction cycle exists |
| LOW | Minor issue; polish | Optional, record for future |
| OPTIONAL | Enhancement suggestion; not required | Builder discretion |

---

## Hermes Adjudication

For every BLOCKER, HIGH, or MEDIUM finding, Hermes records:

```yaml
finding_decision:
  finding_id:
  decision: accepted|rejected|deferred
  reason:
  approved_correction:  # if accepted
  escalated_to_amjad: true|false
```

### Decision Rules

- **Accepted:** Finding is valid. Approved correction sent to builder.
- **Rejected:** Finding is incorrect, out of scope, or conflicts with authority. Reason documented.
- **Deferred:** Requires more information or product decision. Moves to AWAITING_DECISION.

---

## Correction Flow

1. Hermes adjudicates all findings
2. Only **accepted** findings are sent to builder as approved corrections
3. Builder implements corrections within same task contract (no scope expansion)
4. Corrections re-enter AUTOMATED_VALIDATION → VISUAL_QA → TECHNICAL_REVIEW cycle
5. Max 2 correction cycles before Hermes considers re-routing to Codex

---

## Claude Code Restrictions

Claude must NOT:
- Directly instruct Kimi or any builder
- Change task scope or objectives
- Automatically rewrite the implementation
- Merge code or approve production deployment
- Act as a second orchestrator

Claude may report only: "Review completed with findings."

---

## Reviewer-Driven Architecture Changes

If Claude recommends a broad refactor or architecture change that is not essential to correct the approved contract, it becomes a **separate task**. It does not expand the current task scope.

---

## Fallback Path

Until native Claude Code is authenticated, review may be performed using:
- OpenCode with `anthropic/claude-opus-4.8` via OpenRouter
- Same review package and findings schema
- Clearly labeled as "TEMPORARY FALLBACK — not native Claude Code"
- Documented limitations: no interactive TUI, no `/review` command, no hooks, no worktree isolation

---

*Part of Hermes OS v3.1 — Specification. Awaiting implementation.*