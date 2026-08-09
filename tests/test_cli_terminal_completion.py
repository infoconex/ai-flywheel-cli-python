from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import ai_flywheel_cli.cli as cli
from ai_flywheel_cli.validation import ValidationResult
from test_completion import _repository, _write_yaml
from test_terminal_mission_completion import _completion, _mission_path, _write_mission

runner = CliRunner()


def test_complete_execution_cli_accepts_explicit_terminal_mission_evaluation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository, state_path, goal_path, next_goal_path, execution_path = _repository(tmp_path)
    next_goal_path.unlink()
    requirement = "Approval before external publication"
    _write_mission(repository, approvals_required=[requirement])
    completion_path = tmp_path / "mission-completion.yaml"
    _write_yaml(completion_path, _completion(requirement=requirement))
    monkeypatch.setattr(
        "ai_flywheel_cli.mutation.validate_repository",
        lambda _: ValidationResult(issues=()),
    )

    result = runner.invoke(
        cli.app,
        [
            "complete-execution",
            "--summary",
            "Terminal goal and mission completed without performing external publication.",
            "--ref",
            "VAL-001",
            "--ref",
            "EVIDENCE-001",
            "--ref",
            "REUSE-001",
            "--mission-completion-file",
            str(completion_path),
            "--repository",
            str(repository),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["operation"] == "complete-execution"
    assert payload["status"] == "completed"
    assert payload["next_goal_id"] is None

    mission = cli.load_yaml_mapping(_mission_path(repository), cli.CompletionRejectedError)
    assert mission["status"] == "completed"
    completion = mission["completion"]
    assert completion["approval_evaluations"][0]["scope"] == "external-follow-on"
    assert completion["approval_evaluations"][0]["status"] == "pending"

    state = cli.load_yaml_mapping(state_path, cli.CompletionRejectedError)
    assert state["status"] == "ready"
    assert state["active_mission"] is None
    assert state["active_goal"] is None
    assert state["active_execution"] is None
    assert state["lifecycle_stage"] is None

    goal = cli.load_yaml_mapping(goal_path, cli.CompletionRejectedError)
    assert goal["status"] == "completed"
    execution = cli.load_yaml_mapping(execution_path, cli.CompletionRejectedError)
    assert execution["status"] == "succeeded"
    assert execution["lifecycle"]["reuse"]["status"] == "completed"
