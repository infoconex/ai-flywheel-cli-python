from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

LIFECYCLE_STAGES = {
    "execute",
    "observe",
    "evaluate",
    "classify",
    "adapt",
    "validate",
    "persist",
    "reuse",
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...]

    @property
    def passed(self) -> bool:
        return not self.issues


def _load_yaml(path: Path, issues: list[ValidationIssue]) -> Any:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return yaml.safe_load(stream)
    except OSError as error:
        issues.append(ValidationIssue("FILE_READ_FAILED", str(path), str(error)))
    except yaml.YAMLError as error:
        issues.append(ValidationIssue("INVALID_YAML", str(path), str(error)))
    return None


def _require_file(root: Path, relative_path: str, issues: list[ValidationIssue]) -> Path:
    path = root / relative_path
    if not path.is_file():
        issues.append(
            ValidationIssue(
                "MISSING_REQUIRED_FILE",
                relative_path,
                f"Required file does not exist: {relative_path}",
            )
        )
    return path


def _validate_state(root: Path, state: Any, issues: list[ValidationIssue]) -> None:
    path = ".flywheel/state.yaml"
    if not isinstance(state, dict):
        issues.append(ValidationIssue("INVALID_STATE", path, "State must be a YAML mapping."))
        return

    required = {
        "schema_version",
        "phase",
        "readiness",
        "status",
        "active_mission",
        "active_goal",
        "active_execution",
        "lifecycle_stage",
        "implementation_available",
        "application_missions_allowed",
        "blockers",
        "last_durable_update",
    }
    for field in sorted(required - state.keys()):
        issues.append(ValidationIssue("MISSING_STATE_FIELD", path, f"Missing field: {field}"))

    active_execution = state.get("active_execution")
    lifecycle_stage = state.get("lifecycle_stage")
    status = state.get("status")
    readiness = state.get("readiness")

    if active_execution is None and lifecycle_stage is not None:
        issues.append(
            ValidationIssue(
                "STATE_EXECUTION_STAGE_MISMATCH",
                path,
                "lifecycle_stage must be null when active_execution is null.",
            )
        )
    if active_execution is not None:
        if not state.get("active_mission") or not state.get("active_goal"):
            issues.append(
                ValidationIssue(
                    "STATE_ACTIVE_REFERENCE_MISSING",
                    path,
                    "An active execution requires active_mission and active_goal.",
                )
            )
        if lifecycle_stage not in LIFECYCLE_STAGES:
            issues.append(
                ValidationIssue(
                    "INVALID_LIFECYCLE_STAGE",
                    path,
                    f"Unsupported lifecycle stage: {lifecycle_stage}",
                )
            )
        if status not in {"active", "blocked"}:
            issues.append(
                ValidationIssue(
                    "INVALID_ACTIVE_STATUS",
                    path,
                    "An active execution requires state.status active or blocked.",
                )
            )

    if readiness == "ready-for-missions" and not state.get("application_missions_allowed"):
        issues.append(
            ValidationIssue(
                "READINESS_PERMISSION_MISMATCH",
                path,
                "ready-for-missions requires application_missions_allowed true.",
            )
        )
    if readiness != "ready-for-missions" and state.get("application_missions_allowed"):
        issues.append(
            ValidationIssue(
                "READINESS_PERMISSION_MISMATCH",
                path,
                "application_missions_allowed must be false unless ready-for-missions.",
            )
        )
    if status == "blocked" and not state.get("blockers"):
        issues.append(
            ValidationIssue(
                "BLOCKED_WITHOUT_BLOCKER",
                path,
                "Blocked state requires at least one blocker.",
            )
        )

    mission_id = state.get("active_mission")
    goal_id = state.get("active_goal")
    execution_id = state.get("active_execution")
    if mission_id:
        _require_file(
            root,
            f".flywheel/operations/missions/{mission_id}/mission.yaml",
            issues,
        )
    if mission_id and goal_id:
        _require_file(
            root,
            f".flywheel/operations/missions/{mission_id}/goals/{goal_id}.yaml",
            issues,
        )
    if mission_id and goal_id and execution_id:
        execution_path = (
            root
            / ".flywheel"
            / "operations"
            / "records"
            / str(mission_id)
            / str(goal_id)
            / "executions"
            / f"{execution_id}.yaml"
        )
        if not execution_path.is_file():
            issues.append(
                ValidationIssue(
                    "BROKEN_ACTIVE_EXECUTION_REFERENCE",
                    str(execution_path.relative_to(root)),
                    "The active execution file does not exist.",
                )
            )
        else:
            execution = _load_yaml(execution_path, issues)
            if isinstance(execution, dict):
                if execution.get("id") != execution_id:
                    issues.append(
                        ValidationIssue(
                            "FILENAME_ID_MISMATCH",
                            str(execution_path.relative_to(root)),
                            "Execution filename and id do not match.",
                        )
                    )
                if execution.get("mission_id") != mission_id or execution.get("goal_id") != goal_id:
                    issues.append(
                        ValidationIssue(
                            "EXECUTION_PARENT_MISMATCH",
                            str(execution_path.relative_to(root)),
                            "Execution parent references do not match active state.",
                        )
                    )
                lifecycle = execution.get("lifecycle")
                if not isinstance(lifecycle, dict) or set(lifecycle) != LIFECYCLE_STAGES:
                    issues.append(
                        ValidationIssue(
                            "INCOMPLETE_LIFECYCLE",
                            str(execution_path.relative_to(root)),
                            "Execution must contain exactly the eight lifecycle stages.",
                        )
                    )
                elif lifecycle_stage and lifecycle.get(lifecycle_stage, {}).get("status") not in {
                    "in-progress",
                    "blocked",
                }:
                    issues.append(
                        ValidationIssue(
                            "ACTIVE_STAGE_STATUS_MISMATCH",
                            str(execution_path.relative_to(root)),
                            "The active lifecycle stage must be in-progress or blocked.",
                        )
                    )


def validate_repository(root: Path) -> ValidationResult:
    repository = root.resolve()
    issues: list[ValidationIssue] = []
    manifest_path = _require_file(repository, ".flywheel/manifest.yaml", issues)
    state_path = _require_file(repository, ".flywheel/state.yaml", issues)

    if manifest_path.is_file():
        manifest = _load_yaml(manifest_path, issues)
        if isinstance(manifest, dict):
            required_files = manifest.get("required_files", [])
            if not isinstance(required_files, list):
                issues.append(
                    ValidationIssue(
                        "INVALID_MANIFEST_REQUIRED_FILES",
                        ".flywheel/manifest.yaml",
                        "required_files must be a list.",
                    )
                )
            else:
                for relative_path in required_files:
                    if isinstance(relative_path, str):
                        _require_file(repository, relative_path, issues)
                    else:
                        issues.append(
                            ValidationIssue(
                                "INVALID_REQUIRED_FILE_PATH",
                                ".flywheel/manifest.yaml",
                                "Each required_files entry must be a string.",
                            )
                        )

    if state_path.is_file():
        _validate_state(repository, _load_yaml(state_path, issues), issues)

    unique = {(issue.code, issue.path, issue.message): issue for issue in issues}
    ordered = tuple(unique[key] for key in sorted(unique))
    return ValidationResult(issues=ordered)
