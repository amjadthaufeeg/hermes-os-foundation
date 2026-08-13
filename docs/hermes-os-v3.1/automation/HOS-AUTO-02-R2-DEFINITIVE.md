# HOS-AUTO-02 / R2 — Definitive Design

**GitHub bidirectional transport. Private repo. Zero Amjad manual actions.**

---

## A. Corrected Final Architecture

```
┌──────────┐     ┌──────────────────────────────┐     ┌──────────┐
│ ChatGPT   │────▶│  PRIVATE GitHub Repo           │────▶│ Hermes    │
│ (creates  │     │  amjadthaufeeg/hermes-control  │     │ (watches  │
│  tasks)   │     │                                │     │  + claims │
│ (reads    │     │  /tasks/inbox/    ← ChatGPT    │     │  + executes│
│  results) │◀────│  /tasks/active/   ← Hermes     │◀────│  + publishes
└──────────┘     │  /tasks/completed/← Hermes      │     └─────┬──────┘
                 │  /tasks/stopped/  ← Rejected    │           │
                 │  /results/        ← Published    │     HOS-AUTO-01
                 │  /receipts/index/ ← Hashes       │     Bridge+Broker
                 └──────────────────────────────────┘           │
                                                                ▼
                                                              VPS
```

**Transport:** Private GitHub repo `amjadthaufeeg/hermes-control`.
**Mode:** Pull-based. ChatGPT writes to inbox; Hermes polls; Hermes writes results; ChatGPT reads on request.
**Zero Amjad copy/paste/save/upload for routine AUTO work.**

## B. Private Transport Repository Requirements

| Field | Value |
|---|---|
| Repository | `amjadthaufeeg/hermes-control` |
| Visibility | **PRIVATE** |
| Branch | `main` (protected, no force push) |
| Purpose | Machine-readable task/result exchange only |
| Must NOT contain | Production secrets, credentials, tokens |
| GitHub integration | Amjad's authenticated identity (read/write) |

## C. Exact Repository Layout

```
hermes-control/
├── README.md
├── tasks/
│   ├── inbox/        ← ChatGPT commits new task JSON here
│   ├── active/       ← Hermes moves task here when claiming
│   ├── completed/    ← Hermes writes result here
│   └── stopped/      ← Rejected/expired tasks
├── results/
│   └── <task_id>.json
├── receipts/
│   └── index/        ← Receipt hash → task mapping
└── claims/
    └── <task_id>/    ← Claim artifacts (claim.json + nonce)
```

**Each task is a single JSON file. `task_id` is the filename stem.**

## D. Task Schema

```json
{
  "task_id": "GPT-20260813-001",
  "source": "chatgpt",
  "created_at": "2026-08-13T16:00:00Z",
  "ttl_seconds": 3600,
  "authority_suggestion": "AUTO",
  "max_depth": 3,
  "correlation_id": "conv-abc123",
  "parent_task_id": null,
  "objective": "Inspect production container health",

  "contract": {
    "operations": [
      {
        "type": "inspect_container",
        "params": {
          "container_name": "hermes-product-os-prod",
          "format": "{{.Name}}"
        },
        "timeout_seconds": 30
      }
    ],
    "expected_assertions": [
      {"id": "A1", "check": "exit_code", "expect": "0"}
    ],
    "timeout_seconds": 120
  },

  "result_required": "structured_receipt",
  "nonce": "uuid-v4-or-random"
}
```

## E. Claim / Idempotency Design

**Problem:** Two Hermes instances or concurrent pulls could process the same task.

**Solution:** Atomic claim via a dedicated claim file.

```
When Hermes detects new task <task_id>.json in inbox/:

1. Hermes reads task at immutable commit SHA (task_commit_sha).
2. Hermes computes task_hash = SHA256(task_commit_sha + task_id + processor_id).
3. Hermes attempts to create:
   claims/<task_id>/claim.json

   {
     "task_id": "<id>",
     "task_commit_sha": "<sha>",
     "processor_id": "hermes-r2-01",
     "claimed_at": "2026-08-13T16:01:00Z",
     "claim_nonce": "<uuid>",
     "claim_hash": "<sha256>"
   }

4. If claim file already exists → another processor claimed it → SKIP.
   (GitHub commit would fail with conflict — Hermes detects this.)
5. If claim succeeds → Hermes owns the task → move to active/ → execute.
```

