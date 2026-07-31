# Persistence and Reuse

This document is normative. `MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, and `SHALL NOT` define mandatory behavior.

Persistence makes execution state, records, confirmed context, certification records, readiness validations, reuse assessments, selected knowledge, and lifecycle outcomes durable across sessions.

## Activation

Persist MUST NOT begin until Validate is completed or justified as not applicable, no required validation remains pending, every failed required validation has a finding, recovery action, and valid linked disposition, and adaptation validation statuses agree with results.

Only an accepted, non-superseded `accepted-risk` or `waived` disposition with `permits_persistence: true` may permit persistence after failed required validation. `retry-required` and `adaptation-required` block persistence.

Before any governed persistence transaction begins, the operator MUST construct and validate one persistence plan conforming to `persistence-plan.schema.yaml`. The plan is the transaction controller. It MUST NOT include itself in `targets` or `write_order`, and it has no self-digest.

The same transaction contract applies to checkpoint persistence during earlier lifecycle stages, the Persist-stage transaction, the dedicated Reuse output transaction required by `reuse.md`, and certification or readiness finalization.

## Checkpoint persistence

A lifecycle transition MUST use a checkpoint persistence plan whenever the proposed execution or state pair will reference a new or changed durable artifact that is not already verified at its canonical path.

A checkpoint target set includes every new or changed supporting evidence, decision, finding, approval, certification record, readiness validation, or other referenced record, followed by the execution and state transition targets. Supporting targets MUST be written and verified before the execution and state that reference them. The terminal `applied` checkpoint plan is the commit marker for that stage transition.

A checkpoint plan does not complete the lifecycle Persist stage, does not promote knowledge, and does not permit reuse claims. It only makes the current stage records and execution/state transition durable. When a transition changes only execution and state and introduces no new or changed external reference, the dual-artifact compare-and-swap sequence in `execution-model.md` may be used without a checkpoint plan.

The final Persist-stage transaction MUST still derive and verify the complete execution outcome. It MUST include every artifact that remains new or changed at Persist and MUST verify that all earlier checkpoint artifacts referenced by the execution exist unchanged at their canonical paths. An artifact already committed by a checkpoint is not recreated or added as an unchanged target merely to enlarge the final transaction.

## Failed-validation authorization precheck

Before constructing a plan that persists an execution containing failed required validation, the operator MUST:

1. Resolve the validation finding and recovery action.
2. Resolve exactly one governing accepted non-superseded decision linked to the validation.
3. Verify decision finding, scope, recovery, execution, goal, and mission agreement.
4. Verify the decision appears in execution `decision_refs`.
5. Resolve and verify required approvals and execution `approval_refs`.
6. Reject missing, ambiguous, stale, superseded, scope-mismatched, unapproved, or non-permitting dispositions.

Every governing decision and approval created or changed by the execution MUST appear in the target set that first makes it durable.

## Plan lifecycle

1. Construct the complete plan in memory with `status: planned`, all targets, digests, and exact write order.
2. Validate the plan and every proposed target.
3. Create the plan at its canonical path using create-only identity rules.
4. Re-read it and retain its blob SHA.
5. CAS-update it to `applying` before the first governed write.
6. Apply and verify targets in order.
7. After whole-set verification, CAS-update it to terminal `applied`, `failed`, `rolled-back`, or `blocked` with final verification and recovery state.
8. A terminal plan is immutable.

Plan control operations are mandatory but are excluded from governed targets and write order.

## Transaction commit marker

The persistence plan's terminal `applied` revision is the atomic commit marker for its governed target set.

A proposed execution, goal, mission, certification record, readiness validation, or state target MAY contain the lifecycle, approval, readiness, or completion values that will become authoritative when the transaction commits, including stage transitions, Persist completion, Reuse activation, Reuse completion, terminal execution completion, goal completion, mission completion, certification approval, readiness validation, and cleared terminal state pointers.

While the plan remains `planned` or `applying`, those written target values are transaction-pending and MUST NOT be reported, reused, or interpreted as durably authoritative outside transaction verification and recovery. Only after all governed targets pass whole-set verification and the plan is CAS-finalized to `applied` and re-read successfully do the proposed lifecycle and completion values become authoritative together.

If plan finalization fails after governed writes pass verification, the target set remains transaction-pending rather than completed. The operator MUST create a blocking finding, prohibit lifecycle continuation or reuse of the pending values, and require reconciliation. Recovery MUST either finalize the exact verified plan or roll back or compensate the governed targets according to this contract.

This commit-marker rule removes any requirement for a later lifecycle update whose only purpose would be to restate values already included in the verified governed set.

## Complete target derivation

The target set MUST include every new or changed durable artifact caused by the transaction:

- Evidence, decisions, findings, approvals, certification records, readiness validations, and reuse assessments.
- Knowledge when promotion or revision requirements are satisfied.
- The execution record.
- Goal, mission, state, repository context, or Flywheel context when values change.
- Every supporting artifact referenced by a changed durable artifact.

The transaction that commits Reuse activation MUST include every required planned reuse assessment as a create target before the execution and state targets that reference it. The later Reuse output transaction MUST include every planned-to-completed assessment as a CAS update target.

A certification-approval or readiness transaction MUST include the governing approval before the certification and readiness-validation updates, and those records before any terminal goal, mission, execution, or state update.

A referenced changed artifact MUST NOT be omitted. An unchanged artifact MUST NOT be added merely to enlarge the transaction. Every target has one canonical path, operation, mutability rule, precondition, proposed digest, dependencies, and recovery action.

## Digests and mutation semantics

Every target digest is SHA-256 lowercase hexadecimal over the exact UTF-8 bytes to be written after LF normalization and without a byte-order mark.

Evidence, decisions, findings, and approvals are create-only. A certification record is create-only at first persistence and CAS-mutable only through its allowed status transitions; a terminal certification record is immutable. A readiness validation is create-only at first persistence and CAS-mutable only from `pending` to `passed` or `failed`; a terminal readiness validation is immutable. A reuse assessment is create-only when first persisted as `planned`, CAS-mutable only from `planned` to `completed`, and immutable after completion. Knowledge is create-only for a new identity; revisions use a new identity with `supersedes`. Execution, goal, mission, state, and context use retained-SHA compare-and-swap. Create targets require confirmed absence. Update targets require retained complete content and blob SHA. Identity collisions use the next deterministic identity when permitted or block the transaction.

## Deterministic write order

Targets MUST be topologically ordered by dependencies and then by this type precedence:

1. Evidence.
2. Decisions.
3. Findings.
4. Approvals.
5. Certification records.
6. Readiness validations.
7. Reuse assessments.
8. Knowledge.
9. Context.
10. Goal.
11. Mission.
12. Execution.
13. State.

Within one type, order by target ID ascending. A target MUST NOT be written before its dependencies are durable and verified. Execution precedes state, and state is the final operational pointer.

## Pre-write validation

Before the first governed write, the operator MUST:

1. Resolve one stable operator identity and whole-second UTC transaction instant.
2. Complete failed-validation authorization prechecks when applicable.
3. Construct the complete proposed set in memory.
4. Validate every artifact against schema and semantic rules.
5. Validate paths, identities, dependencies, references, timestamps, and lifecycle invariants.
6. Retain complete content and blob SHA for every update target.
7. Confirm absence for every create target.
8. Create, verify, and CAS-activate the plan.
9. Re-read all target preconditions.
10. Reject the transaction without governed writes when any precondition is stale or any target is missing.

## Application and final verification

Apply targets in exact order. After each write, re-read and verify its digest before continuing.

After all writes, re-read the entire set and verify:

- Every create exists exactly once at its planned path.
- Every update equals proposed content.
- Every reference resolves.
- Failed-validation authorizations still govern the exact validation and scope.
- Certification and readiness records satisfy their scenario, evidence, approval, gate, and status rules when present.
- Reuse assessments satisfy their planned-to-completed lifecycle and knowledge satisfies `reuse.md` when present.
- State and execution agree on mission, goal, execution, status, and sole active stage or terminal state.
- No unplanned artifact changed.

Only after these checks pass may the plan become `applied` with final verification `passed`. A lifecycle stage, certification result, readiness result, or terminal outcome MUST NOT be reported as durably completed until plan finalization is re-read and verified, even when the governed target content already contains that proposed completion state.

## Partial-persistence recovery

On any write or verification failure:

1. Stop forward writes.
2. Preserve the failing result and current revisions.
3. Roll back mutable targets in reverse order using CAS and retained content.
4. Delete created records in reverse order only when unreferenced and transaction ownership of the current revision is proven.
5. Otherwise create a compensating finding prohibiting orphan use.
6. Re-read the affected set and verify restoration.
7. Persist a finding with plan, targets, preconditions, writes, failure, rollback or compensation, revisions, and recovery.
8. Mark the plan `rolled-back` when restoration is proven.
9. Mark it `blocked`, block state, and require human reconciliation when restoration cannot be proven.

Rollback MUST NOT overwrite concurrent changes. Failure to restore one target blocks further lifecycle work. Failure before plan activation permits no governed writes. Failure to finalize a plan after verified writes creates a blocking finding and requires reconciliation.

## Required semantic rules

- `PERSIST-PLAN-001`: Activation requires a schema-valid complete plan.
- `PERSIST-PLAN-SELF-001`: The plan is excluded from its targets and write order and has no self-digest.
- `PERSIST-PLAN-LIFECYCLE-001`: The plan is created before writes, CAS-updated while active, and immutable when terminal.
- `PERSIST-CHECKPOINT-001`: A transition that introduces new or changed external references uses a checkpoint plan that commits supporting records before execution and state.
- `PERSIST-COMMIT-001`: Terminal applied plan finalization is the commit marker that makes the verified governed target set authoritative together.
- `PERSIST-DIGEST-001`: Target digests use normalized UTF-8 SHA-256 lowercase hexadecimal.
- `PERSIST-VALIDATION-DISPOSITION-001`: Failed required validation has one governing authorized disposition.
- `PERSIST-TARGET-001`: Every new or changed durable artifact appears exactly once.
- `PERSIST-LOCATION-001`: Every target uses its canonical path.
- `PERSIST-MUTABILITY-001`: Create-only history is preserved and mutable artifacts use CAS.
- `PERSIST-CERTIFICATION-001`: Certification and readiness records use their dedicated schemas, allowed transitions, exact references, and approval-before-state ordering.
- `PERSIST-REUSE-ASSESSMENT-001`: Planned assessments are created before Reuse activation, completed through CAS during Reuse, and immutable thereafter.
- `PERSIST-ORDER-001`: Dependency and canonical type order are enforced; state is final.
- `PERSIST-PRECHECK-001`: Create absence and update SHAs are rechecked before writing.
- `PERSIST-VERIFY-001`: Every write and the whole set are re-read and verified.
- `PERSIST-ROLLBACK-001`: Partial persistence triggers reverse-order rollback or compensation.
- `PERSIST-PARTIAL-001`: Unrecoverable inconsistency blocks continuation and requires reconciliation.
- `PERSIST-HISTORY-001`: Execution, validation, record, certification, readiness, assessment, and knowledge history is preserved.
- `PERSIST-REUSE-001`: Persist MUST NOT claim Reuse outcomes; Reuse outputs require their own verified transaction.

## Persist completion

Persist may complete only when its plan is terminal `applied`, final verification passed, all required references and authorizations resolve, the stage has summary and timestamps, and no persistence blocker remains. The applied plan commit marker may make a governed execution/state pair containing Persist completion and Reuse activation authoritative without a redundant follow-up transition, provided every planned assessment referenced by Reuse was created and verified in the same transaction.

## Records, knowledge, and Reuse

Records preserve what happened in an execution. Certification records preserve scenario and approval status. Readiness validations preserve gate decisions. Reuse assessments record qualification and applicability decisions. Knowledge contains validated reusable information.

Do not promote observations directly. Promotion requires evidence, passed validation provenance, applicability, limitations, actionable guidance, origin references, duplicate and conflict resolution, and required approval. Existing knowledge is never silently overwritten.

At startup and goal planning, search validated knowledge and record whether it was reused, inapplicable, or exposed a revision need according to `reuse.md`.
