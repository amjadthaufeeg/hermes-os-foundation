"""HOS-4C: FastAPI Backend — Simulation Mode Only"""

import uuid, time, json
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from config import *
from database import init_db, get_db
from audit import record_audit_event, verify_hash_chain
from state_machine import (
    validate_transition, is_high_risk, requires_typed_confirmation,
    requires_rationale, min_rationale_length, ROLE_PERMISSIONS,
)

app = FastAPI(title="Hermes Decision Actions", version="0.1.0-simulation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# --- Simulation Data ---
SIM_DECISIONS = [
    {"id": "DEC-HOS-001", "title": "Hermes remains the sole orchestrator", "state": "AWAITING_AMJAD", "version": 1, "owner": "amjad", "project": "hermes-os", "decision_text": "Kimi, Codex and Claude may build or review within assigned roles, but they may not independently control scope, task-state transitions, agent routing, approval, merge or deployment.", "reason": "Prevent conflicting agent authority."},
    {"id": "DEC-HOS-002", "title": "Kimi K3 is the primary builder", "state": "LOCKED", "version": 1, "owner": "amjad", "project": "hermes-os", "decision_text": "Kimi K3 handles new features as the default primary builder.", "reason": "Strong multi-file implementation performance."},
    {"id": "DEC-HOS-019", "title": "Product-development philosophy governs future expansion", "state": "LOCKED", "version": 1, "owner": "amjad", "project": "hermes-os", "decision_text": "Future roles and automation must be evaluated against the approved Philosophy.", "reason": "Immutable values."},
]

# --- Session Management ---
def create_session(actor_id: str, role: str = "AMJAD_OWNER") -> str:
    session_id = f"sess-{uuid.uuid4().hex[:16]}"
    now = datetime.now(timezone.utc).isoformat()
    expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TIMEOUT_HOURS)).isoformat()
    with get_db() as db:
        db.execute(
            "INSERT INTO sessions (session_id, actor_id, actor_role, created_at, expires_at, last_activity) VALUES (?,?,?,?,?,?)",
            (session_id, actor_id, role, now, expires, now)
        )
    return session_id

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

# --- Authority Middleware ---
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
    return {"status": "simulation", "mode": "SIMULATION_ONLY", "version": "0.1.0"}

# --- Auth (Simulated) ---
@app.post("/api/auth/login")
def login_simulated():
    """Simulated login — returns a session for 'amjad' with AMJAD_OWNER role."""
    session_id = create_session("amjadthaufeeg", "AMJAD_OWNER")
    resp = JSONResponse({"actor": "amjadthaufeeg", "role": "AMJAD_OWNER", "mode": "SIMULATION"})
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
    action: str = None,
    rationale: str = None,
    typed_confirmation: str = None,
):
    """Simulated decision action. No authoritative writes."""
    # Parse JSON body
    try:
        import asyncio
        async def _body():
            return await request.json()
    except:
        body = {"action": action, "rationale": rationale}
    else:
        body = {"action": action, "rationale": rationale or ""}

    # Simulated auth
    session_id = request.cookies.get("hermes_session", "sess-simulated")
    actor_id = "amjadthaufeeg"
    actor_role = "AMJAD_OWNER"

    # Find decision
    decision = None
    for d in SIM_DECISIONS:
        if d["id"] == decision_id:
            decision = d
            break
    if not decision:
        raise HTTPException(404, "Decision not found")

    action_name = body.get("action", action)
    rationale_text = body.get("rationale", rationale or "")
    idempotency_key = str(uuid.uuid4())

    # Validate
    if not action_name:
        raise HTTPException(400, "Action required")
    if action_name not in ROLE_PERMISSIONS.get(actor_role, []):
        raise HTTPException(403, f"Role {actor_role} cannot perform {action_name}")
    if requires_rationale(action_name) and len(rationale_text) < min_rationale_length(action_name):
        raise HTTPException(422, f"Rationale must be at least {min_rationale_length(action_name)} characters")
    if requires_typed_confirmation(action_name):
        expected = f"{action_name} {decision_id}"
        confirm = body.get("typed_confirmation", typed_confirmation or "")
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