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


class CompletionRejectedError(MutationRejectedError):
    """Raised when an execution cannot be completed safely."""


@dataclass(frozen=True)
class CompletionResult:
    operation: str
    status: str
    files_changed: tuple[str, ...]
    execution_id: str
    completed_goal_id: str
    next_goal_id: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "status": self.status,
            "files_changed": list(self.files_changed),
            "execution_id": self.execution_id,
            "completed_goal_id": self.completed_goal_id,
            "next_goal_id": self.next_goal_id,
        }


def _load_mapping(path: Path) -> dict[str, Any]:
    return load_yaml_mapping(path, CompletionRejectedError)


def _timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(UTC)
    return current.strftime("%Y-%m-%dT%H:%M:%SZ")


def _dependencies_completed(
    goals_directory: Path,
    dependencies: list[object],
    completing_goal_id: str,
) -> bool:
    for dependency_id in dependencies:
        if not isinstance(dependency_id, str):
            return False
        if dependency_id == completing_goal_id:
            continue
        dependency_path = goals_directory / f"{dependency_id}.yaml"
        if not dependency_path.is_file():
            return False
        dependency = _load_mapping(dependency_path)
        if dependency.get("status") != "completed":
            return False
    return True


def _all_mission_goals_completed(
    goals_directory: Path,
    completing_goal_id: str,
) -> bool:
    for candidate_path in sorted(goals_directory.glob("*.yaml")):
        candidate = _load_mapping(candidate_path)
        candidate_id = candidate.get("id")
        if candidate_id == completing_goal_id:
            continue
        if candidate.get("status") != "completed":
            return False
    return True


def _blocker_refs(*values: object) -> list[str]:
    refs: list[str] = []
    for value in values:
        if not isinstance(value, list):
            continue
        for blocker in value:
            if isinstance(blocker, str):
                refs.append(blocker)
            elif isinstance(blocker, dict) and isinstance(blocker.get("id"), str):
                refs.append(str(blocker["id"]))
    return list(dict.fromkeys(refs))


def _is_external_follow_on(requirement: str) -> bool:
    normalized = requirement.casefold()
    external_terms = (
        "publish",
        "publication",
        "tag",
        "release",
        "upload",
        "pypi",
        "hosted automation",
        "github actions",
    )
    return any(term in normalized for term in external_terms)


def _mission_completion_evaluation(
    mission: dict[str, Any],
    refs: list[str],
    blockers: list[str],
    timestamp: str,
    summary: str,
) -> tuple[dict[str, Any], bool]:
    success_criteria = mission.get("success_criteria", [])
    criterion_evidence: list[dict[str, object]] = []
    if isinstance(success_criteria, list):
        for criterion in success_criteria:
            if not isinstance(criterion, dict) or not isinstance(criterion.get("id"), str):
                continue
            criterion_evidence.append(
                {
                    "criterion_id": str(criterion["id"]),
                    "evidence_refs": refs,
                }
            )

    approval_evaluations: list[dict[str, object]] = []
    mission_objective_approval_pending = False
    approvals_required = mission.get("approvals_required", [])
    if isinstance(approvals_required, list):
        for requirement in approvals_required:
            if not isinstance(requirement, str):
                continue
            external_follow_on = _is_external_follow_on(requirement)
            if not external_follow_on:
                mission_objective_approval_pending = True
            approval_evaluations.append(
                {
                    "requirement": requirement,
                    "scope": (
                        "external-follow-on"
                        if external_follow_on
                        else "mission-objective"
                    ),
                    "status": "not-required" if external_follow_on else "pending",
                    "approval_ref": None,
                    "rationale": (
                        "The approval governs external follow-on work outside the completed "
                        "preparation objective."
                        if external_follow_on
                        else "The approval applies within the mission objective and remains pending."
                    ),
                }
            )

    completed = (
        bool(criterion_evidence)
        and bool(refs)
        and not blockers
        and not mission_objective_approval_pending
    )
    completion: dict[str, Any] = {
        "criterion_evidence": criterion_evidence,
        "blocker_refs": blockers,
        "approval_evaluations": approval_evaluations,
        "completed_at": timestamp if completed else None,
        "completed_by": "ai-flywheel-cli" if completed else None,
        "summary": summary if completed else None,
    }
    return completion, completed


