"""
HOS-4D.1: Production OAuth Authentication + Verified Identity
Replaces simulated login with GitHub OAuth + PKCE.
Simulation mode preserved — no authoritative writes.
"""

import os, hashlib, base64, secrets, requests
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

# --- Configuration ---
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
GITHUB_OAUTH_AUTHORIZE = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_TOKEN = "https://github.com/login/oauth/access_token"
GITHUB_API_USER = "https://api.github.com/user"
REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URI", "http://localhost:8420/api/auth/callback")
SIMULATION_MODE = os.environ.get("SIMULATION_MODE", "true").lower() == "true"

# Approved owner: immutable GitHub user ID (set via env var, verified out-of-band)
APPROVED_OWNER_GITHUB_ID = int(os.environ.get("APPROVED_OWNER_GITHUB_ID", "0"))

# --- PKCE Helpers ---
def generate_code_verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()

def generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

# --- OAuth State Store ---
OAUTH_STATES: Dict[str, dict] = {}  # state → {verifier, created_at, session_id}

def create_oauth_state(session_id: str = "") -> tuple:
    state = secrets.token_hex(32)
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    OAUTH_STATES[state] = {
        "verifier": verifier,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "used": False
    }
    return state, challenge

def consume_oauth_state(state: str) -> Optional[str]:
    """Validate and consume OAuth state. Returns verifier or None."""
    record = OAUTH_STATES.pop(state, None)
    if not record or record.get("used"):
        return None
    # State expires in 10 minutes
    created = datetime.fromisoformat(record["created_at"])
    if datetime.now(timezone.utc) - created > timedelta(minutes=10):
        return None
    return record["verifier"]

# --- Identity Binding ---
def get_github_user(access_token: str) -> Optional[dict]:
    """Fetch GitHub user info. Returns {id, login, name, email} or None."""
    resp = requests.get(
        GITHUB_API_USER,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=10
    )
    if resp.status_code != 200:
        return None
    return resp.json()

def is_approved_owner(github_user_id: int) -> bool:
    """Check if GitHub user ID matches the approved owner."""
    if APPROVED_OWNER_GITHUB_ID == 0:
        return False  # Fail closed: no owner configured
    return github_user_id == APPROVED_OWNER_GITHUB_ID

def get_owner_role(github_user_id: int) -> str:
    """Map GitHub user ID to application role."""
    if is_approved_owner(github_user_id):
        return "AMJAD_OWNER"
    return "UNAUTHENTICATED"  # No access for unbound users

# --- OAuth Endpoints (to be integrated into main.py) ---
def oauth_login_redirect():
    """Generate OAuth authorization URL and return redirect."""
    if SIMULATION_MODE:
        return None  # Use simulated login in simulation mode
    state, challenge = create_oauth_state()
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "read:user",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return {"redirect": f"{GITHUB_OAUTH_AUTHORIZE}?{qs}", "state": state}

def oauth_callback(code: str, state: str):
    """Handle OAuth callback. Returns (github_user, role) or raises."""
    verifier = consume_oauth_state(state)
    if not verifier:
        raise ValueError("Invalid or expired OAuth state")

    # Exchange code for token
    resp = requests.post(
        GITHUB_OAUTH_TOKEN,
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
        },
        headers={"Accept": "application/json"},
        timeout=10
    )
    token_data = resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise ValueError("Failed to obtain access token")

    # Fetch user identity
    user = get_github_user(access_token)
    if not user:
        raise ValueError("Failed to fetch GitHub user")

    github_id = user["id"]
    role = get_owner_role(github_id)
    if role == "UNAUTHENTICATED":
        raise PermissionError(f"GitHub user {github_id} ({user.get('login')}) is not an approved owner")

    return {
        "github_id": github_id,
        "github_login": user.get("login"),
        "role": role,
        "name": user.get("name", ""),
    }