**Idempotency:** If `task_id` already appears in active/, completed/, or stopped/ → SKIP (already processed or claimed).

## F. Result Schema

```json
{
  "task_id": "GPT-20260813-001",
  "result_id": "res-GPT-20260813-001",
  "status": "COMPLETED",
  "verdict": "PASS",

  "task_commit_sha": "abc123...",
  "contract_sha256": "def456...",
  "authority_class": "AUTO",
  "processor_id": "hermes-r2-01",

  "summary": "Production container healthy: /hermes-product-os-prod running",

  "evidence_receipts": [
    "70dabd66ce744582b9eb3e8a22926be9e9c33778780f6bf59308ee7f03706658"
  ],
  "artifact_refs": [
    "receipts/index/70dabd66ce744582b9eb3e8a22926be9e9c33778780f6bf59308ee7f03706658.json"
  ],

  "completed_at": "2026-08-13T16:01:45Z",
  "result_sha256": "789abc...",
  "requires_human_decision": false,
  "next_action": "none",
  "warnings": []
}
```

## G. Hermes Watcher Design

```
Loop (every 30s default):

1. git pull origin main (fast-forward only — reject non-ff)
2. List inbox/*.json (new tasks)
3. For each task:
   a. Read task JSON
   b. Record task_commit_sha (HEAD at pull time)
   c. Validate schema
   d. Validate transport: correct repo, branch, path
   e. Classify authority (Hermes reclassifies, not ChatGPT)
   f. Check idempotency (task_id in active/completed/stopped?)
   g. Check deduplication (nonce seen before?)
   h. Check TTL (created_at + ttl < now?)
   i. Attempt claim (commit claim.json to claims/<task_id>/)
   j. If claim succeeds:
      - Move inbox/<id>.json → active/<id>.json (git mv + commit)
      - Execute via HOS-AUTO-01 bridge
      - Write result to completed/<id>.json
      - Write receipt index
      - Commit + push
   k. If any step fails:
      - Write to stopped/<id>.json with reason
      - Commit + push
```

**Git strategy:** Each Hermes operation is a separate commit. Fast-forward pushes only. Conflicts on claim = another processor claimed it.

## H. ChatGPT Write/Read Integration Design

**Write (task creation):**
1. ChatGPT receives task from Amjad ("Ask Hermes to inspect...")
2. ChatGPT constructs task JSON per schema
3. ChatGPT commits to `hermes-control/tasks/inbox/<task_id>.json` via authenticated GitHub integration
4. ChatGPT records commit SHA + task_id
5. ChatGPT reports to Amjad: "Task GPT-20260813-001 submitted, SHA abc123"

**Read (result retrieval):**
1. Amjad asks: "What did Hermes return for GPT-20260813-001?"
2. ChatGPT reads `hermes-control/tasks/completed/GPT-20260813-001.json`
3. ChatGPT verifies: task_id matches, task_commit_sha matches, result_sha256 valid
4. ChatGPT reports result to Amjad

**Zero Amjad copy/paste/save/upload in either direction.**

## I. Authentication / Provenance Design

| Check | Purpose |
|---|---|
| Repo = `amjadthaufeeg/hermes-control` | Correct transport |
| Branch = `main` | Correct branch |
| Path starts with `tasks/inbox/` | Correct location |
| task_id format matches | Valid task namespace |
| contract_sha256 matches content | Task not tampered |
| nonce not previously seen | No replay |
| created_at + ttl < now | Not expired |
| authority_suggestion != authority_class (reclassified) | Hermes is authoritative |
| claim_hash matches expected | Valid claim |

**All checks must pass before execution. Any failure → task moved to stopped/.**

## J. Loop / Replay Protection

