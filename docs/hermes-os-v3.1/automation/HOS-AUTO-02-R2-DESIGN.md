# HOS-AUTO-02 / R2 — ChatGPT ↔ Hermes Courier Elimination

**DESIGN ONLY. No implementation.**

---

## A. Current Manual Workflow

```
ChatGPT
  → Amjad reads task description
  → Amjad re-types/paraphrases instructions to Hermes
  → Hermes orchestrates (AUTO via HOS-AUTO-01)
  → Hermes produces result + evidence receipts
  → Amjad reads result
  → Amjad re-types/summarizes result back to ChatGPT
```

**Manual steps per task:** Amjad reads ChatGPT output, re-types to Hermes,
reads Hermes output, re-types to ChatGPT.

## B. Target Automated Workflow

```
ChatGPT generates structured task (JSON)
  → Amjad saves task file (one action: save to watched directory)
  → Hermes detects new task in inbox
  → Hermes validates + classifies authority
  → Hermes executes/orchestrates via HOS-AUTO-01
  → Hermes writes structured result to outbox
  → ChatGPT reads result (via GitHub public read or Amjad shares file)
```

**Manual steps eliminated:** Amjad re-typing instructions, Amjad re-typing results.
**Remaining manual:** Amjad saves the initial task file (one action).

## C. Selected Architecture

**Local file-watched inbox/outbox + GitHub for result publication.**

```
~/hermes-tasks/
├── inbox/       ← Amjad saves ChatGPT task JSON here
├── active/      ← Hermes moves tasks here during processing
├── completed/   ← Hermes writes results here
├── stopped/     ← Failed/blocked tasks
└── shared/      ← Published to GitHub for ChatGPT read access
```

**Transport:**
- ChatGPT → Hermes: Filesystem (Amjad saves task to inbox/)
- Hermes → ChatGPT: GitHub (Hermes pushes results to repo; ChatGPT reads via browsing)

**Why not direct API?** ChatGPT cannot make authenticated calls to local endpoints on Amjad's machine. The filesystem is the only common denominator: Hermes runs on the same Mac and can watch the filesystem; Amjad can save ChatGPT output to files.

**Why GitHub for results?** ChatGPT can browse public URLs. Hermes can git push. No auth needed for read access.

## D. Why Selected Over Alternatives

| Alternative | Verdict | Reason |
|---|---|---|
| Local HTTP API | ❌ | ChatGPT can't reach localhost on Amjad's machine |
| Unix socket | ❌ | Same — ChatGPT has no local access |
| GitHub Issues | ❌ | Creating issues requires auth token; ChatGPT can't authenticate to Amjad's repos |
| File-backed queue (both sides) | ✅ | Only approach that works with current ChatGPT capabilities |
| Clipboard monitoring | ⚠️ | Fragile; file save is more explicit and structured |

The file-watched inbox is the **only practical approach** given current constraints. A future ChatGPT plugin or API integration would enable full automation.

## E. ChatGPT Integration Path

1. ChatGPT generates a task JSON matching the HOS-AUTO-01 contract schema
2. Amjad receives the JSON (ChatGPT output) and saves it to `~/hermes-tasks/inbox/`
3. Hermes detects the new file and processes it
4. Hermes publishes the result to GitHub (the shared repo)
5. ChatGPT browses the result URL (public GitHub file)

**Eliminated:** Amjad re-typing instructions to Hermes, re-typing results to ChatGPT.
**Remaining:** Amjad saves one file per task (drag-drop or one-click operation).

## F. Hermes Integration Path

Hermes (on the Mac) runs a lightweight watcher that polls `~/hermes-tasks/inbox/` for new task files. When detected:

1. Validate task schema + authority classification
2. Compute contract SHA256
3. If AUTO: dispatch to HOS-AUTO-01 bridge
4. If GATED: hold until Amjad approval
5. Write result to `completed/` + `shared/`
6. Publish to GitHub (git add + commit + push)

**Watcher design:** inotify/kqueue-based (or simple polling). Runs as part of the Hermes session.

## G. Authentication / Trust Model

| Direction | Auth | Rationale |
|---|---|---|
| ChatGPT → task file | Filesystem location (`~/hermes-tasks/inbox/`, macOS user owns it) | No token needed; file creation implies Amjad's intent |
| Task file → Hermes | SHA256 contract hash + Hermes validates schema | Prevents tampered files from being processed |
| Hermes → GitHub result | Git push with stored credential | Same auth as existing git workflow |
| GitHub → ChatGPT read | Public read (no auth) | Repo is public; results contain no secrets |

**Key custody:** Git credential stored in macOS keychain (existing).
**Replay protection:** Task files have unique `task_id`; Hermes deduplicates.
**Timestamp/nonce:** `created_at` UTC in task metadata.

## H. Task Schema

```json
{
  "task_id": "GPT-20260813-001",
  "source": "chatgpt",
  "correlation_id": "conv-abc123",
  "created_at": "2026-08-13T16:00:00Z",
  "authority_class": "AUTO",
  "objective": "Inspect production containers via HOS-AUTO-01",
  "parent_task_id": null,
  "max_depth": 3,
  "ttl_seconds": 3600,
  "contract": {
    "operations": [
      {
        "type": "inspect_container",
        "params": {"container_name": "hermes-product-os-prod"},
        "timeout_seconds": 30
      }
    ],
    "expected_assertions": [
      {"id": "A1", "check": "exit_code", "expect": "0"}
    ]
  },
  "result_required": "structured_receipt"
}
```

