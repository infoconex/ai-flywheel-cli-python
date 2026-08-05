from __future__ import annotations

import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ai_flywheel_cli.mutation import (
    MutationFailure,
    MutationRejectedError,
    load_yaml_mapping,
    sha256_bytes,
)
from ai_flywheel_cli.operations import RepositoryLock
from ai_flywheel_cli.validation import validate_repository


class PersistenceRejectedError(MutationRejectedError):
    """Raised when a Persist-stage transaction cannot be safely completed."""


@dataclass(frozen=True)
class PersistenceResult:
    operation: str
    status: str
    files_changed: tuple[str, ...]
    execution_id: str
    lifecycle_stage: str
    persistence_plan_id: str
    reuse_assessment_id: str

    def as_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "status": self.status,
            "files_changed": list(self.files_changed),
            "execution_id": self.execution_id,
            "lifecycle_stage": self.lifecycle_stage,
            "persistence_plan_id": self.persistence_plan_id,
            "reuse_assessment_id": self.reuse_assessment_id,
        }


def _timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(UTC)
    return current.strftime("%Y-%m-%dT%H:%M:%SZ")


def _yaml_bytes(value: Mapping[str, Any]) -> bytes:
    return yaml.safe_dump(dict(value), sort_keys=False).encode("utf-8")


def _write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(_yaml_bytes(value))
    temporary.replace(path)


def _load(path: Path) -> dict[str, Any]:
    return load_yaml_mapping(path, PersistenceRejectedError)


def _next_plan_id(persistence_root: Path, timestamp: str) -> str:
    stem = timestamp.replace("-", "").replace(":", "")
    for counter in range(1, 1000):
        candidate = f"PERSIST-{stem}-{counter:03d}"
        if not (persistence_root / f"{candidate}.yaml").exists():
            return candidate
    raise PersistenceRejectedError("Persistence-plan identity counter is exhausted.")


def _validate_final_repository(
    root: Path,
    final_values: Mapping[str, Mapping[str, Any]],
) -> None:
    shadow_parent = Path(tempfile.mkdtemp(prefix="flywheel-persist-shadow-"))
    shadow = shadow_parent / "repository"
    try:
        shutil.copytree(root, shadow, ignore=shutil.ignore_patterns(".git", ".runtime"))
        for relative_path, value in final_values.items():
            _write_yaml(shadow / relative_path, value)
        result = validate_repository(shadow)
        if result.passed:
            return
        failures = tuple(
            MutationFailure(issue.code, issue.path, issue.message) for issue in result.issues
        )
        raise PersistenceRejectedError(
            "Proposed persistence transaction failed validation.", failures
        )
    finally:
        shutil.rmtree(shadow_parent, ignore_errors=True)


def _target(
    target_id: str,
    artifact_type: str,
    path: str,
    operation: str,
    dependency_refs: list[str],
    proposed: Mapping[str, Any],
    retained: bytes | None,
) -> dict[str, Any]:
    is_create = operation == "create"
    return {
        "id": target_id,
        "artifact_type": artifact_type,
        "path": path,
        "operation": operation,
        "mutability": "create-only" if is_create else "cas-update",
        "dependency_refs": dependency_refs,
        "expected_precondition": (
            {"absence": True} if is_create else {"blob_sha": sha256_bytes(retained or b"")}
        ),
        "proposed_content_digest": sha256_bytes(_yaml_bytes(proposed)),
        "rollback": {
            "mode": "delete-created" if is_create else "restore-retained-content",
            "retained_content_digest": None if is_create else sha256_bytes(retained or b""),
        },
    }


