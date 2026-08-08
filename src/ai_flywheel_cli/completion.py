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


def _required_strings(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CompletionRejectedError(f"{label} must be a list of strings.")
    return [str(item) for item in value]


def _mission_completion_evaluation(
    mission: dict[str, Any],
    proposed: dict[str, Any] | None,
    blockers: list[str],
    timestamp: str,
    summary: str,
) -> tuple[dict[str, Any], bool]:
    if proposed is None:
        raise CompletionRejectedError(
            "Final-goal completion requires an explicit mission completion evaluation."
        )

    success_criteria = mission.get("success_criteria")
    if not isinstance(success_criteria, list):
        raise CompletionRejectedError("Mission success criteria must be a list.")
    criterion_ids: list[str] = []
    for criterion in success_criteria:
        if not isinstance(criterion, dict) or not isinstance(criterion.get("id"), str):
            raise CompletionRejectedError("Every mission success criterion must have an id.")
        criterion_ids.append(str(criterion["id"]))

    criterion_evidence = proposed.get("criterion_evidence")
    if not isinstance(criterion_evidence, list):
        raise CompletionRejectedError("criterion_evidence must be a list.")
    mapped_ids: list[str] = []
    normalized_criterion_evidence: list[dict[str, object]] = []
    for mapping in criterion_evidence:
        if not isinstance(mapping, dict) or not isinstance(mapping.get("criterion_id"), str):
            raise CompletionRejectedError("Each criterion evidence mapping requires criterion_id.")
        criterion_id = str(mapping["criterion_id"])
        evidence_refs = _required_strings(
            mapping.get("evidence_refs"),
            f"Evidence references for {criterion_id}",
        )
        if not evidence_refs:
            raise CompletionRejectedError(
                f"Mission criterion {criterion_id} requires at least one evidence reference."
            )
        mapped_ids.append(criterion_id)
        normalized_criterion_evidence.append(
            {
                "criterion_id": criterion_id,
                "evidence_refs": list(dict.fromkeys(evidence_refs)),
            }
        )
    if len(mapped_ids) != len(set(mapped_ids)) or set(mapped_ids) != set(criterion_ids):
        raise CompletionRejectedError(
            "Mission completion evidence must map every success criterion exactly once."
        )

    approvals_required = _required_strings(
        mission.get("approvals_required", []),
        "Mission approvals_required",
    )
    proposed_approvals = proposed.get("approval_evaluations")
    if not isinstance(proposed_approvals, list):
        raise CompletionRejectedError("approval_evaluations must be a list.")
    evaluated_requirements: list[str] = []
    normalized_approvals: list[dict[str, object]] = []
    mission_objective_approval_blocking = False
    for evaluation in proposed_approvals:
        if not isinstance(evaluation, dict):
            raise CompletionRejectedError("Each approval evaluation must be a mapping.")
        requirement = evaluation.get("requirement")
        scope = evaluation.get("scope")
        status = evaluation.get("status")
        rationale = evaluation.get("rationale")
        approval_ref = evaluation.get("approval_ref")
        if not isinstance(requirement, str):
            raise CompletionRejectedError("Each approval evaluation requires requirement.")
        if scope not in {"mission-objective", "external-follow-on"}:
            raise CompletionRejectedError(
                f"Approval requirement {requirement} requires an explicit valid scope."
            )
        if status not in {"not-required", "pending", "approved", "rejected"}:
            raise CompletionRejectedError(
                f"Approval requirement {requirement} requires an explicit valid status."
            )
        if not isinstance(rationale, str) or not rationale.strip():
            raise CompletionRejectedError(
                f"Approval requirement {requirement} requires a rationale."
            )
        if status == "approved" and not isinstance(approval_ref, str):
            raise CompletionRejectedError(
                f"Approved requirement {requirement} requires approval_ref."
            )
        if approval_ref is not None and not isinstance(approval_ref, str):
            raise CompletionRejectedError(
                f"Approval reference for {requirement} must be a string or null."
            )
        evaluated_requirements.append(requirement)
        normalized_approvals.append(
            {
                "requirement": requirement,
                "scope": scope,
                "status": status,
                "approval_ref": approval_ref,
                "rationale": rationale.strip(),
            }
        )
        if scope == "mission-objective" and status != "approved":
            mission_objective_approval_blocking = True

    if (
        len(evaluated_requirements) != len(set(evaluated_requirements))
        or set(evaluated_requirements) != set(approvals_required)
    ):
        raise CompletionRejectedError(
            "Mission completion must evaluate every declared approval requirement exactly once."
        )

    proposed_blockers = proposed.get("blocker_refs", blockers)
    if _required_strings(proposed_blockers, "blocker_refs") != blockers:
        raise CompletionRejectedError(
            "Mission completion blocker_refs must exactly match governed unresolved blockers."
        )

    completed = not blockers and not mission_objective_approval_blocking
    completion: dict[str, Any] = {
        "criterion_evidence": normalized_criterion_evidence,
        "blocker_refs": blockers,
        "approval_evaluations": normalized_approvals,
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
    mission_completion: dict[str, Any] | None = None,
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
    blockers = _blocker_refs(state.get("blockers"), execution.get("blockers"))
    if mission_evaluated:
        mission_completion_value, mission_completed = _mission_completion_evaluation(
            mission,
            mission_completion,
            blockers,
            timestamp,
            summary.strip(),
        )
        mission["completion"] = mission_completion_value
        mission["status"] = "completed" if mission_completed else "blocked" if blockers else "active"

    state.update(
        {
            "status": "ready" if not blockers else "blocked",
            "active_mission": None if mission_completed else mission_id,
            "active_goal": None,
            "active_execution": None,
            "lifecycle_stage": None,
            "blockers": blockers,
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
