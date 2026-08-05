from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_flywheel_cli.deterministic_operations import (
    TransitionRejectedError,
    advance_lifecycle,
)
from ai_flywheel_cli.validation import ValidationIssue, ValidationResult
from test_adapt_stage_transition import _repository_at_adapt
from test_evaluate_stage_transition import _execution_path, _load_yaml, _write_yaml


def _repository_at_validate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    repository = _repository_at_adapt(tmp_path, monkeypatch)
    execution_path = _execution_path(repository)
    execution = _load_yaml(execution_path)
    execution["adaptations"] = [
        {
            "id": "ADAPT-001",
            "type": "tooling",
            "statement": "Retain the implemented local quality gate.",
            "classification_refs": ["CLASS-001"],
            "evaluation_refs": ["EVAL-001"],
            "observation_refs": ["OBS-001"],
            "evidence_refs": ["EVIDENCE-001"],
            "affected_scope": ["pyproject.toml", "tools/__main__.py"],
            "rationale": "The gate satisfies the active goal acceptance criteria.",
            "intended_effect": "Provide one repeatable local release-quality command.",
            "alternatives": ["Keep separate undocumented validation commands."],
            "certainty": "confirmed",
            "uncertainty": None,
            "scope_disposition": "within-goal",
            "approval_required": False,
            "approval_status": "not-required",
            "approval_refs": [],
            "decision_ref": None,
            "disposition": "approved",
            "implementation_status": "completed",
            "validation_status": "pending",
            "persistence_status": "not-persisted",
            "reuse_status": "not-assessed",
        }
    ]
    execution["validation_results"] = [
        {
            "id": "VAL-001",
            "phase": "planned",
            "domain": "implementation",
            "status": "pending",
            "severity": "info",
            "adaptation_refs": ["ADAPT-001"],
            "criterion_refs": ["AC-001"],
            "rule_refs": [],
            "method": "Run the local validation command.",
            "scope": ["local quality gate"],
            "expected_outcome": "Every configured check passes.",
            "actual_outcome": None,
            "expected_evidence": ["Local validation output"],
            "evidence_refs": [],
            "eligible": True,
            "exclusion_reason": None,
            "executed_at": None,
            "finding_ref": None,
            "recovery_action": None,
            "supersedes_ref": None,
        }
    ]
    _write_yaml(execution_path, execution)
    advance_lifecycle(
        repository,
        "Recorded the completed local quality-gate adaptation.",
        ("ADAPT-001", "VAL-001"),
        completed_at=datetime(2026, 8, 1, 17, 8, tzinfo=UTC),
        expected_stage="adapt",
    )
    return repository


def test_advance_validate_with_passed_result_starts_persist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository_at_validate(tmp_path, monkeypatch)
    execution_path = _execution_path(repository)
    execution = _load_yaml(execution_path)
    adaptations = execution["adaptations"]
    assert isinstance(adaptations, list)
    adaptations[0]["validation_status"] = "passed"
    execution["validation_results"] = [
        {
            "id": "VAL-001",
            "phase": "executed",
            "domain": "implementation",
            "status": "passed",
            "severity": "info",
            "adaptation_refs": ["ADAPT-001"],
            "criterion_refs": ["AC-001"],
            "rule_refs": [],
            "method": "Run the local validation command.",
            "scope": ["local quality gate"],
            "expected_outcome": "Every configured check passes.",
            "actual_outcome": "Every configured check passed.",
            "expected_evidence": ["Local validation output"],
            "evidence_refs": ["EVIDENCE-002"],
            "eligible": True,
            "exclusion_reason": None,
            "executed_at": "2026-08-01T17:09:00Z",
            "finding_ref": None,
            "recovery_action": None,
            "supersedes_ref": None,
        }
    ]
    execution["evidence_refs"] = ["EVIDENCE-001", "EVIDENCE-002"]
    _write_yaml(execution_path, execution)

    result = advance_lifecycle(
        repository,
        "Validated the implemented local quality gate.",
        ("VAL-001", "ADAPT-001", "EVIDENCE-002"),
        completed_at=datetime(2026, 8, 1, 17, 10, tzinfo=UTC),
        expected_stage="validate",
    )

    assert result.lifecycle_stage == "persist"
    updated_execution = _load_yaml(execution_path)
    lifecycle = updated_execution["lifecycle"]
    assert isinstance(lifecycle, dict)
    assert lifecycle["validate"]["status"] == "completed"
    assert lifecycle["persist"]["status"] == "in-progress"


def test_advance_validate_rejects_pending_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository_at_validate(tmp_path, monkeypatch)
    state_path = repository / ".flywheel/state.yaml"
    execution_path = _execution_path(repository)
    original_state = state_path.read_bytes()
    original_execution = execution_path.read_bytes()

    def validate_completed_result(candidate: Path) -> ValidationResult:
        execution = _load_yaml(_execution_path(candidate))
        results = execution.get("validation_results")
        if isinstance(results, list) and all(
            isinstance(result, dict) and result.get("status") != "pending" for result in results
        ):
            return ValidationResult(issues=())
        return ValidationResult(
            issues=(
                ValidationIssue(
                    "SCHEMA_INVALID",
                    str(_execution_path(candidate).relative_to(candidate)),
                    "Completed validate cannot retain pending validation results.",
                ),
            )
        )

    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        validate_completed_result,
    )

    with pytest.raises(TransitionRejectedError, match="failed validation"):
        advance_lifecycle(
            repository,
            "Validation remained pending.",
            ("VAL-001",),
            completed_at=datetime(2026, 8, 1, 17, 10, tzinfo=UTC),
            expected_stage="validate",
        )

    assert state_path.read_bytes() == original_state
    assert execution_path.read_bytes() == original_execution
