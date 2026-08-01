from __future__ import annotations

import hashlib
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, TypeVar

import yaml

from ai_flywheel_cli.operations import OperationError, RepositoryLock
from ai_flywheel_cli.validation import ValidationIssue, validate_repository

TMutationError = TypeVar("TMutationError", bound="MutationRejectedError")
MutationHook = Callable[[str, str, int], None]


@dataclass(frozen=True)
class MutationFailure:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


class MutationRejectedError(OperationError):
    """Raised when a proposed repository mutation cannot be safely persisted."""

    def __init__(self, message: str, failures: tuple[MutationFailure, ...] = ()) -> None:
        super().__init__(message)
        self.failures = failures

    def as_dict(self) -> dict[str, object]:
        return {
            "status": "mutation-rejected",
            "error": str(self),
            "failures": [failure.as_dict() for failure in self.failures],
        }


def load_yaml_mapping(path: Path, error_type: type[TMutationError]) -> dict[str, Any]:
    if not path.is_file():
        failure = MutationFailure("MISSING_ARTIFACT", str(path), "Required artifact does not exist.")
        raise error_type(f"Required artifact does not exist: {path}", (failure,))
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        failure = MutationFailure("INVALID_ARTIFACT", str(path), str(error))
        raise error_type(f"Unable to load YAML artifact: {path}", (failure,)) from error
    if not isinstance(value, dict):
        failure = MutationFailure("INVALID_ARTIFACT_SHAPE", str(path), "Artifact must be a YAML mapping.")
        raise error_type(f"Artifact must be a YAML mapping: {path}", (failure,))
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(dict(value), sort_keys=False), encoding="utf-8")


def _validation_failures(issues: tuple[ValidationIssue, ...]) -> tuple[MutationFailure, ...]:
    return tuple(MutationFailure(issue.code, issue.path, issue.message) for issue in issues)


def commit_validated_yaml(
    repository: Path,
    changes: Mapping[str, Mapping[str, Any]],
    command: str,
    error_type: type[TMutationError],
    *,
    expected_sha256: Mapping[str, str | None] | None = None,
    interruption_hook: MutationHook | None = None,
) -> tuple[str, ...]:
    root = repository.resolve()
    expected = expected_sha256 or {}
    with RepositoryLock(root, command):
        for relative_path, expected_digest in expected.items():
            target = root / relative_path
            actual_digest = sha256_bytes(target.read_bytes()) if target.is_file() else None
            if actual_digest != expected_digest:
                failure = MutationFailure(
                    "STALE_SOURCE_REVISION",
                    relative_path,
                    f"Expected SHA-256 {expected_digest!r}, found {actual_digest!r}.",
                )
                raise error_type(f"Source artifact changed before persistence: {relative_path}", (failure,))

        shadow_parent = Path(tempfile.mkdtemp(prefix="flywheel-shadow-"))
        shadow = shadow_parent / "repository"
        backups: dict[str, bytes | None] = {}
        try:
            shutil.copytree(root, shadow, ignore=shutil.ignore_patterns(".git", ".runtime"))
            for relative_path, value in changes.items():
                _write_yaml(shadow / relative_path, value)
            validation = validate_repository(shadow)
            if not validation.passed:
                raise error_type("Proposed mutation failed validation.", _validation_failures(validation.issues))
            for index, (relative_path, value) in enumerate(changes.items()):
                target = root / relative_path
                backups[relative_path] = target.read_bytes() if target.is_file() else None
                temporary = target.with_suffix(target.suffix + ".tmp")
                _write_yaml(temporary, value)
                if interruption_hook is not None:
                    interruption_hook("before-replace", relative_path, index)
                temporary.replace(target)
                if interruption_hook is not None:
                    interruption_hook("after-replace", relative_path, index)
        except Exception:
            for relative_path, prior in backups.items():
                target = root / relative_path
                if prior is None:
                    target.unlink(missing_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(prior)
                target.with_suffix(target.suffix + ".tmp").unlink(missing_ok=True)
            raise
        finally:
            shutil.rmtree(shadow_parent, ignore_errors=True)
    return tuple(sorted(changes))
