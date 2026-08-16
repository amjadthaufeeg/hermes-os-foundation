# Hermes OS Final Operations Runbook

**Status:** Closure-candidate operational handoff  
**Authority:** Existing Hermes OS authority model; this runbook does not expand authority.  
**Purpose:** Give operators and future agents one concise reference for normal operation, diagnosis, recovery, rollback, credentials, monitoring, and Amjad approval gates.

## 1. Operational architecture

The control path is:

`ChatGPT task -> private hermes-control R2 Issue -> hermes-r2-watcher (hermes-auto) -> HOS-AUTO-01 typed bridge -> optional privileged broker for allow-listed read-only/container operations -> evidence receipt -> private hermes-control completed result`.

Key boundaries:

- `hermes-auto` is unprivileged and has no sudo, Docker group, root SSH, or arbitrary shell operation.
- The source checkout used for execution is immutable/read-only from the watcher perspective and is bound to `contract.source_git_sha` during preflight.
- R2 transport identity (`issue:<number>:<body_sha>`) is separate from execution Git identity.
- Privileged actions use typed broker operations only; there is no generic privileged command channel.
- Production mutations remain disabled unless separately authorized through the existing GATED model.

## 2. Authority model

Three authority classes apply:

- **AUTO:** inspection, tests, evidence collection, approved disposable/lab operations and other allow-listed actions that cannot mutate protected production state.
- **GATED:** actions that cross a protected operational boundary and require explicit Amjad approval before execution.
- **FORBIDDEN:** operations that Hermes must never execute, including arbitrary root/shell escalation and protected production/destructive operations outside approved gates.

A task's requested authority never overrides independent classification. A mismatch is rejected.

## 3. Normal R2 task lifecycle

1. Accept only the fixed private `hermes-control` repository and approved issue author/title policy.
2. Fetch issue twice and bind processing to the issue body SHA to detect edit races.
3. Validate schema, TTL, depth, nonce/replay limits, transport and rate limits.
4. Independently classify authority.
5. Atomically claim the task.
6. Build a local typed HOS-AUTO-01 contract.
7. Run preflight against the contract's execution Git SHA.
8. Execute only typed operations.
9. Evaluate assertions.
10. Persist an evidence receipt and publish the structured result to `tasks/completed/`.

A PASS is not inferred from transport success; it requires a bridge PASS and required assertions.

## 4. Environment invariants

The watcher service must preserve all of the following:

- `User=hermes-auto`, `Group=hermes-auto`
- `NoNewPrivileges=yes`
- `ProtectSystem=strict`
- `ProtectHome=yes`
- no Docker socket/group access
- no sudo/root SSH path
- source/install code read-only to the watcher
- writable state limited to explicit runtime/evidence/log paths
- broker socket is the only privileged execution path

Because `ProtectSystem=strict` makes standard temporary locations unavailable inside the service namespace while pytest and Python `tempfile` require a writable temporary directory, the watcher service sets `TMPDIR=/var/lib/hermes-auto`, an already-approved writable runtime-state path. This does not make source or production data writable.

## 5. Evidence and observability

Every bridge execution produces a cryptographic receipt containing task/contract/source identity, environment fingerprint, executed operations, assertions, state-change declaration and verdict.

For non-PASS execution, the bridge emits a compact `DETAIL|...` line containing the execution id, failing operation/stage, exit code and output tail. R2 preserves this in the result summary so routine diagnosis does not require Amjad to SSH into the VPS.

Primary evidence locations:

- HOS evidence root: `/opt/hermes-auto/evidence`
- R2 persistent state: `/var/lib/hermes-auto/state/r2-state.json`
- private result publication: `hermes-control/tasks/completed/`
- service logs: systemd journal

## 6. Snapshot / recovery baseline

The snapshot refresh design uses SQLite `.backup`, integrity checking, schema validation, atomic rename, SHA-256 metadata and old-snapshot preservation on failure.

The checked-in refresh timer runs every 900 seconds with up to 30 seconds randomized delay and `Persistent=true`. The design therefore targets a normal refresh interval no greater than 15 minutes 30 seconds, excluding an active failure condition. B6 certification must retain measured live evidence for actual snapshot age and restore time; design cadence alone is not sufficient certification.

The staging recovery target used by HOS tests is:

- RPO target: <= 24 hours
- RTO target: <= 2 hours

Final B6 certification should use stricter measured values when the live snapshot cadence is better than these upper bounds.

## 7. Restart and replay recovery

Persistent R2 state survives watcher process/module restart and stores seen nonces, completed task ids, failure tracking and processed issue versions. Replay attempts must be rejected after restart.

Live restart certification requires a controlled watcher restart followed by:

1. service active as `hermes-auto`;
2. previous replay nonce remains rejected;
3. a fresh AUTO task is accepted and reaches PASS;
4. no manual state-file clearing is required.

Restarting or replacing the root-owned systemd unit is GATED.

## 8. Failure handling

When a task fails:

1. Use the published `DETAIL|...` diagnostic and receipt first.
2. Use further read-only typed tasks for logs/files/timers only when required.
3. Do not ask Amjad to act as a log or command courier for AUTO diagnostics.
4. If the root cause is source code, patch in GitHub, review the exact diff, merge to the authoritative branch, then deploy only through the correct authority boundary.
5. If the fix changes a root-owned service/unit/broker or protected runtime state, stop at the GATED deployment boundary and request explicit Amjad approval.

Never weaken systemd hardening merely to make a test pass; fix the minimum runtime requirement within already-approved writable areas.

## 9. Rollback

For a root-owned deployment, preserve the previous known-good file/unit before replacement. If post-deployment acceptance fails:

1. restore the previous known-good artifact;
2. reload systemd only if a unit changed;
3. restart only the affected HOS service;
4. verify service identity/hardening and a read-only acceptance task;
5. record the failed source SHA and evidence receipt.

Production database/snapshot rollback is a separate protected operation and is never implied by an HOS watcher rollback.

## 10. Credentials

Credentials are fixed-path, least-privilege resources and are never task-controlled:

- R2 GitHub Issues token: read-only issue access for the fixed private control repo.
- R2 deploy key: repository-scoped result/claim publication.
- Credentials must not be printed, copied into receipts, committed to Git, accepted from task payloads, or exposed through generic read operations.

Credential rotation and permission expansion are GATED operational changes.

## 11. Monitoring / Mission Control minimum

Mission Control should surface at minimum:

- overall HOS completion percentage;
- `ACTIVE`, `WAITING`, `BLOCKED`, or `IDLE` state;
- current mission/task;
- last activity time;
- current blockers;
- next action;
- whether manual Amjad action is required;
- watcher/broker/timer health and latest evidence/result state.

`hermes-control` remains the control/evidence source of truth; Mission Control is the visibility layer.

## 12. Closure / freeze rule

HOS may be declared complete only after the closure tracker gates are evidenced, including fresh R2 PASS, measured B6 RPO/RTO, final regression/security PASS, live restart/replay proof, stale-state cleanup, authoritative freeze/tag, runbook handoff and Mission Control visibility.

Final success marker:

`HOS_FOUNDATION_COMPLETE_AVOA_READY`

After that marker, primary engineering focus moves to AVOA. HOS changes should be demand-driven by real AVOA needs rather than open-ended platform expansion.
