from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_flywheel_cli.completion import CompletionRejectedError, complete_execution
from ai_flywheel_cli.validation import ValidationIssue, ValidationResult
from test_completion import MISSION_ID, _load_yaml, _repository, _write_yaml


def _mission_path(repository):
    return repository / ".flywheel/operations/missions" / MISSION_ID / "mission.yaml"


def _completion(
    *,
    requirement: str | None = None,
    scope: str = "external-follow-on",
    status: str = "pending",
    blocker_refs: list[str] | None = None,
) -> dict[str, object]:
    approvals: list[dict[str, object]] = []
    if requirement is not None:
        approvals.append(
            {
                "requirement": requirement,
                "scope": scope,
                "status": status,
                "approval_ref": "APPROVAL-001" if status == "approved" else None,
                "rationale": "Explicit governed approval evaluation.",
            }
        )
    return {
        "criterion_evidence": [
            {"criterion_id": "MSC-001", "evidence_refs": ["EVIDENCE-001"]}
        ],
        "blocker_refs": blocker_refs or [],
        "approval_evaluations": approvals,
    }


def _write_mission(repository, *, approvals_required: list[str] | None = None) -> None:
    _write_yaml(
        _mission_path(repository),
        {
            "schema_version": 1,
            "id": MISSION_ID,
            "title": "Sample Mission",
            "status": "active",
            "objective": "Complete the sample mission.",
            "constraints": [],
            "success_criteria": [
                {"id": "MSC-001", "statement": "The sample goal completes."}
            ],
            "goals": ["001-sample-goal"],
            "approvals_required": approvals_required or [],
        },
    )


def test_complete_execution_completes_terminal_mission_with_external_follow_on(
    tmp_path,
    monkeypatch,
) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path)
    next_goal_path.unlink()
    requirement = "Approval before external publication"
    _write_mission(repository, approvals_required=[requirement])
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    result = complete_execution(
        repository,
        "The terminal goal and mission completed without performing external publication.",
        ("VAL-001", "EVIDENCE-001", "REUSE-001"),
        mission_completion=_completion(requirement=requirement),
        completed_at=datetime(2026, 8, 5, 5, 0, tzinfo=UTC),
    )

    assert result.next_goal_id is None
    assert _load_yaml(goal_path)["status"] == "completed"
    mission = _load_yaml(_mission_path(repository))
    assert mission["status"] == "completed"
    completion = mission["completion"]
    assert completion["approval_evaluations"][0]["scope"] == "external-follow-on"
    assert completion["approval_evaluations"][0]["status"] == "pending"
    state = _load_yaml(state_path)
    assert state["status"] == "ready"
    assert state["active_mission"] is None
    assert state["active_goal"] is None
    assert state["active_execution"] is None
    assert state["lifecycle_stage"] is None
    execution = _load_yaml(execution_path)
    assert execution["status"] == "succeeded"
    assert execution["lifecycle"]["reuse"]["status"] == "completed"


def test_terminal_completion_keeps_mission_active_for_pending_objective_approval(
    tmp_path,
    monkeypatch,
) -> None:
    repository, state_path, _, next_goal_path, _ = _repository(tmp_path)
    next_goal_path.unlink()
    requirement = "Security authorization"
    _write_mission(repository, approvals_required=[requirement])
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    complete_execution(
        repository,
        "Goal complete; mission approval remains pending.",
        ("VAL-001", "EVIDENCE-001", "REUSE-001"),
        mission_completion=_completion(
            requirement=requirement,
            scope="mission-objective",
            status="pending",
        ),
    )

    mission = _load_yaml(_mission_path(repository))
    assert mission["status"] == "active"
    assert mission["completion"]["completed_at"] is None
    state = _load_yaml(state_path)
    assert state["active_mission"] == MISSION_ID
    assert state["active_goal"] is None
    assert state["active_execution"] is None


