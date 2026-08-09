from __future__ import annotations

from pathlib import Path

import pytest

from ai_flywheel_cli.operations import LockContentionError, RepositoryLock


def test_repository_lock_rejects_contention(tmp_path: Path) -> None:
    with (
        RepositoryLock(tmp_path, "persist-execution"),
        pytest.raises(LockContentionError),
        RepositoryLock(tmp_path, "advance-lifecycle"),
    ):
        pass


def test_repository_lock_is_removed_after_operation(tmp_path: Path) -> None:
    with RepositoryLock(tmp_path, "persist-execution"):
        assert (tmp_path / ".flywheel/.runtime/operation.lock").is_file()

    assert not (tmp_path / ".flywheel/.runtime/operation.lock").exists()
