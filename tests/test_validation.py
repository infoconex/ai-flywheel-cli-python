from __future__ import annotations

from pathlib import Path

from ai_flywheel_cli.validation import validate_repository


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _minimal_manifest() -> str:
    return """schema_version: 1
required_files:
  - .flywheel/state.yaml
"""


def _state(**overrides: object) -> str:
    values: dict[str, object] = {
        "schema_version": 1,
        "phase": "onboarding",
        "readiness": "not-ready-for-missions",
        "status": "ready",
        "active_mission": None,
        "active_goal": None,
        "active_execution": None,
        "lifecycle_stage": None,
        "implementation_available": False,
        "application_missions_allowed": False,
        "blockers": [],
        "last_durable_update": {
            "at": "2026-08-01T13:00:00Z",
            "by": "test",
            "reason": "fixture",
        },
    }
    values.update(overrides)
    lines = []
    for key, value in values.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for child_key, child_value in value.items():
                lines.append(f"  {child_key}: {child_value}")
        elif isinstance(value, list):
            lines.append(f"{key}: []")
        elif value is None:
            lines.append(f"{key}: null")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"


def test_valid_idle_state_passes(tmp_path: Path) -> None:
    _write(tmp_path / ".flywheel/manifest.yaml", _minimal_manifest())
    _write(tmp_path / ".flywheel/state.yaml", _state())

    result = validate_repository(tmp_path)

    assert result.passed


def test_stage_without_execution_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path / ".flywheel/manifest.yaml", _minimal_manifest())
    _write(tmp_path / ".flywheel/state.yaml", _state(lifecycle_stage="execute"))

    result = validate_repository(tmp_path)

    assert "STATE_EXECUTION_STAGE_MISMATCH" in {issue.code for issue in result.issues}


def test_ready_permission_mismatch_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path / ".flywheel/manifest.yaml", _minimal_manifest())
    _write(
        tmp_path / ".flywheel/state.yaml",
        _state(readiness="ready-for-missions", application_missions_allowed=False),
    )

    result = validate_repository(tmp_path)

    assert "READINESS_PERMISSION_MISMATCH" in {issue.code for issue in result.issues}


def test_blocked_state_requires_blocker(tmp_path: Path) -> None:
    _write(tmp_path / ".flywheel/manifest.yaml", _minimal_manifest())
    _write(tmp_path / ".flywheel/state.yaml", _state(status="blocked"))

    result = validate_repository(tmp_path)

    assert "BLOCKED_WITHOUT_BLOCKER" in {issue.code for issue in result.issues}


def test_broken_active_references_are_rejected(tmp_path: Path) -> None:
    _write(tmp_path / ".flywheel/manifest.yaml", _minimal_manifest())
    _write(
        tmp_path / ".flywheel/state.yaml",
        _state(
            status="active",
            active_mission="mission-001",
            active_goal="goal-001",
            active_execution="EX-001",
            lifecycle_stage="execute",
        ),
    )

    result = validate_repository(tmp_path)
    codes = {issue.code for issue in result.issues}

    assert "MISSING_REQUIRED_FILE" in codes
    assert "BROKEN_ACTIVE_EXECUTION_REFERENCE" in codes
