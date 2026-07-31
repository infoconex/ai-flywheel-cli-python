# Broken Active Reference Recovery

This document is normative. It defines deterministic startup handling when state or another authoritative operating artifact contains a reference that does not resolve exactly once to the required canonical artifact.

## Purpose

A broken active reference is an authority failure. The operator cannot safely create or resume an execution, inspect the target repository, or choose a replacement based on recency, filename similarity, chat history, or convenience.

## Reference resolution rule

Every active reference MUST resolve from its exact source field to exactly one regular file at the canonical path derived from the referenced identifier.

Resolution cardinality is:

- `zero`: the canonical target is missing.
- `one`: exactly one canonical target exists and its internal identity agrees.
- `multiple`: duplicate, case-colliding, or noncanonical candidates make the target ambiguous.

Only `one` permits startup to continue.

## Deterministic rule identifiers

- `STARTUP-REFERENCE-RESOLUTION-001`: every active mission, goal, execution, and active-stage record reference must resolve exactly once at its canonical path.
- `STARTUP-REFERENCE-IDENTITY-001`: the resolved artifact identity and reciprocal mission, goal, and execution identifiers must agree with the source reference.
- `STARTUP-REFERENCE-AMBIGUITY-001`: zero or multiple candidates, case-only collisions, or noncanonical candidates prohibit inferred selection.
- `STARTUP-REFERENCE-BOUNDARY-001`: a broken active reference before the execution boundary prohibits execution creation, execution resume, repository inspection, and goal-directed work.
- `STARTUP-REFERENCE-EVIDENCE-001`: the startup-failure record must preserve the source artifact and field, referenced identifier, expected canonical path, resolution cardinality, observed candidate paths, and deterministic reconciliation action.
- `STARTUP-REFERENCE-STATE-001`: state may be changed to blocked only through retained-revision compare-and-swap without changing any active reference.

## Required startup result

When an active reference does not resolve exactly once:

- Operating Validation MUST be `failed`.
- Repository Validation MUST remain `pending`.
- Implementation Validation MUST remain `not-applicable`.
- No execution may be created or resumed.
- No target-repository content may be inspected.
- No candidate may be selected automatically.
- No active reference may be rewritten during failure recording.
- The exact source field, referenced identifier, expected canonical path, and all observed candidates MUST be reported.

## Structured startup-failure evidence

A startup-failure record for a broken active reference MUST include `reference_failure` with:

- `source_artifact_path`
- `source_field`
- `reference_type`
- `referenced_id`
- `expected_canonical_path`
- `resolution_cardinality`
- `observed_candidate_paths`
- `identity_mismatches`
- `selection_prohibited: true`

For cardinality `zero`, `observed_candidate_paths` MUST be empty. For cardinality `multiple`, at least two candidates MUST be recorded. For cardinality `one`, the failure must be an identity or reciprocal-reference mismatch and `identity_mismatches` MUST be nonempty.

## Deterministic recovery action

For a zero-cardinality active reference:

`Restore the exact referenced artifact at its canonical path from an authorized, reviewed revision or obtain an authorized reconciliation that updates the source reference, then restart startup validation from the manifest.`

For ambiguous or mismatched references:

`Obtain an authorized reconciliation that identifies the single canonical artifact and preserves conflicting evidence, then restart startup validation from the manifest.`

The operator MUST NOT decide which candidate is intended.

## Optional blocked-state update

State MAY be changed to `status: blocked` only when its retained revision remains current and the broken reference directly prevents active work. The update MUST preserve `active_mission`, `active_goal`, `active_execution`, and `lifecycle_stage` exactly as observed, add a blocker naming the startup-failure record and broken source field, and use compare-and-swap.

If the observed state is itself schema-invalid, or preserving its active references would produce a schema-invalid blocked state, leave state unchanged and report the startup failure.

## Completion and retry

Persisting the startup-failure record is evidence, not reconciliation. After authorized correction, startup MUST restart from the manifest and repeat all required-file, schema, canonical-path, uniqueness, identity, reciprocal-reference, and execution-boundary checks. Historical failure records remain immutable.