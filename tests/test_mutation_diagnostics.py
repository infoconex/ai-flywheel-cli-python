from __future__ import annotations

import json

from typer.testing import CliRunner

from ai_flywheel_cli.cli import app
from ai_flywheel_cli.deterministic_operations import TransitionRejectedError
from ai_flywheel_cli.mutation import MutationFailure

runner = CliRunner()


def test_start_execution_reports_structured_mutation_failures(monkeypatch) -> None:
    failure = MutationFailure(
        "SCHEMA_VALIDATION_FAILED",
        ".flywheel/state.yaml",
        "State is invalid.",
    )

    def reject(*args, **kwargs):
        raise TransitionRejectedError("Proposed mutation failed validation.", (failure,))

    monkeypatch.setattr("ai_flywheel_cli.cli.start_execution", reject)

    result = runner.invoke(
        app,
        [
            "start-execution",
            "mission",
            "goal",
            "EX-20260802T051700Z-001",
            "--intended-outcome",
            "Exercise diagnostics.",
            "--json",
        ],
    )

    assert result.exit_code == 7
    payload = json.loads(result.stdout)
    assert payload["status"] == "operation-failed"
    assert payload["reason"] == "mutation-rejected"
    assert payload["failures"] == [failure.as_dict()]
