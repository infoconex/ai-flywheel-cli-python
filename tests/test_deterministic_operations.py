from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from ai_flywheel_cli.deterministic_operations import (
    TransitionRejectedError,
    UnsupportedDeterministicOperationError,
    advance_lifecycle,
    require_supported_operation,
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


def _repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _write_yaml(
        repository / ".flywheel/state.yaml",
        {
            "schema_version": 1,
            "phase": "operational",
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
    return repository


def test_start_execution_synchronizes_goal_execution_and_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    monkeypatch.setattr(
        "ai_flywheel_cli.deterministic_operations.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    result = start_execution(
        repository,
        MISSION_ID,
        GOAL_ID,
        EXECUTION_ID,
        "Complete the sample goal.",
        started_at=datetime(2026, 8, 1, 17, 2, tzinfo=UTC),
    )

    assert result.status == "completed"
    assert result.lifecycle_stage == "execute"
    state = _load_yaml(repository / ".flywheel/state.yaml")
    assert state["active_goal"] == GOAL_ID
    assert state["active_execution"] == EXECUTION_ID
    assert state["lifecycle_stage"] == "execute"
    goal = _load_yaml(
        repository
        / ".flywheel/operations/missions"
        / MISSION_ID
        / "goals"
        / f"{GOAL_ID}.yaml"
    )
    assert goal["status"] == "active"


def test_start_execution_validation_failure_leaves_repository_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    state_path = repository / ".flywheel/state.yaml"
    goal_path = (
        repository
        / ".flywheel/operations/missions"
        / MISSION_ID
        / "goals"
        / f"{GOAL_ID}.yaml"
    )
    original_state = state_path.read_bytes()
    original_goal = goal_path.read_bytes()
    monkeypatch.setattr(
        "ai_flywheel_cli.deterministic_operations.validate_repository",
        lambda _: ValidationResult(
            issues=(
                ValidationIssue(
                    "INVALID_EXECUTION",
                    ".flywheel/state.yaml",
                    "The proposed execution is invalid.",
                ),
            )
        ),
    )

    with pytest.raises(TransitionRejectedError, match="failed validation"):
        start_execution(
            repository,
            MISSION_ID,
            GOAL_ID,
            EXECUTION_ID,
            "Complete the sample goal.",
            started_at=datetime(2026, 8, 1, 17, 2, tzinfo=UTC),
        )

    execution_path = (
        repository
        / ".flywheel/operations/records"
        / MISSION_ID
        / GOAL_ID
        / "executions"
        / f"{EXECUTION_ID}.yaml"
    )
    assert state_path.read_bytes() == original_state
    assert goal_path.read_bytes() == original_goal
    assert not execution_path.exists()


def test_start_execution_rejects_existing_active_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    state_path = repository / ".flywheel/state.yaml"
    state = _load_yaml(state_path)
    state["active_goal"] = GOAL_ID
    state["active_execution"] = "EX-20260801T170000Z-999"
    state["lifecycle_stage"] = "execute"
    state["status"] = "active"
    _write_yaml(state_path, state)
    monkeypatch.setattr(
        "ai_flywheel_cli.deterministic_operations.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    with pytest.raises(TransitionRejectedError, match="another execution is active"):
        start_execution(
            repository,
            MISSION_ID,
            GOAL_ID,
            EXECUTION_ID,
            "Complete the sample goal.",
        )


def test_advance_lifecycle_completes_current_and_starts_next(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    monkeypatch.setattr(
        "ai_flywheel_cli.deterministic_operations.validate_repository",
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

    result = advance_lifecycle(
        repository,
        "Execution work completed.",
        ("EVIDENCE-001",),
        completed_at=datetime(2026, 8, 1, 17, 3, tzinfo=UTC),
    )

    assert result.lifecycle_stage == "observe"
    state = _load_yaml(repository / ".flywheel/state.yaml")
    assert state["lifecycle_stage"] == "observe"
    execution = _load_yaml(
        repository
        / ".flywheel/operations/records"
        / MISSION_ID
        / GOAL_ID
        / "executions"
        / f"{EXECUTION_ID}.yaml"
    )
    lifecycle = execution["lifecycle"]
    assert isinstance(lifecycle, dict)
    assert lifecycle["execute"]["status"] == "completed"
    assert lifecycle["observe"]["status"] == "in-progress"


def test_advance_lifecycle_rejects_blank_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    monkeypatch.setattr(
        "ai_flywheel_cli.deterministic_operations.validate_repository",
        lambda _: ValidationResult(issues=()),
    )
    start_execution(
        repository,
        MISSION_ID,
        GOAL_ID,
        EXECUTION_ID,
        "Complete the sample goal.",
    )

    with pytest.raises(TransitionRejectedError, match="summary is required"):
        advance_lifecycle(repository, "   ", ())


def test_unsupported_operation_requires_governed_ai_fallback() -> None:
    with pytest.raises(UnsupportedDeterministicOperationError, match="governed AI execution"):
        require_supported_operation("create-mission")
