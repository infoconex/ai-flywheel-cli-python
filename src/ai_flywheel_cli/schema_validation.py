from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema
import yaml

from ai_flywheel_cli.validation import LIFECYCLE_STAGES, ValidationIssue

CORE_SCHEMAS = {
    "manifest": ".flywheel/manifest.yaml",
    "state": ".flywheel/state.yaml",
}
TERMINAL_EXECUTION_STATUSES = {"succeeded", "partially-succeeded", "failed", "abandoned"}
TERMINAL_STAGE_STATUSES = {"completed", "not-applicable", "failed", "blocked"}


def _load(path: Path, issues: list[ValidationIssue]) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        issues.append(ValidationIssue("SCHEMA_INPUT_UNREADABLE", path.as_posix(), str(error)))
        return None


def _schema(root: Path, name: str) -> dict[str, Any] | None:
    path = root / ".flywheel/operating-model/schemas" / f"{name}.schema.yaml"
    if not path.is_file():
        return None
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else None


def _validate_schema(
    root: Path,
    relative: Path,
    schema_name: str,
    issues: list[ValidationIssue],
) -> None:
    schema = _schema(root, schema_name)
    path = root / relative
    if schema is None or not path.is_file():
        return
    value = _load(path, issues)
    if value is None:
        return
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path))
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        issues.append(
            ValidationIssue(
                "SCHEMA_VALIDATION_FAILED",
                relative.as_posix(),
                f"{schema_name} at {location}: {error.message}",
            )
        )


def _legacy_evidence_valid(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("schema_version") != 1 or not isinstance(value.get("summary"), str):
        return False
    evidence_id = value.get("id", value.get("evidence_id"))
    if not isinstance(evidence_id, str) or not evidence_id.startswith("EVIDENCE-"):
        return False
    timestamp_present = any(key in value for key in ("recorded_at", "created_at", "captured_at"))
    content_present = any(key in value for key in ("details", "evidence", "observations", "source"))
    return timestamp_present or content_present


def validate_declared_artifacts(
    root: Path,
    state: Any,
    issues: list[ValidationIssue],
) -> None:
    for schema_name, relative_path in CORE_SCHEMAS.items():
        _validate_schema(root, Path(relative_path), schema_name, issues)

    if not isinstance(state, dict):
        return
    mission_id = state.get("active_mission")
    goal_id = state.get("active_goal")
    execution_id = state.get("active_execution")
    active_execution_relative: Path | None = None
    if isinstance(mission_id, str):
        mission_root = root / ".flywheel/operations/missions" / mission_id
        _validate_schema(
            root,
            mission_root.joinpath("mission.yaml").relative_to(root),
            "mission",
            issues,
        )
        for goal_path in mission_root.glob("goals/*.yaml"):
            _validate_schema(root, goal_path.relative_to(root), "goal", issues)
    if mission_id and goal_id and execution_id:
        active_execution_relative = Path(
            f".flywheel/operations/records/{mission_id}/{goal_id}/executions/"
            f"{execution_id}.yaml"
        )
        _validate_schema(
            root,
            active_execution_relative,
            "execution",
            issues,
        )

    records_root = root / ".flywheel/operations/records"
    if not records_root.is_dir():
        return

    known_evidence: set[str] = set()
    for evidence_path in records_root.glob("*/*/evidence/*.yaml"):
        value = _load(evidence_path, issues)
        relative = evidence_path.relative_to(root)
        if not isinstance(value, dict):
            continue
        evidence_id = value.get("id", value.get("evidence_id"))
        if isinstance(evidence_id, str):
            known_evidence.add(evidence_id)
        if isinstance(evidence_id, str) and not (
            evidence_path.stem == evidence_id or evidence_path.stem.startswith(evidence_id + "-")
        ):
            issues.append(
                ValidationIssue(
                    "FILENAME_ID_MISMATCH",
                    relative.as_posix(),
                    "Evidence filename and id do not match.",
                )
            )
        if "record_type" in value:
            _validate_schema(root, relative, "record", issues)
        elif not _legacy_evidence_valid(value):
            issues.append(
                ValidationIssue(
                    "INVALID_LEGACY_EVIDENCE",
                    relative.as_posix(),
                    "Historical onboarding evidence does not match the approved legacy "
                    "compatibility profile.",
                )
            )

    for execution_path in records_root.glob("*/*/executions/*.yaml"):
        value = _load(execution_path, issues)
        relative = execution_path.relative_to(root)
        if not isinstance(value, dict):
            continue
        if relative == active_execution_relative:
            _validate_schema(root, relative, "execution", issues)
        execution_id = value.get("id")
        if execution_path.stem != execution_id:
            issues.append(
                ValidationIssue(
                    "FILENAME_ID_MISMATCH",
                    relative.as_posix(),
                    "Execution filename and id do not match.",
                )
            )
        parts = relative.parts
        expected_mission, expected_goal = parts[-4], parts[-3]
        if value.get("mission_id") != expected_mission or value.get("goal_id") != expected_goal:
            issues.append(
                ValidationIssue(
                    "EXECUTION_PARENT_MISMATCH",
                    relative.as_posix(),
                    "Execution parent references do not match record placement.",
                )
            )
        lifecycle = value.get("lifecycle")
        if not isinstance(lifecycle, dict) or set(lifecycle) != LIFECYCLE_STAGES:
            issues.append(
                ValidationIssue(
                    "INCOMPLETE_LIFECYCLE",
                    relative.as_posix(),
                    "Execution must contain exactly eight lifecycle stages.",
                )
            )
        if value.get("status") in TERMINAL_EXECUTION_STATUSES:
            if not isinstance(lifecycle, dict) or any(
                not isinstance(stage, dict) or stage.get("status") not in TERMINAL_STAGE_STATUSES
                for stage in lifecycle.values()
            ):
                issues.append(
                    ValidationIssue(
                        "INCOMPLETE_TERMINAL_EXECUTION",
                        relative.as_posix(),
                        "Terminal execution requires every lifecycle stage to be terminal.",
                    )
                )
            completion = value.get("completion")
            if (
                not value.get("outcome")
                or not isinstance(completion, dict)
                or not completion.get("disposition")
            ):
                issues.append(
                    ValidationIssue(
                        "MISSING_EXECUTION_COMPLETION",
                        relative.as_posix(),
                        "Terminal execution requires outcome and completion disposition.",
                    )
                )
        evidence_refs = value.get("evidence_refs")
        if isinstance(evidence_refs, list):
            for evidence_id in evidence_refs:
                if evidence_id not in known_evidence:
                    issues.append(
                        ValidationIssue(
                            "BROKEN_EVIDENCE_REFERENCE",
                            relative.as_posix(),
                            f"Unknown evidence reference: {evidence_id}",
                        )
                    )
