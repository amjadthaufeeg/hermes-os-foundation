# Hermes Product OS v3.2 — Operating Model Refinement

**Status:** Specification | **Version:** 3.2 | **Date:** 1 Aug 2026

---

## 1. Purpose

v3.2 removes ambiguity from the v3.1 operating model. It introduces earned authority, clarifies the human-control boundary, formally separates agents from tools, and adds delivery-oriented maturity tracking.

This is a planning and documentation refinement. No runtime activation. No new architectural layers.

After v3.2 is merged, the operating model is **feature-frozen** until real operational evidence justifies another change.

---

## 2. Maturity Model

Every capability, loop, agent role, and operational component must carry its current maturity state.

| Dimension | Values |
|---|---|
| **SPECIFICATION** | COMPLETE / PARTIAL / PLACEHOLDER / NOT_DEFINED |
| **IMPLEMENTATION** | IMPLEMENTED / NOT_IMPLEMENTED |
| **ACTIVATION** | ACTIVE / INACTIVE / PAUSED |
| **OPERATIONAL MATURITY** | UNPROVEN / PILOT / PROBATION / PROVEN / SUSPENDED |

Maturity advances through demonstrated reliable performance. No agent or tool self-declares its maturity. PROVEN status requires Hermes recommendation and Amjad acknowledgment. Maturity can be revoked at any time.

---

## 3. Current Hermes Maturity

**Hermes authority stage: STAGE_1_ASSISTED_ORCHESTRATION**

Reason:
- Hermes prepares contracts, routes work, and coordinates evidence.
- Every material task still requires Amjad approval.
- No runtime loops are active.
- No Capability Managers are active.
- No production feature has shipped through the complete model.
- Several role and reporting deviations required human correction.
- Runtime observability and execution controls are not yet implemented.

### Stage Definitions

| Stage | Name | Criteria |
|---|---|---|
| 0 | Human-Orchestrated | Amjad performs all orchestration directly |
| **1** | **Assisted Orchestration** | **Hermes drafts, recommends, coordinates. Amjad approves. Current.** |
| 2 | Supervised Orchestration | Hermes approves R1-R2 tasks within contracts. Amjad approves R3+. |
| 3 | Conditional Orchestration | Hermes manages complete cycles with human gates only at key transitions. |
| 4 | Capability-Specific Autonomy | Hermes operates autonomously within proven capabilities. Amjad reserves commercial and critical gates. |

### Promotion Criteria

**To Stage 2:** Successful Navigation Component pilot; no unresolved scope/authority violations; complete evidence; stable CI; successful independent review; verified rollback; Amjad approval.

**To Stage 3:** Ten successfully governed tasks; three production features; acceptable regression/reopen rates; no bypassed human gates; operational observability active; Amjad approval.

**To Stage 4:** Capability-specific. Requires proven performance in that capability. Separately authorized.

---

## 4. Agents vs. Tools — Formal Separation

### Agents (Directed Actors)

Agents receive task contracts, make implementation decisions, and produce work. Their output is reviewed. They earn operational maturity.

| Agent | Role | Spec | Impl | Activation | Maturity |
|---|---|---|---|---|---|
| **Kimi K3** | Primary Builder | COMPLETE | NOT_IMPLEMENTED | INACTIVE | UNPROVEN |
| **Codex** | Precision Builder | COMPLETE | NOT_IMPLEMENTED | INACTIVE | UNPROVEN |

### Tools (Directed Instruments)

Tools perform verification, review, or rendering. Their output is evidence — accepted or rejected by Hermes. Tools are validated every time.

| Tool | Function | Activation | Maturity |
|---|---|---|---|
| **Claude Code** | Reviewer interface | INACTIVE | UNPROVEN |
| **GitHub Actions** | CI/CD, validation gates | ACTIVE | PROVEN |
| **GitHub** | Source of truth | ACTIVE | PROVEN |
| **Replit** | Live Preview | INACTIVE | UNPROVEN |
| **OpenCode** | Claude fallback interface | INACTIVE | UNPROVEN |
| **DeepSeek V4 Pro** | Optional research | ACTIVE | RESTRICTED |

### Role / Model / Tool / Platform Separation

| Category | Examples | Maturity |
|---|---|---|
| **Organizational Roles** | Product Owner, Lead Builder, Precision Builder, Independent Technical Reviewer, Visual QA | Assigned per task |
| **Execution Agents/Models** | Kimi K3, Codex, Claude model, DeepSeek V4 Pro | Varies |
| **Agent Tools/Interfaces** | Claude Code, OpenCode, Hermes runtime, GitHub CLI | Varies |
| **Platforms/Infrastructure** | GitHub, GitHub Actions, Replit, Deployment platform | Varies |

