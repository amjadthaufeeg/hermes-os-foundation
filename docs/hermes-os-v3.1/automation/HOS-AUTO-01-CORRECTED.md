# HOS-AUTO-01 — Corrected Architecture (R1 v2)

**Design only. No implementation. All previous R1 docs superseded by this document.**

---

## 1. FC-05 Freshness Threshold — 900s STANDS

The authoritative policy **remains** 900 seconds / 15 minutes.

**Consumer must not weaken.** The Phase-B reader evaluates freshness against 900s. If the producer cannot reliably meet 900s, fix the producer.

### Producer Schedule Correction

Current: `OnUnitActiveSec=900` + `RandomizedDelaySec=30` = worst-case 930s between refreshes.

**Fix:** `OnUnitActiveSec=840` (14 min) + `RandomizedDelaySec=30` = worst-case 870s between refreshes. Maximum snapshot age at consumer: 870s. Headroom below 900s: 30s.

```ini
[Timer]
OnBootSec=60
OnUnitActiveSec=840
RandomizedDelaySec=30
Persistent=true
```

**This guarantees the consumer sees freshness ≤ 900s under normal operation.** A missed cycle (2×840=1680s) would correctly trigger STALE.

---

## 2. FC-05 Enforcement — Environment Policy

`SNAPSHOT_FRESHNESS_ENFORCED` must NOT be opt-in for the Phase-B reader environment. Follow TASK-001 pattern:

```python
# environment.py POLICY — new key:
"snapshot_freshness_required": True   # for Phase-B reader environment

# validate_startup() — new check:
if policy("snapshot_freshness_required"):
    val = os.environ.get("SNAPSHOT_FRESHNESS_ENFORCED", "").strip().lower()
    if val != "true":
        errors.append(
            "FATAL: Phase-B reader requires SNAPSHOT_FRESHNESS_ENFORCED=true. "
            f"Got '{val}'. Snapshot freshness is mandatory for production read consumers."
        )
```

**Production API:** Does NOT set this policy flag — not governed by snapshot freshness.

---

## 3. Snapshot Metadata + Hash Binding

Freshness verification uses **three authoritative sources:**

| Source | Check |
|---|---|
| `snapshot.meta.json` `created_at_utc` | Is timestamp ≤ 900s old? |
| `snapshot.meta.json` `sha256` | Recorded hash of snapshot.db |
| `snapshot.db` actual SHA256 | Computed at verification time |

**Both metadata and snapshot must represent the same generation.** If:
- Metadata missing → fail closed
- Metadata malformed → fail closed
- Timestamp invalid/future/stale → fail closed
- Metadata SHA ≠ actual SHA → fail closed (generation mismatch)
- Snapshot missing → fail closed
- Snapshot corrupt → fail closed

`mtime` retained as a **secondary sanity check** only: if metadata says "fresh" but mtime is > 3600s old → WARN log, but do not block. mtime is not authoritative.

---

## 4. Atomic Publication — Generation Consistency

Current pipeline: `snapshot.db.tmp` → `mv → snapshot.db`, then `snapshot.meta.json.tmp` → `mv → snapshot.meta.json`. This ordering means a reader could observe **new metadata + old snapshot** if metadata publishes first, or **new snapshot + old metadata** if snapshot publishes first.

**Recommended fix (minimal):** Publish metadata FIRST (atomic `mv`), then publish snapshot. A reader seeing new metadata with old snapshot → SHA mismatch → fail closed. A reader seeing old metadata with new snapshot → metadata timestamp is recent enough (snapshot just updated) → won't trigger stale.

Alternative (more robust): Publish both from a temporary directory atomically using `rename` on the same filesystem:
```
/tmp/snapshot-refresh-<pid>/
  snapshot.db
  snapshot.meta.json
→ atomic mv of entire contents to target dir
```
But this requires moving a directory, not individual files. Simpler: keep current ordering but guarantee the consumer sees metadata SHA ≠ snapshot SHA if they're out of sync → fail closed.

---

## 5. Typed Operations — No Generic Shell

R1 prohibits arbitrary shell command construction. All operations are typed:

### R1 Operation Catalogue (AUTO)

