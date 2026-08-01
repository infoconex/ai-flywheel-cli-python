from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from ai_flywheel_cli.operations import (
    ArchiveSafetyError,
    ChecksumMismatchError,
    LockContentionError,
    RepositoryConflictError,
    RepositoryLock,
    detect_upgrade_conflicts,
    install_from_archive,
    inspect_archive,
    load_installation_metadata,
    sha256_file,
    upgrade_from_archive,
    verify_checksum,
)


def _archive(path: Path, files: dict[str, str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


def test_checksum_verification_accepts_expected_digest(tmp_path: Path) -> None:
    value = tmp_path / "value.bin"
    value.write_bytes(b"flywheel")

    verify_checksum(value, hashlib.sha256(b"flywheel").hexdigest())


def test_checksum_verification_rejects_mismatch(tmp_path: Path) -> None:
    value = tmp_path / "value.bin"
    value.write_bytes(b"flywheel")

    with pytest.raises(ChecksumMismatchError):
        verify_checksum(value, "0" * 64)


def test_archive_rejects_path_traversal(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "unsafe.zip", {"../escape.txt": "bad"})

    with pytest.raises(ArchiveSafetyError):
        inspect_archive(archive)


def test_archive_requires_flywheel_root(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "unsafe.zip", {"README.md": "bad"})

    with pytest.raises(ArchiveSafetyError):
        inspect_archive(archive)


def test_repository_lock_rejects_contention(tmp_path: Path) -> None:
    with RepositoryLock(tmp_path, "install"):
        with pytest.raises(LockContentionError):
            with RepositoryLock(tmp_path, "upgrade"):
                pass


def test_install_refuses_existing_flywheel(tmp_path: Path) -> None:
    (tmp_path / ".flywheel").mkdir()
    archive = _archive(tmp_path / "framework.zip", {".flywheel/manifest.yaml": "schema_version: 1\n"})

    with pytest.raises(RepositoryConflictError):
        install_from_archive(tmp_path, archive, sha256_file(archive), "0.1.0", "fixture")


def test_install_creates_files_and_metadata(tmp_path: Path) -> None:
    archive = _archive(
        tmp_path / "framework.zip",
        {
            ".flywheel/manifest.yaml": "schema_version: 1\n",
            ".flywheel/state.yaml": "schema_version: 1\n",
        },
    )

    result = install_from_archive(
        tmp_path,
        archive,
        sha256_file(archive),
        "0.1.0",
        "fixture-release",
    )

    assert result.status == "installed"
    assert (tmp_path / ".flywheel/manifest.yaml").is_file()
    metadata = load_installation_metadata(tmp_path)
    assert metadata["framework_version"] == "0.1.0"
    assert ".flywheel/manifest.yaml" in metadata["owned_files"]
    assert ".flywheel/state.yaml" not in metadata["owned_files"]


def test_upgrade_detects_local_modification(tmp_path: Path) -> None:
    archive = _archive(
        tmp_path / "framework.zip",
        {
            ".flywheel/manifest.yaml": "schema_version: 1\n",
            ".flywheel/state.yaml": "schema_version: 1\n",
        },
    )
    install_from_archive(tmp_path, archive, sha256_file(archive), "0.1.0", "fixture")
    (tmp_path / ".flywheel/manifest.yaml").write_text("changed: true\n", encoding="utf-8")

    conflicts = detect_upgrade_conflicts(tmp_path, load_installation_metadata(tmp_path))

    assert conflicts == (".flywheel/manifest.yaml",)


def test_upgrade_refuses_local_modification(tmp_path: Path) -> None:
    initial = _archive(
        tmp_path / "initial.zip",
        {
            ".flywheel/manifest.yaml": "schema_version: 1\n",
            ".flywheel/state.yaml": "schema_version: 1\n",
        },
    )
    install_from_archive(tmp_path, initial, sha256_file(initial), "0.1.0", "fixture")
    (tmp_path / ".flywheel/manifest.yaml").write_text("changed: true\n", encoding="utf-8")
    target = _archive(tmp_path / "target.zip", {".flywheel/manifest.yaml": "schema_version: 2\n"})

    with pytest.raises(RepositoryConflictError):
        upgrade_from_archive(tmp_path, target, sha256_file(target), "0.2.0", "fixture")


def test_upgrade_preserves_mutable_state(tmp_path: Path) -> None:
    initial = _archive(
        tmp_path / "initial.zip",
        {
            ".flywheel/manifest.yaml": "schema_version: 1\n",
            ".flywheel/state.yaml": "value: original\n",
        },
    )
    install_from_archive(tmp_path, initial, sha256_file(initial), "0.1.0", "fixture")
    (tmp_path / ".flywheel/state.yaml").write_text("value: local\n", encoding="utf-8")
    target = _archive(
        tmp_path / "target.zip",
        {
            ".flywheel/manifest.yaml": "schema_version: 2\n",
            ".flywheel/state.yaml": "value: release\n",
        },
    )

    upgrade_from_archive(tmp_path, target, sha256_file(target), "0.2.0", "fixture")

    assert (tmp_path / ".flywheel/manifest.yaml").read_text(encoding="utf-8") == "schema_version: 2\n"
