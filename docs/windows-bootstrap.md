# Windows Python Bootstrap Contract

## Purpose

The Windows bootstrap ensures a compatible published AI Flywheel framework is
present, configures an isolated Python CLI, and verifies runtime health. It never
starts onboarding or lifecycle work.

Dependency direction is:

```text
AI Flywheel Specification
          ↓
AI Flywheel Framework
          ↓
Python runtime implementation
```

## Responsibility boundary

- **AI Flywheel framework installer** owns release acquisition, checksum
  verification, archive safety, provenance, staging, atomic `.flywheel`
  publication, rollback, and refusal to overwrite.
- **Windows Python bootstrap** detects framework compatibility, invokes the official
  installer only when the framework is absent, prepares Python and the managed CLI,
  and runs health checks.
- **Python CLI** validates and operates an installed framework. It does not install,
  extract, checksum, publish, or upgrade framework artifacts.

The supported framework identity for this milestone is:

```text
Framework version: 2026.08.08
Release tag: v2026.08.08
Package: ai-flywheel-framework-2026.08.08.zip
Checksum asset: ai-flywheel-framework-2026.08.08.zip.sha256
Installer commit: fe11b801b5dfeef812377a978558fd563b67fa9e
Default CLI source commit: 2d84294cbe9922ec907fe718e9dd06e9944e0ebc
```

## Invocation

```powershell
.\scripts\install-ai-flywheel.ps1
```

Supported inputs:

- `-Repository <path>`: target Git repository or a path inside it.
- `-CliRef <branch|tag|commit>`: CLI source ref; the normal default is immutable.
- `-CliPath <path>`: local CLI source/package for development testing.
- `-NonInteractive`: disables prompts.
- `-Apply`: required with `-NonInteractive` when framework installation is needed.
- `-ValidateOnly`: checks an existing installation without installing one.
- Common `-WhatIf` and `-Confirm` semantics are passed to the official installer.

Framework source parameters are intentionally absent. The Python bootstrap cannot
select a local framework, development ref, archive, checksum, or source identity.

## Setup sequence

1. Resolve the Git root and report repository/Git-operation conditions.
2. Classify the existing framework without mutation.
3. If absent, download and invoke the official installer pinned to
   `fe11b801b5dfeef812377a978558fd563b67fa9e`.
4. Re-detect the framework. Cancellation or unsuccessful installation stops before
   Python setup.
5. Reject older, newer, malformed, inconsistent, legacy, or untracked frameworks
   without overwriting them.
6. Detect Python 3.11+ and offer explicit `winget` remediation when appropriate.
7. Create or reuse a managed CLI environment under
   `%LOCALAPPDATA%\AI-Flywheel\environments`.
8. Run `flywheel doctor`, which verifies CLI version, framework identity,
   compatibility, and repository validation.
9. Stop without invoking onboarding or lifecycle commands.

## Framework compatibility

The classifier reports one of:

- `not-installed`
- `compatible`
- `older-unsupported`
- `newer-unsupported`
- `untracked-or-legacy`
- `malformed`
- `invalid`

It reads `.flywheel/installation.yaml` `framework_version` and
`.flywheel/manifest.yaml` `framework.version`. These values must agree and equal
`2026.08.08`.

Compatibility detection does not recompute installer-owned checksums or regenerate
provenance. A compatible framework is left intact. Existing incompatible content is
never routed through the initial installer because that installer correctly refuses
to overwrite `.flywheel`.

No automatic upgrade path is offered until the framework publishes an official
upgrade contract.

## CLI health contract

`flywheel doctor <repository> --json` reports:

- CLI version;
- supported framework version;
- installed framework version;
- compatibility status and reason;
- repository validation status and issues;
- overall status.

It exits successfully only when the framework is compatible and repository
validation passes. Framework incompatibility and validation failure have distinct
exit codes.

The CLI no longer exposes `flywheel install` or `flywheel upgrade`. Repository
locking remains available to lifecycle and persistence operations.

## Diagnostics

Expected operational conditions use concise messages and remediation, including:

- installation cancellation;
- missing framework in validation-only mode;
- older or newer unsupported framework;
- missing provenance;
- malformed or inconsistent framework identity;
- missing non-interactive `-Apply` authority.

Unexpected exceptions retain exception type, message, source location, failing
statement, stack trace, inner exceptions, native-command output, and diagnostic-log
locations.

## Storage and safety

Managed Python assets remain outside the target repository:

```text
%LOCALAPPDATA%\AI-Flywheel\
├── cache\cli\
├── environments\
└── logs\
```

Temporary CLI-source extraction occurs under `%TEMP%\AIFW\<run-id>` and is
removed after the run. The bootstrap never commits, pushes, merges, changes
application source, enables application missions, or begins lifecycle execution.

## Validation

The full gate includes:

```powershell
.\tools\validate-powershell.ps1
.\tools\test-install-launcher.ps1
.\tools\test-windows-bootstrap.ps1
```

Regression coverage verifies compatibility classifications, immutable official
installer identity, framework-before-Python ordering, preservation of compatible
framework files, absence of Python-owned framework installation logic, CLI source
archive safety, and removal of lifecycle invocation from bootstrap. Python tests
cover the same compatibility policy and deterministic `doctor` output.
