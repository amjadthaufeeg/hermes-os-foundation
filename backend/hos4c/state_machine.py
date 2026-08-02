"""HOS-4C Decision State Machine"""

from typing import Optional, Dict, List

TRANSITIONS: Dict[str, Dict[str, str]] = {
    "AWAITING_AMJAD": {
        "APPROVE": "APPROVED",
        "REJECT": "REJECTED",
        "DEFER": "DEFERRED",
        "PLACE_ON_HOLD": "HOLD",
    },
    "IN_REVIEW": {
        "APPROVE": "APPROVED",
        "REJECT": "REJECTED",
        "RETURN_FOR_REVISION": "RETURNED",
        "PLACE_ON_HOLD": "HOLD",
    },
    "HOLD": {
        "RESUME": "AWAITING_AMJAD",
    },
    "DEFERRED": {
        "RESUME": "AWAITING_AMJAD",
    },
    "APPROVED": {
        "CLOSE": "CLOSED",
        "REOPEN": "AWAITING_AMJAD",
    },
    "REJECTED": {
        "CLOSE": "CLOSED",
        "REOPEN": "AWAITING_AMJAD",
    },
    "CLOSED": {
        "REOPEN": "AWAITING_AMJAD",
    },
    "BLOCKED": {
        "RESOLVE": "AWAITING_AMJAD",
    },
    "RETURNED": {
        "SUBMIT_FOR_REVIEW": "IN_REVIEW",
    },
    "PROPOSED": {
        "SUBMIT": "AWAITING_AMJAD",
    },
}

ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "AMJAD_OWNER": ["APPROVE", "REJECT", "DEFER", "PLACE_ON_HOLD", "RESUME",
                     "RETURN_FOR_REVISION", "CLOSE", "REOPEN", "SUBMIT",
                     "RESOLVE", "SUBMIT_FOR_REVIEW"],
    "REVIEWER": ["RETURN_FOR_REVISION"],
    "CONTRIBUTOR": [],
    "HERMES_ASSISTANT": [],
    "SYSTEM_SERVICE": [],
}

HIGH_RISK_ACTIONS = {"APPROVE", "REJECT"}

def validate_transition(current_state: str, action: str, actor_role: str) -> Optional[str]:
    """Validate a state transition. Returns target state or raises ValueError."""
    if actor_role not in ROLE_PERMISSIONS:
        raise ValueError(f"Unknown role: {actor_role}")
    if action not in ROLE_PERMISSIONS[actor_role]:
        raise ValueError(f"Role {actor_role} cannot perform action {action}")
    valid = TRANSITIONS.get(current_state, {})
    if action not in valid:
        raise ValueError(f"Action {action} not valid from state {current_state}. "
                         f"Valid actions: {list(valid.keys())}")
    return valid[action]

def is_high_risk(action: str) -> bool:
    return action in HIGH_RISK_ACTIONS

def requires_typed_confirmation(action: str) -> bool:
    return action in HIGH_RISK_ACTIONS

def requires_rationale(action: str) -> bool:
    return True  # All mutations require rationale

def min_rationale_length(action: str) -> int:
    return 50 if action in HIGH_RISK_ACTIONS else 20