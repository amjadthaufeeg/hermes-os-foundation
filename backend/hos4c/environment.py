"""
HOS-4D.2: Environment Configuration + Startup Validation
Production-intent runtime foundation.

TASK-001: Environment policy is authoritative.
MUTATIONS_DISABLED=false cannot enable mutations in environments
whose policy prohibits them.
"""

import os, enum, sys, json, hashlib, hmac
from dataclasses import dataclass
from datetime import datetime, timezone

class Environment(enum.Enum):
    LOCAL_TEST = "LOCAL_TEST"
    LOCAL_SIMULATION = "LOCAL_SIMULATION"
    AUTH_REVIEW = "AUTH_REVIEW"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"

ENV = Environment(os.environ.get("HERMES_ENVIRONMENT", "LOCAL_SIMULATION").upper())

# Environment policy matrix
POLICY = {
    Environment.LOCAL_TEST: {
        "sim_login": True, "oauth": False, "secure_cookies": False,
        "debug": True, "api_docs": True, "db_temp": True,
        "mutations": False, "auth_writes": False, "network": "localhost",
        "snapshot_freshness_required": False,
    },
    Environment.LOCAL_SIMULATION: {
        "sim_login": True, "oauth": False, "secure_cookies": False,
        "debug": True, "api_docs": True, "db_temp": True,
        "mutations": False, "auth_writes": False, "network": "localhost",
        "snapshot_freshness_required": False,
    },
    Environment.AUTH_REVIEW: {
        "sim_login": False, "oauth": True, "secure_cookies": False,
        "debug": False, "api_docs": True, "db_temp": False,
        "mutations": False, "auth_writes": False, "network": "localhost",
        "snapshot_freshness_required": False,
    },
    Environment.STAGING: {
        "sim_login": False, "oauth": True, "secure_cookies": True,
        "debug": False, "api_docs": False, "db_temp": False,
        "mutations": False, "auth_writes": False, "network": "private",
        "snapshot_freshness_required": False,
    },
    Environment.PRODUCTION: {
        "sim_login": False, "oauth": True, "secure_cookies": True,
        "debug": False, "api_docs": False, "db_temp": False,
        "mutations": False, "auth_writes": False, "network": "public",
        "snapshot_freshness_required": True,
        "snapshot_max_age_seconds": 990,
        "snapshot_path_prefix": "/opt/hermes/data",
    },
}

def get_env() -> Environment:
    """Return current environment. Unknown or missing-policy environments
    raise ValueError — no silent fallback."""
    val = os.environ.get("HERMES_ENVIRONMENT", "LOCAL_SIMULATION")
    env = Environment(val.upper())
    if env not in POLICY:
        raise ValueError(
            f"Environment '{env.value}' has no policy entry. "
            f"Configuration error."
        )
    return env

def policy(key: str) -> bool:
    """Read a boolean policy value for the current environment."""
    env = get_env()
    return POLICY.get(env, {}).get(key, False)

def snapshot_metadata_path(db_path: str) -> str:
    """Return the metadata path published by deploy/hermes-snapshot-refresh."""
    return os.path.join(os.path.dirname(db_path), "snapshot.meta.json")

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def snapshot_freshness(db_path: str = None) -> tuple[bool, dict]:
    """Validate snapshot freshness using metadata and SHA binding.

    Fail closed: any missing, malformed, stale, unreadable, or mismatched
    snapshot state returns ``False`` with a diagnostic dictionary.
    """
    env = get_env()
    env_policy = POLICY.get(env, {})
    if db_path is None:
        db_path = os.environ.get("DATABASE_PATH", "")

    prefix = env_policy.get("snapshot_path_prefix", "")
    if prefix:
        real_db = os.path.realpath(db_path)
        real_prefix = os.path.realpath(prefix)
        if not (real_db == real_prefix or real_db.startswith(real_prefix + os.sep)):
            return False, {"error": "database_path_outside_snapshot_prefix", "path": db_path}

    if not os.path.isfile(db_path):
        return False, {"error": "snapshot_not_regular_file", "path": db_path}

    meta_path = snapshot_metadata_path(db_path)
    if not os.path.isfile(meta_path):
        return False, {"error": "metadata_missing", "path": meta_path}

    try:
        with open(meta_path) as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return False, {"error": "metadata_unreadable", "detail": str(e)}

    created_raw = meta.get("created_at_utc")
    expected_sha = meta.get("sha256")
    if not created_raw:
        return False, {"error": "metadata_incomplete", "missing": "created_at_utc"}
    if not expected_sha:
        return False, {"error": "metadata_incomplete", "missing": "sha256"}

    try:
        created = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
    except ValueError:
        return False, {"error": "metadata_bad_timestamp", "value": created_raw}

    now = datetime.now(timezone.utc)
    age_s = (now - created).total_seconds()
    max_age_s = int(env_policy.get("snapshot_max_age_seconds", 990))

    if age_s < -60:
        return False, {"error": "future_timestamp", "age_s": age_s}
    if age_s > max_age_s:
        return False, {"error": "stale", "age_s": age_s, "max_age_s": max_age_s}

    try:
        actual_sha = _sha256_file(db_path)
    except OSError as e:
        return False, {"error": "snapshot_unreadable", "detail": str(e)}

    if not hmac.compare_digest(actual_sha, str(expected_sha)):
        return False, {"error": "sha_mismatch"}

    return True, {
        "age_s": age_s,
        "max_age_s": max_age_s,
        "created_at_utc": created_raw,
        "decisions_count": meta.get("validation", {}).get("decisions_count"),
    }

