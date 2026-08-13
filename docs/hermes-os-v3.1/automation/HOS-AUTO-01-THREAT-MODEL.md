# HOS-AUTO-01 — Threat Model

**Design only. Findings classified P0-P3.**

---

## Threat Inventory

### 1. Prompt Injection Through Logs — P0 CRITICAL

**Attack:** Production/container logs contain attacker-controlled text (decision rationale, error messages, user input). An agent that reads these logs could be manipulated into executing unintended operations.

**Mitigation:**
- The bridge never passes raw log content as *instructions* to any agent.
- Log content is treated strictly as *data*, never as *control*.
- Receipts store logs verbatim but flagged `content-type: data`.
- Any operation derived from log content requires a fresh contract, not in-line interpretation.

### 2. Malicious Repository Content — P0 CRITICAL

**Attack:** A pushed commit contains a test that exfiltrates credentials, a build script that modifies production, or a malicious `conftest.py` / `pytest` plugin.

**Mitigation:**
- Executor runs tests in a disposable, network-isolated container.
- Test code has NO access to production credentials, Docker socket, or host network.
- Source SHA pinned in contract; executor checks out exact SHA.
- Preflight verifies source provenance before execution.

### 3. Command Injection — P0 CRITICAL

**Attack:** Malformed contract field (working_directory, path, argument) is interpolated into a shell command.

**Mitigation:**
- No shell string interpolation. Executor uses `execve`-style argument arrays.
- All dynamic values are validated against allowlists / regex.
- Paths are resolved and canonicalized; no `sh -c` with untrusted strings.

### 4. Task-Contract Tampering — P0 CRITICAL

**Attack:** An attacker modifies the contract between Hermes drafting it and the bridge validating it (e.g., to upgrade a FORBIDDEN op to AUTO).

**Mitigation:**
- Contract SHA256 computed at draft time.
- Bridge recomputes and compares before execution.
- Mismatch → STOP, contract rejected.
- Receipts record contract SHA; any change invalidates.

### 5. Stale Authorization Reuse — P1 BLOCKER

**Attack:** A GATED token is captured and replayed for a different operation.

**Mitigation:**
- Tokens are single-purpose, single-use, expiring.
- Consumed on first execution.
- Bound to `task_id` + `contract_sha256`.
- Replay → token invalid.

### 6. Path Traversal — P1 BLOCKER

**Attack:** `working_directory=../../etc` escapes sandbox.

**Mitigation:**
- Canonicalize + resolve paths.
- Enforce allowed-root prefix (e.g., `/opt/hermes-auto/`).
- Reject symlink escapes.

### 7. Symlink Attacks — P1 BLOCKER

**Attack:** Symlink in working dir points to a production path; executor writes through it.

**Mitigation:**
- `realpath` resolution before any write.
- Reject any path resolving outside the allowed root.
- `O_NOFOLLOW` where applicable.

### 8. Environment-Variable Poisoning — P1 BLOCKER

**Attack:** `MUTATIONS_DISABLED=false`, `DATABASE_PATH=/production.db`, or `HERMES_ENVIRONMENT` injected into executor env to change behavior.

**Mitigation:**
- Executor env is explicitly allowlisted.
- Production-critical env vars are never inherited from untrusted input.
- Contract defines exact env; nothing else is set.

### 9. Privilege Escalation — P0 CRITICAL

**Attack:** Executor process gains root or escapes sandbox.

**Mitigation:**
- Executor runs as non-root UID.
- `cap_drop ALL`, `no-new-privileges`.
- No setuid binaries reachable.

### 10. Unrestricted Shell Escape — P0 CRITICAL

**Attack:** A "read-only" command actually opens a shell or arbitrary command execution.

**Mitigation:**
- Whitelist of exact command paths (not `sh`, not `bash`, not `eval`).
- No shell metacharacter processing.
- Operation allowlist enforced by executor, not by prompt.