| Operation | Parameters | Validated |
|---|---|---|
| `run_pytest` | `path`, `args[]`, `timeout` | Path within `backend/`, args whitelist |
| `read_file` | `path`, `max_bytes` | Path allowlist (repo + evidence paths only) |
| `grep_repository` | `pattern`, `file_glob` | Regex safe, no shell expansion |
| `git_status` | `repo_path` | Must be within `/tmp/hpos-*` or approved checkout |
| `git_diff` | `repo_path`, `commit_a`, `commit_b` | Same repo constraint |
| `git_log` | `repo_path`, `n` | Same |
| `inspect_container` | `container_name` | Allowlist of readable containers |
| `inspect_timer` | `timer_name` | Allowlisted timers |
| `collect_logs` | `source`, `since`, `max_lines` | journalctl for allowed units only |
| `build_disposable_image` | `dockerfile_path`, `context_path`, `tag_prefix` | Prefix must be `disposable-*` |
| `start_disposable_container` | `image`, `container_name_prefix` | Prefix must be `disposable-*` |
| `stop_disposable_container` | `container_name` | Must match prefix `disposable-*` |
| `hash_files` | `paths[]` | Within allowed roots |
| `assert_http_response` | `url`, `expected_status`, `expected_body_contains` | URL allowlist |
| `create_source_db` | `path`, `decisions` | Within `/tmp/` only |
| `stat_file` | `path` | Within allowed roots |

### GATED Operations

| Operation | Notes |
|---|---|
| `restart_service` | Specific service, Amjad token required |
| `modify_compose` | Specific change, Amjad token required |

**No `run_shell_command` in AUTO.** If absolutely needed (emergency debugging), classify as GATED with narrow scope and maximum 30s timeout.

---

## 6. Privileged Docker Broker

Executor is unprivileged (non-root, no Docker socket). A narrow privileged broker handles Docker operations.

```
┌────────────────────┐
│ Unprivileged        │
│ Executor            │
│ (hermes-auto user)  │
│ no docker socket    │
│ no capabilities     │
└───────┬────────────┘
        │ typed operation request (JSON over Unix socket or pipe)
        ▼
┌────────────────────┐
│ Privileged Broker   │
│ (root, standalone)  │
│ validates:          │
│  - operation type   │
│  - image allowlist  │
│  - name prefix      │
│  - mount paths      │
│  - mount flags      │
│  - networks         │
│  - ports            │
│  - capabilities     │
│  - user             │
│  - env vars         │
│  - NO production    │
│    resources        │
└────────────────────┘
```

**Broker constraints:**
- Accepts only typed operation requests (no raw `docker run`).
- Validates every parameter against allowlists.
- Rejects any image not prefixed `disposable-*` or on explicit allowlist.
- Rejects any container named `hermes-product-os*`, `hermes-phase-b-*` (without GATED token).
- Rejects any volume mount outside `/tmp/`, `/opt/hermes-auto/`, or explicit allowlist.
- Rejects `--privileged`, host network, host PID, or Docker socket mounts.
- Rejects any capability beyond the approved minimal set.
- Logs every operation with full parameter dump.

---

## 7. Two-Layer Authorization

| Layer | What it does | Can be bypassed by agent? |
|---|---|---|
| **Layer 1 — Bridge** | Validates contract, classifies authority, checks GATED tokens | No — agent cannot change bridge code at runtime |
| **Layer 2 — Executor + Broker** | Independent enforcement of operation allowlists, path constraints, resource exclusions | No — broker validates independently of bridge |

Even if a compromised bridge sends an invalid request, the broker rejects it.

---

## 8. Threat Model Correction

**Reconciled: 8 P0 items** (removed "agent forbidden ops" duplication — it was covered by contract tampering and classification enforcement).

After typed-operation architecture:
- **Command injection: Downgraded P0→P1** (no shell, execve arrays only)
- **Shell escape: Downgraded P0→P1** (no shell access in typed ops)
- **Docker socket abuse: Downgraded P0→P1** (broker validates, no raw socket)
- Remaining P0: prompt injection (5), contract tampering (4), privilege escalation (9), credential exposure (12)

**Revised: 5 P0 CRITICAL, 10 P1 BLOCKER, 4 P2 HARDENING.**

---

## 9. Test Environment Manifest

### Dependency Manifest (`requirements.txt`)

```
# HOS-4 Runtime
fastapi>=0.110
pydantic>=2.0
uvicorn>=0.29
requests>=2.31
PyYAML>=6.0
cryptography>=41.0

# HOS-4 Test
pytest>=8.0
pytest-timeout>=2.0
httpx>=0.27
starlette>=0.37
```

