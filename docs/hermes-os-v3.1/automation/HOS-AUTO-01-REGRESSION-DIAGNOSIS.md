# HOS-AUTO-01 — Regression Environment Diagnosis

**Diagnosis only. No changes made.**

---

## Finding: TEST_ENVIRONMENT_INVALID — NOT a regression failure

The "full regression failed" result was misclassified. The actual condition is an **incomplete test environment**, not failing code.

---

## Root Cause

`backend/hos4c/checkpoint.py` imports `cryptography` (Ed25519 signing for checkpoint-chain verification):

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
```

`test_checkpoint.py` and `test_restore.py` (which imports `checkpoint.py` transitively) fail at **collection time** because `cryptography` is not installed in the test environment:

```
ModuleNotFoundError: No module named 'cryptography'
```

---

## Why cryptography is absent

The repository has **no dependency manifest** — no `requirements.txt`, no `pyproject.toml`, no `setup.py`, no `Pipfile`. The bootstrap log confirms dependencies were installed ad-hoc:

```
requests=2.34.2
yaml=6.0.3
httpx=0.27.2
pytest=9.1.1
```

`fastapi`, `pydantic`, `requests`, `yaml`, `httpx`, `pytest` were installed, but `cryptography` was missed because there is no authoritative list of what to install.

---

## Authoritative Dependency Source (MISSING)

The HOS-4 test suite requires a dependency manifest. Currently there is none. This is a **documentation/engineering gap**, not a code defect.

Required third-party dependencies (from source inspection):

| Package | Used By | Installed in test env? |
|---|---|---|
| `fastapi` | main.py, routes | ✅ |
| `pydantic` | main.py models | ✅ (transitive via fastapi) |
| `uvicorn` | ASGI server | ✅ (runtime) |
| `requests` | auth_oauth.py | ✅ (2.34.2) |
| `PyYAML` | config, tests | ✅ (6.0.3) |
| `httpx` | test client | ✅ (0.27.2) |
| `pytest` | test runner | ✅ (9.1.1) |
| `starlette` | test client | ✅ (transitive via fastapi) |
| **`cryptography`** | **checkpoint.py (Ed25519)** | **❌ MISSING** |
| `pytest-timeout` | timeout plugin | ⚠️ (unverified) |

---

## Additional Risk: Other possibly-missing dependencies

Because there is no manifest, other dependencies may also be missing in future runs. Candidates to verify:
- `pytest-timeout` (if used in test config)
- `python-multipart` (if file uploads used)
- Any test fixtures importing optional packages

---

## How HOS-AUTO-01 Must Detect This

### Preflight MUST import-smoke-test every required module BEFORE launching tests.

```
Preflight:
  python3 --version
  pytest --version
  python3 -c "import fastapi, pydantic, requests, yaml, httpx, cryptography, starlette"
  # Any ImportError → TEST_ENVIRONMENT_INVALID

  git rev-parse HEAD == source_git_sha
  # mismatch → TEST_ENVIRONMENT_INVALID
```

If preflight fails → classification `TEST_ENVIRONMENT_INVALID`, verdict `STOP`.

**Do NOT classify an incomplete runner as `FULL_REGRESSION_FAILED`.**

---

## Recommended Fix (for the eventual test-environment design)

1. Create `requirements.txt` (or `pyproject.toml`) listing ALL runtime + test dependencies.
2. Preflight validates: `python3 -m pip check` or explicit import smoke test.
3. The bridge classifies preflight failure as `TEST_ENVIRONMENT_INVALID`, distinct from code failure.

---

## Impact on FC-05 Assessment

- FC-05 focused tests (28): **PASS** — these don't touch `cryptography`.
- Full regression: **INCONCLUSIVE** — environment invalid, not code failing.
- The FC-05 candidate itself is unaffected by the `cryptography` gap (it doesn't use Ed25519).

---

**Regression environment diagnosis complete. No installation or modification performed.**