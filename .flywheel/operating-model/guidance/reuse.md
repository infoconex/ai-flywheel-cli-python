# Reuse

This document is normative. `MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, and `SHALL NOT` define mandatory behavior.

Reuse evaluates validated execution learning and existing validated knowledge for safe future application. Reuse does not make unvalidated material authoritative.

## Activation

Reuse MUST NOT begin until Persist is `completed`, the persistence plan is terminal with `status: applied`, final whole-set verification passed, all durable references resolve, and no persistence blocker remains.

Before Reuse becomes `in-progress`, every material candidate learning item and every existing knowledge item considered for the execution MUST have a durable planned structured assessment conforming to `reuse-assessment.schema.yaml`. Those planned assessments MUST be created and verified by the transaction whose commit activates Reuse, and the Reuse stage MUST reference their stable IDs.

A planned assessment has no final disposition, rationale, assessed timestamp, or assessor. Its subject, execution, mission, goal, and adaptation scope are fixed at creation.

## Assessment scope

Each assessment MUST identify exactly one subject:

- A `candidate-learning` classification from the execution.
- An `existing-knowledge` artifact considered for the current or future work.

The completed assessment MUST record evidence and validation provenance, applicability, limitations, conflicts, duplicates, approval requirements, decision references, and a final disposition.

## Candidate-learning dispositions

A candidate-learning assessment uses one of:

- `promote`: Create a new validated knowledge artifact.
- `supersede`: Create a new validated knowledge artifact that references every prior knowledge item it replaces.
- `defer`: Preserve the candidate without promotion because validation, applicability, approval, or evidence is incomplete.
- `reject`: Record why the candidate is unsafe, unsupported, duplicate without value, or otherwise unsuitable.
- `not-reusable`: Record that the learning is execution-specific and should not be promoted.

`promote` and `supersede` require:

- A confirmed `validated-learning` classification.
- At least one validation reference whose final applicable result passed.
- Evidence references supporting the knowledge statement.
- Explicit applicability and limitations.
- Actionable reuse guidance.
- No unresolved conflict or duplicate.
- Required approval and decision references when the guidance is material, risk-bearing, governance-changing, destructive, or scope-expanding.

An observation, evaluation, finding, failed validation, rejected adaptation, or provisional classification MUST NOT be promoted directly.

## Existing-knowledge dispositions

An existing-knowledge assessment uses one of:

- `reused`: The item was applicable and informed the execution or a future instruction.
- `inapplicable`: The item was considered but its applicability conditions were not met.
- `revision-required`: New evidence conflicts with or materially narrows the item and a superseding candidate is required.
- `deprecated`: The item must no longer be used; deprecation requires a decision and approval when material.
- `not-considered`: Permitted only when the item was discovered after the relevant decision point or a concrete reason proves it could not materially apply.

Existing validated knowledge MUST NOT be reused outside its recorded applicability or contrary to its limitations.

## Duplicate, conflict, and supersession rules

Before promotion, search canonical knowledge for semantic duplicates and conflicts.

- A duplicate without material improvement MUST be rejected or linked as existing knowledge; it MUST NOT create a new knowledge identity.
- A materially improved replacement MUST use `supersede` and list every replaced knowledge ID.
- A conflict MUST be resolved by rejection, deferral, deprecation, or an approved superseding item. Conflicting validated items MUST NOT remain simultaneously active without an explicit scope distinction.
- Existing knowledge is immutable. Revisions use a new identity and `supersedes` linkage.

## Knowledge artifact requirements

A promoted knowledge artifact MUST conform to `knowledge.schema.yaml` and include:

- Stable identity and `status: validated`.
- Statement, applicability, limitations, and actionable reuse guidance.
- Evidence and validation references.
- Origin mission, goal, execution, classification, and reuse-assessment references.
- Validation timestamp and validating authority.
- Approval and decision references when required.
- Superseded knowledge references when applicable.

## Assessment lifecycle

A reuse assessment is created once as `planned`, updated through retained-SHA compare-and-swap to `completed`, and immutable after completion.

The update from planned to completed MUST preserve the assessment ID, mission, goal, execution, subject type, subject reference, and adaptation references. It supplies the final disposition, provenance, applicability, limitations, guidance, duplicate and conflict results, proposed knowledge reference, approvals, decision, rationale, timestamp, and assessor.

A stale assessment SHA, changed fixed field, second completion, or attempted completed-to-planned transition MUST be rejected. A later correction requires a new assessment identity with explicit linkage in rationale and governing records.

## Reuse output durability

Reuse assessments and promoted knowledge are not durable merely because they were evaluated in memory.

Before Reuse completes, the operator MUST create and apply a dedicated persistence plan using `persistence-plan.schema.yaml`. That plan MUST be referenced by the Reuse stage and MUST include every new or changed Reuse output:

- CAS updates of every required planned reuse assessment to `completed` under the canonical goal `reuse/` directory.
- New knowledge artifacts under the canonical knowledge root.
- Required decisions and approvals.
- Goal and mission updates when their terminal values change.
- The execution update containing final assessment references, synchronized adaptation reuse statuses, Reuse completion, outcome, completion disposition, and completion timestamp when applicable.
- The state update as the final operational pointer.

The Reuse persistence transaction follows every rule in `persistence.md`. Its canonical type order inserts `reuse-assessment` after approvals and before knowledge. Planned assessments use retained-SHA CAS updates; completed assessments and knowledge are immutable. Goal, mission, execution, and state use retained-SHA compare-and-swap when modeled as existing durable artifacts. State is written last. The transaction plan remains its own controller and is excluded from its own targets and write order.

The governed target content MAY contain the proposed completed Reuse stage, terminal execution, completed goal and mission, and cleared terminal state. While the plan is `planned` or `applying`, those values are transaction-pending and MUST NOT be reported as durable completion. The terminal `applied` plan revision is the commit marker that makes the verified Reuse outputs and lifecycle closure authoritative together.

Reuse MUST NOT report completion until the dedicated plan is terminal `applied`, final whole-set verification passed, and the final governed set was re-read and verified. Partial Reuse persistence uses the same rollback, compensation, blocking, transaction-pending, and human-reconciliation rules as any other persistence transaction.

## Adaptation synchronization

`REUSE-SYNC-001`:

- An adaptation uses `reuse_status: reusable` only when at least one completed assessment links to it and results in `promote`, `supersede`, or `reused`.
- An adaptation uses `reuse_status: not-reusable` when every completed linked assessment results in `reject`, `not-reusable`, `inapplicable`, `defer`, or `revision-required` without a completed promotion.
- `reuse_status: not-assessed` blocks Reuse completion for an adaptation with validated learning or material reuse implications.

## Completion

Reuse may complete only when:

- At least one structured assessment exists, or the stage is `not-applicable` with a concrete reason proving no candidate or existing knowledge required assessment.
- Every required assessment is durably `completed` and has a final disposition.
- Every reference resolves.
- Every promotion or supersession has a schema-valid knowledge artifact at its canonical path.
- Duplicate, conflict, approval, and supersession rules pass.
- Adaptation reuse statuses agree with assessments.
- The dedicated Reuse persistence plan is terminal `applied` with passed final verification.
- The Reuse stage has references, summary, and timestamps.

The applied Reuse plan commit marker may make Reuse completion, terminal execution completion, goal and mission completion, and terminal state cleanup authoritative together. No redundant follow-up lifecycle update is required when those exact values were included in the verified governed set.

## Required semantic rules

- `REUSE-ACTIVATE-001`: Reuse requires completed, verified Persist and durable planned assessments for every required subject.
- `REUSE-ASSESS-001`: Every material candidate and considered existing knowledge item has one stable planned-to-completed assessment lifecycle.
- `REUSE-ASSESS-CAS-001`: Planned assessments complete only through retained-SHA CAS; completed assessments are immutable.
- `REUSE-PROMOTE-001`: Promotion requires validated learning, passed validation provenance, evidence, applicability, limitations, and reuse guidance.
- `REUSE-DIRECT-001`: Observations and other unqualified records cannot be promoted directly.
- `REUSE-DUPLICATE-001`: Unresolved duplicates cannot create new knowledge.
- `REUSE-CONFLICT-001`: Unresolved conflicting knowledge cannot be promoted or reused.
- `REUSE-SUPERSEDE-001`: Revisions use new identities and explicit supersedes linkage.
- `REUSE-APPROVAL-001`: Material or risk-bearing knowledge requires the applicable decision and approval.
- `REUSE-EXISTING-001`: Existing knowledge use or rejection is recorded with applicability reasoning.
- `REUSE-DURABILITY-001`: Reuse outputs and final lifecycle updates become authoritative together through the dedicated applied plan commit marker.
- `REUSE-SYNC-001`: Adaptation reuse status agrees with completed assessments.
- `REUSE-COMPLETE-001`: Reuse completes only when every required assessment and knowledge artifact passes validation and the Reuse persistence transaction is verified.
- `REUSE-HISTORY-001`: Completed assessment and knowledge history is immutable and preserved.