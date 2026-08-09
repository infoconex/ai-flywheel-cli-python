# AI Flywheel CLI for Python

A cross-platform command-line application for inspecting, validating, and safely operating AI Flywheel artifacts in a repository.

## Requirements

- Python 3.11 or newer
- A local repository directory
- A compatible AI Flywheel framework installed by the official framework installer

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

## Quick install by shell

PowerShell example:

```powershell
PS> python -m venv .venv
PS> .\.venv\Scripts\Activate.ps1
PS> python -m pip install --upgrade pip
PS> python -m pip install -e ".[dev]"
PS> flywheel --version
PS> flywheel doctor . --json
```

Bash example:

```bash
$ python -m venv .venv
$ source .venv/bin/activate
$ python -m pip install --upgrade pip
$ python -m pip install -e '.[dev]'
$ flywheel --version
$ flywheel doctor . --json
```

If `flywheel` is not yet on `PATH`, use the module entrypoint instead:

```text
python -m ai_flywheel_cli --version
python -m ai_flywheel_cli doctor . --json
```

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

Validation failures return Flywheel exit code `3` with structured `category` and `reason` fields in JSON output.

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

### Framework installation

The Python CLI does not install or upgrade `.flywheel`. Framework installation is
owned by the published AI Flywheel Framework installer. On Windows, use the
repository bootstrap to ensure framework `2026.08.08` is present before preparing
the managed Python CLI:

```powershell
.\scripts\install-ai-flywheel.ps1
```

The bootstrap invokes the official framework installer when `.flywheel` is absent,
leaves a compatible installation intact, and stops without overwriting older,
newer, malformed, legacy, or untracked installations.

## Exit code contract

- `0`: command completed successfully (including read-only planning paths)
- `1`: process-level runtime abort outside normal Flywheel error handling (platform-dependent)
- `2`: Typer/Click usage error for invalid command syntax or argument usage

Flywheel-defined failures are sequential and single-purpose:

- `3`: validation failure (`category=validation-failure`, `reason=repository-validation-errors`)
- `4`: repository conflict (`category=repository-conflict`, `reason=repository-content-conflict`)
- `5`: operation lock contention (`category=lock-contention`, `reason=repository-lock-active`)
- `6`: governed AI fallback required (`category=ai-fallback-required`, `reason=governed-ai-step-required`)
- `7`: other expected operation failure (`category=operation-failed`, `reason=mutation-rejected` or `operation-error`)
- `8`: framework absent or incompatible during `doctor`

For automation, rely on the numeric exit code for coarse control flow and use structured JSON `category` and `reason` fields for stable, finer-grained branching.

Runtime and shell statuses observed outside explicit Flywheel exits (for example signal termination or shell-specific interruption codes) are platform-dependent and should not be treated as part of the Flywheel-defined contract.

## Framework installation metadata

Successful official framework installation writes:

```text
.flywheel/installation.yaml
```

The framework installer owns this metadata. The CLI reads `framework_version` only
to determine compatibility; it does not regenerate or independently prove the
installer's checksum and provenance contract.

## Safety model

- Framework installation and archive safety remain owned by the official framework installer
- No Python-side extraction, checksum verification, provenance generation, or `.flywheel` publication
- No automatic framework upgrade until the framework publishes an upgrade contract
- Atomic lock-file acquisition under `.flywheel/.runtime`
- No automatic deletion of ambiguous stale locks
- No GitHub Actions or other hosted execution without separate approval

## Runtime files

`.flywheel/.runtime/` contains temporary locks, staging information, and local build output. It must not be committed.

## Current limitations

- Offline release bundles and standalone executable distribution remain deferred.
- The CLI currently supports framework `2026.08.08` exactly.
- Automatic framework upgrade remains deferred until an official framework upgrade contract is published.
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
.release-proof\Scripts\flywheel --help
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
