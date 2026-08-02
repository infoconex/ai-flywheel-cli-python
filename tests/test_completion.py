from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from ai_flywheel_cli.completion import CompletionRejectedError, complete_execution
from ai_flywheel_cli.validation import ValidationIssue, ValidationResult

MISSION_ID = "sample-mission"
GOAL_ID = "001-sample-goal"
NEXT_GOAL_ID = "002-next-goal"
EXECUTION_ID = "EX-20260802T050000Z-001"


def _write_yaml(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _load_yaml(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _repository(tmp_path: Path, *, stage: str = "reuse", validation_status: str = "passed") -> tuple[Path, Path, Path, Path, Path]:
    repository = tmp_path / "repository"
    repository.mkdir()
    state_path = repository / ".flywheel/state.yaml"
    goal_path = repository / ".flywheel/operations/missions" / MISSION_ID / "goals" / f"{GOAL_ID}.yaml"
    next_goal_path = repository / ".flywheel/operations/missions" / MISSION_ID / "goals" / f"{NEXT_GOAL_ID}.yaml"
    execution_path = repository / ".flywheel/operations/records" / MISSION_ID / GOAL_ID / "executions" / f"{EXECUTION_ID}.yaml"

    _write_yaml(
        state_path,
        {
            "schema_version": 1,
            "phase": "operating",
            "readiness": "ready-for-missions",
            "status": "active",
            "active_mission": MISSION_ID,
            "active_goal": GOAL_ID,
            "active_execution": EXECUTION_ID,
            "lifecycle_stage": stage,
            "implementation_available": True,
            "application_missions_allowed": True,
            "blockers": [],
            "last_durable_update": {
                "at": "2026-08-02T05:00:00Z",
                "by": "test",
                "reason": "Fixture active.",
            },
        },
    )
    _write_yaml(
        goal_path,
        {
            "schema_version": 1,
            "id": GOAL_ID,
            "mission_id": MISSION_ID,
            "title": "Sample Goal",
            "status": "active",
            "objective": "Complete the sample goal.",
            "acceptance_criteria": [{"id": "AC-001", "statement": "The goal completes."}],
            "evidence_required": [{"criterion_id": "AC-001", "evidence_types": ["test result"]}],
        },
    )
    _write_yaml(
        next_goal_path,
        {
            "schema_version": 1,
            "id": NEXT_GOAL_ID,
            "mission_id": MISSION_ID,
            "title": "Next Goal",
            "status": "proposed",
            "objective": "Continue the mission.",
            "depends_on": [GOAL_ID],
            "acceptance_criteria": [{"id": "AC-001", "statement": "The next goal completes."}],
            "evidence_required": [{"criterion_id": "AC-001", "evidence_types": ["test result"]}],
        },
    )
    completed_stage = {
        "status": "completed",
        "started_at": "2026-08-02T05:00:00Z",
        "completed_at": "2026-08-02T05:01:00Z",
        "summary": "Completed.",
        "refs": ["EVIDENCE-001"],
        "reason": None,
    }
    lifecycle = {name: dict(completed_stage) for name in ("execute", "observe", "evaluate", "classify", "adapt", "validate", "persist")}
    lifecycle["reuse"] = {
        "status": "in-progress" if stage == "reuse" else "pending",
        "started_at": "2026-08-02T05:02:00Z" if stage == "reuse" else None,
        "completed_at": None,
        "summary": None,
        "refs": [],
        "reason": None,
    }
    _write_yaml(
        execution_path,
        {
            "schema_version": 1,
            "id": EXECUTION_ID,
            "mission_id": MISSION_ID,
            "goal_id": GOAL_ID,
            "status": "in-progress",
            "intended_outcome": "Complete the sample goal.",
            "acceptance_criteria": ["AC-001"],
            "started_at": "2026-08-02T05:00:00Z",
            "completed_at": None,
            "lifecycle": lifecycle,
            "actions": [],
            "observations": [],
            "evaluations": [],
            "classifications": [],
            "adaptations": [],
            "blockers": [],
            "approval_refs": [],
            "evidence_refs": ["EVIDENCE-001"],
            "decision_refs": [],
            "finding_refs": [],
            "validation_results": [{"id": "VAL-001", "status": validation_status}],
            "outcome": None,
            "completion": {"disposition": None, "rationale": None},
        },
    )
    return repository, state_path, goal_path, next_goal_path, execution_path


def test_complete_execution_closes_goal_and_readies_next_goal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path)
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    result = complete_execution(
        repository,
        "Release baseline completed and reusable.",
        ("VAL-001", "EVIDENCE-001"),
        completed_at=datetime(2026, 8, 2, 5, 3, tzinfo=UTC),
    )

    assert result.status == "completed"
    assert result.next_goal_id == NEXT_GOAL_ID
    state = _load_yaml(state_path)
    assert state["status"] == "ready"
    assert state["active_goal"] is None
    assert state["active_execution"] is None
    assert state["lifecycle_stage"] is None
    assert _load_yaml(goal_path)["status"] == "completed"
    assert _load_yaml(next_goal_path)["status"] == "ready"
    execution = _load_yaml(execution_path)
    assert execution["status"] == "succeeded"
    assert execution["lifecycle"]["reuse"]["status"] == "completed"
    assert execution["completion"]["disposition"] == "goal-completed"


def test_complete_execution_rejects_non_reuse_stage_without_changes(tmp_path: Path) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path, stage="persist")
    originals = [path.read_bytes() for path in (state_path, goal_path, next_goal_path, execution_path)]

    with pytest.raises(CompletionRejectedError, match="requires lifecycle stage reuse"):
        complete_execution(repository, "Complete.", ("VAL-001",))

    assert [path.read_bytes() for path in (state_path, goal_path, next_goal_path, execution_path)] == originals


def test_complete_execution_requires_passed_validation(tmp_path: Path) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path, validation_status="failed")
    originals = [path.read_bytes() for path in (state_path, goal_path, next_goal_path, execution_path)]

    with pytest.raises(CompletionRejectedError, match="passed validation result"):
        complete_execution(repository, "Complete.", ("VAL-001",))

    assert [path.read_bytes() for path in (state_path, goal_path, next_goal_path, execution_path)] == originals


def test_complete_execution_validation_rejection_is_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path)
    originals = [path.read_bytes() for path in (state_path, goal_path, next_goal_path, execution_path)]
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(
            issues=(ValidationIssue("INVALID_COMPLETION", str(execution_path), "Completion is invalid."),)
        ),
    )

    with pytest.raises(CompletionRejectedError, match="failed validation"):
        complete_execution(repository, "Complete.", ("VAL-001",))

    assert [path.read_bytes() for path in (state_path, goal_path, next_goal_path, execution_path)] == originals
