from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from ai_flywheel_cli.cli import app

runner = CliRunner()


def _archive(path: Path, files: dict[str, str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


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


def test_status_reports_invalid_when_validation_fails(tmp_path: Path) -> None:
    flywheel = tmp_path / ".flywheel"
    flywheel.mkdir()
    (flywheel / "state.yaml").write_text("schema_version: 1\n", encoding="utf-8")

    result = runner.invoke(app, ["status", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "invalid"
    assert payload["issue_count"] > 0


def test_validate_returns_structured_errors(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", str(tmp_path), "--json"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "validation-failed"
    assert payload["error_count"] == 2
    assert {error["code"] for error in payload["errors"]} == {"MISSING_REQUIRED_FILE"}


def test_install_displays_plan_without_apply(tmp_path: Path) -> None:
    archive = _archive(
        tmp_path / "framework.zip",
        {".flywheel/manifest.yaml": "schema_version: 1\n"},
    )

    result = runner.invoke(
        app,
        [
            "install",
            str(tmp_path),
            "--archive",
            str(archive),
            "--checksum",
            hashlib.sha256(archive.read_bytes()).hexdigest(),
            "--framework-version",
            "0.1.0",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "planned"
    assert payload["apply_required"] is True


def test_install_reports_repository_conflict(tmp_path: Path) -> None:
    (tmp_path / ".flywheel").mkdir()
    archive = _archive(
        tmp_path / "framework.zip",
        {".flywheel/manifest.yaml": "schema_version: 1\n"},
    )

    result = runner.invoke(
        app,
        [
            "install",
            str(tmp_path),
            "--archive",
            str(archive),
            "--checksum",
            hashlib.sha256(archive.read_bytes()).hexdigest(),
            "--framework-version",
            "0.1.0",
            "--apply",
            "--json",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["status"] == "repository-conflict"


def test_upgrade_displays_plan_without_apply(tmp_path: Path) -> None:
    archive = _archive(
        tmp_path / "framework.zip",
        {".flywheel/manifest.yaml": "schema_version: 1\n"},
    )

    result = runner.invoke(
        app,
        [
            "upgrade",
            str(tmp_path),
            "--archive",
            str(archive),
            "--checksum",
            hashlib.sha256(archive.read_bytes()).hexdigest(),
            "--framework-version",
            "0.2.0",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "planned"


def test_upgrade_reports_repository_conflict(tmp_path: Path) -> None:
    archive = _archive(
        tmp_path / "framework.zip",
        {".flywheel/manifest.yaml": "schema_version: 1\n"},
    )

    result = runner.invoke(
        app,
        [
            "upgrade",
            str(tmp_path),
            "--archive",
            str(archive),
            "--checksum",
            hashlib.sha256(archive.read_bytes()).hexdigest(),
            "--framework-version",
            "0.2.0",
            "--apply",
            "--json",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["status"] == "repository-conflict"
