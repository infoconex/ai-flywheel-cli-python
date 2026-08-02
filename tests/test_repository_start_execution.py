from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from ai_flywheel_cli.deterministic_operations import (
    TransitionRejectedError,
    start_execution,
)

MISSION_ID = "prepare-python-cli-initial-release"
GOAL_ID = "002-apply-local-quality-gates"
EXECUTION_ID = "EX-20260802T051700Z-001"


def _write_pre_start_state(repository: Path) -> None:
    state_path = repository / ".flywheel/state.yaml"
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    state.update(
        {
            "status": "ready",
            "active_goal": None,
            "active_execution": None,
            "lifecycle_stage": None,
        }
    )
    state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")

    goal_path = repository / ".flywheel/operations/missions" / MISSION_ID / "goals" / f"{GOAL_ID}.yaml"
    goal = yaml.safe_load(goal_path.read_text(encoding="utf-8"))
    goal["status"] = "ready"
    goal_path.write_text(yaml.safe_dump(goal, sort_keys=False), encoding="utf-8")


def test_checked_in_repository_can_start_ready_goal(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1] / ".flywheel"
    repository = tmp_path / "repository"
    shutil.copytree(
        source,
        repository / ".flywheel",
        ignore=shutil.ignore_patterns(".runtime", "records"),
    )
    _write_pre_start_state(repository)

    try:
        result = start_execution(
            repository,
            MISSION_ID,
            GOAL_ID,
            EXECUTION_ID,
            (
                "Establish and document justified local linting, formatting, typing, "
                "and package-build quality gates that run through one command without "
                "hosted automation."
            ),
            started_at=datetime(2026, 8, 2, 5, 17, tzinfo=UTC),
        )
    except TransitionRejectedError as error:
        failures = [failure.as_dict() for failure in error.failures]
        pytest.fail(f"Checked-in repository rejected start-execution: {failures}")

    assert result.status == "completed"
    assert result.lifecycle_stage == "execute"
