from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ai_flywheel_cli.deterministic_operations import TransitionRejectedError
from ai_flywheel_cli.mutation import commit_validated_yaml, load_yaml_mapping, sha256_bytes
from ai_flywheel_cli.validation import ValidationIssue, ValidationResult


def test_load_yaml_mapping_returns_structured_shape_failure(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.yaml"
    artifact.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(TransitionRejectedError) as captured:
        load_yaml_mapping(artifact, TransitionRejectedError)

    assert captured.value.failures[0].code == "INVALID_ARTIFACT_SHAPE"
    assert captured.value.as_dict()["status"] == "mutation-rejected"


def test_commit_rejects_stale_source_before_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    target = repository / ".flywheel/state.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("schema_version: 1\n", encoding="utf-8")
    original_digest = sha256_bytes(target.read_bytes())
    target.write_text("schema_version: 2\n", encoding="utf-8")
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    with pytest.raises(TransitionRejectedError) as captured:
        commit_validated_yaml(
            repository,
            {".flywheel/state.yaml": {"schema_version": 3}},
            "test",
            TransitionRejectedError,
            expected_sha256={".flywheel/state.yaml": original_digest},
        )

    assert captured.value.failures[0].code == "STALE_SOURCE_REVISION"
    assert yaml.safe_load(target.read_text(encoding="utf-8"))["schema_version"] == 2


def test_commit_exposes_repository_validation_issues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(
            issues=(ValidationIssue("BROKEN_REFERENCE", ".flywheel/state.yaml", "Broken."),)
        ),
    )

    with pytest.raises(TransitionRejectedError) as captured:
        commit_validated_yaml(
            repository,
            {".flywheel/state.yaml": {"schema_version": 1}},
            "test",
            TransitionRejectedError,
            expected_sha256={".flywheel/state.yaml": None},
        )

    assert captured.value.failures[0].as_dict() == {
        "code": "BROKEN_REFERENCE",
        "path": ".flywheel/state.yaml",
        "message": "Broken.",
    }
    assert not (repository / ".flywheel/state.yaml").exists()
