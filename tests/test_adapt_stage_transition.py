from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_flywheel_cli.deterministic_operations import (
    TransitionRejectedError,
    advance_lifecycle,
)
from ai_flywheel_cli.validation import ValidationIssue, ValidationResult
from test_classify_stage_transition import _repository_at_classify
from test_evaluate_stage_transition import _execution_path, _load_yaml, _write_yaml


def _repository_at_adapt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    repository = _repository_at_classify(tmp_path, monkeypatch)
    execution_path = _execution_path(repository)
    execution = _load_yaml(execution_path)
    execution["classifications"] = [
        {
            "id": "CLASS-001",
            "type": "finding",
            "statement": "External installation proof remains deferred.",
            "evaluation_refs": ["EVAL-001"],
            "evidence_refs": ["EVIDENCE-001"],
            "rationale": "The current goal proves only the local quality gate.",
            "certainty": "confirmed",
            "uncertainty": None,
            "conflicts_with": [],
            "related_classification_refs": [],
            "decision_ref": None,
            "finding_ref": "FINDING-001",
            "validation_refs": [],
        }
    ]
    execution["finding_refs"] = ["FINDING-001"]
    _write_yaml(execution_path, execution)
    advance_lifecycle(
        repository,
        "Classified the remaining proof boundary.",
        ("CLASS-001", "FINDING-001", "EVAL-001"),
        completed_at=datetime(2026, 8, 1, 17, 7, tzinfo=UTC),
        expected_stage="classify",
    )
    return repository


def test_advance_adapt_with_completed_adaptation_starts_validate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    result = advance_lifecycle(
        repository,
        "Recorded the completed local quality-gate adaptation.",
        (
            "ADAPT-001",
            "VAL-001",
            "CLASS-001",
            "EVAL-001",
            "OBS-001",
            "EVIDENCE-001",
        ),
        completed_at=datetime(2026, 8, 1, 17, 8, tzinfo=UTC),
        expected_stage="adapt",
    )

    assert result.lifecycle_stage == "validate"
    updated_execution = _load_yaml(execution_path)
    lifecycle = updated_execution["lifecycle"]
    assert isinstance(lifecycle, dict)
    assert lifecycle["adapt"]["status"] == "completed"
    assert lifecycle["validate"]["status"] == "in-progress"
    assert lifecycle["validate"]["refs"] == [
        "ADAPT-001",
        "VAL-001",
        "CLASS-001",
        "EVAL-001",
        "OBS-001",
        "EVIDENCE-001",
    ]


def test_advance_adapt_rejects_missing_adaptation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository_at_adapt(tmp_path, monkeypatch)
    state_path = repository / ".flywheel/state.yaml"
    execution_path = _execution_path(repository)
    original_state = state_path.read_bytes()
    original_execution = execution_path.read_bytes()

    def validate_adaptation(candidate: Path) -> ValidationResult:
        execution = _load_yaml(_execution_path(candidate))
        if execution.get("adaptations"):
            return ValidationResult(issues=())
        return ValidationResult(
            issues=(
                ValidationIssue(
                    "SCHEMA_INVALID",
                    str(_execution_path(candidate).relative_to(candidate)),
                    "Completed adapt requires at least one adaptation.",
                ),
            )
        )

    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        validate_adaptation,
    )

    with pytest.raises(TransitionRejectedError, match="failed validation"):
        advance_lifecycle(
            repository,
            "Adaptation was not recorded.",
            ("ADAPT-001",),
            completed_at=datetime(2026, 8, 1, 17, 8, tzinfo=UTC),
            expected_stage="adapt",
        )

    assert state_path.read_bytes() == original_state
    assert execution_path.read_bytes() == original_execution