## I. Result Schema

```json
{
  "task_id": "GPT-20260813-001",
  "result_id": "res-20260813-001",
  "status": "PASS",
  "summary": "Production container healthy: hermes-product-os-prod running",
  "evidence_receipts": ["70dabd66ce744582b9eb3e8a22926be9e9c33778780f6bf59308ee7f03706658"],
  "artifact_refs": ["shared/res-GPT-20260813-001/receipt.json"],
  "verdict": "PASS",
  "completed_at": "2026-08-13T16:00:45Z",
  "next_action": "none",
  "requires_human_decision": false,
  "result_sha256": "abc123..."
}
```

## J. Loop Prevention

| Mechanism | Implementation |
|---|---|
| Max task depth | Each task has `max_depth` (default 3). Child tasks decrement. Depth 0 → STOP |
| Parent/child tracking | `parent_task_id` + chain visible in audit |
| Task TTL | `ttl_seconds` — task expires after TTL, no retry |
| Rate limiting | Max tasks per time window (configurable, default 10/min) |
| Duplicate detection | `task_id` deduplication. Replay → rejected |
| Idempotency | Same contract SHA256 + task_id → same result returned (no re-exec) |
| Max continuations | Max 3 AUTO continuations per parent chain |
| STOP on repeated failure | 3 identical failures → STOP, human escalation |
| Human escalation | `requires_human_decision: true` in result → Amjad notified |

## K. Authority Handling

| Task authority | Bridge behavior |
|---|---|
| AUTO | Process immediately via HOS-AUTO-01 bridge |
| GATED | Hold in `active/` with `approval: pending`. Amjad must approve |
| FORBIDDEN | Rejected at validation. Written to `stopped/` |

**ChatGPT cannot submit GATED tasks** without Amjad's explicit approval token.
**No authority downgrade** possible — authority is Hermes-classified, not ChatGPT-declared.

## L. Threat Model

| Threat | Severity | Mitigation |
|---|---|---|
| ChatGPT spoofing another source | **P1** | `source: chatgpt` enforced; filesystem location = Amjad's intent |
| Task tampering after file save | **P1** | Contract SHA256 computed at save; Hermes verifies before execution |
| Result tampering before ChatGPT read | **P1** | Result SHA256 + git commit hash (immutable) |
| Replay of old task | **P1** | task_id deduplication; timestamps checked |
| Stale approval | **P2** | GATED tokens expire (same as HOS-AUTO-01) |
| Prompt injection through task objective | **P2** | Objective is metadata only; contract drives execution, not objective text |
| Recursive loops | **P1** | Max depth, TTL, rate limiting |
| Task storms | **P1** | Rate limiting (10/min default) |
| Malicious contract | **P0** | Hermes validates contract against authority matrix; FORBIDDEN ops hard-blocked |
| Cross-project contamination | **P2** | task_id namespace: `GPT-*` for ChatGPT origin; isolated from native Hermes tasks |
| Secret leakage through result | **P0** | Result redaction pass before publication to GitHub (same as HOS-AUTO-01 receipts) |
| GATED → AUTO downgrade | **P1** | Authority classified by Hermes, not ChatGPT. Contract authority overridden if mismatch |

**Classification summary:** 2 P0, 7 P1, 4 P2, 0 P3.

## M. Implementation Sequence

```
R2a: File-watched inbox/outbox (Hermes watcher + result publication)
R2b: GitHub result publication (git push results to repo)
R2c: End-to-end flow (ChatGPT task → file → Hermes → GitHub → ChatGPT read)
R2d: Loop prevention + rate limiting
R2e: Full threat-model verification
```

## N. Rollback

```
Stop the watcher → tasks remain in inbox (no data loss)
Remove the `~/hermes-tasks/` directory
No production impact (read-only infrastructure)
```

## O. Acceptance Tests

| Test | Criterion |
|---|---|
| ChatGPT generates valid task JSON | Hermes validates schema → accepted |
| Amjad saves task to inbox | Hermes detects within 2 seconds |
| AUTO task executes | Receipt generated in `completed/` |
| GATED task holds | Status: `approval_pending` |
| Result published to GitHub | ChatGPT can browse public URL |
| ChatGPT reads result | Structured JSON, no Amjad retyping |
| FORBIDDEN task rejected | Written to `stopped/` |
| Duplicate task_id | Rejected with idempotency message |
| Task storm | Rate limited |

## P. Estimated Effort

| Component | Effort |
|---|---|
| Watcher (inotify/poll) | 0.5 day |
| Task schema + validation | 0.5 day |
| Result schema + publication | 0.5 day |
| GitHub result push | 0.25 day |
| Loop prevention | 0.5 day |
| Tests | 1 day |
| **Total** | **~3 days** |

## Q. Exact Expected Reduction in Amjad Manual Work

| Before R2 | After R2 |
|---|---|
| Amjad reads ChatGPT output | Amjad reads ChatGPT output (unchanged) |
| Amjad **re-types** instructions to Hermes | Amjad **saves** one JSON file → inbox |
| Hermes executes (already automated) | Hermes executes (unchanged) |
| Amjad **reads** Hermes output | Hermes writes structured result |
| Amjad **re-types** result to ChatGPT | ChatGPT browses GitHub result URL |

**Eliminated:** Amjad re-typing (both directions). **Remaining:** Amjad saves one file per task (single action, not content transport). Estimated manual-work reduction: ~80% of remaining courier work after HOS-AUTO-01.

---

**R2 design complete. Awaiting Amjad review and authorization to implement.**