from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ai_flywheel_cli.deterministic_operations import (
    TransitionRejectedError,
    advance_lifecycle,
    start_execution,
)
from ai_flywheel_cli.mutation import commit_validated_yaml, sha256_bytes
from ai_flywheel_cli.validation import ValidationResult


def test_interruption_after_first_replace_restores_all_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    first = repository / "first.yaml"
    second = repository / "second.yaml"
    first.write_text("value: old-first\n", encoding="utf-8")
    second.write_text("value: old-second\n", encoding="utf-8")
    first_bytes = first.read_bytes()
    second_bytes = second.read_bytes()
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    def interrupt(phase: str, path: str, index: int) -> None:
        if phase == "after-replace" and index == 0:
            raise RuntimeError("injected interruption")

    with pytest.raises(RuntimeError, match="injected interruption"):
        commit_validated_yaml(
            repository,
            {
                "first.yaml": {"value": "new-first"},
                "second.yaml": {"value": "new-second"},
            },
            "test",
            TransitionRejectedError,
            expected_sha256={
                "first.yaml": sha256_bytes(first_bytes),
                "second.yaml": sha256_bytes(second_bytes),
            },
            interruption_hook=interrupt,
        )

    assert first.read_bytes() == first_bytes
    assert second.read_bytes() == second_bytes
    assert not list(repository.glob("*.tmp"))


def test_retry_after_interruption_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    target = repository / "state.yaml"
    target.write_text("value: old\n", encoding="utf-8")
    digest = sha256_bytes(target.read_bytes())
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    def interrupt(phase: str, path: str, index: int) -> None:
        if phase == "before-replace":
            raise RuntimeError("stop")

    with pytest.raises(RuntimeError):
        commit_validated_yaml(
            repository,
            {"state.yaml": {"value": "new"}},
            "test",
            TransitionRejectedError,
            expected_sha256={"state.yaml": digest},
            interruption_hook=interrupt,
        )

    result = commit_validated_yaml(
        repository,
        {"state.yaml": {"value": "new"}},
        "test",
        TransitionRejectedError,
        expected_sha256={"state.yaml": digest},
    )
    assert result == ("state.yaml",)
    assert yaml.safe_load(target.read_text(encoding="utf-8"))["value"] == "new"


def test_advance_retry_guard_prevents_duplicate_transition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    goal = repository / ".flywheel/operations/missions/sample/goals/001-goal.yaml"
    state = repository / ".flywheel/state.yaml"
    goal.parent.mkdir(parents=True)
    state.parent.mkdir(parents=True, exist_ok=True)
    goal.write_text(
        "schema_version: 1\nid: 001-goal\nmission_id: sample\ntitle: Goal\nstatus: proposed\nobjective: Test.\nacceptance_criteria:\n  - id: AC-001\n    statement: Pass.\n",
        encoding="utf-8",
    )
    state.write_text(
        "schema_version: 1\nphase: operating\nreadiness: ready-for-missions\nstatus: ready\nactive_mission: sample\nactive_goal: null\nactive_execution: null\nlifecycle_stage: null\nimplementation_available: true\napplication_missions_allowed: true\nblockers: []\nlast_durable_update:\n  at: '2026-08-01T18:00:00Z'\n  by: test\n  reason: Ready.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )
    start_execution(repository, "sample", "001-goal", "EX-001", "Test.")
    advance_lifecycle(repository, "Done.", (), expected_stage="execute")

    with pytest.raises(TransitionRejectedError, match="Lifecycle stage changed before retry"):
        advance_lifecycle(repository, "Done.", (), expected_stage="execute")

    assert yaml.safe_load(state.read_text(encoding="utf-8"))["lifecycle_stage"] == "observe"
