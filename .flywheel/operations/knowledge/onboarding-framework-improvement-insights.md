# Onboarding Framework Improvement Insights

## Purpose

This document captures framework-level lessons discovered while onboarding and operating `Infoconex/ai-flywheel-cli-python`. It is intended for later use when improving the AI Flywheel framework. These are observations and recommendations only; no framework changes are made by this document.

## Summary

The onboarding and deterministic-operations missions worked, but they exposed several places where the framework should provide stronger contracts for repositories that build, distribute, or embed Flywheel tooling. The most important improvements are:

1. Clarify that onboarding may resolve implementation-policy decisions without performing implementation.
2. Define how generated artifacts must be executed and validated after creation.
3. Support human delegation of recommended onboarding decisions.
4. Separate recommendation origin from human approval in provenance.
5. Make answer, evidence, configuration, and multi-artifact mutation persistence atomic and recoverable.
6. Introduce a dedicated implementation decision register.
7. Expand conditional onboarding for tool-producing repositories.
8. Define a practical stopping rule for onboarding.
9. Add explicit mission and goal communication checkpoints.
10. Define ownership boundaries between framework-owned and repository-specific files.
11. Record the exact framework revision installed in each repository.
12. Add deterministic framework drift detection and bounded synchronization.
13. Preserve repository-specific state during framework upgrades.
14. Keep deterministic tooling optional and evidence-driven.

## 1. Clarify onboarding as decision discovery

When the target repository implements or distributes Flywheel tooling, onboarding should resolve the operating, packaging, safety, upgrade, execution, and validation policies required to create implementation goals. It should not implement those decisions during onboarding.

The framework should clearly distinguish:

- describing future implementation requirements;
- creating implementation goals;
- generating code or scaffolding;
- executing generated code as validation.

## 2. Add a generated-artifact execution contract

The framework should distinguish configuration that describes future implementation from code or scaffolding created by a later goal and the execution required to prove that generated content works.

Recommended model:

```yaml
generated_artifacts:
  must_be_executable: true
  post_creation_validation_required: true
  completion_command: python -m tools validate
```

A goal that creates generated artifacts should execute the configured validation command before completion. File creation alone is not sufficient evidence.

## 3. Support recommended-default delegation

The human may authorize the operator to select remaining recommended answers within a defined scope. The framework should model that delegation explicitly rather than recording each later choice as though the human directly supplied it.

Recommended model:

```yaml
decision_delegation:
  scope: remaining-onboarding-decisions
  authority: recommend-and-select
  constraints:
    - do not cross existing approval boundaries
    - do not enable hosted services
    - persist rationale and provenance
    - surface high-impact or irreversible decisions
```

Delegation should never authorize actions outside established governance.

## 4. Expand provenance semantics

The framework should distinguish where a value came from from how it was approved.

Recommended model:

```yaml
origin: recommended
approval:
  method: delegated
  status: approved
  evidence_ref: EVIDENCE-...
```

Possible origin values include discovered, provided, inferred, defaulted, and recommended. Approval should be represented independently as not-required, pending, explicitly-approved, delegated-approved, rejected, or deferred.

## 5. Define atomic persistence and mutation safety

Onboarding and later deterministic operations both exposed the need for a shared persistence contract. Evidence creation, configuration updates, state changes, execution creation, and lifecycle transitions may span multiple artifacts.

The framework should require a deterministic transaction:

1. Read the current source revisions.
2. Reserve or validate identifiers.
3. Stage every intended artifact change.
4. Validate the staged repository as a complete proposed state.
5. Confirm source revisions are still current.
6. Replace canonical files atomically where possible.
7. Roll back every touched artifact after an interrupted write.
8. Surface rollback failure as a manual-recovery-required condition.
9. Mark the transition complete only after all writes and references validate.

The framework should define duplicate identifier, sequence gap, stale-source, retry, replay, and partial-write behavior.

## 6. Add an implementation decision register

`flywheel-context.yaml` can become a mixture of resolved configuration, operational policy, dependency choices, implementation decisions, rationale, and notes.

A dedicated register would preserve decision history without overloading configuration.

Recommended path:

```text
.flywheel/operating-model/config/implementation-decisions.yaml
```

The context file should hold resolved values. The decision register should hold why they were selected, under what authority, and with what consequences.

## 7. Expand onboarding for tool-producing repositories

When repository evidence identifies a project as tooling, an installer, generator, validator, framework, or distribution system, onboarding should conditionally cover:

### Distribution and installation

- release source and version selection;
- checksum verification;
- package-manager and installer behavior;
- offline expectations;
- existing-installation behavior.

### Safety and recovery

- approval before writes;
- transactional installation;
- rollback behavior;
- archive extraction security;
- path traversal prevention;
- timeout and retry policy.

### Upgrade behavior

- framework-owned file identification;
- per-file installation checksums;
- local modification detection;
- conflict handling;
- compatibility and migrations.

### Concurrency and runtime state

- repository-level locking;
- stale-lock recovery;
- staging locations;
- version-control exclusions.

### Interface contracts

- human-readable output;
- structured output such as `--json`;
- stable exit codes;
- diagnostics and secret redaction.

### Validation and release discipline

- unit, integration, and fixture-based tests;
- generated-artifact execution;
- local versus hosted validation;
- release archives, checksums, and release notes.