def persist_execution(
    repository: Path,
    summary: str,
    reuse_id: str,
    *,
    operator: str = "ai-flywheel-cli",
    completed_at: datetime | None = None,
) -> PersistenceResult:
    root = repository.resolve()
    timestamp = _timestamp(completed_at)
    state_relative = ".flywheel/state.yaml"
    state_path = root / state_relative
    state = _load(state_path)
    mission_id = state.get("active_mission")
    goal_id = state.get("active_goal")
    execution_id = state.get("active_execution")
    if not all(isinstance(value, str) for value in (mission_id, goal_id, execution_id)):
        raise PersistenceRejectedError("Persist requires an active mission, goal, and execution.")
    if state.get("lifecycle_stage") != "persist":
        raise PersistenceRejectedError("persist-execution requires lifecycle_stage persist.")
    if not summary.strip():
        raise PersistenceRejectedError("A persistence summary is required.")
    if not reuse_id.startswith("REUSE-"):
        raise PersistenceRejectedError("Reuse assessment identity must use REUSE-NNN.")

    record_root = f".flywheel/operations/records/{mission_id}/{goal_id}"
    execution_relative = f"{record_root}/executions/{execution_id}.yaml"
    reuse_relative = f"{record_root}/reuse/{reuse_id}.yaml"
    persistence_root = root / record_root / "persistence"
    execution_path = root / execution_relative
    reuse_path = root / reuse_relative
    execution = _load(execution_path)
    if reuse_path.exists():
        raise PersistenceRejectedError(f"Reuse assessment already exists: {reuse_id}")

    lifecycle = execution.get("lifecycle")
    if not isinstance(lifecycle, dict):
        raise PersistenceRejectedError("Execution lifecycle must be a mapping.")
    persist_stage = lifecycle.get("persist")
    reuse_stage = lifecycle.get("reuse")
    validate_stage = lifecycle.get("validate")
    if not isinstance(persist_stage, dict) or persist_stage.get("status") != "in-progress":
        raise PersistenceRejectedError("Persist must be in-progress.")
    if not isinstance(validate_stage, dict) or validate_stage.get("status") != "completed":
        raise PersistenceRejectedError("Validate must be completed before persistence.")
    if not isinstance(reuse_stage, dict) or reuse_stage.get("status") != "pending":
        raise PersistenceRejectedError("Reuse must be pending before persistence.")

    validations = execution.get("validation_results")
    if not isinstance(validations, list) or not validations:
        raise PersistenceRejectedError("At least one completed validation result is required.")
    if any(not isinstance(item, dict) or item.get("status") == "pending" for item in validations):
        raise PersistenceRejectedError("Persistence cannot begin while validation is pending.")
    if any(isinstance(item, dict) and item.get("status") == "failed" for item in validations):
        raise PersistenceRejectedError(
            "Failed validation requires an authorized persistence disposition."
        )

    adaptations = execution.get("adaptations")
    if not isinstance(adaptations, list) or not adaptations:
        raise PersistenceRejectedError("At least one adaptation is required for reuse assessment.")
    adaptation_refs: list[str] = []
    for adaptation in adaptations:
        if not isinstance(adaptation, dict) or not isinstance(adaptation.get("id"), str):
            raise PersistenceRejectedError("Every adaptation must have a stable identity.")
        if adaptation.get("validation_status") != "passed":
            raise PersistenceRejectedError(
                "Every persisted adaptation must have passed validation."
            )
        adaptation["persistence_status"] = "persisted"
        adaptation_refs.append(adaptation["id"])

    evidence_refs = [item for item in execution.get("evidence_refs", []) if isinstance(item, str)]
    validation_refs = [
        item["id"]
        for item in validations
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    reuse = {
        "schema_version": 1,
        "id": reuse_id,
        "mission_id": mission_id,
        "goal_id": goal_id,
        "execution_id": execution_id,
        "subject_type": "candidate-learning",
        "subject_ref": "validated-adaptations",
        "adaptation_refs": adaptation_refs,
        "status": "planned",
        "disposition": None,
        "statement": "Assess validated execution adaptations for reusable guidance.",
        "evidence_refs": evidence_refs,
        "validation_refs": validation_refs,
        "applicability": ["Python CLI repositories using the AI Flywheel operating model"],
        "limitations": [
            "Validated in the current repository context; verify applicability when "
            "platform, process, or policy constraints differ."
        ],
        "reuse_guidance": None,
        "duplicate_refs": [],
        "conflict_refs": [],
        "proposed_knowledge_ref": None,
        "supersedes_refs": [],
        "approval_required": False,
        "approval_refs": [],
        "decision_ref": None,
        "rationale": None,
        "assessed_at": None,
        "assessed_by": None,
    }

    plan_id = _next_plan_id(persistence_root, timestamp)
    plan_relative = f"{record_root}/persistence/{plan_id}.yaml"
    persist_refs = [plan_id, reuse_id, *validation_refs, *evidence_refs]
    persist_stage.update(
        {
            "status": "completed",
            "completed_at": timestamp,
            "summary": summary.strip(),
            "refs": list(dict.fromkeys(persist_refs)),
            "reason": None,
        }
    )
    reuse_stage.update(
        {
            "status": "in-progress",
            "started_at": timestamp,
            "completed_at": None,
            "summary": None,
            "refs": [reuse_id],
            "reason": None,
        }
    )
    state.update(
        {
            "status": "active",
            "lifecycle_stage": "reuse",
            "blockers": [],
            "last_durable_update": {
                "at": timestamp,
                "by": operator,
                "reason": f"Applied {plan_id}; completed persist and started reuse.",
            },
        }
    )

    state_retained = state_path.read_bytes()
    execution_retained = execution_path.read_bytes()
    targets = [
        _target("PT-001", "reuse-assessment", reuse_relative, "create", [], reuse, None),
        _target(
            "PT-002",
            "execution",
            execution_relative,
            "update",
            ["PT-001"],
            execution,
            execution_retained,
        ),
        _target(
            "PT-003",
            "state",
            state_relative,
            "update",
            ["PT-002"],
            state,
            state_retained,
        ),
    ]
    base_plan = {
        "schema_version": 1,
        "id": plan_id,
        "mission_id": mission_id,
        "goal_id": goal_id,
        "execution_id": execution_id,
        "created_at": timestamp,
        "operator": operator,
        "status": "planned",
        "targets": targets,
        "write_order": ["PT-001", "PT-002", "PT-003"],
        "recovery": {"mode": "not-started", "finding_ref": None, "blocker": None},
        "final_verification": {"required": True, "verified_at": None, "result": "pending"},
    }
    applied_plan = dict(base_plan)
    applied_plan["status"] = "applied"
    applied_plan["final_verification"] = {
        "required": True,
        "verified_at": timestamp,
        "result": "passed",
    }
    final_values = {
        reuse_relative: reuse,
        execution_relative: execution,
        state_relative: state,
        plan_relative: applied_plan,
    }
    _validate_final_repository(root, final_values)

    retained: dict[str, bytes | None] = {
        reuse_relative: None,
        execution_relative: execution_retained,
        state_relative: state_retained,
        plan_relative: None,
    }
    with RepositoryLock(root, "persist-execution"):
        if reuse_path.exists():
            raise PersistenceRejectedError(f"Reuse assessment already exists: {reuse_id}")
        if sha256_bytes(execution_path.read_bytes()) != sha256_bytes(execution_retained):
            raise PersistenceRejectedError("Execution changed before persistence could begin.")
        if sha256_bytes(state_path.read_bytes()) != sha256_bytes(state_retained):
            raise PersistenceRejectedError("State changed before persistence could begin.")
        try:
            _write_yaml(root / plan_relative, base_plan)
            applying_plan = dict(base_plan)
            applying_plan["status"] = "applying"
            _write_yaml(root / plan_relative, applying_plan)
            _write_yaml(reuse_path, reuse)
            _write_yaml(execution_path, execution)
            _write_yaml(state_path, state)
            for target in targets:
                target_path = root / target["path"]
                actual = sha256_bytes(target_path.read_bytes())
                if actual != target["proposed_content_digest"]:
                    raise PersistenceRejectedError(
                        f"Persistence target verification failed: {target['path']}"
                    )
            final_validation = validate_repository(root)
            if not final_validation.passed:
                failures = tuple(
                    MutationFailure(issue.code, issue.path, issue.message)
                    for issue in final_validation.issues
                )
                raise PersistenceRejectedError(
                    "Applied persistence targets failed final validation.", failures
                )
            _write_yaml(root / plan_relative, applied_plan)
        except Exception:
            rollback_paths = (
                state_relative,
                execution_relative,
                reuse_relative,
                plan_relative,
            )
            for relative_path in rollback_paths:
                prior = retained[relative_path]
                target_path = root / relative_path
                if prior is None:
                    target_path.unlink(missing_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_bytes(prior)
                target_path.with_suffix(target_path.suffix + ".tmp").unlink(missing_ok=True)
            raise

    assert isinstance(execution_id, str)
    return PersistenceResult(
        operation="persist-execution",
        status="completed",
        files_changed=tuple(sorted(final_values)),
        execution_id=execution_id,
        lifecycle_stage="reuse",
        persistence_plan_id=plan_id,
        reuse_assessment_id=reuse_id,
    )
