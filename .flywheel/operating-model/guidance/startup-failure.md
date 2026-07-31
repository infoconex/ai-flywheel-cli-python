# Startup Failure Persistence

This document is normative. It defines the only durable write permitted when Operating Validation fails before an execution can be created or resumed.

## Purpose

A startup-failure record preserves deterministic evidence that startup could not complete. It does not repair the defect, authorize goal-directed work, create an execution, or permit target-repository inspection.

## When a startup-failure record is permitted

A startup-failure record MAY be created only when all of the following are true:

- Startup has resolved the immutable repository revision and operator identity.
- Operating Validation has failed before the execution boundary.
- The failure prevents startup from completing or makes authority ambiguous.
- The failure can be described using observed durable repository facts without inventing missing content.
- The canonical startup-failure directory can be addressed safely.

A missing manifest-required file is a permitted startup-failure condition even when the missing file is itself a schema, guidance file, or configuration file.

## Required stop boundary

When a manifest-required file is missing:

- Operating Validation MUST be `failed`.
- Repository Validation MUST remain `pending`.
- Implementation Validation MUST remain `not-applicable`.
- No execution may be created or resumed.
- No goal-directed action may begin.
- No target-repository file may be inspected.
- The missing artifact MUST NOT be guessed, regenerated, copied from another revision, or replaced by an inferred substitute.
- The exact repository-root-relative missing path MUST be reported.

## Deterministic rule identifiers

Use these rule identifiers:

- `STARTUP-REQUIRED-FILE-001`: every path listed in `manifest.required_files` must resolve exactly once to a regular file.
- `STARTUP-FAILURE-BOUNDARY-001`: a startup failure before the execution boundary prohibits execution creation, execution resume, repository inspection, and goal-directed work.
- `STARTUP-FAILURE-RECORD-001`: a permitted startup failure may be persisted only as a create-only startup-failure record at the canonical location.
- `STARTUP-FAILURE-IDENTITY-001`: startup-failure identity and path follow the deterministic timestamp-and-counter rule.
- `STARTUP-FAILURE-EVIDENCE-001`: the record must identify the exact failed rules, exact affected artifact paths, observed evidence, and one deterministic recovery action.
- `STARTUP-FAILURE-STATE-001`: state may be changed to blocked only by retained-revision compare-and-swap when the startup failure directly prevents the active work represented by state.
- `STARTUP-FAILURE-DUPLICATE-001`: repeated observation of the same unresolved failure must not overwrite a prior record; create a new identity only when recording a materially new observation or changed repository revision.

## Identity and canonical path

Capture one whole-second UTC timestamp and select the lowest unused counter beginning at `001` for that second.

The identifier is:

`SF-YYYYMMDDTHHMMSSZ-NNN`

The canonical path is:

`.flywheel/operations/records/startup-failures/<startup-failure-id>.yaml`

The record is create-only. Confirm the path is absent immediately before creation. On collision, re-list and select the next lowest unused counter for the same timestamp. Counter exhaustion is a blocking failure and no record is written.

## Record construction

The record MUST validate against `startup-failure.schema.yaml` and contain:

- The exact immutable observed revision.
- The branch when known, otherwise null.
- The resolved operator identity.
- The captured whole-second UTC occurrence time.
- Every failed deterministic rule identifier.
- Every exact affected repository-root-relative artifact path.
- Evidence describing what was checked and what was absent or contradictory.
- One concrete recovery action that does not invent or silently repair the artifact.
- The orphaned execution identifier when startup created an execution before failure; otherwise null.

For a manifest-required file that is absent before execution creation, `orphaned_execution_id` MUST be null.

## Persistence

Startup-failure persistence is a startup action and does not require an active execution or goal-directed persistence plan. The operator MUST:

1. Construct and validate the complete record in memory.
2. Confirm the canonical target path is absent.
3. Create the record once.
4. Re-read it and verify exact content and schema validity.
5. Report whether persistence succeeded.

If record persistence fails, preserve the failure in the opening report and do not retry destructively or weaken the startup boundary.

## Optional blocked-state update

A state update is optional and separate from the startup-failure record creation.

State MAY be changed to `status: blocked` only when:

- The existing state revision is still current.
- The missing artifact directly prevents the active mission or goal represented by state from starting.
- The proposed state remains schema-valid.
- A blocker identifies the exact startup-failure record and missing path.
- The update uses retained-revision compare-and-swap.

If any condition is not provable, leave state unchanged and report the startup failure. A state update MUST NOT create an active execution or lifecycle stage.

## Recovery action

For a missing required operating file, the deterministic recovery action is:

`Restore the exact missing required artifact from an authorized, reviewed framework revision or perform an approved framework repair, then restart startup validation from the manifest.`

The operator MUST NOT choose the content or source revision without authority.

## Completion and retry

Startup remains failed after the record is written. The record is evidence, not resolution.

After an authorized correction, a new session MUST restart from the manifest, re-read all required files, revalidate state and references, and make a new execution decision. A prior startup-failure record is never edited or deleted to indicate recovery.
