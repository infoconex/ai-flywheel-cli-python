# AI Flywheel Python CLI Implementation Proposal

## Purpose

Implement a cross-platform Python command-line application that installs, validates, inspects, and safely upgrades the AI Flywheel operating model in empty or existing repositories. The repository will also serve as the proving example for building the CLI through the Flywheel lifecycle.

## Initial release scope

The first release provides these commands:

- `flywheel doctor`
- `flywheel install`
- `flywheel validate`
- `flywheel status`
- `flywheel upgrade`

Mission, goal, execution, and broader lifecycle-management commands remain deferred. The architecture must leave clear extension points for them without implementing them prematurely.

## Runtime and packaging

- Python 3.11 or newer.
- `pyproject.toml` as the authoritative project configuration.
- `src/` package layout.
- Console entry point named `flywheel`.
- Typer used only for argument parsing, help text, terminal interaction, and command dispatch.
- Core application and domain behavior remain independently testable without Typer.

Proposed package layout:

```text
src/
  ai_flywheel_cli/
    __init__.py
    __main__.py
    cli.py
    application/
      commands/
      services/
      ports/
    domain/
      models/
      policies/
      errors.py
    infrastructure/
      filesystem/
      github_releases/
      hashing/
      locking/
      archives/
      process/
    presentation/
      output.py
      json_output.py
      exit_codes.py
tests/
  unit/
  integration/
  fixtures/
tools/
  __init__.py
  __main__.py
```

## Architecture

Use a layered ports-and-adapters design suited to a CLI:

1. **Presentation layer**
   - Typer command definitions.
   - Human-readable terminal output.
   - Deterministic `--json` output.
   - Stable exit-code mapping.

2. **Application layer**
   - One application command handler per CLI operation.
   - Coordinates domain policies through explicit ports.
   - Owns transaction orchestration, approval checks, and command-level outcomes.

3. **Domain layer**
   - Framework version and compatibility rules.
   - Installation plans and ownership metadata.
   - Upgrade conflict detection.
   - Repository operation-lock policy.
   - Validation results and structured failure categories.
   - No filesystem, network, subprocess, or Typer dependencies.

4. **Infrastructure layer**
   - Filesystem and atomic file operations.
   - GitHub Release retrieval.
   - Checksum verification.
   - Safe archive inspection and extraction.
   - Repository locking and stale-lock inspection.
   - Process and environment detection.

Dependencies flow inward. Presentation and infrastructure depend on application/domain contracts; domain code does not depend on external frameworks.

## Command behavior

### `flywheel doctor`

Read-only diagnostics for Python runtime, installer availability, network access when required, repository accessibility, and common environmental constraints. It reports actionable remediation and supports `--json`.

### `flywheel install`

- Refuses when `.flywheel` already exists.
- Resolves the latest stable framework release unless `--version` is supplied.
- Downloads an immutable GitHub Release archive.
- Verifies the published archive checksum before extraction.
- Inspects archive paths and rejects unsafe content.
- Builds and displays a complete change plan.
- Requires interactive confirmation or explicit noninteractive `--yes`/`--apply`.
- Acquires the repository mutation lock.
- Stages all changes under `.flywheel/.runtime/`.
- Applies changes transactionally.
- Runs post-install validation.
- Rolls back to the original repository state on write or validation failure.
- Finalizes installation metadata only after success.

### `flywheel validate`

Read-only validation of installed structure, schemas, references, installation metadata, framework-owned file checksums, and compatibility. Returns structured validation findings and stable exit codes.

### `flywheel status`

Read-only summary of installed framework version, repository readiness, active mission/goal/execution pointers, detected conflicts, lock state, and upgrade availability when network access is explicitly requested or allowed.

### `flywheel upgrade`

- Requires an existing installation.
- Resolves the requested target release.
- Verifies archive checksum and safe contents.
- Uses installation metadata as the baseline for three-way conflict detection.
- Preserves locally modified framework-owned files and stops with a conflict report.
- Excludes mutable operational content from framework ownership conflicts.
- Acquires the repository mutation lock.
- Stages, applies, validates, and rolls back transactionally.
- Blocks unsupported major-version changes unless an explicit migration path exists.

## Repository mutation and recovery

Mutating operations use one repository-level lock stored beneath `.flywheel/.runtime/`. Lock acquisition must be atomic. Lock metadata includes operation ID, command, process ID when available, hostname, and start time.

Valid active locks cause a clear lock-contention result. Stale locks are reported conservatively and are not silently deleted. A later explicit recovery command or approved force-unlock workflow may be added.

Staging and rollback files live under `.flywheel/.runtime/`, which must be excluded from version control. Installation and upgrade are transactional from the user's perspective. Rollback failure is reported separately from the original failure.

## Installation metadata

Persist versioned metadata after successful installation or upgrade containing:

- Resolved framework version.
- Release archive checksum.
- Framework source/release identity.
- Per-file checksum for every framework-owned file.
- Metadata schema version.

Mutable state, missions, goals, executions, evidence, findings, approvals, and knowledge are excluded from the framework-owned checksum manifest.

## Configuration and compatibility

- Repository configuration is YAML.
- Configuration schemas are versioned.
- Unknown required semantics are rejected rather than guessed.
- CLI releases follow semantic versioning.
- Unsupported major framework upgrades are blocked.
- Breaking changes require explicit migration handling.

