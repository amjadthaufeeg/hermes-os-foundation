"""HOS-4C: FastAPI Backend — Simulation Mode Only"""

import uuid, time, json, secrets
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, HTTPException, Depends, Body
from pydantic import BaseModel, Field

class ActionRequest(BaseModel):
    action: str
    rationale: str = ""
    typed_confirmation: str = ""

class ActionResponse(BaseModel):
    decision_id: str
    action: str
    previous_state: str
    resulting_state: str
    version: int
    audit_event_id: str
    mode: str = "SIMULATION"
    warning: str = "NO AUTHORITATIVE DECISION WAS CHANGED"
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.hos4c.config import *
from backend.hos4c.database import init_db, get_db
from backend.hos4c.audit import record_audit_event, verify_hash_chain
from backend.hos4c.state_machine import (
    validate_transition, is_high_risk, requires_typed_confirmation,
    requires_rationale, min_rationale_length, ROLE_PERMISSIONS,
)
from backend.hos4c.auth_oauth import (
    oauth_login_redirect, oauth_callback, SIMULATION_MODE as OAUTH_SIM,
)
from backend.hos4c.environment import get_env as env_get_env, is_protected, mutations_disabled, validate_startup

app = FastAPI(title="Hermes Decision Actions", version="0.1.0-simulation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# init_db() — called by fixtures or startup, not at module level

# --- Simulation Data ---
SIM_DECISIONS = [
    {"id": "DEC-HOS-001", "title": "Hermes remains the sole orchestrator", "state": "AWAITING_AMJAD", "version": 1, "owner": "amjad", "project": "hermes-os", "decision_text": "Kimi, Codex and Claude may build or review within assigned roles, but they may not independently control scope, task-state transitions, agent routing, approval, merge or deployment.", "reason": "Prevent conflicting agent authority."},
    {"id": "DEC-HOS-002", "title": "Kimi K3 is the primary builder", "state": "LOCKED", "version": 1, "owner": "amjad", "project": "hermes-os", "decision_text": "Kimi K3 handles new features as the default primary builder.", "reason": "Strong multi-file implementation performance."},
    {"id": "DEC-HOS-019", "title": "Product-development philosophy governs future expansion", "state": "LOCKED", "version": 1, "owner": "amjad", "project": "hermes-os", "decision_text": "Future roles and automation must be evaluated against the approved Philosophy.", "reason": "Immutable values."},
]

# --- Session Management ---
def create_session(actor_id: str, role: str = "AMJAD_OWNER") -> str:
    session_id = f"sess-{secrets.token_hex(16)}"
    csrf_token = secrets.token_hex(32)
    now = datetime.now(timezone.utc).isoformat()
    expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TIMEOUT_HOURS)).isoformat()
    with get_db() as db:
        db.execute(
            "INSERT INTO sessions (session_id, actor_id, actor_role, csrf_token, created_at, expires_at, last_activity) VALUES (?,?,?,?,?,?,?)",
            (session_id, actor_id, role, csrf_token, now, expires, now)
        )
    return session_id, csrf_token

def get_session(session_id: str) -> dict:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM sessions WHERE session_id = ? AND is_revoked = 0",
            (session_id,)
        ).fetchone()
    if not row:
        raise HTTPException(401, "Invalid or expired session")
    if row["expires_at"] < datetime.now(timezone.utc).isoformat():
        raise HTTPException(401, "Session expired")
    return dict(row)

# --- CSRF Protection ---
def validate_csrf(request: Request):
    """Validate CSRF token for state-changing requests."""
    session_id = request.cookies.get("hermes_session")
    if not session_id:
        raise HTTPException(401, "Not authenticated")
    session = get_session(session_id)
    csrf_header = request.headers.get("X-CSRF-Token")
    if not csrf_header:
        raise HTTPException(403, "Missing CSRF token")
    stored = session.get("csrf_token", "")
    if not stored or not secrets.compare_digest(csrf_header, stored):
        raise HTTPException(403, "Invalid CSRF token")
def require_role(min_role: str):
    async def _auth(request: Request):
        session_id = request.cookies.get("hermes_session")
        if not session_id:
            raise HTTPException(401, "Not authenticated")
        session = get_session(session_id)
        role = session["actor_role"]
        if role != "AMJAD_OWNER" and role != min_role:
            raise HTTPException(403, f"Insufficient authority. Has: {role}, Needs: {min_role}")
        return session
    return _auth

# --- Health ---
@app.get("/api/health")
def health():
    return {"status": "alive", "environment": env_get_env().value, "mutations": "DISABLED" if mutations_disabled() else "SIMULATION_ONLY"}

