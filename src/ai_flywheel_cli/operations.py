from __future__ import annotations

import json
import os
import socket
import uuid
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path

RUNTIME_DIRECTORY = ".flywheel/.runtime"


class OperationError(RuntimeError):
    """Base class for expected repository-operation failures."""


class RepositoryConflictError(OperationError):
    """Raised when an operation would overwrite repository-owned content."""


class LockContentionError(OperationError):
    """Raised when another repository mutation owns the operation lock."""


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