## Output and error contract

Default output is concise and human-readable. Every command supports deterministic structured JSON where automation benefits.

Stable exit categories cover:

- success
- validation failure
- usage error
- dependency/runtime failure
- repository conflict
- lock contention
- network failure
- internal failure

Exact numeric assignments will be defined once in a central module and tested as a public compatibility contract.

Verbose diagnostics are opt-in. Secrets, credentials, tokens, and sensitive headers must be redacted from output and logs. Persistent logs are written only when configured or required for recovery evidence.

## Network and security

- Bounded connection and read timeouts.
- Limited retries with backoff only for safe idempotent reads.
- No implicit retry of repository mutations.
- Reject path traversal, absolute archive paths, unsafe links, duplicate extraction destinations, and files absent from or inconsistent with the verified release manifest.
- Initial installation requires network access.
- Routine installed operations should work locally unless the invoked command explicitly needs an external service.

## Dependencies

Runtime dependencies should be kept small:

- Typer for CLI presentation.
- A YAML implementation appropriate for safe schema-backed configuration parsing.
- Standard-library facilities wherever practical for hashing, archives, filesystem operations, subprocesses, and networking, unless a narrowly scoped dependency materially improves correctness or portability.

Development dependencies:

- pytest
- pytest-cov / coverage.py
- Ruff
- mypy

Any additional runtime dependency requires explicit review against portability, maintenance, licensing, and security considerations.

## Testing strategy

- Unit tests for domain policies, application handlers, output mapping, path safety, conflict detection, and rollback planning.
- Integration tests for filesystem operations, repository locks, staged writes, rollback, CLI invocation, and installation metadata.
- Fixture-based end-to-end tests for empty repository installation, existing repository installation, refusal when `.flywheel` exists, validation, status, safe upgrade, local-modification conflicts, failed validation rollback, archive attacks, and lock contention.
- Minimum enforced coverage: 80 percent.

## Project task interface

Provide a cross-platform Python task runner invoked through `python -m tools` with:

- `test`
- `lint`
- `format`
- `typecheck`
- `coverage`
- `validate`

`python -m tools validate` runs all required checks and is the authoritative local validation command. The initial scaffold is incomplete until this command executes successfully.

## Documentation requirements

The first release includes:

- Installation and inspect-before-run instructions.
- Quick start.
- Command reference, options, exit behavior, and examples.
- Empty and existing repository workflows.
- Configuration reference.
- Upgrade and compatibility behavior.
- Troubleshooting, rollback, conflict, lock, and recovery guidance.
- Security and safe-operation notes.

## Release discipline

- Local validation is mandatory before release.
- Versioned release artifacts include checksums and release notes.
- GitHub Actions or other hosted execution is not enabled without separate human approval.
- One mission branch is used, with goal-scoped commits and one pull request at mission completion.

## Capability classification

### Required for this repository

- Read and validate Flywheel configuration.
- Associate work with active mission and goal records.
- Enforce approval and state boundaries in generated/installed content.
- Capture structured evidence and completion information through the installed framework.
- Cross-platform installation, validation, status, and upgrade safety.

### Selected for the initial release

- `doctor`
- `install`
- `validate`
- `status`
- `upgrade`
- Human-readable and JSON output.
- Transactional mutation, locking, checksums, and conflict detection.
- Local validation tooling and consumer documentation.

### Deferred

- Mission CRUD/list commands.
- Goal CRUD/list commands.
- Execution commands.
- Full eight-stage lifecycle assistance.
- Offline installation bundles.
- Standalone executable distribution.
- Hosted CI/CD execution.
- Explicit unlock/recovery command unless required by implementation findings.

### Rejected for the initial release

- Silent overwrite of an existing `.flywheel` installation.
- Silent overwrite of locally modified framework-owned files.
- Nontransactional repository mutation.
- Automatic removal of ambiguous stale locks.
- Implicit hosted-service dependency.

## Key tradeoffs and risks

- A ports-and-adapters structure introduces more modules than a script-oriented CLI, but it protects core behavior from Typer, filesystem, and network coupling and supports later lifecycle commands.
- Transactional cross-platform filesystem behavior is complex. Implementation goals must build and test it incrementally rather than treating it as one large feature.
- GitHub Release checksum publication is an external contract. The CLI must fail safely when the expected checksum asset or manifest is missing.
- File locking differs across platforms. The initial implementation should use atomic lock-file creation as the portable baseline rather than relying on platform-specific advisory locks.
- Schema and framework compatibility rules must remain explicit to avoid accidental upgrades that corrupt operational state.

## Proposed implementation sequence

1. Create package, task runner, quality configuration, and executable validation baseline.
2. Implement shared domain models, result/error contract, and output adapters.
3. Implement repository discovery and `doctor`.
4. Implement installed-structure validation and `status`.
5. Implement framework release resolution, download, checksum, and archive safety.
6. Implement operation locking, staging, transactional writes, and rollback.
7. Implement `install` end to end.
8. Implement installation metadata and upgrade conflict detection.
9. Implement `upgrade` end to end.
10. Complete consumer documentation, fixtures, release validation, and mission-level review.

## Approval boundary

This proposal authorizes implementation design only after explicit human approval is recorded. Approval does not authorize merging the mission branch or enabling hosted execution. Those remain separate approval boundaries.
