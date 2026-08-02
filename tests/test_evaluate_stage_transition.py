from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from ai_flywheel_cli.deterministic_operations import (
    TransitionRejectedError,
    advance_lifecycle,
    start_execution,
)
from ai_flywheel_cli.validation import ValidationIssue, ValidationResult

MISSION_ID = "sample-mission"
GOAL_ID = "001-sample-goal"
EXECUTION_ID = "EX-20260801T170200Z-001"


def _write_yaml(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _load_yaml(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _execution_path(repository: Path) -> Path:
    return (
        repository
        / ".flywheel/operations/records"
        / MISSION_ID
        / GOAL_ID
        / "executions"
        / f"{EXECUTION_ID}.yaml"
    )


def _repository_at_evaluate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _write_yaml(
        repository / ".flywheel/state.yaml",
        {
            "schema_version": 1,
            "phase": "operating",
            "readiness": "ready-for-missions",
            "status": "ready",
            "active_mission": MISSION_ID,
            "active_goal": None,
            "active_execution": None,
            "lifecycle_stage": None,
            "implementation_available": True,
            "application_missions_allowed": True,
            "blockers": [],
            "last_durable_update": {
                "at": "2026-08-01T17:00:00Z",
                "by": "test",
                "reason": "Fixture ready.",
            },
        },
    )
    _write_yaml(
        repository
        / ".flywheel/operations/missions"
        / MISSION_ID
        / "goals"
        / f"{GOAL_ID}.yaml",
        {
            "schema_version": 1,
            "id": GOAL_ID,
            "mission_id": MISSION_ID,
            "title": "Sample Goal",
            "status": "proposed",
            "objective": "Exercise deterministic operations.",
            "acceptance_criteria": [
                {"id": "AC-001", "statement": "The operation succeeds."}
            ],
        },
    )
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )
    start_execution(
        repository,
        MISSION_ID,
        GOAL_ID,
        EXECUTION_ID,
        "Complete the sample goal.",
        started_at=datetime(2026, 8, 1, 17, 2, tzinfo=UTC),
    )
    advance_lifecycle(
        repository,
        "Execution work completed.",
        ("implementation.py",),
        completed_at=datetime(2026, 8, 1, 17, 3, tzinfo=UTC),
    )
    execution_path = _execution_path(repository)
    execution = _load_yaml(execution_path)
    execution["observations"] = [
        {
            "id": "OBS-001",
            "statement": "The local quality gate passed.",
            "type": "direct",
            "status": "complete",
            "observed_at": "2026-08-01T17:04:00Z",
            "source_or_method": "Executed the local validation command.",
            "evidence_refs": ["EVIDENCE-001"],
            "uncertainty": None,
            "conflicts_with": [],
        }
    ]
    execution["evidence_refs"] = ["EVIDENCE-001"]
    _write_yaml(execution_path, execution)
    advance_lifecycle(
        repository,
        "Observed the complete local validation result.",
        ("OBS-001", "EVIDENCE-001"),
        completed_at=datetime(2026, 8, 1, 17, 5, tzinfo=UTC),
        expected_stage="observe",
    )
    return repository


def test_advance_evaluate_with_structured_record_starts_classify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository_at_evaluate(tmp_path, monkeypatch)
    execution_path = _execution_path(repository)
    execution = _load_yaml(execution_path)
    execution["evaluations"] = [
        {
            "id": "EVAL-001",
            "statement": "The quality gate satisfies the acceptance criteria.",
            "result": "supports",
            "observation_refs": ["OBS-001"],
            "evidence_refs": ["EVIDENCE-001"],
            "criterion_refs": ["AC-001"],
            "rule_refs": [],
            "limitations": [],
            "rationale": "The recorded command result passed every adopted check.",
        }
    ]
    _write_yaml(execution_path, execution)

    result = advance_lifecycle(
        repository,
        "Evaluated the quality gate against the acceptance criteria.",
        ("EVAL-001", "OBS-001", "EVIDENCE-001"),
        completed_at=datetime(2026, 8, 1, 17, 6, tzinfo=UTC),
        expected_stage="evaluate",
    )

    assert result.lifecycle_stage == "classify"
    state = _load_yaml(repository / ".flywheel/state.yaml")
    assert state["lifecycle_stage"] == "classify"
    updated_execution = _load_yaml(execution_path)
    lifecycle = updated_execution["lifecycle"]
    assert isinstance(lifecycle, dict)
    assert lifecycle["evaluate"]["status"] == "completed"
    assert lifecycle["evaluate"]["refs"] == [
        "EVAL-001",
        "OBS-001",
        "EVIDENCE-001",
    ]
    assert lifecycle["classify"]["status"] == "in-progress"


def test_advance_evaluate_rejects_missing_evaluation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository_at_evaluate(tmp_path, monkeypatch)
    state_path = repository / ".flywheel/state.yaml"
    execution_path = _execution_path(repository)
    original_state = state_path.read_bytes()
    original_execution = execution_path.read_bytes()

    def validate_evaluation(candidate: Path) -> ValidationResult:
        execution = _load_yaml(_execution_path(candidate))
        if execution.get("evaluations"):
            return ValidationResult(issues=())
        return ValidationResult(
            issues=(
                ValidationIssue(
                    "SCHEMA_INVALID",
                    str(_execution_path(candidate).relative_to(candidate)),
                    "Completed evaluate requires at least one evaluation.",
                ),
            )
        )

    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        validate_evaluation,
    )

    with pytest.raises(TransitionRejectedError, match="failed validation"):
        advance_lifecycle(
            repository,
            "Evaluation was not recorded.",
            ("EVAL-001",),
            completed_at=datetime(2026, 8, 1, 17, 6, tzinfo=UTC),
            expected_stage="evaluate",
        )

    assert state_path.read_bytes() == original_state
    assert execution_path.read_bytes() == original_execution
