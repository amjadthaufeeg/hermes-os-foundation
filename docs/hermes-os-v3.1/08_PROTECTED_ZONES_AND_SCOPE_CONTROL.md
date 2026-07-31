# 08 — Protected Zones and Scope Control

**Status:** SPECIFICATION
**Version:** 3.1

## Protected Zones (AVOA Repository)

See machine-readable policy at `.hermes/policies/protected-zones.yaml` for the complete path listing.

### Domains and Risk Levels

| Domain | Risk | Unlock Authority |
|---|---|---|
| Pricing engine | R4 | Amjad |
| Offer engine | R4 | Amjad |
| Occupancy engine | R4 | Amjad |
| Tax logic | R4 | Amjad |
| Markup and commission | R4 | Amjad |
| Cancellation logic | R4 | Amjad |
| Reconciliation | R4 | Amjad |
| Authentication | R3 | Hermes |
| Permissions | R3 | Hermes |
| Database schema | R3 | Hermes |
| Migrations | R3 | Hermes |
| Reservation state machine | R3 | Hermes |
| API contracts | R3 | Hermes |
| Audit records | R3 | Hermes |
| Design system foundations | R2 | Design Studio lead |

## Enforcement

**Current (transition):** Prompt-based + procedural. AGENTS.md and task contracts define boundaries.

**Target:** Automated via CI gate — diff-check script compares changed files against `protected-zones.yaml`.

## SCOPE_EXCEEDED Protocol

On detection of unauthorized protected-area change:
1. Stop work immediately
2. Mark task state: `SCOPE_EXCEEDED`
3. Return to Hermes for disposition
4. Builder must NOT continue or widen scope

## Change Budgets

Default budgets per risk level — individual task contracts may set tighter limits:

| Risk | Max Files | Max Folders | Max Lines | New Deps | Migrations |
|---|---|---|---|---|---|
| R1 | 5 | 3 | 200 | N/A | N/A |
| R2 | 15 | 5 | 500 | With approval | N/A |
| R3 | 10 | 3 | 300 | No | No |
| R4 | 5 | 2 | 200 | No | No |

Budgets are safety boundaries, not performance targets. Hermes may revise only after reviewing why additional scope is necessary.

## Unlock Procedure

1. Builder or Hermes identifies need to touch protected zone
2. Hermes evaluates: is the change within task objectives?
3. If yes, Hermes requests unlock (or escalates to Amjad for R4)
4. Unlock recorded with: task ID, zone, reason, scope, duration
5. After task closure, zone returns to protected state

## Emergency Override

Authorized by Amjad only. Must record: authorization, reason, time, scope. Post-emergency full review required.

---

*Part of Hermes OS v3.1 — Specification.*