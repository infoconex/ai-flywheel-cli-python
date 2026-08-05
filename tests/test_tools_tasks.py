from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest
from tools.__main__ import BUILD_OUTPUT, main, task_commands


def test_validate_includes_package_build_after_quality_checks() -> None:
    commands = task_commands("validate")

    assert commands[-1] == [sys.executable, "-m", "build", "--outdir", BUILD_OUTPUT]
    assert commands[:-1] == [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        [sys.executable, "-m", "mypy"],
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=ai_flywheel_cli",
            "--cov-report=term-missing",
        ],
    ]


def test_build_task_uses_ignored_runtime_output() -> None:
    assert task_commands("build") == [
        [sys.executable, "-m", "build", "--outdir", ".flywheel/.runtime/dist"]
    ]


def test_source_distribution_excludes_repository_only_content() -> None:
    configuration = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    exclusions = configuration["tool"]["hatch"]["build"]["targets"]["sdist"]["exclude"]

    assert exclusions == [
        "/.flywheel",
        "/.gitignore",
        "/.release-proof",
        "/tests",
        "/tools",
    ]


def test_main_stops_after_first_failed_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str]) -> int:
        calls.append(command)
        return 9

    monkeypatch.setattr("tools.__main__._run", fake_run)
    monkeypatch.setattr(sys, "argv", ["tools", "validate"])

    assert main() == 9
    assert calls == [[sys.executable, "-m", "ruff", "check", "."]]
