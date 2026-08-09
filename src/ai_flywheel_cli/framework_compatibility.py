from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_FRAMEWORK_VERSION = "2026.08.08"


@dataclass(frozen=True)
class FrameworkCompatibility:
    status: str
    installed_version: str | None
    reason: str

    @property
    def compatible(self) -> bool:
        return self.status == "compatible"


def _mapping(path: Path) -> dict[str, Any] | None:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return None
    return value if isinstance(value, dict) else None


def _calver(value: object) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        return None
    return int(parts[0]), int(parts[1]), int(parts[2])


def classify_framework(repository: Path) -> FrameworkCompatibility:
    flywheel = repository.resolve() / ".flywheel"
    if not flywheel.exists():
        return FrameworkCompatibility(
            "not-installed",
            None,
            "No .flywheel directory is installed.",
        )
    if not flywheel.is_dir():
        return FrameworkCompatibility(
            "malformed",
            None,
            ".flywheel exists but is not a directory.",
        )

    installation_path = flywheel / "installation.yaml"
    if not installation_path.is_file():
        return FrameworkCompatibility(
            "untracked-or-legacy",
            None,
            "Installation provenance is missing; the framework will not be overwritten.",
        )
    installation = _mapping(installation_path)
    if installation is None:
        return FrameworkCompatibility(
            "malformed",
            None,
            "installation.yaml is not a readable YAML mapping.",
        )
    installed_version = installation.get("framework_version")
    installed_calver = _calver(installed_version)
    if installed_calver is None:
        return FrameworkCompatibility(
            "malformed",
            str(installed_version) if installed_version is not None else None,
            "installation.yaml does not contain a valid CalVer framework_version.",
        )

    manifest = _mapping(flywheel / "manifest.yaml")
    if manifest is None:
        return FrameworkCompatibility(
            "malformed",
            str(installed_version),
            "manifest.yaml is missing or is not a readable YAML mapping.",
        )
    framework = manifest.get("framework")
    manifest_version = framework.get("version") if isinstance(framework, dict) else None
    if _calver(manifest_version) is None:
        return FrameworkCompatibility(
            "malformed",
            str(installed_version),
            "manifest.yaml does not contain a valid framework.version CalVer.",
        )
    if manifest_version != installed_version:
        return FrameworkCompatibility(
            "invalid",
            str(installed_version),
            "installation.yaml and manifest.yaml report different framework versions.",
        )

    supported_calver = _calver(SUPPORTED_FRAMEWORK_VERSION)
    if installed_calver == supported_calver:
        return FrameworkCompatibility(
            "compatible",
            str(installed_version),
            "The installed framework is compatible with this CLI.",
        )
    if supported_calver is not None and installed_calver < supported_calver:
        return FrameworkCompatibility(
            "older-unsupported",
            str(installed_version),
            "The installed framework is older than the supported framework; "
            "no automatic upgrade contract is available.",
        )
    return FrameworkCompatibility(
        "newer-unsupported",
        str(installed_version),
        "The installed framework is newer than the supported framework and cannot be "
        "assumed compatible.",
    )
