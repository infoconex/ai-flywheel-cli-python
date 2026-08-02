from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from ai_flywheel_cli.deterministic_operations import (
    LIFECYCLE_ORDER,
    TransitionRejectedError,
    UnsupportedDeterministicOperationError,
    advance_lifecycle,
)
from ai_flywheel_cli.validation import ValidationIssue, ValidationResult

MISSION_ID = "sample-mission"
GOAL_ID = "001-sample-goal"
EXECUTION_ID = "EX-20260802T050000Z-001"
BASE_TIME = datetime(2026, 8, 2, 5, 0, tzinfo=UTC)


def _write_yaml(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _load_yaml(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _pending_stage() -> dict[str, object]:
    return {
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "summary": None,
        "refs": [],
        "reason": None,
    }


def _completed_stage(stage: str, index: int) -> dict[str, object]:
    started = BASE_TIME + timedelta(minutes=index * 2)
    completed = started + timedelta(minutes=1)
    return {
        "status": "completed",
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "completed_at": completed.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": f"Completed {stage}.",
        "refs": [f"REF-{stage.upper()}"],
        "reason": None,
    }


def _active_stage(stage: str, index: int) -> dict[str, object]:
    started = BASE_TIME + timedelta(minutes=index * 2)
    return {
        "status": "in-progress",
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "completed_at": None,
        "summary": None,
        "refs": ["VAL-001"] if stage == "validate" else [],
        "reason": None,
    }


def _execution_for_stage(stage: str) -> dict[str, object]:
    stage_index = LIFECYCLE_ORDER.index(stage)
    lifecycle: dict[str, object] = {}
    for index, lifecycle_stage in enumerate(LIFECYCLE_ORDER):
        if index < stage_index:
            lifecycle[lifecycle_stage] = _completed_stage(lifecycle_stage, index)
        elif index == stage_index:
            lifecycle[lifecycle_stage] = _active_stage(lifecycle_stage, index)
        else:
            lifecycle[lifecycle_stage] = _pending_stage()

    return {
        "schema_version": 1,
        "id": EXECUTION_ID,
        "mission_id": MISSION_ID,
        "goal_id": GOAL_ID,
        "status": "in-progress",
        "intended_outcome": "Exercise all deterministic lifecycle transitions.",
        "acceptance_criteria": ["AC-001"],
        "started_at": BASE_TIME.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "completed_at": None,
        "lifecycle": lifecycle,
        "actions": [],
        "observations": [
            {
                "id": "OBS-001",
                "statement": "The expected behavior was observed.",
                "type": "direct",
                "status": "complete",
                "observed_at": BASE_TIME.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source_or_method": "Lifecycle transition test fixture.",
                "evidence_refs": ["EVIDENCE-001"],
                "uncertainty": None,
                "conflicts_with": [],
            }
        ],
        "evaluations": [
            {
                "id": "EVAL-001",
                "statement": "The observation supports the criterion.",
                "result": "supports",
                "observation_refs": ["OBS-001"],
                "evidence_refs": ["EVIDENCE-001"],
                "criterion_refs": ["AC-001"],
                "rule_refs": [],
                "limitations": [],
                "rationale": "The recorded result matches the expected behavior.",
            }
        ],
        "classifications": [
            {
                "id": "CLASS-001",
                "type": "decision",
                "statement": "Continue using the validated lifecycle behavior.",
                "evaluation_refs": ["EVAL-001"],
                "evidence_refs": ["EVIDENCE-001"],
                "rationale": "The evaluation supports the decision.",
                "certainty": "confirmed",
                "uncertainty": None,
                "conflicts_with": [],
                "related_classification_refs": [],
                "decision_ref": "DECISION-001",
                "finding_ref": None,
                "validation_refs": [],
            }
        ],
        "adaptations": [
            {
                "id": "ADAPT-001",
                "type": "plan",
                "statement": "Use the validated transition sequence.",
                "classification_refs": ["CLASS-001"],
                "evaluation_refs": ["EVAL-001"],
                "observation_refs": ["OBS-001"],
                "evidence_refs": ["EVIDENCE-001"],
                "affected_scope": ["lifecycle"],
                "rationale": "The transition sequence is supported.",
                "intended_effect": "Preserve deterministic lifecycle behavior.",
                "alternatives": ["Use manual lifecycle mutation."],
                "certainty": "confirmed",
                "uncertainty": None,
                "scope_disposition": "within-goal",
                "approval_required": False,
                "approval_status": "not-required",
                "approval_refs": [],
                "decision_ref": "DECISION-001",
                "disposition": "approved",
                "implementation_status": "completed",
                "validation_status": "pending",
                "persistence_status": "not-persisted",
                "reuse_status": "reusable",
            }
        ],
        "blockers": [],
        "approval_refs": [],
        "evidence_refs": ["EVIDENCE-001"],
        "decision_refs": ["DECISION-001"],
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
    }


def _repository(tmp_path: Path, stage: str) -> tuple[Path, Path, Path]:
    repository = tmp_path / "repository"
    repository.mkdir()
    state_path = repository / ".flywheel/state.yaml"
    execution_path = (
        repository
        / ".flywheel/operations/records"
        / MISSION_ID
        / GOAL_ID
        / "executions"
        / f"{EXECUTION_ID}.yaml"
    )
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
                "at": BASE_TIME.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "by": "test",
                "reason": "Fixture active.",
            },
        },
    )
    _write_yaml(execution_path, _execution_for_stage(stage))
    return repository, state_path, execution_path


