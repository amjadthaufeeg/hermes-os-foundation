"""
HOS-4C: Controlled Decision Actions — Security Backend
Simulation mode. No authoritative writes.

FastAPI + SQLite + GitHub OAuth + audit ledger
"""

import os, sqlite3, uuid, hashlib, time, json, hmac
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager

# --- Configuration ---
DATABASE_PATH = os.environ.get("AUDIT_DB", ".hermes/audit/audit.db")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
SIMULATION_MODE = os.environ.get("SIMULATION_MODE", "true").lower() == "true"

def is_simulation_mode() -> bool:
    """Return True if running in simulation mode.
    Reads from os.environ each call — test-safe."""
    return os.environ.get("SIMULATION_MODE", "true").lower() == "true"
SESSION_TIMEOUT_HOURS = 12
REAUTH_WINDOW_MINUTES = 5