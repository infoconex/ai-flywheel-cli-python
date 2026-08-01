from __future__ import annotations

from pathlib import Path

from ai_flywheel_cli.validation import validate_repository


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _baseline(tmp_path: Path) -> None:
    _write(
        tmp_path / ".flywheel/manifest.yaml",
        "schema_version: 1\nrequired_files:\n  - .flywheel/state.yaml\n",
    )
    _write(
        tmp_path / ".flywheel/state.yaml",
        """schema_version: 1
phase: onboarding
readiness: not-ready-for-missions
status: ready
active_mission: null
active_goal: null
active_execution: null
lifecycle_stage: null
implementation_available: false
application_missions_allowed: false
blockers: []
last_durable_update:
  at: 2026-08-01T15:00:00Z
  by: test
  reason: fixture
""",
    )


def _execution(
    *,
    execution_id: str = "EXEC-001",
    mission_id: str = "m",
    goal_id: str = "g",
    status: str = "active",
    lifecycle_status: str = "completed",
    outcome: str | None = None,
    disposition: str | None = None,
    evidence_refs: tuple[str, ...] = (),
) -> str:
    lifecycle = "\n".join(
        f"  {stage}:\n    status: {lifecycle_status}"
        for stage in (
            "execute",
            "observe",
            "evaluate",
            "classify",
            "adapt",
            "validate",
            "persist",
            "reuse",
        )
    )
    lines = [
        "schema_version: 1",
        f"id: {execution_id}",
        f"mission_id: {mission_id}",
        f"goal_id: {goal_id}",
        f"status: {status}",
        "lifecycle:",
        lifecycle,
    ]
    if outcome is not None:
        lines.append(f"outcome: {outcome}")
    if disposition is not None:
        lines.extend(("completion:", f"  disposition: {disposition}"))
    if evidence_refs:
        lines.append("evidence_refs:")
        lines.extend(f"  - {evidence_id}" for evidence_id in evidence_refs)
    return "\n".join(lines) + "\n"


def test_approved_legacy_evidence_shape_passes(tmp_path: Path) -> None:
    _baseline(tmp_path)
    _write(
        tmp_path / ".flywheel/operations/records/m/g/evidence/EVIDENCE-001.yaml",
        """schema_version: 1
id: EVIDENCE-001
mission_id: m
goal_id: g
type: test
summary: accepted historical evidence
details: {}
recorded_at: 2026-08-01T15:00:00Z
""",
    )

    assert validate_repository(tmp_path).passed


def test_alternate_historical_evidence_id_is_supported(tmp_path: Path) -> None:
    _baseline(tmp_path)
    _write(
        tmp_path / ".flywheel/operations/records/m/g/evidence/EVIDENCE-002.yaml",
        """schema_version: 1
evidence_id: EVIDENCE-002
summary: accepted early bootstrap evidence
source: human-confirmed onboarding response
captured_at: 2026-08-01T15:00:00Z
""",
    )

    assert validate_repository(tmp_path).passed


def test_invalid_legacy_evidence_is_rejected(tmp_path: Path) -> None:
    _baseline(tmp_path)
    _write(
        tmp_path / ".flywheel/operations/records/m/g/evidence/EVIDENCE-003.yaml",
        "schema_version: 1\nid: EVIDENCE-003\n",
    )

    codes = {issue.code for issue in validate_repository(tmp_path).issues}

    assert "INVALID_LEGACY_EVIDENCE" in codes


def test_evidence_filename_must_match_identity(tmp_path: Path) -> None:
    _baseline(tmp_path)
    _write(
        tmp_path / ".flywheel/operations/records/m/g/evidence/WRONG.yaml",
        """schema_version: 1
id: EVIDENCE-004
summary: wrong filename
details: {}
recorded_at: 2026-08-01T15:00:00Z
""",
    )

    codes = {issue.code for issue in validate_repository(tmp_path).issues}

    assert "FILENAME_ID_MISMATCH" in codes


def test_execution_identity_parent_and_lifecycle_are_validated(tmp_path: Path) -> None:
    _baseline(tmp_path)
    _write(
        tmp_path / ".flywheel/operations/records/m/g/executions/WRONG.yaml",
        """schema_version: 1
id: EXEC-001
mission_id: other-mission
goal_id: other-goal
status: active
lifecycle:
  execute:
    status: in-progress
""",
    )

    codes = {issue.code for issue in validate_repository(tmp_path).issues}

    assert {
        "FILENAME_ID_MISMATCH",
        "EXECUTION_PARENT_MISMATCH",
        "INCOMPLETE_LIFECYCLE",
    } <= codes


def test_terminal_execution_requires_terminal_stages_and_completion(tmp_path: Path) -> None:
    _baseline(tmp_path)
    _write(
        tmp_path / ".flywheel/operations/records/m/g/executions/EXEC-001.yaml",
        _execution(status="succeeded", lifecycle_status="in-progress"),
    )

    codes = {issue.code for issue in validate_repository(tmp_path).issues}

    assert "INCOMPLETE_TERMINAL_EXECUTION" in codes
    assert "MISSING_EXECUTION_COMPLETION" in codes


def test_terminal_execution_with_completion_is_accepted(tmp_path: Path) -> None:
    _baseline(tmp_path)
    _write(
        tmp_path / ".flywheel/operations/records/m/g/executions/EXEC-001.yaml",
        _execution(status="succeeded", outcome="passed", disposition="completed"),
    )

    assert validate_repository(tmp_path).passed


def test_execution_evidence_references_must_resolve(tmp_path: Path) -> None:
    _baseline(tmp_path)
    _write(
        tmp_path / ".flywheel/operations/records/m/g/evidence/EVIDENCE-001.yaml",
        """schema_version: 1
id: EVIDENCE-001
summary: known evidence
details: {}
recorded_at: 2026-08-01T15:00:00Z
""",
    )
    _write(
        tmp_path / ".flywheel/operations/records/m/g/executions/EXEC-001.yaml",
        _execution(evidence_refs=("EVIDENCE-001", "EVIDENCE-MISSING")),
    )

    issues = validate_repository(tmp_path).issues

    broken = [issue for issue in issues if issue.code == "BROKEN_EVIDENCE_REFERENCE"]
    assert len(broken) == 1
    assert "EVIDENCE-MISSING" in broken[0].message
