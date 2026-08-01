from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence


def _run(command: Sequence[str]) -> int:
    completed = subprocess.run(command, check=False)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repository-local project tasks.")
    parser.add_argument(
        "task",
        choices=("test", "lint", "format", "typecheck", "coverage", "validate"),
    )
    args = parser.parse_args()

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
        ],
    }

    for command in commands[args.task]:
        return_code = _run(command)
        if return_code != 0:
            return return_code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
