from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import tempfile
import uuid
import zipfile
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

RUNTIME_DIRECTORY = ".flywheel/.runtime"
INSTALLATION_METADATA = ".flywheel/installation.yaml"
MUTABLE_PREFIXES = (
    ".flywheel/state.yaml",
    ".flywheel/operations/",
)


class OperationError(RuntimeError):
    """Base class for expected repository-operation failures."""


class RepositoryConflictError(OperationError):
    """Raised when an operation would overwrite repository-owned content."""


class LockContentionError(OperationError):
    """Raised when another repository mutation owns the operation lock."""


class ArchiveSafetyError(OperationError):
    """Raised when an archive contains unsafe or ambiguous paths."""


class ChecksumMismatchError(OperationError):
    """Raised when downloaded or supplied content fails checksum verification."""


@dataclass(frozen=True)
class ChangePlan:
    command: str
    files: tuple[str, ...]
    framework_version: str

    def as_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "files": list(self.files),
            "framework_version": self.framework_version,
        }


@dataclass(frozen=True)
class OperationResult:
    command: str
    status: str
    framework_version: str
    files_changed: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "status": self.status,
            "framework_version": self.framework_version,
            "files_changed": list(self.files_changed),
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_checksum(path: Path, expected: str) -> None:
    normalized = expected.strip().lower()
    actual = sha256_file(path)
    if actual != normalized:
        raise ChecksumMismatchError(
            f"SHA-256 mismatch for {path.name}: expected {normalized}, found {actual}."
        )


def _safe_relative_path(name: str) -> Path:
    normalized_name = name.replace("\\", "/")
    pure = PurePosixPath(normalized_name)
    if pure.is_absolute() or ".." in pure.parts:
        raise ArchiveSafetyError(f"Unsafe archive path: {name}")
    if not pure.parts or pure.parts[0] != ".flywheel":
        raise ArchiveSafetyError(f"Archive content must be rooted under .flywheel: {name}")
    return Path(*pure.parts)


def inspect_archive(archive_path: Path) -> tuple[str, ...]:
    destinations: set[str] = set()
    files: list[str] = []
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                relative = _safe_relative_path(info.filename)
                destination = relative.as_posix().rstrip("/")
                if not destination:
                    continue
                if destination in destinations:
                    raise ArchiveSafetyError(f"Duplicate archive destination: {destination}")
                destinations.add(destination)
                mode = info.external_attr >> 16
                if mode & 0o170000 == 0o120000:
                    raise ArchiveSafetyError(f"Symbolic links are not permitted: {destination}")
                if not info.is_dir():
                    files.append(destination)
    except zipfile.BadZipFile as error:
        raise ArchiveSafetyError(f"Invalid ZIP archive: {archive_path}") from error
    return tuple(sorted(files))


def extract_archive(archive_path: Path, destination: Path) -> tuple[str, ...]:
    files = inspect_archive(archive_path)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            relative = _safe_relative_path(info.filename)
            target = destination / relative
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    return files


class RepositoryLock(AbstractContextManager["RepositoryLock"]):
    def __init__(self, repository: Path, command: str) -> None:
        self.repository = repository.resolve()
        self.command = command
        self.lock_path = self.repository / RUNTIME_DIRECTORY / "operation.lock"
        self._owned = False

    def __enter__(self) -> RepositoryLock:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "schema_version": 1,
            "operation_id": str(uuid.uuid4()),
            "command": self.command,
            "process_id": os.getpid(),
            "hostname": socket.gethostname(),
            "started_at": datetime.now(UTC).isoformat(),
        }
        try:
            descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            existing = self.lock_path.read_text(encoding="utf-8", errors="replace")
            raise LockContentionError(
                f"Repository mutation lock already exists: {existing}"
            ) from error
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(metadata, stream, sort_keys=True)
            stream.write("\n")
        self._owned = True
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._owned:
            self.lock_path.unlink(missing_ok=True)
            self._owned = False


def _owned_file(path: str) -> bool:
    return not any(path == prefix or path.startswith(prefix) for prefix in MUTABLE_PREFIXES)


def _write_metadata(
    repository: Path,
    framework_version: str,
    archive_checksum: str,
    source_identity: str,
    files: tuple[str, ...],
) -> None:
    owned = {
        path: sha256_file(repository / path)
        for path in files
        if _owned_file(path) and (repository / path).is_file()
    }
    metadata = {
        "schema_version": 1,
        "framework_version": framework_version,
        "archive_sha256": archive_checksum,
        "source_identity": source_identity,
        "installed_at": datetime.now(UTC).isoformat(),
        "owned_files": dict(sorted(owned.items())),
    }
    target = repository / INSTALLATION_METADATA
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".yaml.tmp")
    temporary.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    os.replace(temporary, target)


def load_installation_metadata(repository: Path) -> dict[str, Any]:
    path = repository / INSTALLATION_METADATA
    if not path.is_file():
        raise RepositoryConflictError(f"Missing installation metadata: {INSTALLATION_METADATA}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RepositoryConflictError("Installation metadata must be a YAML mapping.")
    return value


def detect_upgrade_conflicts(repository: Path, metadata: dict[str, Any]) -> tuple[str, ...]:
    owned_files = metadata.get("owned_files")
    if not isinstance(owned_files, dict):
        raise RepositoryConflictError("Installation metadata owned_files must be a mapping.")
    conflicts: list[str] = []
    for path, baseline in owned_files.items():
        if not isinstance(path, str) or not isinstance(baseline, str):
            raise RepositoryConflictError(
                "Installation metadata contains an invalid checksum entry."
            )
        target = repository / path
        if not target.is_file() or sha256_file(target) != baseline:
            conflicts.append(path)
    return tuple(sorted(conflicts))


def _apply_staged_tree(repository: Path, staged_root: Path, files: tuple[str, ...]) -> None:
    backup_root = Path(tempfile.mkdtemp(prefix="flywheel-backup-", dir=repository))
    changed: list[str] = []
    try:
        for path in files:
            source = staged_root / path
            target = repository / path
            backup = backup_root / path
            if target.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            changed.append(path)
    except Exception:
        for path in reversed(changed):
            target = repository / path
            backup = backup_root / path
            if backup.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, target)
            else:
                target.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(backup_root, ignore_errors=True)


def plan_install(archive_path: Path, framework_version: str) -> ChangePlan:
    return ChangePlan("install", inspect_archive(archive_path), framework_version)


def install_from_archive(
    repository: Path,
    archive_path: Path,
    expected_checksum: str,
    framework_version: str,
    source_identity: str,
) -> OperationResult:
    repository = repository.resolve()
    if (repository / ".flywheel").exists():
        raise RepositoryConflictError("Refusing to install because .flywheel already exists.")
    verify_checksum(archive_path, expected_checksum)
    files = inspect_archive(archive_path)
    with RepositoryLock(repository, "install"):
        staging = Path(tempfile.mkdtemp(prefix="flywheel-stage-", dir=repository))
        try:
            extract_archive(archive_path, staging)
            _apply_staged_tree(repository, staging, files)
            _write_metadata(
                repository,
                framework_version,
                sha256_file(archive_path),
                source_identity,
                files,
            )
        except Exception:
            shutil.rmtree(repository / ".flywheel", ignore_errors=True)
            raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    return OperationResult("install", "installed", framework_version, files)
