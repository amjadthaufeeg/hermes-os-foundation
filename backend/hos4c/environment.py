"""
HOS-4D.2: Environment Configuration + Startup Validation
Production-intent runtime foundation.

TASK-001: Environment policy is authoritative.
MUTATIONS_DISABLED=false cannot enable mutations in environments
whose policy prohibits them.
"""

import os, enum, sys
from dataclasses import dataclass

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
    },
    Environment.LOCAL_SIMULATION: {
        "sim_login": True, "oauth": False, "secure_cookies": False,
        "debug": True, "api_docs": True, "db_temp": True,
        "mutations": False, "auth_writes": False, "network": "localhost",
    },
    Environment.AUTH_REVIEW: {
        "sim_login": False, "oauth": True, "secure_cookies": False,
        "debug": False, "api_docs": True, "db_temp": False,
        "mutations": False, "auth_writes": False, "network": "localhost",
    },
    Environment.STAGING: {
        "sim_login": False, "oauth": True, "secure_cookies": True,
        "debug": False, "api_docs": False, "db_temp": False,
        "mutations": False, "auth_writes": False, "network": "private",
    },
    Environment.PRODUCTION: {
        "sim_login": False, "oauth": True, "secure_cookies": True,
        "debug": False, "api_docs": False, "db_temp": False,
        "mutations": False, "auth_writes": False, "network": "public",
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