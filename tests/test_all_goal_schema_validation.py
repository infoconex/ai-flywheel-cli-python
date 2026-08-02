from __future__ import annotations

from pathlib import Path

from ai_flywheel_cli.validation import validate_repository


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_inactive_goal_is_schema_validated(tmp_path: Path) -> None:
    _write(
        tmp_path / ".flywheel/manifest.yaml",
        "schema_version: 1\nrequired_files:\n  - .flywheel/state.yaml\n",
    )
    _write(
        tmp_path / ".flywheel/state.yaml",
        """schema_version: 1
phase: operating
readiness: ready-for-missions
status: ready
active_mission: sample-mission
active_goal: null
active_execution: null
lifecycle_stage: null
implementation_available: true
application_missions_allowed: true
blockers: []
last_durable_update:
  at: 2026-08-02T05:00:00Z
  by: test
  reason: fixture
""",
    )
    _write(
        tmp_path / ".flywheel/operating-model/schemas/goal.schema.yaml",
        """$schema: https://json-schema.org/draft/2020-12/schema
type: object
required:
  - schema_version
  - id
  - mission_id
  - title
  - status
  - objective
  - acceptance_criteria
  - evidence_required
""",
    )
    _write(
        tmp_path
        / ".flywheel/operations/missions/sample-mission/goals/002-invalid-goal.yaml",
        """schema_version: 1
id: 002-invalid-goal
mission_id: sample-mission
title: Invalid Inactive Goal
status: ready
objective: Prove all goals are validated.
acceptance_criteria:
- id: AC-001
  statement: Validation rejects this goal.
""",
    )

    issues = validate_repository(tmp_path).issues

    matching = [
        issue
        for issue in issues
        if issue.code == "SCHEMA_VALIDATION_FAILED"
        and issue.path.endswith("002-invalid-goal.yaml")
    ]
    assert matching
    assert "evidence_required" in matching[0].message