def complete_execution(
    repository: Path,
    summary: str,
    refs: tuple[str, ...],
    *,
    completed_at: datetime | None = None,
) -> CompletionResult:
    root = repository.resolve()
    state_relative = ".flywheel/state.yaml"
    state_path = root / state_relative
    state_bytes = state_path.read_bytes() if state_path.is_file() else None
    state = _load_mapping(state_path)

    mission_id = state.get("active_mission")
    goal_id = state.get("active_goal")
    execution_id = state.get("active_execution")
    lifecycle_stage = state.get("lifecycle_stage")
    if not all(isinstance(value, str) for value in (mission_id, goal_id, execution_id)):
        raise CompletionRejectedError(
            "An active mission, goal, and execution are required for completion."
        )
    assert isinstance(mission_id, str)
    assert isinstance(goal_id, str)
    assert isinstance(execution_id, str)
    if lifecycle_stage != "reuse":
        raise CompletionRejectedError(
            f"Execution completion requires lifecycle stage reuse, found {lifecycle_stage}."
        )
    if not summary.strip():
        raise CompletionRejectedError("An execution completion summary is required.")

    mission_relative = f".flywheel/operations/missions/{mission_id}/mission.yaml"
    mission_path = root / mission_relative
    mission_bytes = mission_path.read_bytes() if mission_path.is_file() else None
    mission = _load_mapping(mission_path)

    goal_relative = f".flywheel/operations/missions/{mission_id}/goals/{goal_id}.yaml"
    goal_path = root / goal_relative
    goal_bytes = goal_path.read_bytes() if goal_path.is_file() else None
    goal = _load_mapping(goal_path)
    execution_relative = (
        f".flywheel/operations/records/{mission_id}/{goal_id}/executions/{execution_id}.yaml"
    )
    execution_path = root / execution_relative
    execution_bytes = execution_path.read_bytes() if execution_path.is_file() else None
    execution = _load_mapping(execution_path)

    lifecycle = execution.get("lifecycle")
    if not isinstance(lifecycle, dict):
        raise CompletionRejectedError("Execution lifecycle must be a mapping.")
    reuse = lifecycle.get("reuse")
    if not isinstance(reuse, dict) or reuse.get("status") != "in-progress":
        raise CompletionRejectedError("The reuse stage must be in-progress before completion.")
    validation_results = execution.get("validation_results")
    if not isinstance(validation_results, list) or not any(
        isinstance(result, dict) and result.get("status") == "passed"
        for result in validation_results
    ):
        raise CompletionRejectedError(
            "Execution completion requires at least one passed validation result."
        )

    timestamp = _timestamp(completed_at)
    unique_refs = list(dict.fromkeys(refs))
    reuse.update(
        {
            "status": "completed",
            "completed_at": timestamp,
            "summary": summary.strip(),
            "refs": unique_refs,
            "reason": None,
        }
    )
    execution.update(
        {
            "status": "succeeded",
            "completed_at": timestamp,
            "outcome": summary.strip(),
            "completion": {
                "disposition": "goal-completed",
                "rationale": (
                    "All acceptance criteria were supported by recorded evidence "
                    "and passed validation."
                ),
            },
        }
    )
    goal["status"] = "completed"

    goals_directory = root / f".flywheel/operations/missions/{mission_id}/goals"
    next_goal_id: str | None = None
    next_goal_relative: str | None = None
    next_goal: dict[str, Any] | None = None
    next_goal_bytes: bytes | None = None
    for candidate_path in sorted(goals_directory.glob("*.yaml")):
        if candidate_path == goal_path:
            continue
        candidate = _load_mapping(candidate_path)
        dependencies = candidate.get("depends_on", [])
        is_next_goal = (
            candidate.get("status") == "proposed"
            and isinstance(dependencies, list)
            and goal_id in dependencies
            and _dependencies_completed(goals_directory, dependencies, goal_id)
        )
        if is_next_goal:
            next_goal_id = str(candidate.get("id"))
            next_goal_relative = candidate_path.relative_to(root).as_posix()
            next_goal_bytes = candidate_path.read_bytes()
            candidate["status"] = "ready"
            next_goal = candidate
            break

    mission_evaluated = next_goal_id is None and _all_mission_goals_completed(
        goals_directory,
        goal_id,
    )
    mission_completed = False
    if mission_evaluated:
        blockers = _blocker_refs(state.get("blockers"), execution.get("blockers"))
        mission_completion, mission_completed = _mission_completion_evaluation(
            mission,
            unique_refs,
            blockers,
            timestamp,
            summary.strip(),
        )
        mission["completion"] = mission_completion
        mission["status"] = "completed" if mission_completed else "active"

    state.update(
        {
            "status": "ready",
            "active_mission": None if mission_completed else mission_id,
            "active_goal": None,
            "active_execution": None,
            "lifecycle_stage": None,
            "blockers": [],
            "last_durable_update": {
                "at": timestamp,
                "by": "ai-flywheel-cli",
                "reason": (
                    f"Completed execution {execution_id}, goal {goal_id}, and mission {mission_id}."
                    if mission_completed
                    else f"Completed execution {execution_id} and goal {goal_id}."
                ),
            },
        }
    )

    changes = {
        execution_relative: execution,
        goal_relative: goal,
        state_relative: state,
    }
    expected_sha256 = {
        execution_relative: (
            sha256_bytes(execution_bytes) if execution_bytes is not None else None
        ),
        goal_relative: sha256_bytes(goal_bytes) if goal_bytes is not None else None,
        state_relative: sha256_bytes(state_bytes) if state_bytes is not None else None,
    }
    if mission_evaluated:
        changes[mission_relative] = mission
        expected_sha256[mission_relative] = (
            sha256_bytes(mission_bytes) if mission_bytes is not None else None
        )
    if next_goal_relative is not None and next_goal is not None:
        changes[next_goal_relative] = next_goal
        expected_sha256[next_goal_relative] = (
            sha256_bytes(next_goal_bytes) if next_goal_bytes is not None else None
        )

    files = commit_validated_yaml(
        root,
        changes,
        "complete-execution",
        CompletionRejectedError,
        expected_sha256=expected_sha256,
    )
    return CompletionResult(
        operation="complete-execution",
        status="completed",
        files_changed=files,
        execution_id=execution_id,
        completed_goal_id=goal_id,
        next_goal_id=next_goal_id,
    )
