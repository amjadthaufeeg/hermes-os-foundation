# HOS-AUTO-02 / R2 — Corrected Architecture

**GitHub bidirectional task/result exchange. Zero Amjad transport.**

---

## A. Confirmed ChatGPT-Side Capabilities

| Capability | Status | Notes |
|---|---|---|
| GitHub repository access | ✅ Connected integration | Authenticated as Amjad |
| Create/update files via GitHub | ✅ | Commit task JSON to repo |
| Read files from GitHub | ✅ | Browse result files |
| Private repo access | ✅ If authenticated | Same identity |

## B. Confirmed Hermes-Side Capabilities

| Capability | Status |
|---|---|
| Git clone/pull/push | ✅ (existing, token-stored) |
| File-system watcher (poll) | ✅ |
| HOS-AUTO-01 bridge invocation | ✅ |
| Commit structured results | ✅ |

## C. Feasibility of GitHub Bidirectional Transport

**FEASIBLE.** ChatGPT commits tasks to a private repo. Hermes pulls, processes, pushes results. ChatGPT reads results. Zero Amjad manual actions.

## D. Corrected Architecture

```
              Private GitHub Repo
              (amjadthaufeeg/hermes-tasks)
         ┌────────────────────────────────┐
         │  inbox/     ← ChatGPT commits   │
         │  active/    ← Hermes claims     │
         │  completed/ ← Hermes publishes   │
         │  stopped/   ← Rejected/expired  │
         └───┬────────────┬───────────────┘
             │            │
    ┌────────┴──┐    ┌───┴──────────┐
    │ ChatGPT    │    │   Hermes     │
    │ (creates   │    │ (processes  │
    │  tasks)    │    │  + publishes │
    │ (reads     │    │  results)   │
    │  results)  │    │             │
    └────────────┘    └──┬───────────┘
                         │
                    HOS-AUTO-01
                    Bridge + Broker
                         │
                         ▼
                       VPS
```

**Transport:** Private GitHub repo. Both ChatGPT and Hermes read/write via authenticated Git.

**Task lifecycle states:**
```
RECEIVED  → task committed to inbox/
VALIDATED → Hermes validates schema + authority
CLASSIFIED→ AUTO / GATED / FORBIDDEN
CLAIMED   → Hermes moves to active/ (commits)
RUNNING   → HOS-AUTO-01 executes
COMPLETED → Result committed to completed/
STOPPED   → Failure or expired → stopped/
REJECTED  → FORBIDDEN → stopped/
EXPIRED   → TTL exceeded → stopped/
```

## E. Exact ChatGPT → Hermes Path

1. ChatGPT constructs a task JSON (HOS-AUTO-01 contract schema)
2. ChatGPT commits the file to `inbox/<task_id>.json` via authenticated GitHub integration
3. **Zero Amjad actions required**

## F. Exact Hermes → ChatGPT Path

1. Hermes pulls the repo
2. Hermes detects new task in `inbox/`
3. Hermes validates + classifies authority
4. Hermes moves task to `active/` (commits + pushes)
5. Hermes executes via HOS-AUTO-01 bridge
6. Hermes writes structured result to `completed/<task_id>.json`
7. Hermes commits + pushes result
8. ChatGPT pulls/reads `completed/<task_id>.json`
9. **Zero Amjad actions required**

## G. Authentication Model

