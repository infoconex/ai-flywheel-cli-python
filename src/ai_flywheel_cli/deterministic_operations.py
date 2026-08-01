from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

import yaml

from ai_flywheel_cli.operations import OperationError, RepositoryLock
from ai_flywheel_cli.validation import LIFECYCLE_STAGES, validate_repository

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


class TransitionRejectedError(OperationError):
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
    if not path.is_file():
        raise TransitionRejectedError(f"Required artifact does not exist: {path}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TransitionRejectedError(f"Artifact must be a YAML mapping: {path}")
    return value


def _timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(UTC)
    return current.strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(dict(value), sort_keys=False), encoding="utf-8")


def _validated_commit(repository: Path, changes: Mapping[str, Mapping[str, Any]], command: str) -> tuple[str, ...]:
    repository = repository.resolve()
    with RepositoryLock(repository, command):
        shadow_parent = Path(tempfile.mkdtemp(prefix="flywheel-shadow-"))
        shadow = shadow_parent / "repository"
        backups: dict[str, bytes | None] = {}
        try:
            shutil.copytree(repository, shadow, ignore=shutil.ignore_patterns(".git", ".runtime"))
            for relative_path, value in changes.items():
                _write_yaml(shadow / relative_path, value)
            validation = validate_repository(shadow)
            if not validation.passed:
                details = "; ".join(
                    f"{issue.code}:{issue.path}:{issue.message}" for issue in validation.issues
                )
                raise TransitionRejectedError(f"Proposed mutation failed validation: {details}")
            for relative_path, value in changes.items():
                target = repository / relative_path
                backups[relative_path] = target.read_bytes() if target.is_file() else None
                temporary = target.with_suffix(target.suffix + ".tmp")
                _write_yaml(temporary, value)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary.replace(target)
        except Exception:
            for relative_path, prior in backups.items():
                target = repository / relative_path
                if prior is None:
                    target.unlink(missing_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(prior)
            raise
        finally:
            shutil.rmtree(shadow_parent, ignore_errors=True)
    return tuple(sorted(changes))


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
    state = _load_mapping(state_path)
    goal = _load_mapping(goal_path)
    if state.get("active_execution") is not None:
        raise TransitionRejectedError("Cannot start an execution while another execution is active.")
    if execution_path.exists():
        raise TransitionRejectedError(f"Execution already exists: {execution_id}")
    if goal.get("mission_id") != mission_id or goal.get("id") != goal_id:
        raise TransitionRejectedError("Goal identity or mission reference does not match the request.")
    criteria = [
        item.get("id")
        for item in goal.get("acceptance_criteria", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    if not criteria:
        raise TransitionRejectedError("Goal must define acceptance criteria before execution starts.")
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
) -> DeterministicOperationResult:
    root = repository.resolve()
    state = _load_mapping(root / ".flywheel/state.yaml")
    mission_id = state.get("active_mission")
    goal_id = state.get("active_goal")
    execution_id = state.get("active_execution")
    current_stage = state.get("lifecycle_stage")
    if not all(isinstance(value, str) for value in (mission_id, goal_id, execution_id, current_stage)):
        raise TransitionRejectedError("An active mission, goal, execution, and lifecycle stage are required.")
    if current_stage not in LIFECYCLE_STAGES:
        raise TransitionRejectedError(f"Unsupported lifecycle stage: {current_stage}")
    execution_relative = (
        f".flywheel/operations/records/{mission_id}/{goal_id}/executions/{execution_id}.yaml"
    )
    execution = _load_mapping(root / execution_relative)
    lifecycle = execution.get("lifecycle")
    if not isinstance(lifecycle, dict):
        raise TransitionRejectedError("Execution lifecycle must be a mapping.")
    stage = lifecycle.get(current_stage)
    if not isinstance(stage, dict) or stage.get("status") != "in-progress":
        raise TransitionRejectedError("The active lifecycle stage must be in-progress before advancing.")
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
            "Completing reuse and closing the execution remains governed AI work in the approved scope."
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
    )
    return DeterministicOperationResult(
        "advance-lifecycle", "completed", files, execution_id, next_stage
    )


def require_supported_operation(operation: str) -> None:
    supported = {"start-execution", "advance-lifecycle"}
    if operation not in supported:
        raise UnsupportedDeterministicOperationError(
            f"Operation '{operation}' is not deterministic in the approved scope; continue through governed AI execution."
        )