## 8. Define when onboarding stops

Recommended stopping rule:

> Stop onboarding when enough confirmed context and decisions exist to define coherent implementation goals with testable acceptance criteria. Do not continue selecting low-level design details that can safely be decided and validated within an implementation goal.

Onboarding should continue only when a missing decision would materially change goal boundaries, approval requirements, architecture direction, installation or upgrade safety, evidence requirements, or compatibility expectations.

## 9. Add mission and goal communication checkpoints

The framework should require explicit communication at three points.

### Mission kickoff

Before the first goal starts, state the mission purpose, expected outcome, ordered goals, approval boundaries, dependencies, and likely human-input points. Ask for adjustments before execution begins.

### Goal kickoff

Before each goal starts, state its identifier, title, purpose, expected outcome, acceptance criteria, boundaries, and known human inputs or approvals.

### Goal completion summary

When a goal completes, summarize the disposition, changes, acceptance-criteria results, findings, adaptations, limitations, evidence, validation, mission impact, and next goal.

Lifecycle transitions and progress updates should not create unnecessary conversational pauses. Once a goal is approved, execution should continue until completion or a real stop condition is reached.

## 10. Define framework-owned and repository-specific ownership

Embedded `.flywheel` installations need a formal ownership contract. Without it, operators cannot reliably determine which files should track the framework distribution and which files belong uniquely to the installed repository.

The framework should classify paths or individual files as:

- framework-owned canonical content;
- repository-specific configuration;
- mutable operating state;
- mission, execution, evidence, approval, and knowledge records;
- implementation-specific artifacts;
- locally extendable framework content.

The ownership declaration should be machine-readable and versioned. A synchronization or upgrade operation must not infer ownership only from directory location.

## 11. Record the installed framework revision

An installed repository should durably record the exact framework source used to create or last synchronize its canonical operating model.

Recommended metadata:

```yaml
framework_source:
  repository: Infoconex/ai-flywheel-framework
  revision: 351f85c9a10a559edfc694904163d435eceae0af
  synchronized_at: "2026-08-01T19:14:00Z"
```

A release tag may be recorded in addition to the immutable commit, but it should not replace the commit identity.

## 12. Add deterministic drift detection and bounded synchronization

The CLI repository had canonical guidance that differed from the framework repository even though both declared the same development version. Manual comparison found only two true canonical differences, while the manifest difference was repository-specific and expected.

The framework or CLI should provide a command that:

1. reads the recorded framework revision;
2. identifies framework-owned files;
3. compares expected and installed hashes;
4. classifies missing, changed, locally modified, and repository-specific files;
5. presents a plan before applying changes;
6. updates only approved framework-owned content;
7. preserves local and repository-specific artifacts;
8. validates the complete repository after synchronization;
9. records the new source revision and evidence.

A simple whole-directory copy is unsafe and should not be treated as synchronization.

## 13. Preserve repository-specific state during upgrades

Framework installation and synchronization must preserve:

- repository context;
- implementation declarations and implementation manifests;
- state and readiness;
- missions and goals;
- executions, evidence, approvals, decisions, and findings;
- validated knowledge;
- permitted local extensions.

Conflicts involving locally modified framework-owned files should be reported explicitly. The tool should never silently overwrite or silently retain them while claiming synchronization succeeded.

## 14. Keep deterministic tooling optional and evidence-driven

The programmatic-operations mission confirmed that AI is the operator and deterministic tooling is an optimization, not a conformance requirement.

The framework should state that:

- governed AI execution may fully conform without repository-specific automation;
- deterministic tools should be selected only for repeated, stable, validation-sensitive operations;
- unsupported operations remain valid governed AI work;
- capability claims must be limited to tested operations;
- movement across the determinism boundary requires operational evidence and human approval;
- a successful tool implementation does not justify broad automation of judgment-heavy work.

For this repository, the evidence supported deterministic execution start, lifecycle transition, and shared safe persistence. It did not support general mission design, goal decomposition, evidence interpretation, approval creation, or completion judgment.

## Recommended framework change set

The highest-value future framework work is:

1. Framework-owned versus repository-specific ownership declarations.
2. Installed framework revision metadata.
3. Drift detection and bounded synchronization contracts.
4. Atomic persistence, interruption recovery, retry, and replay rules.
5. Recommended-default delegation support.
6. Generated-artifact execution requirements.
7. Conditional onboarding for tool-producing repositories.
8. A dedicated implementation decision register.
9. Explicit onboarding stopping rules.
10. Mission kickoff, goal kickoff, and goal completion communication requirements.
11. Explicit optional and evidence-driven determinism-boundary guidance.

## What should remain repository-specific

The following choices should not become universal framework defaults:

- Python 3.11+;
- Typer;
- pytest;
- Ruff;
- mypy;
- `src/` layout;
- 80 percent coverage threshold;
- `python -m tools`;
- GitHub Release archives as the distribution source;
- `uv`, `pipx`, and managed virtual-environment installer behavior;
- the specific deterministic operations selected by this repository.

The framework should define how such decisions are discovered, approved, persisted, synchronized, and validated without prescribing their values.

## Intended follow-up

Use this document later to create a focused framework mission or goal set. Framework changes should be made on a new framework branch, validated independently, and not merged without human approval.