| Component | Auth Mechanism |
|---|---|
| ChatGPT → repo commit | GitHub authenticated identity (Amjad's integration) |
| Hermes → repo pull/push | Existing GitHub token (stored credential) |
| Task immutability | Hermes reads task from `inbox/` at a specific commit SHA; task hash = contract_sha256 |
| Hermes claims task | Hermes commits `inbox/<id>.json → active/<id>.json` move. Any parallel modification detected by git conflict |
| Result authenticity | Hermes commits result to `completed/`; commit hash = tamper-evident |
| Replay protection | task_id uniqueness enforced by Hermes; duplicate → REJECTED |

**No filesystem-location-based trust. All trust derives from GitHub commit identity + contract hash.**

## H. Authority Model

| Task Origin | Classification | By Whom |
|---|---|---|
| ChatGPT commits to inbox | Contract declares `authority_class` | **Hermes reclassifies independently** |
| AUTO in contract, verified by Hermes | AUTO → execute via HOS-AUTO-01 | Bridge + authority matrix |
| GATED in contract | GATED → hold. Requires Amjad approval token | Token must be separately committed or interactively approved |
| FORBIDDEN | Reject → `stopped/` with reason | Hard-blocked by Hermes |

**ChatGPT's declared authority is a suggestion — Hermes is the authority classifier.**

## I. Private-Data Handling

| Layer | Protection |
|---|---|
| Repo | **Private repository** (not public). Only authenticated users have access |
| Secrets | Never in task/result content. Same redaction rules as HOS-AUTO-01 receipts |
| Sensitive findings | Results in private repo. Only accessible to Amjad's authenticated identity |
| Git history | Force-push protection prevents history deletion/tampering |

## J. Threat Model

| Threat | Severity | Mitigation |
|---|---|---|
| Unauthorized task commit to inbox | **P1** | Private repo; only Amjad's GitHub identity has write access |
| Compromised GitHub account | **P0** | 2FA on GitHub account; separate task repo limits blast radius |
| Malicious PR / branch injection | **P1** | Hermes watches specific branch + path only; no PR auto-merge |
| Task created on wrong branch | **P1** | Hermes enforces branch = `main` (or designated task branch) |
| Force push rewriting history | **P1** | Branch protection: no force push to main |
| Replayed task (same task_id) | **P1** | Hermes deduplicates task_id across all states |
| Task modification after Hermes claims | **P1** | Hermes moves to `active/` on first claim; git conflict blocks parallel modification |
| Result forgery (non-Hermes commit) | **P1** | Hermes result commit signed by Hermes; ChatGPT can verify commit author |
| Prompt injection through task content | **P2** | Task objective is metadata; contract drives execution, not objective text |
| Secret leakage in task/result | **P0** | Redaction pass; never store secrets in repo |
| Recursive task storm | **P1** | Max depth, TTL, rate limiting, STOP on repeat failure |
| Stale approval token reuse | **P1** | Single-use, expiring tokens (same as HOS-AUTO-01) |

**Classification summary:** 2 P0, 9 P1, 1 P2, 0 P3.

## K. E2E Acceptance Test

```
1. ChatGPT commits harmless AUTO task:
   task_id: GPT-ACCEPT-001
   contract: inspect_container hermes-product-os-prod

2. Amjad performs NO copy/paste/save/upload action.

3. Hermes polls repo, detects new task in inbox/

4. Hermes validates → AUTO → moves to active/

5. HOS-AUTO-01 bridge executes inspect_container

6. Hermes writes result to completed/GPT-ACCEPT-001.json

7. Hermes commits + pushes result

8. ChatGPT reads completed/GPT-ACCEPT-001.json

9. ChatGPT reports: verdict=PASS, container healthy
```

**Success criteria:**
- Amjad copied: NO
- Amjad pasted: NO
- Amjad saved file: NO
- Amjad transported result: NO
- Amjad opened Terminal: NO
- Amjad sent screenshot: NO

```
AC-03 = PASS
AC-04 = PASS
```

## L. Fallback If GitHub Transport Unavailable

If ChatGPT's GitHub integration is disconnected or unavailable, fall back to the **local file inbox** model (Hermes watches `~/hermes-tasks/inbox/`). In this fallback, Amjad saves the task JSON file manually — a single file-save action, not content re-typing.

AC-03 would be PARTIAL in fallback mode. Hermes logs a warning when operating in fallback.

## M. Revised Implementation Effort

| Component | Effort |
|---|---|
| Task repo setup (private repo, branch protection) | 0.25 day |
| Hermes task watcher (git pull + poll inbox/) | 0.5 day |
| Task lifecycle state machine (RECEIVED → CLAIMED → COMPLETED) | 0.5 day |
| Hermes → GitHub result publication | 0.25 day |
| ChatGPT task schema + generation template | 0.25 day |
| Loop prevention + rate limiting | 0.5 day |
| Threat model verification | 0.5 day |
| E2E acceptance test | 0.5 day |
| **Total (GitHub transport)** | **~3.25 days** |
| **Total (with fallback)** | **~4 days** |

## N. Expected Amjad Manual Actions After R2

| Scenario | Amjad Action |
|---|---|
| ChatGPT creates AUTO task | **ZERO** (fully automated) |
| ChatGPT creates GATED task | Approve once (GATED token) |
| ChatGPT creates FORBIDDEN task | **ZERO** (auto-rejected) |
| Hermes result published | **ZERO** (ChatGPT reads directly) |
| GitHub transport unavailable (fallback) | Save task JSON file to inbox (one action) |

**After R2 with GitHub transport: zero manual Amjad actions for routine AUTO work.**
**AC-03 = PASS. AC-04 = PASS.**

---

**Corrected R2 design complete. Awaiting review.**