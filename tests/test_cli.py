from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import ai_flywheel_cli.cli as cli
from ai_flywheel_cli.deterministic_operations import UnsupportedDeterministicOperationError
from ai_flywheel_cli.framework_compatibility import FrameworkCompatibility
from ai_flywheel_cli.operations import OperationError
from ai_flywheel_cli.validation import ValidationResult

runner = CliRunner()


def test_version_is_available() -> None:
    result = runner.invoke(cli.app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


def test_doctor_reports_repository_without_modifying_it(tmp_path: Path) -> None:
    result = runner.invoke(cli.app, ["doctor", str(tmp_path), "--json"])

    assert result.exit_code == 8
    payload = json.loads(result.stdout)
    assert payload["command"] == "doctor"
    assert payload["framework_status"] == "not-installed"
    assert payload["supported_framework_version"] == "2026.08.08"
    assert payload["repository_validation_status"] == "not-run"
    assert list(tmp_path.iterdir()) == []


def test_doctor_reports_compatible_valid_repository(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        cli,
        "classify_framework",
        lambda _: FrameworkCompatibility("compatible", "2026.08.08", "Compatible."),
    )
    monkeypatch.setattr(cli, "validate_repository", lambda _: ValidationResult(issues=()))

    result = runner.invoke(cli.app, ["doctor", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["cli_version"] == "0.1.0"
    assert payload["framework_status"] == "compatible"
    assert payload["installed_framework_version"] == "2026.08.08"
    assert payload["repository_validation_status"] == "passed"


def test_status_reports_not_installed_when_state_is_missing(tmp_path: Path) -> None:
    result = runner.invoke(cli.app, ["status", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "not-installed"


def test_status_reports_invalid_when_validation_fails(tmp_path: Path) -> None:
    flywheel = tmp_path / ".flywheel"
    flywheel.mkdir()
    (flywheel / "state.yaml").write_text("schema_version: 1\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["status", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "invalid"
    assert payload["issue_count"] > 0


def test_validate_returns_structured_errors(tmp_path: Path) -> None:
    result = runner.invoke(cli.app, ["validate", str(tmp_path), "--json"])

    assert result.exit_code == 3
    payload = json.loads(result.stdout)
    assert payload["status"] == "validation-failed"
    assert payload["category"] == "validation-failure"
    assert payload["reason"] == "repository-validation-errors"
    assert payload["error_count"] == 2
    assert {error["code"] for error in payload["errors"]} == {"MISSING_REQUIRED_FILE"}


def test_usage_errors_keep_typer_exit_code_2() -> None:
    result = runner.invoke(cli.app, ["validate", "--unknown-option"])

    assert result.exit_code == 2


def test_install_and_upgrade_commands_are_not_exposed() -> None:
    for command in ("install", "upgrade"):
        result = runner.invoke(cli.app, [command])
        assert result.exit_code == 2
        assert "No such command" in result.output


def test_advance_lifecycle_reports_ai_fallback(monkeypatch, tmp_path: Path) -> None:
    def fallback(*_args, **_kwargs):
        raise UnsupportedDeterministicOperationError("governed step")

    monkeypatch.setattr(cli, "advance_lifecycle", fallback)

    result = runner.invoke(
        cli.app,
        [
            "advance-lifecycle",
            "--summary",
            "Attempted deterministic completion.",
            "--repository",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 6
    payload = json.loads(result.stdout)
    assert payload["status"] == "ai-fallback-required"
    assert payload["reason"] == "governed-ai-step-required"


def test_start_execution_reports_generic_operation_error(monkeypatch) -> None:
    def reject(*_args, **_kwargs):
        raise OperationError("unexpected operation failure")

    monkeypatch.setattr(cli, "start_execution", reject)

    result = runner.invoke(
        cli.app,
        [
            "start-execution",
            "mission",
            "goal",
            "EX-20260805T040000Z-001",
            "--intended-outcome",
            "Exercise generic operation failure path.",
            "--json",
        ],
    )

    assert result.exit_code == 7
    payload = json.loads(result.stdout)
    assert payload["status"] == "operation-failed"
    assert payload["category"] == "operation-failed"
    assert payload["reason"] == "operation-error"
    assert "failures" not in payload
