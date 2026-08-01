from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ai_flywheel_cli.cli import app

runner = CliRunner()


def test_version_is_available() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


def test_doctor_reports_repository_without_modifying_it(tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "doctor"
    assert payload["flywheel_exists"] is False
    assert list(tmp_path.iterdir()) == []


def test_status_reports_not_installed_when_state_is_missing(tmp_path: Path) -> None:
    result = runner.invoke(app, ["status", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "not-installed"


def test_validate_returns_structured_errors(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", str(tmp_path), "--json"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "validation-failed"
    assert payload["error_count"] == 2
    assert {error["code"] for error in payload["errors"]} == {"MISSING_REQUIRED_FILE"}


def test_install_is_not_silently_treated_as_implemented() -> None:
    result = runner.invoke(app, ["install"])

    assert result.exit_code == 3
    assert "pending within Goal 004" in result.stdout


def test_upgrade_is_not_silently_treated_as_implemented() -> None:
    result = runner.invoke(app, ["upgrade"])

    assert result.exit_code == 3
    assert "pending within Goal 004" in result.stdout