def test_terminal_completion_preserves_governed_blockers(
    tmp_path,
    monkeypatch,
) -> None:
    repository, state_path, _, next_goal_path, _ = _repository(tmp_path)
    next_goal_path.unlink()
    _write_mission(repository)
    state = _load_yaml(state_path)
    state["blockers"] = ["BLOCKER-001"]
    _write_yaml(state_path, state)
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    complete_execution(
        repository,
        "Goal complete; mission blocker remains.",
        ("VAL-001", "EVIDENCE-001", "REUSE-001"),
        mission_completion=_completion(blocker_refs=["BLOCKER-001"]),
    )

    mission = _load_yaml(_mission_path(repository))
    assert mission["status"] == "blocked"
    assert mission["completion"]["blocker_refs"] == ["BLOCKER-001"]
    state = _load_yaml(state_path)
    assert state["status"] == "blocked"
    assert state["blockers"] == ["BLOCKER-001"]
    assert state["active_mission"] == MISSION_ID


def test_terminal_completion_rejects_missing_explicit_evaluation_without_changes(
    tmp_path,
) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path)
    next_goal_path.unlink()
    _write_mission(repository)
    mission_path = _mission_path(repository)
    originals = {
        path: path.read_bytes()
        for path in (state_path, goal_path, execution_path, mission_path)
    }

    with pytest.raises(CompletionRejectedError, match="explicit mission completion evaluation"):
        complete_execution(
            repository,
            "Complete.",
            ("VAL-001", "EVIDENCE-001", "REUSE-001"),
        )

    assert {
        path: path.read_bytes()
        for path in (state_path, goal_path, execution_path, mission_path)
    } == originals


def test_terminal_completion_rejects_incomplete_criterion_mapping_without_changes(
    tmp_path,
) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path)
    next_goal_path.unlink()
    _write_mission(repository)
    mission_path = _mission_path(repository)
    originals = {
        path: path.read_bytes()
        for path in (state_path, goal_path, execution_path, mission_path)
    }
    proposed = _completion()
    proposed["criterion_evidence"] = []

    with pytest.raises(CompletionRejectedError, match="every success criterion exactly once"):
        complete_execution(
            repository,
            "Complete.",
            ("VAL-001", "EVIDENCE-001", "REUSE-001"),
            mission_completion=proposed,
        )

    assert {
        path: path.read_bytes()
        for path in (state_path, goal_path, execution_path, mission_path)
    } == originals


def test_terminal_completion_rejects_ambiguous_approval_scope_without_changes(
    tmp_path,
) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path)
    next_goal_path.unlink()
    requirement = "Human authorization"
    _write_mission(repository, approvals_required=[requirement])
    mission_path = _mission_path(repository)
    originals = {
        path: path.read_bytes()
        for path in (state_path, goal_path, execution_path, mission_path)
    }
    proposed = _completion(requirement=requirement)
    proposed["approval_evaluations"][0]["scope"] = "unknown"

    with pytest.raises(CompletionRejectedError, match="explicit valid scope"):
        complete_execution(
            repository,
            "Complete.",
            ("VAL-001", "EVIDENCE-001", "REUSE-001"),
            mission_completion=proposed,
        )

    assert {
        path: path.read_bytes()
        for path in (state_path, goal_path, execution_path, mission_path)
    } == originals


def test_terminal_completion_is_atomic_when_mission_validation_fails(
    tmp_path,
    monkeypatch,
) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path)
    next_goal_path.unlink()
    _write_mission(repository)
    mission_path = _mission_path(repository)
    originals = {
        path: path.read_bytes()
        for path in (state_path, goal_path, execution_path, mission_path)
    }
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(
            issues=(
                ValidationIssue(
                    "INVALID_TERMINAL_MISSION",
                    str(mission_path),
                    "Terminal mission completion is invalid.",
                ),
            )
        ),
    )

    with pytest.raises(CompletionRejectedError, match="failed validation"):
        complete_execution(
            repository,
            "Complete.",
            ("VAL-001", "EVIDENCE-001", "REUSE-001"),
            mission_completion=_completion(),
        )

    assert {
        path: path.read_bytes() for path in (state_path, goal_path, execution_path, mission_path)
    } == originals
