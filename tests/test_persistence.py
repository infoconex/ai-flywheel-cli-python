from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from ai_flywheel_cli.persistence import PersistenceRejectedError, persist_execution
from ai_flywheel_cli.validation import ValidationResult

MISSION_ID = "sample-mission"
GOAL_ID = "001-sample-goal"
EXECUTION_ID = "EX-20260803T010000Z-001"


def _write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _repository_at_persist(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _write_yaml(
        repository / ".flywheel/state.yaml",
        {
            "schema_version": 1,
            "phase": "operating",
            "readiness": "ready-for-missions",
            "status": "active",
            "active_mission": MISSION_ID,
            "active_goal": GOAL_ID,
            "active_execution": EXECUTION_ID,
            "lifecycle_stage": "persist",
            "implementation_available": True,
            "application_missions_allowed": True,
            "blockers": [],
            "last_durable_update": {
                "at": "2026-08-03T01:00:00Z",
                "by": "test",
                "reason": "Fixture at persist.",
            },
        },
    )
    completed_stage = {
        "status": "completed",
        "started_at": "2026-08-03T00:00:00Z",
        "completed_at": "2026-08-03T00:10:00Z",
        "summary": "Completed.",
        "refs": [],
        "reason": None,
    }
    pending_stage = {
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "summary": None,
        "refs": [],
        "reason": None,
    }
    execution_relative = (
        f".flywheel/operations/records/{MISSION_ID}/{GOAL_ID}/executions/{EXECUTION_ID}.yaml"
    )
    _write_yaml(
        repository / execution_relative,
        {
            "schema_version": 1,
            "id": EXECUTION_ID,
            "mission_id": MISSION_ID,
            "goal_id": GOAL_ID,
            "status": "in-progress",
            "intended_outcome": "Exercise persistence.",
            "acceptance_criteria": ["AC-001"],
            "started_at": "2026-08-03T00:00:00Z",
            "completed_at": None,
            "lifecycle": {
                "execute": dict(completed_stage),
                "observe": dict(completed_stage),
                "evaluate": dict(completed_stage),
                "classify": dict(completed_stage),
                "adapt": dict(completed_stage),
                "validate": dict(completed_stage),
                "persist": {
                    "status": "in-progress",
                    "started_at": "2026-08-03T01:00:00Z",
                    "completed_at": None,
                    "summary": None,
                    "refs": [],
                    "reason": None,
                },
                "reuse": dict(pending_stage),
            },
            "actions": [],
            "observations": [],
            "evaluations": [],
            "classifications": [],
            "adaptations": [
                {
                    "id": "ADAPT-001",
                    "validation_status": "passed",
                    "persistence_status": "not-persisted",
                }
            ],
            "blockers": [],
            "approval_refs": [],
            "evidence_refs": ["EVIDENCE-001"],
            "decision_refs": [],
            "finding_refs": [],
            "validation_results": [
                {
                    "id": "VAL-001",
                    "status": "passed",
                }
            ],
            "outcome": None,
            "completion": {"disposition": None, "rationale": None},
        },
    )
    return repository


def test_persist_execution_applies_plan_and_starts_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository_at_persist(tmp_path)
    monkeypatch.setattr(
        "ai_flywheel_cli.persistence.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    result = persist_execution(
        repository,
        "Persisted the validated outcome.",
        "REUSE-001",
        completed_at=datetime(2026, 8, 3, 1, 1, tzinfo=UTC),
    )

    assert result.lifecycle_stage == "reuse"
    assert result.persistence_plan_id == "PERSIST-20260803T010100Z-001"
    state = _load_yaml(repository / ".flywheel/state.yaml")
    assert state["lifecycle_stage"] == "reuse"
    execution_path = (
        repository
        / ".flywheel/operations/records"
        / MISSION_ID
        / GOAL_ID
        / "executions"
        / f"{EXECUTION_ID}.yaml"
    )
    execution = _load_yaml(execution_path)
    assert execution["lifecycle"]["persist"]["status"] == "completed"
    assert execution["lifecycle"]["reuse"]["status"] == "in-progress"
    assert execution["adaptations"][0]["persistence_status"] == "persisted"
    reuse_path = (
        repository
        / ".flywheel/operations/records"
        / MISSION_ID
        / GOAL_ID
        / "reuse/REUSE-001.yaml"
    )
    reuse = _load_yaml(reuse_path)
    assert reuse["status"] == "planned"
    plan_path = (
        repository
        / ".flywheel/operations/records"
        / MISSION_ID
        / GOAL_ID
        / "persistence"
        / f"{result.persistence_plan_id}.yaml"
    )
    plan = _load_yaml(plan_path)
    assert plan["status"] == "applied"
    assert plan["write_order"] == ["PT-001", "PT-002", "PT-003"]
    assert [target["artifact_type"] for target in plan["targets"]] == [
        "reuse-assessment",
        "execution",
        "state",
    ]
    assert plan["final_verification"]["result"] == "passed"


def test_persist_execution_rejects_wrong_stage(tmp_path: Path) -> None:
    repository = _repository_at_persist(tmp_path)
    state_path = repository / ".flywheel/state.yaml"
    state = _load_yaml(state_path)
    state["lifecycle_stage"] = "validate"
    _write_yaml(state_path, state)

    with pytest.raises(PersistenceRejectedError, match="lifecycle_stage persist"):
        persist_execution(repository, "Persisted.", "REUSE-001")


def test_persist_execution_rolls_back_when_target_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository_at_persist(tmp_path)
    state_path = repository / ".flywheel/state.yaml"
    execution_path = (
        repository
        / ".flywheel/operations/records"
        / MISSION_ID
        / GOAL_ID
        / "executions"
        / f"{EXECUTION_ID}.yaml"
    )
    original_state = state_path.read_bytes()
    original_execution = execution_path.read_bytes()
    monkeypatch.setattr(
        "ai_flywheel_cli.persistence.validate_repository",
        lambda _: ValidationResult(issues=()),
    )
    from ai_flywheel_cli import persistence

    original_write = persistence._write_yaml

    def fail_on_execution(path: Path, value: dict[str, Any]) -> None:
        if path == execution_path:
            raise OSError("simulated execution write failure")
        original_write(path, value)

    monkeypatch.setattr("ai_flywheel_cli.persistence._write_yaml", fail_on_execution)

    with pytest.raises(OSError, match="simulated execution write failure"):
        persist_execution(
            repository,
            "Persisted the validated outcome.",
            "REUSE-001",
            completed_at=datetime(2026, 8, 3, 1, 1, tzinfo=UTC),
        )

    assert state_path.read_bytes() == original_state
    assert execution_path.read_bytes() == original_execution
    record_root = repository / ".flywheel/operations/records" / MISSION_ID / GOAL_ID
    assert not (record_root / "reuse/REUSE-001.yaml").exists()
    assert list((record_root / "persistence").glob("*.yaml")) == []
