from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_flywheel_cli.completion import CompletionRejectedError, complete_execution
from ai_flywheel_cli.validation import ValidationIssue, ValidationResult
from test_completion import MISSION_ID, _load_yaml, _repository, _write_yaml


def test_complete_execution_completes_terminal_mission_atomically(
    tmp_path,
    monkeypatch,
) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path)
    next_goal_path.unlink()
    mission_path = (
        repository
        / ".flywheel/operations/missions"
        / MISSION_ID
        / "mission.yaml"
    )
    _write_yaml(
        mission_path,
        {
            "schema_version": 1,
            "id": MISSION_ID,
            "title": "Sample Mission",
            "status": "active",
            "objective": "Complete the sample mission without external publication.",
            "constraints": ["External publication remains approval-bound."],
            "success_criteria": [
                {"id": "MSC-001", "statement": "The sample goal completes."}
            ],
            "goals": ["001-sample-goal"],
            "approvals_required": ["Approval before external publication"],
        },
    )
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    result = complete_execution(
        repository,
        "The terminal goal and mission completed without performing external publication.",
        ("VAL-001", "EVIDENCE-001", "REUSE-001"),
        completed_at=datetime(2026, 8, 5, 5, 0, tzinfo=UTC),
    )

    assert result.next_goal_id is None
    assert _load_yaml(goal_path)["status"] == "completed"
    assert _load_yaml(mission_path)["status"] == "completed"
    state = _load_yaml(state_path)
    assert state["status"] == "ready"
    assert state["active_mission"] is None
    assert state["active_goal"] is None
    assert state["active_execution"] is None
    assert state["lifecycle_stage"] is None
    execution = _load_yaml(execution_path)
    assert execution["status"] == "succeeded"
    assert execution["lifecycle"]["reuse"]["status"] == "completed"


def test_terminal_completion_is_atomic_when_mission_validation_fails(
    tmp_path,
    monkeypatch,
) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path)
    next_goal_path.unlink()
    mission_path = (
        repository
        / ".flywheel/operations/missions"
        / MISSION_ID
        / "mission.yaml"
    )
    _write_yaml(
        mission_path,
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
            "approvals_required": [],
        },
    )
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
            ("VAL-001", "REUSE-001"),
        )

    assert {
        path: path.read_bytes()
        for path in (state_path, goal_path, execution_path, mission_path)
    } == originals