def is_protected() -> bool:
    """True in STAGING or PRODUCTION."""
    env = get_env()
    return env in (Environment.STAGING, Environment.PRODUCTION)

def mutations_disabled() -> bool:
    """Returns True if mutations are disabled.

    Environment policy is authoritative. If policy prohibits mutations,
    returns True regardless of MUTATIONS_DISABLED value.

    If policy permits mutations, only explicit 'false' enables them.
    Any malformed, missing, or non-false value disables mutations.
    """
    env = get_env()
    env_allows = POLICY.get(env, {}).get("mutations", False)

    # Environment policy is authoritative
    if not env_allows:
        return True

    # Environment permits — check explicit flag
    raw = os.environ.get("MUTATIONS_DISABLED")
    if raw is None:
        return True  # absent — disabled
    normalized = raw.strip().lower()

    if normalized == "false":
        return False  # explicitly enabled

    # "true", malformed, empty — disabled
    return True

def validate_startup() -> list:
    """Validate configuration at startup. Returns list of error strings.
    Strings prefixed with 'FATAL:' indicate configuration conflicts
    that should prevent the application from becoming serving-ready.
    """
    errors = []

    # --- Policy / MUTATIONS_DISABLED cross-validation (TASK-001) ---
    env = get_env()
    env_allows = POLICY.get(env, {}).get("mutations", False)
    raw = os.environ.get("MUTATIONS_DISABLED")

    if raw is not None:
        normalized = raw.strip().lower()

        if normalized == "":
            errors.append(
                "FATAL: MUTATIONS_DISABLED is set but empty. "
                "Must be 'true' or 'false'. Mutations disabled."
            )
        elif normalized not in ("true", "false"):
            errors.append(
                "FATAL: MUTATIONS_DISABLED='%s' is invalid. "
                "Must be 'true' or 'false'. Mutations disabled." % raw.strip()
            )
        elif not env_allows and normalized == "false":
            errors.append(
                "FATAL: Environment '%s' prohibits mutations but "
                "MUTATIONS_DISABLED=false was supplied. "
                "Mutations remain disabled. Fix configuration." % env.value
            )

    # --- PRODUCTION simulation-mode enforcement ---
    if env == Environment.PRODUCTION:
        sim_raw = os.environ.get("SIMULATION_MODE", "")
        sim_normalized = sim_raw.strip().lower()
        if sim_normalized != "false":
            errors.append(
                "FATAL: PRODUCTION requires SIMULATION_MODE=false. "
                "Got '%s'. Production must never serve simulation data. "
                "Set SIMULATION_MODE=false." % sim_raw.strip()
            )

    # --- OAuth configuration required in AUTH_REVIEW, STAGING, PRODUCTION ---
    if policy("oauth"):
        if not os.environ.get("GITHUB_CLIENT_ID"):
            errors.append("GITHUB_CLIENT_ID required for OAuth environment")
        if not os.environ.get("GITHUB_CLIENT_SECRET"):
            errors.append("GITHUB_CLIENT_SECRET required for OAuth environment")
        if not os.environ.get("APPROVED_OWNER_GITHUB_ID"):
            errors.append("APPROVED_OWNER_GITHUB_ID required for OAuth environment")

    # --- Debug disabled in protected environments ---
    if is_protected():
        import backend.hos4c.main as main
        if hasattr(main.app, 'debug') and main.app.debug:
            errors.append("Debug mode must be disabled in protected environments")

    # --- Database persistence check ---
    db_path = os.environ.get("DATABASE_PATH", "")
    if not policy("db_temp") and not db_path:
        errors.append("DATABASE_PATH required for persistent environments")

    # --- Production snapshot freshness/path enforcement (FC-05) ---
    if policy("snapshot_freshness_required"):
        fresh, diag = snapshot_freshness(db_path)
        if not fresh:
            errors.append(
                "FATAL: Snapshot freshness validation failed: %s" %
                diag.get("error", "unknown")
            )

    return errors

def has_fatal_errors(errors: list) -> bool:
    """True if any error string starts with 'FATAL:'."""
    return any(e.startswith("FATAL:") for e in errors)

def startup_policy_check():
    """Call during application startup. Raises RuntimeError on fatal
    configuration conflicts so the ASGI server refuses to serve.
    """
    errors = validate_startup()
    fatal = [e for e in errors if e.startswith("FATAL:")]
    if fatal:
        for e in fatal:
            print("CRITICAL: " + e, file=sys.stderr, flush=True)
        raise RuntimeError(
            "Startup aborted: %d fatal configuration error(s)" % len(fatal)
        )

def startup_ok() -> bool:
    """Check if startup validation passes."""
    return len(validate_startup()) == 0
