from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_flywheel_cli.mutation import (
    MutationRejectedError,
    commit_validated_yaml,
    load_yaml_mapping,
    sha256_bytes,
)
from ai_flywheel_cli.operations import OperationError
from ai_flywheel_cli.validation import LIFECYCLE_STAGES

LIFECYCLE_ORDER = (
    "execute",
    "observe",
    "evaluate",
    "classify",
    "adapt",
    "validate",
    "persist",
    "reuse",
)


class UnsupportedDeterministicOperationError(OperationError):
    """Raised when work remains assigned to governed AI execution."""


class TransitionRejectedError(MutationRejectedError):
    """Raised when a requested deterministic transition violates the operating model."""


@dataclass(frozen=True)
class DeterministicOperationResult:
    operation: str
    status: str
    files_changed: tuple[str, ...]
    execution_id: str
    lifecycle_stage: str

    def as_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "status": self.status,
            "files_changed": list(self.files_changed),
            "execution_id": self.execution_id,
            "lifecycle_stage": self.lifecycle_stage,
        }


def _load_mapping(path: Path) -> dict[str, Any]:
    return load_yaml_mapping(path, TransitionRejectedError)


def _timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(UTC)
    return current.strftime("%Y-%m-%dT%H:%M:%SZ")


def _validated_commit(
    repository: Path,
    changes: dict[str, dict[str, Any]],
    command: str,
    expected_sha256: dict[str, str | None],
) -> tuple[str, ...]:
    return commit_validated_yaml(
        repository,
        changes,
        command,
        TransitionRejectedError,
        expected_sha256=expected_sha256,
    )


def _empty_stage() -> dict[str, Any]:
    return {
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "summary": None,
        "refs": [],
        "reason": None,
    }