Claude Code is the **tool** through which the Claude **model** performs the **Independent Technical Reviewer role**. These are distinct concepts.

---

## 5. Fallback Orchestration Policy

### Normal Path

Amjad → Hermes-assisted orchestration → Approved builder → Automated validation → Independent review → Hermes finding triage → Amjad approval.

### Probation Breach

When Hermes breaches probation:
- Stop new Hermes-routed work.
- Preserve current branches and evidence.
- Mark Hermes maturity **SUSPENDED**.
- Return active work to **AWAITING_HUMAN_GATE**.
- Amjad becomes direct orchestrator.
- CI, protected-zone, and review gates remain active.

### Direct-Orchestration Fallback

Amjad may directly: define the task, select Kimi or Codex, select the reviewer, approve corrections, approve merge.

Hermes may remain read-only for: context retrieval, evidence collection, status reporting.

### Suspension Triggers

- Unauthorized scope expansion
- Bypassed human gate
- False readiness claim
- Repeated missing evidence
- Unauthorized production change
- Repeated unreported provider stalls
- Repeated role-boundary violation
- Unresolved critical review finding
- Self-expansion of permissions
- Repeated regression caused by orchestration

### Restoration

Hermes may be restored only after: root-cause review, corrective controls, successful probation task, independent review, Amjad approval.

---

## 6. Human-Gate Matrix

| Action | R1 | R2 | R3 | R4 | Approver | Entry Evidence | Exit Evidence |
|---|---|---|---|---|---|---|---|
| Task-contract approval | Amjad | Amjad | Amjad | Amjad | Amjad | Task contract, risk classification | Approved contract |
| Scope expansion | Hermes | Amjad | Amjad | Amjad | Amjad (R2+) | Original contract, proposed expansion | Amended contract |
| Protected-zone authorization | Amjad | Amjad | Amjad | Amjad | Amjad | Protected zone, change detail, justification | Authorization record |
| Implementation auth | Amjad | Amjad | Amjad | Amjad | Amjad | Approved contract | Dispatch record |
| Correction auth | Hermes | Amjad | Amjad | Amjad | Amjad (R2+) | Review findings, proposed correction | Correction contract |
| Merge | Amjad | Amjad | Amjad | Amjad | Amjad | CI pass, review pass, findings resolved, rollback | Merge commit |
| Deployment | Amjad | Amjad | Amjad | Amjad | Amjad | Merge, post-merge CI, rollback package | Deployment record |
| Rollback | Amjad | Amjad | Amjad | Amjad | Amjad | Affected commit, rollback procedure | Reverted state |
| Irreversible action | Amjad | Amjad | Amjad | Amjad | Amjad | Action detail, impact, alternatives | Confirmation record |
| Capability activation | Amjad | Amjad | Amjad | Amjad | Amjad | Capability spec, risk assessment, pilot results | Activation record |
| Loop activation | Amjad | Amjad | Amjad | Amjad | Amjad | Loop contract, pilot results | Activation record |
| Recurring schedule | Amjad | Amjad | Amjad | Amjad | Amjad | Schedule spec, risk assessment | Schedule record |
| Permission expansion | Amjad | Amjad | Amjad | Amjad | Amjad | Current permissions, proposed expansion, justification | Updated permissions |
| Model-roster change | Amjad | Amjad | Amjad | Amjad | Amjad | Evidence, benchmarks, risk assessment | Updated roster, decision record |

**During Stage 1:** Amjad approves every production implementation, merge, deployment, protected-zone change, capability activation, and loop activation. Human gates have no timeout override. Silence is not approval.

---

## 7. Product and Architecture Responsibility

### Executive and Product

**Owner:** Amjad

Responsibilities: product direction, priorities, roadmap, business outcome, commercial acceptance, final product approval.

### Architecture

**Accountable authority:** Amjad during Stage 1.

Advisory/drafting: Hermes, designated Architect role, approved technical reviewer.

Responsibilities: system boundaries, API contracts, data architecture, event architecture, security architecture, scalability, technical standards, cross-system dependencies.

Builders may implement approved architecture. Builders may not redefine architecture informally. Material architecture changes require: decision record, impact assessment, migration plan, rollback, Amjad approval.

---

## 8. Division Clarification

Divisions are responsibility domains — not claims that Hermes Product OS has seven staffed departments. A human, model, or tool may serve multiple roles, each under its own permissions and contract.

