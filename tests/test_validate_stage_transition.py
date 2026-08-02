from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from ai_flywheel_cli.deterministic_operations import advance_lifecycle
from ai_flywheel_cli.validation import ValidationResult


def _write_yaml(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _load_yaml(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_advance_lifecycle_carries_refs_into_validate_stage(
    tmp_path: Path, monkeypatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    execution_id = "EX-20260802T043000Z-001"
    mission_id = "sample-mission"
    goal_id = "001-sample-goal"
    execution_relative = (
        f".flywheel/operations/records/{mission_id}/{goal_id}/executions/{execution_id}.yaml"
    )
    _write_yaml(
        repository / ".flywheel/state.yaml",
        {
            "schema_version": 1,
            "phase": "operating",
            "readiness": "ready-for-missions",
            "status": "active",
            "active_mission": mission_id,
            "active_goal": goal_id,
            "active_execution": execution_id,
            "lifecycle_stage": "adapt",
            "implementation_available": True,
            "application_missions_allowed": True,
            "blockers": [],
            "last_durable_update": {
                "at": "2026-08-02T04:30:00Z",
                "by": "test",
                "reason": "Fixture active.",
            },
        },
    )
    pending_stage = {
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "summary": None,
        "refs": [],
        "reason": None,
    }
    completed_stage = {
        "status": "completed",
        "started_at": "2026-08-02T04:00:00Z",
        "completed_at": "2026-08-02T04:10:00Z",
        "summary": "Completed.",
        "refs": ["EVIDENCE-001"],
        "reason": None,
    }
    _write_yaml(
        repository / execution_relative,
        {
            "schema_version": 1,
            "id": execution_id,
            "mission_id": mission_id,
            "goal_id": goal_id,
            "status": "in-progress",
            "intended_outcome": "Exercise the validation transition.",
            "acceptance_criteria": ["AC-001"],
            "started_at": "2026-08-02T04:00:00Z",
            "completed_at": None,
            "lifecycle": {
                "execute": dict(completed_stage),
                "observe": dict(completed_stage),
                "evaluate": dict(completed_stage),
                "classify": dict(completed_stage),
                "adapt": {
                    "status": "in-progress",
                    "started_at": "2026-08-02T04:20:00Z",
                    "completed_at": None,
                    "summary": None,
                    "refs": [],
                    "reason": None,
                },
                "validate": dict(pending_stage),
                "persist": dict(pending_stage),
                "reuse": dict(pending_stage),
            },
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
            "validation_results": [
                {
                    "id": "VAL-001",
                    "phase": "planned",
                    "domain": "repository",
                    "status": "pending",
                    "severity": "info",
                    "adaptation_refs": ["ADAPT-001"],
                    "criterion_refs": ["AC-001"],
                    "rule_refs": [],
                    "method": "Run repository validation.",
                    "scope": ["repository"],
                    "expected_outcome": "Validation passes.",
                    "actual_outcome": None,
                    "expected_evidence": ["Validation output"],
                    "evidence_refs": [],
                    "eligible": True,
                    "exclusion_reason": None,
                    "executed_at": None,
                    "finding_ref": None,
                    "recovery_action": None,
                    "supersedes_ref": None,
                }
            ],
            "outcome": None,
            "completion": {"disposition": None, "rationale": None},
        },
    )
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    result = advance_lifecycle(
        repository,
        "Adaptation completed.",
        ("ADAPT-001", "VAL-001"),
        completed_at=datetime(2026, 8, 2, 4, 31, tzinfo=UTC),
        expected_stage="adapt",
    )

    assert result.lifecycle_stage == "validate"
    execution = _load_yaml(repository / execution_relative)
    lifecycle = execution["lifecycle"]
    assert isinstance(lifecycle, dict)
    assert lifecycle["validate"]["status"] == "in-progress"
    assert lifecycle["validate"]["refs"] == ["ADAPT-001", "VAL-001"]