@app.get("/api/health/readiness")
def readiness():
    errors = validate_startup()
    if errors:
        return {"ready": False, "errors": errors}
    return {"ready": True, "environment": env_get_env().value, "mutations_disabled": mutations_disabled()}

# --- Auth (Simulated) ---
@app.post("/api/auth/login")
def login_simulated():
    """Simulated login — returns a session for 'amjad' with AMJAD_OWNER role."""
    session_id, csrf_token = create_session("amjadthaufeeg", "AMJAD_OWNER")
    resp = JSONResponse({"actor": "amjadthaufeeg", "role": "AMJAD_OWNER", "csrf_token": csrf_token, "mode": "SIMULATION"})
    resp.set_cookie("hermes_session", session_id, httponly=True, samesite="lax", max_age=SESSION_TIMEOUT_HOURS * 3600)
    return resp

@app.post("/api/auth/logout")
def logout():
    resp = JSONResponse({"status": "logged_out"})
    resp.delete_cookie("hermes_session")
    return resp

@app.get("/api/auth/session")
def current_session(request: Request):
    session_id = request.cookies.get("hermes_session")
    if not session_id:
        return {"authenticated": False}
    try:
        session = get_session(session_id)
        return {"authenticated": True, "actor": session["actor_id"], "role": session["actor_role"]}
    except HTTPException:
        return {"authenticated": False}

# --- GitHub OAuth Routes (Production Auth — gated behind SIMULATION_MODE) ---
@app.get("/auth/github/login")
def github_login():
    """Initiate GitHub OAuth login. Redirects to GitHub."""
    if SIMULATION_MODE:
        raise HTTPException(400, "OAuth unavailable in simulation mode — use /api/auth/login")
    result = oauth_login_redirect()
    if not result:
        raise HTTPException(503, "OAuth not configured")
    return RedirectResponse(result["redirect"])

@app.get("/auth/github/callback")
def github_callback(code: str, state: str, request: Request):
    """Handle GitHub OAuth callback. Creates authenticated session."""
    if SIMULATION_MODE:
        raise HTTPException(400, "OAuth unavailable in simulation mode")
    try:
        user = oauth_callback(code, state)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))

    # Create authenticated session
    session_id, csrf_token = create_session(user["github_login"], user["role"])

    # Record audit event
    from backend.hos4c.audit import record_audit_event
    record_audit_event(
        event_type="auth.oauth_completed",
        decision_id="N/A",
        action="LOGIN",
        actor_id=user["github_login"],
        actor_role=user["role"],
        session_id=session_id,
        previous_state="UNAUTHENTICATED",
        resulting_state="AUTHENTICATED",
        rationale=f"GitHub OAuth: user_id={user['github_id']}",
        reason_code="OAUTH_SUCCESS",
        decision_version=0,
        expected_version=0,
        idempotency_key=str(uuid.uuid4()),
        result="success",
        correlation_id=str(uuid.uuid4()),
    )

    resp = RedirectResponse("/")
    resp.set_cookie("hermes_session", session_id, httponly=True, samesite="lax",
                    max_age=SESSION_TIMEOUT_HOURS * 3600)
    return resp

@app.post("/auth/logout")
def auth_logout(request: Request):
    """Logout — invalidates session."""
    session_id = request.cookies.get("hermes_session")
    if session_id:
        try:
            session = get_session(session_id)
            with get_db() as db:
                db.execute("UPDATE sessions SET is_revoked = 1 WHERE session_id = ?", (session_id,))
        except HTTPException:
            pass
    resp = JSONResponse({"status": "logged_out"})
    resp.delete_cookie("hermes_session")
    return resp

@app.post("/auth/sessions/revoke")
def revoke_session(request: Request):
    """Revoke current session (CSRF-protected)."""
    validate_csrf(request)
    session_id = request.cookies.get("hermes_session")
    if session_id:
        with get_db() as db:
            db.execute("UPDATE sessions SET is_revoked = 1 WHERE session_id = ?", (session_id,))
    resp = JSONResponse({"status": "revoked"})
    resp.delete_cookie("hermes_session")
    return resp

@app.post("/auth/sessions/revoke-all")
def revoke_all_sessions(request: Request):
    """Revoke all sessions for the current actor (CSRF-protected)."""
    validate_csrf(request)
    session_id = request.cookies.get("hermes_session")
    if session_id:
        try:
            session = get_session(session_id)
            with get_db() as db:
                db.execute("UPDATE sessions SET is_revoked = 1 WHERE actor_id = ?",
                          (session["actor_id"],))
        except HTTPException:
            pass
    resp = JSONResponse({"status": "all_revoked"})
    resp.delete_cookie("hermes_session")
    return resp