@pytest.mark.parametrize(
    ("current_stage", "next_stage"),
    list(zip(LIFECYCLE_ORDER[:-1], LIFECYCLE_ORDER[1:], strict=True)),
)
def test_each_supported_lifecycle_transition_completes_current_and_starts_next(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    current_stage: str,
    next_stage: str,
) -> None:
    repository, state_path, execution_path = _repository(tmp_path, current_stage)
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    refs = (f"REF-{current_stage.upper()}", "VAL-001")
    result = advance_lifecycle(
        repository,
        f"Completed {current_stage}.",
        refs,
        completed_at=BASE_TIME + timedelta(hours=1),
        expected_stage=current_stage,
    )

    assert result.lifecycle_stage == next_stage
    state = _load_yaml(state_path)
    assert state["lifecycle_stage"] == next_stage
    execution = _load_yaml(execution_path)
    lifecycle = execution["lifecycle"]
    assert isinstance(lifecycle, dict)
    assert lifecycle[current_stage]["status"] == "completed"
    assert lifecycle[next_stage]["status"] == "in-progress"
    expected_refs = list(dict.fromkeys(refs)) if next_stage == "validate" else []
    assert lifecycle[next_stage]["refs"] == expected_refs


def test_expected_stage_mismatch_is_rejected_without_file_changes(
    tmp_path: Path,
) -> None:
    repository, state_path, execution_path = _repository(tmp_path, "evaluate")
    original_state = state_path.read_bytes()
    original_execution = execution_path.read_bytes()

    with pytest.raises(TransitionRejectedError, match="expected observe, found evaluate"):
        advance_lifecycle(
            repository,
            "Complete evaluate.",
            ("EVAL-001",),
            expected_stage="observe",
        )

    assert state_path.read_bytes() == original_state
    assert execution_path.read_bytes() == original_execution


def test_blank_summary_is_rejected_without_file_changes(tmp_path: Path) -> None:
    repository, state_path, execution_path = _repository(tmp_path, "persist")
    original_state = state_path.read_bytes()
    original_execution = execution_path.read_bytes()

    with pytest.raises(TransitionRejectedError, match="summary is required"):
        advance_lifecycle(repository, "   ", ("EVIDENCE-001",))

    assert state_path.read_bytes() == original_state
    assert execution_path.read_bytes() == original_execution


def test_non_pending_next_stage_is_rejected_without_file_changes(tmp_path: Path) -> None:
    repository, state_path, execution_path = _repository(tmp_path, "classify")
    execution = _load_yaml(execution_path)
    lifecycle = execution["lifecycle"]
    assert isinstance(lifecycle, dict)
    lifecycle["adapt"] = _completed_stage("adapt", 4)
    _write_yaml(execution_path, execution)
    original_state = state_path.read_bytes()
    original_execution = execution_path.read_bytes()

    with pytest.raises(TransitionRejectedError, match="Next lifecycle stage is not pending"):
        advance_lifecycle(repository, "Complete classify.", ("CLASS-001",))

    assert state_path.read_bytes() == original_state
    assert execution_path.read_bytes() == original_execution


def test_validation_rejection_is_atomic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, state_path, execution_path = _repository(tmp_path, "observe")
    original_state = state_path.read_bytes()
    original_execution = execution_path.read_bytes()
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(
            issues=(
                ValidationIssue(
                    "INVALID_PROPOSED_TRANSITION",
                    str(execution_path),
                    "The proposed transition is invalid.",
                ),
            )
        ),
    )

    with pytest.raises(TransitionRejectedError, match="failed validation"):
        advance_lifecycle(repository, "Complete observe.", ("OBS-001",))

    assert state_path.read_bytes() == original_state
    assert execution_path.read_bytes() == original_execution


def test_reuse_completion_requires_governed_completion_operation(
    tmp_path: Path,
) -> None:
    repository, state_path, execution_path = _repository(tmp_path, "reuse")
    original_state = state_path.read_bytes()
    original_execution = execution_path.read_bytes()

    with pytest.raises(
        UnsupportedDeterministicOperationError,
        match="Completing reuse and closing the execution remains governed AI work",
    ):
        advance_lifecycle(repository, "Complete reuse.", ("EVIDENCE-001",))

    assert state_path.read_bytes() == original_state
    assert execution_path.read_bytes() == original_execution


def test_duplicate_refs_are_deduplicated_in_completed_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _, execution_path = _repository(tmp_path, "execute")
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    advance_lifecycle(
        repository,
        "Complete execute.",
        ("EVIDENCE-001", "EVIDENCE-001", "COMMIT-001"),
        expected_stage="execute",
    )

    execution = _load_yaml(execution_path)
    lifecycle = execution["lifecycle"]
    assert isinstance(lifecycle, dict)
    assert lifecycle["execute"]["refs"] == ["EVIDENCE-001", "COMMIT-001"]
