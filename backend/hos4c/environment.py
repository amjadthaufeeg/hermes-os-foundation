"""
HOS-4D.2: Environment Configuration + Startup Validation
Production-intent runtime foundation.
"""

import os, enum
from dataclasses import dataclass

class Environment(enum.Enum):
    LOCAL_TEST = "LOCAL_TEST"
    LOCAL_SIMULATION = "LOCAL_SIMULATION"
    AUTH_REVIEW = "AUTH_REVIEW"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"

ENV = Environment(os.environ.get("HERMES_ENVIRONMENT", "LOCAL_SIMULATION").upper())

# Mutation safety: always disabled unless explicitly authorized
def mutations_disabled() -> bool:
    return os.environ.get("MUTATIONS_DISABLED", "true").lower() != "false"

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
    """Return current environment. Fails if invalid."""
    val = os.environ.get("HERMES_ENVIRONMENT", "")
    try:
        env = Environment(val.upper())
    except ValueError:
        # Fail closed: unknown environment → safest known
        return Environment.LOCAL_SIMULATION
    if env not in POLICY:
        return Environment.LOCAL_SIMULATION
    return env

def policy(key: str) -> bool:
    """Read a boolean policy value for the current environment."""
    return POLICY.get(ENV, {}).get(key, False)

def is_protected() -> bool:
    """True in STAGING or PRODUCTION."""
    return ENV in (Environment.STAGING, Environment.PRODUCTION)

def validate_startup() -> list:
    """Validate configuration at startup. Returns list of errors."""
    errors = []

    # OAuth configuration required in AUTH_REVIEW, STAGING, PRODUCTION
    if policy("oauth"):
        if not os.environ.get("GITHUB_CLIENT_ID"):
            errors.append("GITHUB_CLIENT_ID required for OAuth environment")
        if not os.environ.get("GITHUB_CLIENT_SECRET"):
            errors.append("GITHUB_CLIENT_SECRET required for OAuth environment")
        if not os.environ.get("APPROVED_OWNER_GITHUB_ID"):
            errors.append("APPROVED_OWNER_GITHUB_ID required for OAuth environment")

    # Debug disabled in protected environments
    if is_protected():
        import backend.hos4c.main as main
        if hasattr(main.app, 'debug') and main.app.debug:
            errors.append("Debug mode must be disabled in protected environments")

    # Mutations must remain disabled
    if not mutations_disabled():
        errors.append("MUTATIONS_DISABLED must be true — live mutations not authorized")

    # Database persistence check
    db_path = os.environ.get("DATABASE_PATH", "")
    if not policy("db_temp") and not db_path:
        errors.append("DATABASE_PATH required for persistent environments")

    return errors

def startup_ok() -> bool:
    """Check if startup validation passes."""
    return len(validate_startup()) == 0