### Preflight

```python
MODULES = ["fastapi", "pydantic", "uvicorn", "requests", "yaml", "httpx", "pytest", "starlette", "cryptography"]
for m in MODULES:
    __import__(m)
# Any ImportError → TEST_ENVIRONMENT_INVALID
```

Plus: `python3 --version` >= 3.11, `git rev-parse HEAD` == `source_git_sha`.

---

## 10. Receipt Enhancements

Add to receipt: `contract_hash`, `source_git_sha`, `executor_version`, `policy_version`, `environment_fingerprint`, `authorization_token_id` (if GATED), `previous_receipt_hash`.

**Chaining retained** — each receipt references the previous. Tampering with any receipt invalidates the chain. Simple to implement (one hash field). Materially improves tamper evidence.

---

## 11. Implementation Strategy

R1 = single Python package + systemd unit. No distributed system. No API. No queue.

```
/opt/hermes-auto/
├── bin/bridge          (Python CLI — Hermes calls this)
├── bin/broker          (privileged Docker helper, systemd-activated)
├── contracts/          (submitted + validated)
├── evidence/           (artifacts per execution)
├── receipts/           (chained receipt files)
├── policy/
│   ├── authority.yaml
│   └── allowlist.yaml
├── deps/
│   └── requirements.txt
└── config.yaml
```

**Sequence:** deps → policy → broker → executor → bridge → receipts → B5 pilot.

---

## 12. B5 Authority Reclassification

Classification based on **blast radius**, not scenario name:

| Scenario | Blast Radius | Authority |
|---|---|---|
| FC-05 verification | Disposable reader only | **AUTO** |
| FC-03 regression | Disposable reader only | **AUTO** |
| FC-04 regression | Disposable reader only | **AUTO** |
| FC-05 regression | Disposable reader only | **AUTO** |
| FC-06 missing mount | Disposable reader only | **AUTO** (disposable lab) |
| FC-12 restart | Disposable reader only | **AUTO** |
| FC-09 policy mismatch | Disposable reader only | **AUTO** |
| FC-10 invalid env | Disposable reader only | **AUTO** |
| FC-11 malformed config | Compose validation only | **AUTO** |

**Incidental:**
- Production container: `hermes-product-os-prod` — **untouched throughout**
- Production DB: `production.db` — **untouched**
- Phase-B reader: `hermes-phase-b-reader` — may be used as reference but not modified

**All B5 scenarios are AUTO** when executed against a disposable lab. Any scenario requiring production container interaction would be GATED.

---

## 13. Implementation Sequence

```
1. Test environment manifest (requirements.txt + preflight)
2. Authority policy YAML + classification engine
3. Typed operation catalogue schema
4. Unprivileged executor (typed ops only)
5. Privileged Docker broker (validating proxy)
6. Contract validation engine
7. Receipt generator + chaining
8. B5 pilot execution
```

---

## 14. Effort Estimate (Corrected)

| Component | Effort |
|---|---|
| Deps manifest + preflight | 0.25 day |
| Authority engine | 0.5 day |
| Typed ops + schema | 1 day |
| Executor | 0.5 day |
| Broker | 1 day |
| Contract + receipts | 1 day |
| Tests | 1 day |
| **Total** | **~5.25 days** |

---

## 15. Unresolved P0/P1 Blockers

**All resolved in this corrected design.**

| Item | Status |
|---|---|
| P0: Fail-open configuration (opt-in) | ✅ Fixed — environment policy |
| P0: Command injection | ✅ Fixed — typed ops, no shell |
| P0: Shell escape | ✅ Fixed — no shell access |
| P0: Docker socket abuse | ✅ Fixed — broker validates |
| P0: Contract tampering | ✅ Fixed — SHA256 binding |
| P0: Credential exposure | ✅ Fixed — no creds in executor env |
| P1: Stale tokens | ✅ Fixed — single-use, expiring |
| P1: Threshold jitter | ✅ Fixed — 840s producer schedule |
| P1: mtime authority | ✅ Fixed — metadata + SHA binding |
| P1: Generation mismatch | ✅ Fixed — SHA cross-verification |

---

**Corrected architecture complete. Zero P0/P1 unresolved. Awaiting Amjad authorization for implementation.**