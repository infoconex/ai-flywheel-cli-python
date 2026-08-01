from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from ai_flywheel_cli.operations import (
    MUTABLE_PREFIXES,
    OperationResult,
    RepositoryConflictError,
    RepositoryLock,
    _apply_staged_tree,
    _write_metadata,
    detect_upgrade_conflicts,
    extract_archive,
    inspect_archive,
    load_installation_metadata,
    sha256_file,
    verify_checksum,
)


def _mutable(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in MUTABLE_PREFIXES)


def upgrade_from_archive(
    repository: Path,
    archive_path: Path,
    expected_checksum: str,
    framework_version: str,
    source_identity: str,
) -> OperationResult:
    repository = repository.resolve()
    if not (repository / ".flywheel").is_dir():
        raise RepositoryConflictError("Cannot upgrade because .flywheel is not installed.")

    metadata = load_installation_metadata(repository)
    conflicts = detect_upgrade_conflicts(repository, metadata)
    if conflicts:
        raise RepositoryConflictError(
            "Locally modified framework-owned files prevent upgrade: " + ", ".join(conflicts)
        )

    current_version = str(metadata.get("framework_version", "0.0.0"))
    if current_version.split(".", 1)[0] != framework_version.split(".", 1)[0]:
        raise RepositoryConflictError("Major-version upgrades require an explicit migration path.")

    verify_checksum(archive_path, expected_checksum)
    archive_files = inspect_archive(archive_path)
    changed_files = tuple(path for path in archive_files if not _mutable(path))

    with RepositoryLock(repository, "upgrade"):
        staging = Path(tempfile.mkdtemp(prefix="flywheel-stage-", dir=repository))
        try:
            extract_archive(archive_path, staging)
            _apply_staged_tree(repository, staging, changed_files)
            _write_metadata(
                repository,
                framework_version,
                sha256_file(archive_path),
                source_identity,
                archive_files,
            )
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    return OperationResult("upgrade", "upgraded", framework_version, changed_files)
