"""HOS-AUTO-01 — Authority Policy Engine + Contract Schema.

All classification happens before execution.
Enforced at two layers: bridge policy + executor/broker independent enforcement.
"""
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AuthorityClass(str, Enum):
    AUTO = "AUTO"
    GATED = "GATED"
    FORBIDDEN = "FORBIDDEN"


class OperationType(str, Enum):
    RUN_PYTEST = "run_pytest"
    READ_FILE = "read_file"
    GREP_REPOSITORY = "grep_repository"
    GIT_STATUS = "git_status"
    GIT_DIFF = "git_diff"
    GIT_LOG = "git_log"
    INSPECT_CONTAINER = "inspect_container"
    INSPECT_TIMER = "inspect_timer"
    COLLECT_LOGS = "collect_logs"
    BUILD_DISPOSABLE_IMAGE = "build_disposable_image"
    CREATE_DISPOSABLE_CONTAINER = "create_disposable_container"
    START_DISPOSABLE_CONTAINER = "start_disposable_container"
    STOP_DISPOSABLE_CONTAINER = "stop_disposable_container"
    REMOVE_DISPOSABLE_CONTAINER = "remove_disposable_container"
    HASH_FILES = "hash_files"
    ASSERT_HTTP_RESPONSE = "assert_http_response"
    STAT_FILE = "stat_file"
    CREATE_SOURCE_DB = "create_source_db"


FORBIDDEN_OPERATIONS = frozenset({
    "enable_production_mutations",
    "delete_production_db",
    "delete_production_snapshot",
    "modify_constitution",
    "modify_locked_decisions",
    "activate_b7",
    "expose_public_route",
    "privilege_escalation",
    "run_shell_command",
    "docker_exec_production",
    "docker_restart_production",
})

# Authority matrix: OperationType → AuthorityClass
AUTHORITY_MATRIX: dict[OperationType, AuthorityClass] = {
    OperationType.RUN_PYTEST: AuthorityClass.AUTO,
    OperationType.READ_FILE: AuthorityClass.AUTO,
    OperationType.GREP_REPOSITORY: AuthorityClass.AUTO,
    OperationType.GIT_STATUS: AuthorityClass.AUTO,
    OperationType.GIT_DIFF: AuthorityClass.AUTO,
    OperationType.GIT_LOG: AuthorityClass.AUTO,
    OperationType.INSPECT_CONTAINER: AuthorityClass.AUTO,
    OperationType.INSPECT_TIMER: AuthorityClass.AUTO,
    OperationType.COLLECT_LOGS: AuthorityClass.AUTO,
    OperationType.BUILD_DISPOSABLE_IMAGE: AuthorityClass.AUTO,
    OperationType.CREATE_DISPOSABLE_CONTAINER: AuthorityClass.AUTO,
    OperationType.START_DISPOSABLE_CONTAINER: AuthorityClass.AUTO,
    OperationType.STOP_DISPOSABLE_CONTAINER: AuthorityClass.AUTO,
    OperationType.REMOVE_DISPOSABLE_CONTAINER: AuthorityClass.AUTO,
    OperationType.HASH_FILES: AuthorityClass.AUTO,
    OperationType.ASSERT_HTTP_RESPONSE: AuthorityClass.AUTO,
    OperationType.STAT_FILE: AuthorityClass.AUTO,
    OperationType.CREATE_SOURCE_DB: AuthorityClass.AUTO,
}


@dataclass
class Operation:
    type: OperationType
    params: dict = field(default_factory=dict)
    timeout_seconds: int = 300


@dataclass
class Assertion:
    id: str
    check: str
    expect: str
    actual: Optional[str] = None
    passed: Optional[bool] = None


@dataclass
class TaskContract:
    task_id: str
    objective: str
    authority_class: AuthorityClass
    working_directory: str
    source_git_sha: str
    authorization_token_id: Optional[str] = None
    operations: list[Operation] = field(default_factory=list)
    expected_assertions: list[Assertion] = field(default_factory=list)
    timeout_seconds: int = 600
    contract_sha256: Optional[str] = None

    def compute_hash(self) -> str:
        raw = json.dumps({
            "task_id": self.task_id, "objective": self.objective,
            "authority_class": self.authority_class.value,
            "working_directory": self.working_directory,
            "source_git_sha": self.source_git_sha,
            "operations": [(op.type.value, op.params) for op in self.operations],
            "timeout_seconds": self.timeout_seconds,
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def validate(self) -> list[str]:
        errors = []
        if not self.task_id: errors.append("task_id required")
        if not self.objective: errors.append("objective required")
        if not self.working_directory: errors.append("working_directory required")
        if not self.source_git_sha: errors.append("source_git_sha required")
        if self.authority_class == AuthorityClass.GATED and not self.authorization_token_id:
            errors.append("GATED requires authorization_token_id")
        if not self.operations:
            errors.append("at least one operation required")
        for op in self.operations:
            if op.type is None:
                errors.append("operation type required")
            if op.type.value in FORBIDDEN_OPERATIONS:
                errors.append(f"FORBIDDEN operation: {op.type.value}")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


def classify_operation(op: Operation) -> AuthorityClass:
    classification = AUTHORITY_MATRIX.get(op.type)
    return classification if classification else AuthorityClass.FORBIDDEN


def classify_contract(contract: TaskContract) -> AuthorityClass:
    highest = AuthorityClass.AUTO
    for op in contract.operations:
        c = classify_operation(op)
        if c == AuthorityClass.FORBIDDEN:
            return AuthorityClass.FORBIDDEN
        if c == AuthorityClass.GATED and highest != AuthorityClass.FORBIDDEN:
            highest = AuthorityClass.GATED
    return highest


def validate_authority(contract: TaskContract) -> tuple[bool, str]:
    actual = classify_contract(contract)
    if contract.authority_class != actual:
        return False, f"Authority mismatch: declared={contract.authority_class.value} actual={actual.value}"
    if contract.authority_class == AuthorityClass.GATED and not contract.authorization_token_id:
        return False, "GATED requires authorization_token_id"
    return True, f"AUTHORITY_OK: {actual.value}"