| Division | Owner | Status | Purpose |
|---|---|---|---|
| Executive | Amjad | ACTIVE | Product direction, business authority |
| Engineering | Hermes | ACTIVE (planning) | Capabilities, loops, task execution |
| Design Studio | Design Studio | PLANNED | Visual and interaction quality |
| Quality | Hermes | ACTIVE (planning) | Gates, reviews, evidence |
| Knowledge | Hermes | PLANNED | Decisions, regressions, memory |
| Research | Research Div | PLANNED | Read-only evidence and analysis |
| Operations | Hermes | PLANNED | CI, deployment, monitoring |

Planned divisions are not active operational teams. They activate when their first runtime responsibility is authorized.

---

## 9. Builder-Selection Policy

### Roster Statuses

PROVISIONAL / PILOT / APPROVED / RESTRICTED / SUSPENDED

### Selection Criteria

Task type, risk level, golden-task performance, regression fixtures, scope adherence, correctness, review findings, correction rate, timeout rate, execution speed, cost, evidence quality, tool availability.

### Current Roster

| Model | Role | Status | Reason |
|---|---|---|---|
| **Kimi K3** | Primary Builder | **PROVISIONAL** | Selected through observed use; no comparative benchmarks |
| **Codex** | Precision/Fallback Builder | **PROVISIONAL** | Observed reliability for narrow corrections; no formal comparison |
| **Claude model** | Independent Technical Reviewer | **PILOT** | Multiple useful reviews; reviewer has produced factual errors requiring human verification |
| **DeepSeek V4 Pro** | Optional research/challenger | **RESTRICTED** | Repeated timeouts; zero successful HOS-2 specialist completions |

No model is classified as PROVEN without comparative evidence.

### Model-Roster Change Rule

Every change requires: reason, evidence, benchmark/observed task record, risk impact, fallback, Amjad approval, effective date, review date. Flow: Evidence → Recommendation → Decision → Amjad → Policy update → Pilot → Review.

---

## 10. Delivery Metrics

| Metric | Formula | Status |
|---|---|---|
| Features shipped | Count of production features merged, deployed, accepted | **NO_BASELINE** |
| Production releases | Count of verified production releases | **NO_BASELINE** |
| Lead time | Approved request → production acceptance | **NOT_MEASURED** |
| Cycle time | BUILDING → READY_FOR_AMJAD / CLOSED | **INSUFFICIENT_DATA** |
| Regression rate | Verified regressions / completed production tasks | **NO_BASELINE** |
| Reopened-task rate | Tasks reopened / approved tasks | **NOT_MEASURED** |
| Scope-violation rate | SCOPE_EXCEEDED / executed tasks | **INSUFFICIENT_DATA** |
| Human coordination burden | Count + time of Amjad interventions / completed task | **NOT_MEASURED** |

All metrics are advisory. They inform routing and maturity decisions — they do not replace human judgment. No targets are set until baseline data exists.

---

## 11. Operating-Model Evaluation Framework

### Review Questions

- What production value was shipped?
- Did regressions decrease? Did rework decrease?
- Did cycle time improve?
- Did Hermes reduce Amjad's coordination burden?
- Did evidence quality improve?
- Were unsafe changes prevented?
- Did governance create excessive delay?
- Were model assignments effective?
- Were provider stalls handled correctly?

### Review Triggers

- First Navigation Component pilot
- First three production features
- First ten governed tasks
- First rollback or major regression
- Three months of operation

### Review Outcomes

**CONTINUE** — Operating model is working. Continue with current settings.
**SIMPLIFY** — Remove excessive governance that produced no safety benefit.
**SUSPEND** — Pause governed operation. Return to direct orchestration.
**ROLL_BACK** — Revert to previous operating model version.
**REVISE** — Targeted changes to specific policies without full model change.

The OS must be capable of failing its own evaluation.

---

## 12. Observability and Execution Budgets

### Required Visible State

Task ID, current stage, active agent/model, provider, branch, HEAD commit, last successful action, last heartbeat, runtime, files changed, commits created, validation cycles, repair cycles, external retries, provider status, current blocker, remaining budget, next gate, safest resume point.

### Default Controls

```yaml
execution_controls:
  heartbeat_interval_minutes: 2
  silent_warning_minutes: 5
  checkpoint_interval_minutes: 15
  provider_timeout_minutes: 8
  max_provider_retries: 1
  max_repair_cycles: 3
  max_validation_cycles: 4
  max_external_retries: 5
  max_runtime_minutes: 30
```

**Current state:** Specification COMPLETE. Implementation NOT_IMPLEMENTED. Activation INACTIVE. Maturity UNPROVEN.

