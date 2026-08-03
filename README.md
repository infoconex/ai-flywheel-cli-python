# AI Flywheel CLI for Python

A cross-platform command-line application for inspecting, installing, validating, upgrading, and safely operating AI Flywheel artifacts in a repository.

## Requirements

- Python 3.11 or newer
- A local repository directory
- A verified AI Flywheel framework ZIP archive and its published SHA-256 checksum for installation or upgrade

Hosted execution is not enabled. All validation is performed locally.

## Implementation status

Version `0.1.0` is a locally validated release candidate. The package builds successfully as both a wheel and source distribution, installs into a clean Python environment, exposes the `flywheel` console command and `python -m ai_flywheel_cli` module entrypoint, and passes representative installed-command checks.

This status does not mean the package has been published. Tagging, GitHub release creation, and package-index publication remain pending explicit human approval.

## Development setup

```text
python -m venv .venv
python -m pip install -e ".[dev]"
python -m tools validate
```

`python -m tools validate` is the single local quality-gate command. It runs Ruff linting, Ruff formatting checks, strict mypy, pytest with coverage enforcement, and an isolated source-distribution and wheel build through the declared Hatchling backend. Build output is written under `.flywheel/.runtime/dist/` and is not committed.

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

### Execution lifecycle

Start an execution for a ready goal:

```text
flywheel start-execution <mission-id> <goal-id> <execution-id> \
  --intended-outcome "<outcome>" \
  --repository .
```

Advance the active execution through Execute, Observe, Evaluate, Classify, Adapt, and Validate:

```text
flywheel advance-lifecycle \
  --summary "<summary>" \
  --ref <record-id> \
  --expected-stage <stage> \
  --repository .
```

Persist a validated execution and activate Reuse:

```text
flywheel persist-execution \
  --summary "<summary>" \
  --reuse-id <reuse-id> \
  --repository .
```

Complete Reuse, close the execution, and ready the next dependent goal:

```text
flywheel complete-execution \
  --summary "<summary>" \
  --ref <record-id> \
  --repository .
```

These commands enforce schema validation, active-stage boundaries, reference integrity, and atomic state updates.

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

`.flywheel/.runtime/` contains temporary locks, staging information, and local build output. It must not be committed.

## Current limitations

- Release discovery and download are not performed implicitly; the first implementation accepts an already downloaded immutable archive and expected checksum.
- Offline release bundles and standalone executable distribution remain deferred.
- Mission and goal creation, editing, listing, and broader administrative management remain deferred; execution lifecycle transitions are supported.
- A dedicated stale-lock recovery command remains deferred.
- Release-candidate proof has been completed on Windows with Python 3.13.14; other supported platforms require their own execution evidence.

## Local release checklist

Run this checklist from a clean working tree before requesting release approval:

```text
python -m tools validate
python -m build
python -m venv .release-proof
.release-proof\Scripts\python -m pip install --upgrade pip
.release-proof\Scripts\python -m pip install dist\ai_flywheel_cli-0.1.0-py3-none-any.whl
.release-proof\Scripts\flywheel --version
.release-proof\Scripts\python -m ai_flywheel_cli --version
.release-proof\Scripts\flywheel doctor .
.release-proof\Scripts\flywheel status .
.release-proof\Scripts\flywheel validate .
```

Then inspect both files under `dist/` and confirm:

- the wheel and source distribution contain only expected package and metadata files
- repository-only content such as `.flywheel`, tests, tools, local environments, caches, and Git metadata is absent
- the installed version reports `0.1.0`
- the working tree contains no uncommitted release changes

The `.release-proof` environment is disposable and must not be committed.

## Release approval boundary

The local checklist establishes technical readiness only. The following actions require separate, explicit human approval and are not performed automatically:

- creating or pushing a version tag
- creating a GitHub release
- uploading artifacts to GitHub or a package index
- publishing release notes
- enabling hosted release automation or GitHub Actions

## License

MIT