def start_execution(
    repository: Path,
    mission_id: str,
    goal_id: str,
    execution_id: str,
    intended_outcome: str,
    *,
    started_at: datetime | None = None,
) -> DeterministicOperationResult:
    root = repository.resolve()
    state_path = root / ".flywheel/state.yaml"
    goal_relative = f".flywheel/operations/missions/{mission_id}/goals/{goal_id}.yaml"
    goal_path = root / goal_relative
    execution_relative = (
        f".flywheel/operations/records/{mission_id}/{goal_id}/executions/{execution_id}.yaml"
    )
    execution_path = root / execution_relative
    state_bytes = state_path.read_bytes() if state_path.is_file() else None
    goal_bytes = goal_path.read_bytes() if goal_path.is_file() else None
    state = _load_mapping(state_path)
    goal = _load_mapping(goal_path)
    if state.get("active_execution") is not None:
        raise TransitionRejectedError(
            "Cannot start an execution while another execution is active."
        )
    if execution_path.exists():
        raise TransitionRejectedError(f"Execution already exists: {execution_id}")
    if goal.get("mission_id") != mission_id or goal.get("id") != goal_id:
        raise TransitionRejectedError(
            "Goal identity or mission reference does not match the request."
        )
    criteria = [
        item.get("id")
        for item in goal.get("acceptance_criteria", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    if not criteria:
        raise TransitionRejectedError(
            "Goal must define acceptance criteria before execution starts."
        )
    timestamp = _timestamp(started_at)
    lifecycle = {stage: _empty_stage() for stage in LIFECYCLE_ORDER}
    lifecycle["execute"] = {
        "status": "in-progress",
        "started_at": timestamp,
        "completed_at": None,
        "summary": None,
        "refs": [],
        "reason": None,
    }
    execution = {
        "schema_version": 1,
        "id": execution_id,
        "mission_id": mission_id,
        "goal_id": goal_id,
        "status": "in-progress",
        "intended_outcome": intended_outcome,
        "acceptance_criteria": criteria,
        "started_at": timestamp,
        "completed_at": None,
        "lifecycle": lifecycle,
        "actions": [],
        "observations": [],
        "evaluations": [],
        "classifications": [],
        "adaptations": [],
        "blockers": [],
        "approval_refs": [],
        "evidence_refs": [],
        "decision_refs": [],
        "finding_refs": [],
        "validation_results": [],
        "outcome": None,
        "completion": {"disposition": None, "rationale": None},
    }
    goal["status"] = "active"
    state.update(
        {
            "status": "active",
            "active_mission": mission_id,
            "active_goal": goal_id,
            "active_execution": execution_id,
            "lifecycle_stage": "execute",
            "blockers": [],
            "last_durable_update": {
                "at": timestamp,
                "by": "ai-flywheel-cli",
                "reason": f"Started execution {execution_id} for goal {goal_id}.",
            },
        }
    )
    files = _validated_commit(
        root,
        {
            goal_relative: goal,
            execution_relative: execution,
            ".flywheel/state.yaml": state,
        },
        "start-execution",
        {
            ".flywheel/state.yaml": sha256_bytes(state_bytes) if state_bytes is not None else None,
            goal_relative: sha256_bytes(goal_bytes) if goal_bytes is not None else None,
            execution_relative: None,
        },
    )
    return DeterministicOperationResult(
        "start-execution", "completed", files, execution_id, "execute"
    )


def advance_lifecycle(
    repository: Path,
    summary: str,
    refs: tuple[str, ...],
    *,
    completed_at: datetime | None = None,
    expected_stage: str | None = None,
) -> DeterministicOperationResult:
    root = repository.resolve()
    state_path = root / ".flywheel/state.yaml"
    state_bytes = state_path.read_bytes() if state_path.is_file() else None
    state = _load_mapping(state_path)
    mission_id = state.get("active_mission")
    goal_id = state.get("active_goal")
    execution_id = state.get("active_execution")
    current_stage = state.get("lifecycle_stage")
    if not all(
        isinstance(value, str) for value in (mission_id, goal_id, execution_id, current_stage)
    ):
        raise TransitionRejectedError(
            "An active mission, goal, execution, and lifecycle stage are required."
        )
    if current_stage not in LIFECYCLE_STAGES:
        raise TransitionRejectedError(f"Unsupported lifecycle stage: {current_stage}")
    if expected_stage is not None and current_stage != expected_stage:
        raise TransitionRejectedError(
            "Lifecycle stage changed before retry: "
            f"expected {expected_stage}, found {current_stage}."
        )
    execution_relative = (
        f".flywheel/operations/records/{mission_id}/{goal_id}/executions/{execution_id}.yaml"
    )
    execution_path = root / execution_relative
    execution_bytes = execution_path.read_bytes() if execution_path.is_file() else None
    execution = _load_mapping(execution_path)
    lifecycle = execution.get("lifecycle")
    if not isinstance(lifecycle, dict):
        raise TransitionRejectedError("Execution lifecycle must be a mapping.")
    stage = lifecycle.get(current_stage)
    if not isinstance(stage, dict) or stage.get("status") != "in-progress":
        raise TransitionRejectedError(
            "The active lifecycle stage must be in-progress before advancing."
        )
    if not summary.strip():
        raise TransitionRejectedError("A lifecycle completion summary is required.")
    timestamp = _timestamp(completed_at)
    stage.update(
        {
            "status": "completed",
            "completed_at": timestamp,
            "summary": summary.strip(),
            "refs": list(dict.fromkeys(refs)),
            "reason": None,
        }
    )
    index = LIFECYCLE_ORDER.index(current_stage)
    if index == len(LIFECYCLE_ORDER) - 1:
        raise UnsupportedDeterministicOperationError(
            "Completing reuse and closing the execution remains governed AI work "
            "in the approved scope."
        )
    next_stage = LIFECYCLE_ORDER[index + 1]
    next_value = lifecycle.get(next_stage)
    if not isinstance(next_value, dict) or next_value.get("status") != "pending":
        raise TransitionRejectedError(f"Next lifecycle stage is not pending: {next_stage}")
    next_value.update(
        {
            "status": "in-progress",
            "started_at": timestamp,
            "completed_at": None,
            "summary": None,
            "refs": [],
            "reason": None,
        }
    )
    state.update(
        {
            "status": "active",
            "lifecycle_stage": next_stage,
            "blockers": [],
            "last_durable_update": {
                "at": timestamp,
                "by": "ai-flywheel-cli",
                "reason": f"Completed {current_stage} and started {next_stage}.",
            },
        }
    )
    files = _validated_commit(
        root,
        {execution_relative: execution, ".flywheel/state.yaml": state},
        "advance-lifecycle",
        {
            ".flywheel/state.yaml": sha256_bytes(state_bytes) if state_bytes is not None else None,
            execution_relative: sha256_bytes(execution_bytes)
            if execution_bytes is not None
            else None,
        },
    )
    assert isinstance(execution_id, str)
    return DeterministicOperationResult(
        "advance-lifecycle", "completed", files, execution_id, next_stage
    )


def require_supported_operation(operation: str) -> None:
    supported = {"start-execution", "advance-lifecycle"}
    if operation not in supported:
        raise UnsupportedDeterministicOperationError(
            f"Operation '{operation}' is not deterministic in the approved scope; "
            "continue through governed AI execution."
        )
