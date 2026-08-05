from __future__ import annotations

from pathlib import Path

import yaml

from ai_flywheel_cli.schema_validation import validate_declared_artifacts


def _write_yaml(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _lifecycle() -> dict[str, object]:
    return {
        stage: {
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "summary": None,
            "refs": [],
            "reason": None,
        }
        for stage in (
            "execute",
            "observe",
            "evaluate",
            "classify",
            "adapt",
            "validate",
            "persist",
            "reuse",
        )
    }


def _execution(execution_id: str, mission_id: str, goal_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": execution_id,
        "mission_id": mission_id,
        "goal_id": goal_id,
        "status": "in-progress",
        "lifecycle": _lifecycle(),
        "evidence_refs": [],
    }


def test_historical_execution_is_not_forced_through_current_schema(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / ".flywheel/operating-model/schemas/execution.schema.yaml",
        {
            "type": "object",
            "required": ["current_only"],
        },
    )
    historical = _execution("EX-20260801T000000Z-001", "historical", "001-goal")
    _write_yaml(
        tmp_path
        / ".flywheel/operations/records/historical/001-goal/executions"
        / "EX-20260801T000000Z-001.yaml",
        historical,
    )

    issues = []
    validate_declared_artifacts(
        tmp_path,
        {"active_mission": "current", "active_goal": None, "active_execution": None},
        issues,
    )

    assert not any(issue.code == "SCHEMA_VALIDATION_FAILED" for issue in issues)


def test_active_execution_uses_current_schema(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / ".flywheel/operating-model/schemas/execution.schema.yaml",
        {
            "type": "object",
            "required": ["current_only"],
        },
    )
    execution_id = "EX-20260802T051700Z-001"
    active = _execution(execution_id, "current", "002-goal")
    _write_yaml(
        tmp_path
        / ".flywheel/operations/records/current/002-goal/executions"
        / f"{execution_id}.yaml",
        active,
    )

    issues = []
    validate_declared_artifacts(
        tmp_path,
        {
            "active_mission": "current",
            "active_goal": "002-goal",
            "active_execution": execution_id,
        },
        issues,
    )

    matching = [issue for issue in issues if issue.code == "SCHEMA_VALIDATION_FAILED"]
    assert len(matching) == 1
    assert "current_only" in matching[0].message