# --- Decisions ---
@app.get("/api/decisions")
def list_decisions():
    return {"decisions": SIM_DECISIONS, "count": len(SIM_DECISIONS), "mode": "SIMULATION"}

@app.get("/api/decisions/{decision_id}")
def get_decision(decision_id: str):
    for d in SIM_DECISIONS:
        if d["id"] == decision_id:
            return {**d, "mode": "SIMULATION"}
    raise HTTPException(404, "Decision not found")

# --- Controlled Action ---
@app.post("/api/decisions/{decision_id}/actions")
def perform_action(
    decision_id: str,
    request: Request,
    body: ActionRequest,
):

    validate_csrf(request)

    if mutations_disabled():
        raise HTTPException(503, "Mutations disabled — simulation only")

    session_id = request.cookies.get("hermes_session", "sess-simulated")
    session = get_session(session_id)
    actor_id = session["actor_id"]
    actor_role = session["actor_role"]

    # Find decision
    decision = None
    for d in SIM_DECISIONS:
        if d["id"] == decision_id:
            decision = d
            break
    if not decision:
        raise HTTPException(404, "Decision not found")

    action_name = body.action
    rationale_text = body.rationale
    idempotency_key = str(uuid.uuid4())

    # Idempotency: check if this action was already processed
    with get_db() as db:
        existing = db.execute(
            "SELECT result FROM idempotency_records WHERE idempotency_key = ? AND decision_id = ? AND action = ?",
            (idempotency_key, decision_id, action_name)
        ).fetchone()
        if existing:
            return {"status": "duplicate", "result": existing["result"], "idempotency_key": idempotency_key}

    # Validate
    if not action_name:
        raise HTTPException(400, "Action required")
    if action_name not in ROLE_PERMISSIONS.get(actor_role, []):
        raise HTTPException(403, f"Role {actor_role} cannot perform {action_name}")
    if requires_rationale(action_name) and len(rationale_text) < min_rationale_length(action_name):
        raise HTTPException(422, f"Rationale must be at least {min_rationale_length(action_name)} characters")
    if requires_typed_confirmation(action_name):
        expected = f"{action_name} {decision_id}"
        confirm = body.typed_confirmation
        if confirm != expected:
            raise HTTPException(422, f"Type '{expected}' to confirm")

    try:
        target_state = validate_transition(decision["state"], action_name, actor_role)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Simulate: update decision in memory
    old_state = decision["state"]
    decision["state"] = target_state
    decision["version"] += 1

    # Record audit event
    audit = record_audit_event(
        event_type=f"decision.{action_name.lower()}",
        decision_id=decision_id,
        action=action_name,
        actor_id=actor_id,
        actor_role=actor_role,
        session_id=session_id,
        previous_state=old_state,
        resulting_state=target_state,
        rationale=rationale_text,
        reason_code=None,
        decision_version=decision["version"],
        expected_version=decision["version"] - 1,
        idempotency_key=idempotency_key,
        result="success",
        correlation_id=str(uuid.uuid4()),
    )

    # Persist idempotency record
    now = datetime.now(timezone.utc).isoformat()
    expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    with get_db() as db:
        db.execute(
            "INSERT INTO idempotency_records (idempotency_key, decision_id, action, result, created_at, expires_at) VALUES (?,?,?,?,?,?)",
            (idempotency_key, decision_id, action_name, "success", now, expires)
        )

    return {
        "decision_id": decision_id,
        "action": action_name,
        "previous_state": decision["state"],
        "resulting_state": target_state,
        "version": decision["version"],
        "audit_event_id": audit["event_id"],
        "mode": "SIMULATION",
        "warning": "NO AUTHORITATIVE DECISION WAS CHANGED",
    }

# --- Audit Verification ---
@app.get("/api/audit/verify")
def verify_audit():
    return verify_hash_chain()

@app.get("/api/audit/events")
def list_audit_events(limit: int = 50):
    with get_db() as db:
        rows = db.execute(
            "SELECT event_id, event_type, decision_id, action, actor_id, actor_role, previous_state, resulting_state, result, created_at FROM audit_events ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return {"events": [dict(r) for r in rows], "count": len(rows)}

# --- Data Export ---
@app.get("/api/audit/export")
def export_audit():
    with get_db() as db:
        rows = db.execute("SELECT * FROM audit_events ORDER BY created_at ASC").fetchall()
    return {"events": [dict(r) for r in rows], "exported_at": datetime.now(timezone.utc).isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8420)