| Mechanism | Implementation |
|---|---|
| Max depth | `max_depth` decrements per child. Zero → STOP |
| TTL | `created_at + ttl_seconds` — expired tasks rejected |
| Rate limit | Max 10 new tasks per 5-minute window (configurable) |
| Deduplication | Nonce uniqueness enforced across all states |
| Idempotency | Same task_id → same result (no re-exec) |
| Max continuations | 3 AUTO continuations per parent chain |
| STOP on repeat failure | 3 identical failures → STOP + human escalation |
| Parent tracking | `parent_task_id` + `correlation_id` chain |
| Loop detection | task_id chain depth > max_depth → STOP |

## K. Implementation Files

```
deploy/hos_auto_02/
├── watcher.py          # Hermes task watcher (poll + claim + execute)
├── claim.py            # Atomic claim mechanism
├── schema.py           # Task + result JSON schemas + validation
├── transport.py        # Git operations (pull/commit/push)
├── loop_guard.py       # Rate limit, dedup, TTL, depth checks
└── tests/
    └── test_watcher.py
```

## L. Test Plan

| Test | Description |
|---|---|
| Valid AUTO task committed to inbox | Hermes detects, claims, executes, publishes result |
| Invalid schema → rejected | Written to stopped/ |
| GATED task without token → held | Written to stopped/ with "approval required" |
| FORBIDDEN task → rejected | Written to stopped/ |
| Duplicate task_id → SKIP | Idempotent, second claim fails |
| Expired task → rejected | TTL check fails |
| Concurrent claim → one wins | Second processor gets git conflict, SKIPs |
| Wrong repo/branch task → rejected | Transport validation fails |
| Malformed JSON → rejected | Schema validation fails |
| ChatGPT reads result | Verifies task_id, commit SHA, result SHA |

## M. E2E AC-03/AC-04 Acceptance Procedure

```
1. Amjad tells ChatGPT:
   "Ask Hermes to inspect the production snapshot timer."

2. ChatGPT creates GPT-ACCEPT-003.json in hermes-control/tasks/inbox/
   (contract: inspect_timer hermes-production-snapshot-refresh.timer)

3. Amjad performs NO action (no copy, paste, save, upload).

4. Hermes (within 30s) detects task, validates, claims, classifies AUTO.

5. HOS-AUTO-01 bridge executes inspect_timer via broker socket.

6. Hermes writes result to completed/GPT-ACCEPT-003.json + pushes.

7. Amjad asks ChatGPT: "What did Hermes return for GPT-ACCEPT-003?"

8. ChatGPT reads the result from hermes-control.

9. ChatGPT reports: "Timer active, PASS."

Amjad copied: NO    Amjad pasted: NO    Amjad saved: NO
Amjad uploaded: NO  Amjad transported: NO  Amjad Terminal: NO
Amjad screenshot: NO

AC-03 = PASS
AC-04 = PASS
```

## N. Estimated Effort

| Component | Effort |
|---|---|
| Private repo creation + branch protection | 0.25 day |
| Task/result schemas + validation | 0.5 day |
| Hermes watcher (poll + git ops) | 0.75 day |
| Atomic claim mechanism | 0.5 day |
| Loop/replay protection | 0.5 day |
| Tests (all scenarios above) | 1 day |
| E2E acceptance | 0.5 day |
| **Total** | **~4 days** |

## O. Unresolved P0/P1

**Zero.** All P0/P1 findings mitigated in this design:
- P0: Malicious contract → Hermes reclassifies (2 P0 items both resolved)
- P1: Auth/tampering/replay/loop (9 P1 items all resolved)

## P. One-Time Amjad Action Required

**Create the private transport repository:**

Amjad must create `amjadthaufeeg/hermes-control` as a **PRIVATE** GitHub repository.
- Grant Hermes token push access (same token as current repo).
- Enable branch protection on `main` (no force push, no direct push — require PR? No, Hermes needs direct push for claims. At minimum: no force push).
- Confirm ChatGPT's GitHub integration can read/write this repo.

This is the **only one-time manual action** required for R2. After this, all task/result transport is automated.

---

**Definitive R2 design complete. Awaiting transport repo creation + implementation authorization.**