---

## 13. Capability Status Model

| CAP | Spec | Impl | Activation | Maturity | Health |
|---|---|---|---|---|---|
| CAP-001 Commercial Safety | COMPLETE | NOT_IMPLEMENTED | INACTIVE | UNPROVEN | UNKNOWN |
| CAP-002 Design Quality | COMPLETE | NOT_IMPLEMENTED | INACTIVE | UNPROVEN | UNKNOWN |
| CAP-003 Documentation Health | COMPLETE | NOT_IMPLEMENTED | INACTIVE | UNPROVEN | UNKNOWN |
| CAP-004 Release Readiness | PLACEHOLDER | NOT_IMPLEMENTED | INACTIVE | UNPROVEN | UNKNOWN |
| CAP-005 Engineering Health | PLACEHOLDER | NOT_IMPLEMENTED | INACTIVE | UNPROVEN | UNKNOWN |
| CAP-006 Research Intelligence | PLACEHOLDER | NOT_IMPLEMENTED | INACTIVE | UNPROVEN | UNKNOWN |
| CAP-007 Knowledge Integrity | PLACEHOLDER | NOT_IMPLEMENTED | INACTIVE | UNPROVEN | UNKNOWN |
| CAP-008 Operations | PLACEHOLDER | NOT_IMPLEMENTED | INACTIVE | UNPROVEN | UNKNOWN |

No capability may display HEALTHY before runtime evidence exists.

---

## 14. Loop Status Model

| Loop | Access | Impl | Activation | Maturity |
|---|---|---|---|---|
| LOOP-PILOT-001 CI Triage | Read-only | NOT_IMPLEMENTED | INACTIVE | UNPROVEN |
| LOOP-PILOT-002 Governance Drift | Read-only | NOT_IMPLEMENTED | INACTIVE | UNPROVEN |
| LOOP-PILOT-003 Regression Verify | Test-only | NOT_IMPLEMENTED | INACTIVE | UNPROVEN |
| LOOP-PILOT-004 Documentation Drift | Read-only | NOT_IMPLEMENTED | INACTIVE | UNPROVEN |

**Zero runtime loops active.**

---

## 15. v3.2 Migration Plan

| Phase | Description | Entry | Rollback |
|---|---|---|---|
| A — Documentation | Complete all v3.2 specs and diagrams | Correction authorization | Revert docs |
| B — Validation | Remote CI + independent review | Phase A complete | Fix findings |
| C — Merge | Amjad approval + merge to main | Phase B pass | Revert merge |
| D — Feature Freeze | Freeze architectural expansion | Phase C complete | Unfreeze by Amjad |
| E — Operational Evidence | Navigation pilot + governed tasks | Phase D complete + separate auth | Pause tasks |
| F — Maturity Review | Evaluate Stage 1→2 promotion | Phase E complete | Remain at Stage 1 |

No phase activates automatically. Each requires explicit authorization.

---

## 16. Independent Review Plan

Reviewer: Independent Technical Reviewer through Claude Code or OpenCode + Claude fallback.

Scope: completeness, consistency, authority clarity, probation model, fallback path, human-gate precision, role/model/tool/platform separation, roster rationale, delivery metrics, evaluation framework, observability, diagram accuracy, feature-freeze safety, governance overhead, planning-only compliance.

Findings: BLOCKER / HIGH / MEDIUM / LOW / OPTIONAL. All BLOCKER and HIGH must be resolved.

---

## 17. v3.2 Operating Principles

**P1 — Evidence Before Trust:** Trust earned through repeated evidence. No agent starts trusted.
**P2 — Human Gate Is Absolute:** No timeout override. No silent escalation.
**P3 — Separation of Generation and Evaluation:** Builder never sole evaluator.
**P4 — Default Closed:** Protected zones and permissions default closed.
**P5 — Delivery Over Activity:** Verified, accepted evidence is the only measure.
**P6 — Maturity Is Earned:** Never self-declared. Can be revoked.
**P7 — Feature Freeze Is Binding:** After merge, changes require operational evidence.

---

## 18. Feature-Freeze Policy

Effective after: all deliverables complete, both diagrams exist, independent review passes, remote CI passes, Amjad approves merge, post-merge CI passes.

Freeze applies to: architectural expansion, new organizational layers, new divisions, new agent roles.

Freeze does not apply to: bug fixes, evidence corrections, security fixes, compliance fixes, operational simplification, changes required by observed runtime failure.

---

*Hermes Product OS v3.2 — Feature-frozen after merge.*