from __future__ import annotations

from pathlib import Path

import yaml

from ai_flywheel_cli.framework_compatibility import classify_framework


def _write_yaml(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _framework(repository: Path, installation_version: str, manifest_version: str) -> None:
    _write_yaml(
        repository / ".flywheel/installation.yaml",
        {"schema_version": 1, "framework_version": installation_version},
    )
    _write_yaml(
        repository / ".flywheel/manifest.yaml",
        {"schema_version": 1, "framework": {"version": manifest_version}},
    )


def test_classifies_absent_framework(tmp_path: Path) -> None:
    assert classify_framework(tmp_path).status == "not-installed"


def test_classifies_supported_framework(tmp_path: Path) -> None:
    _framework(tmp_path, "2026.08.08", "2026.08.08")
    result = classify_framework(tmp_path)
    assert result.status == "compatible"
    assert result.installed_version == "2026.08.08"


def test_classifies_older_and_newer_frameworks(tmp_path: Path) -> None:
    _framework(tmp_path, "2026.07.31", "2026.07.31")
    assert classify_framework(tmp_path).status == "older-unsupported"
    _framework(tmp_path, "2026.08.09", "2026.08.09")
    assert classify_framework(tmp_path).status == "newer-unsupported"


def test_classifies_framework_without_provenance(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / ".flywheel/manifest.yaml",
        {"schema_version": 1, "framework": {"version": "2026.08.08"}},
    )
    assert classify_framework(tmp_path).status == "untracked-or-legacy"


def test_classifies_malformed_metadata(tmp_path: Path) -> None:
    installation = tmp_path / ".flywheel/installation.yaml"
    installation.parent.mkdir(parents=True)
    installation.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    assert classify_framework(tmp_path).status == "malformed"


def test_rejects_manifest_and_installation_version_disagreement(tmp_path: Path) -> None:
    _framework(tmp_path, "2026.08.08", "2026.08.09")
    assert classify_framework(tmp_path).status == "invalid"
