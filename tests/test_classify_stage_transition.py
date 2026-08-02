from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_flywheel_cli.deterministic_operations import (
    TransitionRejectedError,
    advance_lifecycle,
)
from ai_flywheel_cli.validation import ValidationIssue, ValidationResult
from test_evaluate_stage_transition import (
    _execution_path,
    _load_yaml,
    _repository_at_evaluate,
    _write_yaml,
)


def _repository_at_classify(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
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
    advance_lifecycle(
        repository,
        "Evaluated the quality gate against the acceptance criteria.",
        ("EVAL-001", "OBS-001", "EVIDENCE-001"),
        completed_at=datetime(2026, 8, 1, 17, 6, tzinfo=UTC),
        expected_stage="evaluate",
    )
    return repository


def test_advance_classify_with_structured_record_starts_adapt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    result = advance_lifecycle(
        repository,
        "Classified the remaining proof boundary.",
        ("CLASS-001", "FINDING-001", "EVAL-001"),
        completed_at=datetime(2026, 8, 1, 17, 7, tzinfo=UTC),
        expected_stage="classify",
    )

    assert result.lifecycle_stage == "adapt"
    updated_execution = _load_yaml(execution_path)
    lifecycle = updated_execution["lifecycle"]
    assert isinstance(lifecycle, dict)
    assert lifecycle["classify"]["status"] == "completed"
    assert lifecycle["adapt"]["status"] == "in-progress"


def test_advance_classify_rejects_missing_classification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository_at_classify(tmp_path, monkeypatch)
    state_path = repository / ".flywheel/state.yaml"
    execution_path = _execution_path(repository)
    original_state = state_path.read_bytes()
    original_execution = execution_path.read_bytes()

    def validate_classification(candidate: Path) -> ValidationResult:
        execution = _load_yaml(_execution_path(candidate))
        if execution.get("classifications"):
            return ValidationResult(issues=())
        return ValidationResult(
            issues=(
                ValidationIssue(
                    "SCHEMA_INVALID",
                    str(_execution_path(candidate).relative_to(candidate)),
                    "Completed classify requires at least one classification.",
                ),
            )
        )

    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        validate_classification,
    )

    with pytest.raises(TransitionRejectedError, match="failed validation"):
        advance_lifecycle(
            repository,
            "Classification was not recorded.",
            ("CLASS-001",),
            completed_at=datetime(2026, 8, 1, 17, 7, tzinfo=UTC),
            expected_stage="classify",
        )

    assert state_path.read_bytes() == original_state
    assert execution_path.read_bytes() == original_execution