### 11. Docker Socket Abuse — P0 CRITICAL

**Attack:** Executor mounts `/var/run/docker.sock` and controls production containers.

**Mitigation:**
- Docker socket NOT mounted into executor by default.
- Disposable-container operations use a restricted Docker context.
- Production container control requires GATED token + explicit socket grant.

### 12. Credential Exposure — P0 CRITICAL

**Attack:** Credentials leak into logs, receipts, or evidence artifacts.

**Mitigation:**
- Executor has NO credentials in its environment.
- Receipts redact `authorization`, `cookie`, `x-api-key`, `token`, `secret`, `key`.
- Pre-commit/Pre-receipt redaction pass.

### 13. Evidence Tampering — P1 BLOCKER

**Attack:** Evidence is modified after collection to hide a failure.

**Mitigation:**
- Receipts are SHA256-chained (each references previous).
- Append-only evidence store.
- Receipt SHA computed at creation; verified on read.

### 14. Log Tampering — P1 BLOCKER

**Attack:** stdout/stderr edited post-execution.

**Mitigation:**
- Captured at source, hashed immediately.
- Stored with receipt; hash mismatch → receipt invalid.

### 15. Replay Attacks — P1 BLOCKER

**Attack:** A valid GATED token/receipt is replayed to re-run an operation.

**Mitigation:**
- Single-use tokens, nonce, timestamp check.
- Receipts are evidence, not authorization — cannot be replayed as commands.

### 16. Concurrent Execution Conflicts — P2 HARDENING

**Attack:** Two executions run simultaneously, race on shared state (e.g., two restarts).

**Mitigation:**
- Lock per task/resource (`flock`/DB lock).
- Concurrent conflicting operations rejected.

### 17. Race Conditions — P2 HARDENING

**Attack:** TOCTOU between check and use (e.g., file checked then replaced).

**Mitigation:**
- Atomic operations where possible.
- Hash verification after read.
- Documented residual risk in receipts.

### 18. Agent Attempting Forbidden Operations — P0 CRITICAL

**Attack:** The agent (Hermes) itself drafts a contract with a FORBIDDEN operation.

**Mitigation:**
- Bridge classifies independently of Hermes.
- FORBIDDEN list is hardcoded, not negotiated.
- Even Hermes cannot reclassify a FORBIDDEN op as GATED/AUTO.

### 19. Malformed Task Contracts — P1 BLOCKER

**Attack:** Structurally invalid contract causes bridge crash or ambiguous behavior.

**Mitigation:**
- Strict schema validation.
- Malformed → STOP, no execution.
- Parser fuzz-tested.

### 20. Compromised Builder Output — P2 HARDENING

**Attack:** A builder (Kimi/Codex) emits a malicious patch that passes tests but alters production behavior.

**Mitigation:**
- Independent review (Claude) remains a gate.
- Production-impacting changes always GATED.
- Diff is part of evidence, reviewed by Hermes.

### 21. Compromised Reviewer Output — P2 HARDENING

**Attack:** Reviewer approves malicious code.

**Mitigation:**
- Hermes retains review-triage authority (accept/reject findings).
- Reviewer findings are data, not authorization.

---

## Classification Summary

| Severity | Count | Items |
|---|---|---|
| **P0 CRITICAL** | 8 | Prompt injection, malicious repo, command injection, contract tampering, privilege escalation, shell escape, Docker socket, credential exposure, agent forbidden ops |
| **P1 BLOCKER** | 7 | Stale token, path traversal, symlink, env poisoning, evidence/log tampering, replay, malformed contract |
| **P2 HARDENING** | 4 | Concurrency, race conditions, compromised builder/reviewer |
| **P3 FUTURE** | 0 | — |

---

## Mitigation Priority

R1 must address **all 8 P0 CRITICAL** findings before any execution is permitted against shared infrastructure. The P1 items must be addressed before GATED operations are enabled. P2 items are hardening for later iterations.

---

**Threat model complete.**