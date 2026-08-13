# HOS-AUTO-01 — Human Courier Elimination: Architecture

**Mode:** DESIGN ONLY — no implementation, no deployment, no VPS changes.  
**Date:** 2026-08-13

---

## 1. Problem

Current workflow is manual and lossy:

```
ChatGPT → Amjad → Terminal → screenshot → ChatGPT
Hermes   → Amjad → ChatGPT  → Amjad → Hermes
```

Amjad manually relays commands and evidence between two AI systems and a terminal. This is slow, error-prone, and screenshots are not machine-readable evidence.

---

## 2. Design Goals

1. **Eliminate routine manual relay** — Hermes submits structured execution contracts directly to a controlled executor.
2. **Preserve fail-closed authority** — the executor is NOT an unrestricted root shell.
3. **Machine-readable evidence** — structured receipts, not screenshots.
4. **Zero autonomous production mutation** — production-impacting operations remain gated.
5. **Constitution compatibility** — the bridge is Hermes' execution arm, not an independent authority.

---

## 3. Core Components

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   HERMES    │────▶│  EXECUTION        │────▶│  CONTROLLED      │
│ orchestrator│     │  BRIDGE (R1)      │     │  EXECUTOR        │
│             │◀────│  policy + contract │◀────│  (sandboxed)     │
└─────────────┘     └──────────────────┘     └─────────────────┘
                          │
                          ├── Contract validation
                          ├── Authority classification
                          ├── Evidence receipt generation
                          ├── Assertion evaluation
                          └── STOP on unexpected result
```

### 3.1 Hermes (existing)
- Sole orchestrator. Creates task contracts. Reviews evidence. Decides next steps.

### 3.2 Execution Bridge (new — R1 scope)
- Receives task contracts from Hermes.
- Validates contract structure + SHA256.
- Classifies authority (AUTO / GATED / FORBIDDEN).
- Dispatches to executor.
- Captures structured results.
- Evaluates assertions.
- Produces immutable evidence receipts.

### 3.3 Controlled Executor (new — R1 scope)
- Runs approved operations in a sandboxed context.
- NOT a generic unrestricted root shell.
- Whitelist of permitted operations per authority class.
- No direct network exposure.
- Docker socket NOT exposed by default.
- No credentials available to the executor process.

---

## 4. Execution Flow

```
1. Hermes drafts task contract (YAML/JSON)
2. Contract SHA256 computed
3. Bridge validates contract structure
4. Bridge classifies authority:
   - AUTO → dispatch immediately
   - GATED → require Amjad authorization token
   - FORBIDDEN → reject
5. Bridge runs preflight (test env validity check)
6. Executor runs approved operations
7. Bridge captures stdout/stderr/exit/state
8. Bridge evaluates assertions automatically
9. Bridge produces evidence receipt (immutable)
10. Result returned to Hermes
```

---

## 5. Key Architectural Principles

| Principle | Rationale |
|---|---|
| **Contract-first** | No ad-hoc shell commands. Every execution has a structured contract. |
| **Authority classification** | Every operation is AUTO, GATED, or FORBIDDEN — evaluated before execution. |
| **Fail-closed executor** | Executor cannot perform operations outside its contract's allowed list. |
| **Immutable receipts** | SHA256-chained receipts, tamper-evident. |
| **Preflight validation** | Test environment verified before tests run (prevents TEST_ENVIRONMENT_INVALID misclassification). |
| **Least privilege** | Executor runs with minimal capabilities, not root. |
| **Single-purpose tokens** | GATED actions require expiring, single-purpose authorization. |

---

## 6. What R1 Is NOT

- NOT an unrestricted AI shell on the VPS.
- NOT a replacement for Hermes orchestration authority.
- NOT a path to autonomous production mutation.
- NOT a full CI/CD platform — R1 is deliberately small and auditable.
- NOT a ChatGPT integration — R1 solves the Hermes↔executor leg first.

---

## 7. Scope Boundaries

**In scope (R1):**
- AUTO operations (read-only, tests, disposable containers, evidence collection)
- GATED operation authorization tokens
- Evidence receipt generation
- Test environment preflight
- Assertion evaluation

**Out of scope (R1):**
- ChatGPT↔Hermes direct integration (Task 5 — future stages)
- Production mutation (FORBIDDEN permanently)
- B7 canary activation (GATED, requires Amjad)
- Full observability platform

---

## 8. Security Posture

- Executor process: non-root, minimal capabilities, no Docker socket, no credentials.
- Contracts: SHA256-hashed, validated before execution.
- Receipts: SHA256-chained, append-only evidence store.
- GATED tokens: single-purpose, expiring, Amjad-authorized.
- FORBIDDEN operations: rejected at contract validation, cannot reach executor.

---

**Architecture design complete. See companion documents for authority model, threat model, execution contract, evidence receipt, implementation plan, and B5 pilot plan.**