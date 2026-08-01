# AI Flywheel CLI for Python

A cross-platform command-line application for inspecting, installing, validating, and safely upgrading AI Flywheel operating artifacts in a repository.

## Requirements

- Python 3.11 or newer
- A local repository directory
- A verified AI Flywheel framework ZIP archive and its published SHA-256 checksum for installation or upgrade

Hosted execution is not enabled. All validation is performed locally.

## Development setup

```text
python -m venv .venv
python -m pip install -e ".[dev]"
python -m tools validate
```

`python -m tools validate` runs Ruff linting, Ruff formatting checks, mypy, pytest, coverage, and the repository artifact validator.

## Commands

### Doctor

Read-only inspection of repository prerequisites:

```text
flywheel doctor .
flywheel doctor . --json
```

### Status

Reports whether Flywheel artifacts are installed and whether the current installation validates:

```text
flywheel status .
```

### Validate

Validates required files, state invariants, active references, execution parentage, filename-to-ID consistency, and lifecycle completeness:

```text
flywheel validate .
flywheel validate . --json
```

Validation failures return exit code `2`.

### Install

Installation is plan-first. Omitting `--apply` makes no repository changes:

```text
flywheel install . \
  --archive ai-flywheel-framework.zip \
  --checksum <sha256> \
  --framework-version 0.1.0
```

After inspecting the plan, apply it explicitly:

```text
flywheel install . \
  --archive ai-flywheel-framework.zip \
  --checksum <sha256> \
  --framework-version 0.1.0 \
  --source-identity github-release-v0.1.0 \
  --apply
```

Installation refuses to overwrite an existing `.flywheel` directory. The archive checksum is verified before extraction, archive paths are inspected, a repository mutation lock is acquired, changes are staged, and installation metadata is written only after the operation succeeds.

### Upgrade

Upgrade is also plan-first:

```text
flywheel upgrade . \
  --archive ai-flywheel-framework.zip \
  --checksum <sha256> \
  --framework-version 0.2.0
```

Use `--apply` after reviewing the requested target. Upgrade refuses to overwrite locally modified framework-owned files and blocks unsupported major-version transitions. Mutable operating content such as state, missions, goals, executions, evidence, approvals, and knowledge is not treated as framework-owned upgrade content.

## Exit categories

- `0`: success or read-only plan produced
- `2`: validation failure
- `4`: repository conflict
- `5`: operation lock contention
- `8`: other expected operation failure
- Typer reserves its normal usage-error behavior for invalid command syntax

## Installation metadata

Successful installation and upgrade write:

```text
.flywheel/installation.yaml
```

The metadata records the framework version, archive checksum, source identity, installation time, and SHA-256 checksum for each framework-owned file.

## Safety model

- No silent overwrite of an existing installation
- No silent overwrite of locally modified framework-owned files
- SHA-256 verification before extraction
- Rejection of path traversal, absolute paths, symbolic links, duplicate destinations, and content outside `.flywheel`
- Atomic lock-file acquisition under `.flywheel/.runtime`
- Staged writes with rollback for write failures
- No automatic deletion of ambiguous stale locks
- No GitHub Actions or other hosted execution without separate approval

## Runtime files

`.flywheel/.runtime/` contains temporary locks and staging information. It must not be committed.

## Current limitations

- Release discovery and download are not performed implicitly; the first implementation accepts an already downloaded immutable archive and expected checksum.
- Offline release bundles and standalone executable distribution remain deferred.
- Mission, goal, execution, and full lifecycle-management commands remain deferred.
- A dedicated stale-lock recovery command remains deferred.

## License

MIT
