# HOS-AUTO-01 — Execution Contract Specification

**Design only.**

---

## 1. Contract Schema

```yaml
task_id: B5-FC06
objective: "Verify missing snapshot mount fails closed in Phase-B reader"
authority_class: AUTO          # AUTO | GATED | FORBIDDEN

working_directory: /opt/hermes-auto/run
source_git_sha: 60e47d0ca8798139b7cc3b95f77dfb265fdad4b2
image: hermes-product-os-hpos:prod-p4-release   # where relevant

allowed_operations:
  - type: docker_exec
    target: hermes-phase-b-reader
    command: ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')"]

forbidden_operations:
  - type: docker_compose_restart
  - type: image_change
  - type: db_mutation

environment:
  - HERMES_ENVIRONMENT=PRODUCTION
  - MUTATIONS_DISABLED=true

expected_assertions:
  - id: A1
    check: http_status
    expect: 503
  - id: A2
    check: decision_count_unchanged
    expect: true
  - id: A3
    check: production_healthy
    expect: true

timeout_seconds: 300

rollback:
  type: none
  note: "Read-only test, no state change"

evidence_requirements:
  - stdout
  - stderr
  - exit_code
  - before_state
  - after_state

contract_sha256: <computed-at-draft>
```

---

## 2. Contract Lifecycle

```
DRAFTED (Hermes)
→ VALIDATED (bridge schema check)
→ CLASSIFIED (AUTO/GATED/FORBIDDEN)
→ AUTHORIZED (GATED: token present + valid)
→ PREFLIGHT (env check)
→ DISPATCHED (executor)
→ EXECUTED (operations run)
→ ASSERTED (expected conditions evaluated)
→ RECEIPTED (evidence sealed)
→ COMPLETE | STOP | FAILED
```

---

## 3. Required Fields (all mandatory)

| Field | Purpose |
|---|---|
| `task_id` | Traceability |
| `objective` | Human-readable intent |
| `authority_class` | Classification |
| `working_directory` | Sandboxed location |
| `source_git_sha` | Pinned source identity |
| `allowed_operations` | Whitelist |
| `forbidden_operations` | Deny list (defense-in-depth) |
| `expected_assertions` | Machine-checkable PASS/FAIL |
| `timeout_seconds` | Bounded execution |
| `rollback` | Reversibility |
| `evidence_requirements` | What to capture |
| `contract_sha256` | Tamper-evidence |

---

## 4. Operation Whitelist Types

| Type | Description |
|---|---|
| `docker_ps` | List containers |
| `docker_inspect` | Inspect container/image |
| `docker_exec` | Execute command inside container |
| `docker_run_rm` | Disposable container (non-production) |
| `docker_build` | Build image (non-production tag) |
| `journalctl` | Read logs |
| `read_file` | Read non-secret file |
| `stat` | File metadata |
| `run_test` | Execute test suite |
| `run_lint` | Execute linter |
| `run_typecheck` | Type checking |
| `collect_evidence` | Gather evidence artifacts |
| `docker_compose_restart` | GATED — restart service |
| `docker_compose_up` | GATED — deployment |

---

## 5. Assertion Types

| Type | Evaluation |
|---|---|
| `http_status` | Compare HTTP response code |
| `exit_code` | Compare process exit code |
| `decision_count_unchanged` | before == after |
| `audit_count_unchanged` | before == after |
| `container_healthy` | Docker health check |
| `file_exists` | Path existence |
| `file_absent` | Path non-existence |
| `string_contains` | stdout/stderr contains substring |
| `hash_equals` | SHA256 match |
| `status_equals` | Health payload field match |

---

## 6. STOP Semantics

If any `expected_assertion` evaluates to FAIL:

- Execution STOPS immediately.
- No reinterpretation of FAIL as "acceptable."
- Receipt records verdict `FAILED`.
- Hermes reviews, does NOT auto-retry unless a new contract is drafted.

If an unexpected exception occurs (not covered by assertions):

- Execution STOPS.
- Verdict `STOP`.
- Receipt records the anomaly.

---

## 7. Preflight (Test Environment Validation)

Before any `run_test` operation, the bridge MUST verify:

| Check | Method |
|---|---|
| Interpreter present | `python3 --version` |
| Dependency set complete | `import` smoke test of required modules |
| Test runner present | `pytest --version` |
| Source SHA correct | `git rev-parse HEAD` == `source_git_sha` |
| Fixtures present | Check fixture files |
| Required binaries | `which` for shell dependencies |

If any preflight check fails:

- Classification: `TEST_ENVIRONMENT_INVALID`
- Verdict: `STOP`
- **NOT** reported as `FULL_REGRESSION_FAILED`

---

## 8. Contract Example — GATED

```yaml
task_id: B5-FC06-RESTART
objective: "Restart Phase-B reader to test restart fail-closed"
authority_class: GATED
authorization_token: AUTH-2026-0041
allowed_operations:
  - type: docker_compose_restart
    target: hermes-phase-b-reader
    project: hermes-phase-b
forbidden_operations:
  - type: image_change
  - type: db_mutation
  - type: network_change
  - type: credential_change
...
```

---

**Execution contract specification complete.**