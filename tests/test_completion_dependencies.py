from pathlib import Path

import yaml

from ai_flywheel_cli.completion import _dependencies_completed


def _write_goal(goals_directory: Path, goal_id: str, status: str) -> None:
    path = goals_directory / f"{goal_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "id": goal_id,
                "mission_id": "sample-mission",
                "title": goal_id,
                "status": status,
                "objective": "Exercise dependency handoff behavior.",
                "acceptance_criteria": [
                    {"id": "AC-001", "statement": "The dependency state is respected."}
                ],
                "evidence_required": [
                    {"criterion_id": "AC-001", "evidence_types": ["test result"]}
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_all_dependencies_must_be_completed_before_handoff(tmp_path: Path) -> None:
    goals_directory = tmp_path / "goals"
    _write_goal(goals_directory, "001-first", "completed")
    _write_goal(goals_directory, "002-second", "ready")

    assert not _dependencies_completed(
        goals_directory,
        ["001-first", "002-second"],
        "001-first",
    )


def test_handoff_is_allowed_when_other_dependencies_are_completed(tmp_path: Path) -> None:
    goals_directory = tmp_path / "goals"
    _write_goal(goals_directory, "001-first", "completed")
    _write_goal(goals_directory, "002-second", "completed")

    assert _dependencies_completed(
        goals_directory,
        ["001-first", "002-second"],
        "001-first",
    )


def test_missing_dependency_prevents_handoff(tmp_path: Path) -> None:
    goals_directory = tmp_path / "goals"
    _write_goal(goals_directory, "001-first", "completed")

    assert not _dependencies_completed(
        goals_directory,
        ["001-first", "missing-goal"],
        "001-first",
    )


def test_non_string_dependency_prevents_handoff(tmp_path: Path) -> None:
    goals_directory = tmp_path / "goals"
    _write_goal(goals_directory, "001-first", "completed")

    assert not _dependencies_completed(
        goals_directory,
        ["001-first", 2],
        "001-first",
    )
