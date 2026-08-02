from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence

BUILD_OUTPUT = ".flywheel/.runtime/dist"


def _run(command: Sequence[str]) -> int:
    completed = subprocess.run(command, check=False)
    return completed.returncode


def task_commands(task: str) -> list[list[str]]:
    commands: dict[str, list[list[str]]] = {
        "test": [[sys.executable, "-m", "pytest"]],
        "lint": [[sys.executable, "-m", "ruff", "check", "."]],
        "format": [[sys.executable, "-m", "ruff", "format", "--check", "."]],
        "typecheck": [[sys.executable, "-m", "mypy"]],
        "coverage": [
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=ai_flywheel_cli",
                "--cov-report=term-missing",
            ]
        ],
        "build": [[sys.executable, "-m", "build", "--outdir", BUILD_OUTPUT]],
        "validate": [
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
            [sys.executable, "-m", "build", "--outdir", BUILD_OUTPUT],
        ],
    }
    return commands[task]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repository-local project tasks.")
    parser.add_argument(
        "task",
        choices=("test", "lint", "format", "typecheck", "coverage", "build", "validate"),
    )
    args = parser.parse_args()

    for command in task_commands(args.task):
        return_code = _run(command)
        if return_code != 0:
            return return_code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
