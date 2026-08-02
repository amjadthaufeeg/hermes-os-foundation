# HOS-4 — Program Plan

**Status:** Planning | **Requires:** Amjad approval before implementation

---

## Program Structure

| Release | Scope | Authorization |
|---|---|---|
| **HOS-4A** | Decisions Workspace — read-only | Authorized after planning approval |
| **HOS-4B** | Evidence Workspace — read-only | Authorized after HOS-4A stable |
| **HOS-4C** | Controlled Decision Actions — mutations | **Separate Amjad authorization required** |

---

## Branch Strategy

Separate branches per release for rollback isolation and review quality:

```
feature/HOS-4A-decisions
feature/HOS-4B-evidence
feature/HOS-4C-mutations (planning only)
```

## File Manifest

| File | Deliverables Covered | Type |
|---|---|---|
| `TASK-HOS-4.yaml` | #1 Program contract | Contract |
| `TASK-HOS-4A.yaml` | #3 HOS-4A contract | Contract |
| `TASK-HOS-4B.yaml` | #5 HOS-4B contract | Contract |
| `TASK-HOS-4C.yaml` | #7 HOS-4C contract | Contract |
| `HOS-4-PROGRAM.md` | #2,4,6,8,9,10,11 (consolidated) | Planning |

Consolidation justified: data model, routes, components, source matrix, QA plan are deeply interconnected. Separate files would fragment cross-references.

---

## HOS-4A — Decisions Workspace

### Task Contract

```yaml
task_id: TASK-HOS-4A
project: Hermes Product OS
release: HOS-4A
title: "Decisions Workspace"
task_type: feature
risk_level: R1
```

### Route

