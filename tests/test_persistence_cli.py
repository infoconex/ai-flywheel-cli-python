from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from ai_flywheel_cli import cli
from ai_flywheel_cli.persistence import PersistenceResult

runner = CliRunner()


def test_primary_cli_registers_persist_execution_command(tmp_path: Path, monkeypatch) -> None:
    def persist(
        repository: Path,
        summary: str,
        reuse_id: str,
        *,
        operator: str,
    ) -> PersistenceResult:
        assert repository == tmp_path
        assert summary == "Persisted."
        assert reuse_id == "REUSE-001"
        assert operator == "test-operator"
        return PersistenceResult(
            operation="persist-execution",
            status="completed",
            files_changed=("reuse.yaml", "state.yaml"),
            execution_id="EX-20260803T010000Z-001",
            lifecycle_stage="reuse",
            persistence_plan_id="PERSIST-20260803T010100Z-001",
            reuse_assessment_id="REUSE-001",
        )

    monkeypatch.setattr(cli, "persist_execution", persist)

    result = runner.invoke(
        cli.app,
        [
            "persist-execution",
            "--summary",
            "Persisted.",
            "--reuse-id",
            "REUSE-001",
            "--operator",
            "test-operator",
            "--repository",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["lifecycle_stage"] == "reuse"
    assert payload["persistence_plan_id"] == "PERSIST-20260803T010100Z-001"


def test_advance_lifecycle_rejects_direct_persist_completion(tmp_path: Path) -> None:
    state_path = tmp_path / ".flywheel/state.yaml"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "phase": "operating",
                "readiness": "ready-for-missions",
                "status": "active",
                "active_mission": "sample-mission",
                "active_goal": "001-sample-goal",
                "active_execution": "EX-20260803T010000Z-001",
                "lifecycle_stage": "persist",
                "implementation_available": True,
                "application_missions_allowed": True,
                "blockers": [],
                "last_durable_update": {
                    "at": "2026-08-03T01:00:00Z",
                    "by": "test",
                    "reason": "Fixture at persist.",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli.app,
        [
            "advance-lifecycle",
            "--summary",
            "Incorrect direct persistence.",
            "--expected-stage",
            "persist",
            "--repository",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 8
    payload = json.loads(result.stdout)
    assert payload["command"] == "advance-lifecycle"
    assert "persist-execution" in payload["error"]