`/decisions` — replaces placeholder. Static HTML routing via hash-based navigation (#/decisions).

### Components

| Component | Source | Status |
|---|---|---|
| DecisionList | New | Required |
| DecisionFilter | New | Required |
| DecisionSearch | New | Required |
| DecisionCard | Reuse from MC | Minor adaptation |
| DecisionDetail | New | Required |
| EvidenceSummary | New (shared with HOS-4B) | Required |
| StatusBadge | **Reuse** from HOS-3 | No changes |
| EmptyState | **Reuse** from HOS-3 | No changes |
| StaleState | **Reuse** from HOS-3 | No changes |
| UnavailableState | **Reuse** from HOS-3 | No changes |

Reuses 5 components from HOS-3. Creates 5 new. Total component delta: minimal.

### States

- Default list with decisions
- Filtered list (by state, project, owner, risk)
- Search results
- No results
- Detail view
- Stale evidence on detail
- Unavailable source
- Empty (zero decisions)

### Navigation

- Mission Overview → Decisions (#/decisions)
- Decision list → Decision detail (#/decisions/DEC-HOS-001)
- Decision detail → back to list
- Decision detail → related evidence (HOS-4B link)
- Browser back/forward functional

---

## HOS-4B — Evidence Workspace

### Task Contract

```yaml
task_id: TASK-HOS-4B
project: Hermes Product OS
release: HOS-4B
title: "Evidence Workspace"
task_type: feature
risk_level: R1
```

### Route

`/evidence` — replaces placeholder.

### Components

| Component | Source | Status |
|---|---|---|
| EvidenceList | New | Required |
| EvidenceFilter | New | Required |
| EvidenceCard | New | Required |
| EvidenceDetail | New | Required |
| DecisionLink | New (cross-ref) | Required |
| StatusBadge | **Reuse** | No changes |
| FreshnessIndicator | **Reuse** | No changes |
| Empty/Stale/Unavailable | **Reuse** | No changes |

Reuses 4, creates 5.

### Navigation

- Evidence detail → related decisions (HOS-4A cross-link)
- Evidence list → Evidence detail (#/evidence/EVID-001)
- Decision detail → related evidence (bidirectional)

---

## HOS-4C — Controlled Decision Actions

### Task Contract

```yaml
task_id: TASK-HOS-4C
project: Hermes Product OS
release: HOS-4C
title: "Controlled Decision Actions — Planning and Security"
task_type: infrastructure
risk_level: R3
amjad_approval_required: true
```

### Planning Scope Only

- Authentication model (who can act)
- Authority and role model
- Permission checks per action
- Action eligibility rules
- Explicit confirmation flow
- Mandatory rationale
- Audit event format
- Immutable history
- Timestamp and actor identity
- Idempotency
- Concurrent-update handling
- Stale-record protection
- Rollback design
- Error recovery
- Threat model
- Security review
- Human-gate enforcement

### Actions (FUTURE — not in HOS-4A/4B)

- APPROVE, REJECT, DEFER, RETURN_FOR_REVISION, PLACE_ON_HOLD, RESUME

### Authority Rule

Hermes never approves or rejects on Amjad's behalf. Hermes may recommend, summarize, and identify gaps. Final authenticated human confirmation required.

---

## Decision Data Model

| Field | Source | Trust | Fallback |
|---|---|---|---|
| id | `.hermes/registers/decisions/` | HIGH | UNKNOWN |
| title | Same | HIGH | "Untitled decision" |
| project | Same | HIGH | UNKNOWN |
| state | Same | HIGH | UNKNOWN |
| owner | Same | HIGH | UNKNOWN |
| risk | Same | MEDIUM | UNKNOWN |
| decision text | Same | HIGH | NO DATA |
| reason | Same | HIGH | NO DATA |
| created_at | File timestamp | HIGH | UNKNOWN |
| updated_at | Git log | HIGH | UNKNOWN |
| evidence_refs | Cross-reference | MEDIUM | NO DATA |
| task_refs | Cross-reference | MEDIUM | NO DATA |
| freshness | File age vs current | HIGH | STALE |

## Evidence Data Model

| Field | Source | Trust | Fallback |
|---|---|---|---|
| id | Derived from source | HIGH | UNKNOWN |
| type | Mapped from source type | HIGH | UNKNOWN |
| source_path | File path or API ref | HIGH | UNAVAILABLE |
| produced_at | File/API timestamp | HIGH | UNKNOWN |
| freshness | Age check | HIGH | STALE |
| trust_level | Source classification | MEDIUM | UNKNOWN |
| decision_refs | Cross-reference | MEDIUM | NO DATA |

---

## Change Budgets

| Release | Max Files | Max Lines |
|---|---|---|
| HOS-4A | 8 | 2,000 |
| HOS-4B | 8 | 2,000 |
| HOS-4C (planning) | 5 | 1,500 |

---

## Design Requirements

Frozen HOS-3 baselines intact. No redesign. No new token system. No new colour palette. Preserve: dark graphite, gold authority, cyan execution, amber attention, green verified, red blockers, Inter-preferred font stack, zero external deps.

---

## Responsive Priority

Desktop: list + detail coordinated. Tablet: stack or controlled panel. Mobile: decision title, state, action, risk, evidence — in that order. Blockers and stale evidence never hidden.

## Accessibility

WCAG 2.1 AA. Semantic landmarks, logical headings, native controls, keyboard operation, visible focus, filter labels, disclosure controls, route-change announcements, status text independent of colour.

---

## HOS-4C Security Model

### Threat Model
- Unauthorized decision mutation via unauthenticated access
- State corruption via concurrent writes
- Stale-record mutation (decision changed since loaded)
- Missing audit trail
- Hermes self-approval

### Mitigations
- Authentication required for mutations
- Confirmation with rationale
- Server-side state comparison
- Immutable audit log
- Hermes may recommend, never approve

### Audit Format
```yaml
audit_id: AUD-XXX
decision_id: DEC-XXX
action: APPROVE | REJECT | DEFER | RETURN | HOLD | RESUME
actor: amjad
timestamp: ISO8601
rationale: "required text"
previous_state: AWAITING_AMJAD
resulting_state: CLOSED
idempotency_key: UUID
evidence_commit: SHA
```

---

## CI / Review / Visual Evidence

Standard HOS-3 validated workflow: CI (schema, scope, protected-zone), technical review, visual review, screenshot evidence at 5 breakpoints per release, zero-fabrication audit, secrets scan, rollback verification.

## Rollback

```bash
git revert <merge-commit>  # Per release
```

---

## Recommended Execution Order

1. Amjad approves this planning package
2. Implement HOS-4A (Decisions Workspace)
3. Independent review + merge HOS-4A
4. Implement HOS-4B (Evidence Workspace)
5. Independent review + merge HOS-4B
6. Complete HOS-4C security/mutation plan
7. Amjad separately authorizes HOS-4C mutation implementation

---

*Part of Hermes Product OS v3.2 — HOS-4 Planning.*