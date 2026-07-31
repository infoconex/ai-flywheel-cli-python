# Lifecycle Transition Recovery

This document is normative. `MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, and `SHALL NOT` define mandatory behavior.

This contract governs every non-initial lifecycle transition that changes an existing execution and `.flywheel/state.yaml`. It makes transition intent and recovery durable across operator and chat sessions.

## Normative relationship

The transition sequence in `execution-model.md`, the transaction rules in `persistence.md`, and the startup rules in `startup.md` remain authoritative except where this document provides a more specific lifecycle-transition recovery rule.

For repositories containing this document:

- The allowance in `persistence.md` for a direct execution/state compare-and-swap transition without a checkpoint plan is narrowed to mean a plan-governed transition whose only governed targets are execution and state.
- A transition plan is REQUIRED even when the transition introduces no external evidence, decision, finding, approval, or other record.
- A transition plan that contains only execution and state is not lifecycle checkpoint persistence and does not complete Persist.
- A transition that introduces new or changed external references remains a checkpoint transaction and includes those supporting targets before execution and state.

## Transition plan

Before the first governed write, the operator MUST construct a persistence plan conforming to `persistence-plan.schema.yaml` at the canonical `persistence/` path.

The transition plan MUST:

- Identify the active mission, goal, and execution.
- Use a deterministic `PERSIST-YYYYMMDDTHHMMSSZ-NNN` identity.
- Include the execution update and state update as targets.
- Include every new or changed supporting record when the proposed execution or state references it.
- Retain the current execution and state blob SHAs as update preconditions.
- Record the proposed normalized-content digest for every target.
- Record the retained execution and state content digests for exact rollback.
- Order supporting records before execution, execution before state, and state last.
- Be created, re-read, and compare-and-swap updated to `applying` before the first governed target write.

The plan's terminal `applied` revision is the commit marker for the transition. Proposed stage and state values remain transaction-pending until the plan is finalized to `applied`, re-read, and the complete governed set is verified.

## Application sequence

A plan-governed lifecycle transition MUST use this sequence:

1. Resolve one stable operator identity and one whole-second UTC transition instant.
2. Read and retain the complete current execution and state plus their blob SHAs.
3. Verify the current execution and state agree on mission, goal, execution identity, status, and sole active lifecycle stage.
4. Construct the complete proposed execution and state using the same transition instant.
5. Construct every new or changed supporting artifact required by the proposed pair.
6. Validate all proposed artifacts, references, lifecycle ordering, timestamps, semantic rules, paths, digests, and rollback data.
7. Create and verify the complete transition plan.
8. Compare-and-swap the plan from `planned` to `applying`.
9. Re-read every target precondition. If any is stale, perform no governed target write and finalize or reconcile the plan without applying the transition.
10. Write and verify supporting targets in plan order.
11. Update the execution using compare-and-swap against its retained SHA.
12. Re-read state and verify its retained SHA remains current.
13. Update state using compare-and-swap against its retained SHA.
14. Re-read and verify the entire governed target set equals the validated proposed set.
15. Compare-and-swap the plan to `applied` with final verification `passed`.
16. Re-read the terminal plan and governed target set.
17. Only then report the transition durable and begin successor-stage work.

A force update is prohibited. A lifecycle transition without a durable transition plan is prohibited.

## Startup discovery

During startup, the operator MUST inspect persistence plans for the active goal before treating a state/execution disagreement as an unexplained contradiction.

A nonterminal transition plan is a recovery authority only when all of the following are true:

- Exactly one `planned` or `applying` plan governs the active execution and the relevant execution and state paths.
- Its mission, goal, and execution identities match durable state and the execution path.
- Its targets, write order, preconditions, proposed digests, and rollback data are complete and schema-valid.
- Current artifact revisions can be matched deterministically to the retained preconditions or proposed target digests.
- No second nonterminal plan claims the same mutable target.

Chat history, prior-session memory, and an unpersisted proposed transition MUST NOT be used as recovery authority.

If no unique valid plan explains the current revisions, Operating Validation fails and human reconciliation is required.

## Deterministic partial-transition states

The following current states have deterministic handling.

### No governed target written

When the plan is `planned` or `applying` and every target still matches its retained precondition:

- Do not apply the transition from startup memory.
- Finalize the plan as `rolled-back` with recovery mode `not-started`, a null finding reference, no blocker, and final verification `passed`.
- Verify the original execution/state pair remains intact.
- Continue only after the terminal plan and original pair are re-read and no other blocker exists.

A no-target-written plan is not a partial transition and does not require a recovery finding.

### Execution written, state not written

This is the expected recoverable partial lifecycle transition when:

- The execution current content digest equals the plan's proposed execution digest.
- The execution current blob SHA differs from its retained precondition SHA.
- State still equals its retained precondition SHA and content.
- No concurrent target or plan ambiguity exists.

The operator MUST NOT retry the state update, even when state still has the retained SHA. Recovery MUST restore the exact retained execution content.

### State written, execution not written

This violates canonical write order. Do not attempt automatic forward completion or state rollback. Persist a blocking finding when safely possible and require human reconciliation.

### Both targets written but plan not applied

The values remain transaction-pending. Re-read and verify the complete target set. Finalize the exact plan to `applied` only when every governed target equals its proposed content, all references resolve, no target is stale, and final verification is reproducible. Otherwise apply rollback or human reconciliation.

### Applied plan with mismatched targets

Treat this as a blocking repository inconsistency. Do not normalize, reapply, or overwrite artifacts automatically.

## Exact execution rollback

For an execution-written/state-not-written failure:

1. Re-read the transition plan, execution, and state.
2. Verify the plan is still the unique nonterminal controller for both mutable targets.
3. Verify the execution current digest equals the planned proposed digest.
4. Verify state still equals the retained precondition revision and content.
5. Resolve the exact retained execution content from the retained blob SHA.
6. Verify its normalized digest equals `rollback.retained_content_digest` for the execution target.
7. Compare-and-swap the execution from its current post-write SHA back to the exact retained content.
8. Re-read execution and state and verify the original durable pair is restored.
9. Do not roll back state, because the failed transition did not establish ownership of a changed state revision.

If any verification fails, do not guess or overwrite. Recovery becomes blocked and requires human reconciliation.

## Recovery finding

Every partial transition MUST produce a create-only finding record with `kind: finding`, `finding.finding_type: partial-lifecycle-transition`, and a complete `finding.transition_recovery` object conforming to `record.schema.yaml`.

The structured recovery payload MUST record:

- `original_plan_id` and `original_plan_path`.
- `transition_operator`, `transition_at`, and recovery `observed_at`.
- One target entry for every governed target, including target identity, artifact type, path, operation, retained revision and digest when applicable, proposed digest, observed revision and digest, write result, and failure detail.
- A nonempty `failure_condition`.
- Structured rollback status including whether rollback was attempted, governed target identities, exact result, restored content digest when successful, whether state was mutated, and explanatory detail.
- Whether the original pair was restored.
- The lifecycle-continuation prohibition and its reason.
- The required recovery action.
- Whether human reconciliation is required.

The payload MUST contain at least one succeeded target write and at least one failed or not-attempted target write. A successful exact rollback MUST identify the restored digest and MUST record `state_mutated: false`. An unrestored original pair MUST prohibit continuation and require human reconciliation.

Schema validation is necessary but not sufficient. Semantic validation MUST also verify:

- The finding's top-level mission, goal, and execution identities agree with the original transition plan.
- `original_plan_id`, `original_plan_path`, and the finding's `source_refs` or `artifact_refs` resolve to the same canonical plan.
- Every recovery target maps exactly once to a target in the original plan.
- Target paths, operations, retained SHAs, retained digests, and proposed digests equal the original plan.
- Observed SHAs and digests equal the repository revisions used for recovery.
- Write results, failure condition, rollback result, restored-pair status, continuation disposition, and recovery action agree with the durable recovery trace.
- The finding is rejected when any required structured field is absent, null where prohibited, inconsistent, ambiguous, or not traceable to durable artifacts.

The finding MUST be persisted through a separate recovery persistence plan whose governed target is the new finding and any other recovery artifact that can be changed safely. The recovery plan MUST reference the original transition plan through the finding's `source_refs` or `artifact_refs`.

A recovery finding MUST NOT be inserted retroactively into the restored pre-transition execution unless a later authorized plan-governed transition adds that reference. The finding remains discoverable through the canonical goal record set and its `execution_id`.

## Plan finalization after recovery

When exact rollback succeeds:

1. Verify the original execution/state pair is restored.
2. Persist and verify the recovery finding under its recovery plan.
3. Compare-and-swap the original transition plan to `rolled-back` with recovery mode `exact-rollback`, the finding reference, no unresolved blocker, and final verification `passed`.
4. Re-read the finding, recovery plan, original transition plan, execution, and state.
5. Report the transition not applied.

When rollback fails or restoration cannot be proven:

1. Persist a blocking finding through a recovery plan when repository ownership permits the create-only write.
2. Compare-and-swap the original transition plan to `blocked` when its revision is still owned and the finding exists.
3. Perform no further lifecycle work.
4. Require human reconciliation.

If the recovery finding, recovery plan, or original-plan finalization cannot be made durable, leave the original plan non-applied, report the incomplete recovery, and require human reconciliation. Do not claim rollback completion from in-memory work.

## Continuation boundary

Lifecycle work may continue only when one of these conditions is durably proven:

- The transition plan is `applied`, final verification passed, and the execution/state pair equals the proposed pair.
- The transition plan is `rolled-back`, recovery mode is `not-started`, no governed target changed, and the execution/state pair equals the retained pre-transition pair.
- The transition plan is `rolled-back`, recovery mode is `exact-rollback`, the recovery finding is durable, and the execution/state pair equals the retained pre-transition pair.

A `planned`, `applying`, `failed`, or `blocked` transition plan prevents lifecycle continuation until reconciled. A terminal plan whose target set does not match its declared outcome also prevents continuation.

## Required semantic rules

- `TRANSITION-PLAN-001`: Every non-initial execution/state lifecycle transition has one durable persistence-plan controller before target writes.
- `TRANSITION-PLAN-UNIQUE-001`: No two nonterminal plans may govern the same mutable transition target.
- `TRANSITION-PRECHECK-001`: Every target precondition is re-read before the first governed write.
- `TRANSITION-ORDER-001`: Supporting records precede execution, execution precedes state, and state is last.
- `TRANSITION-CAS-001`: Execution and state updates use retained-SHA compare-and-swap.
- `TRANSITION-COMMIT-001`: Transition values become authoritative only after terminal `applied` plan finalization and whole-set re-read.
- `TRANSITION-RECOVERY-DURABLE-001`: Fresh-session recovery derives only from the durable plan and repository artifacts.
- `TRANSITION-ROLLBACK-001`: Execution-written/state-not-written recovery restores exact retained execution content and never retries or rolls back state.
- `TRANSITION-FINDING-001`: Every partial transition has a durable create-only finding persisted under a separate recovery plan.
- `TRANSITION-FINDING-CONTENT-001`: A partial-transition finding contains the complete structured recovery payload required by `record.schema.yaml`.
- `TRANSITION-FINDING-PLAN-001`: Finding identity, plan identity, target identity, paths, operations, preconditions, and proposed digests agree with the original transition plan.
- `TRANSITION-FINDING-REVISION-001`: Observed revisions and digests agree with the durable artifacts used for recovery.
- `TRANSITION-FINDING-OUTCOME-001`: Write results, failure, rollback, restoration, continuation, and recovery action agree and are evidence-backed.
- `TRANSITION-PAIR-001`: Applied or rolled-back completion requires exact final pair verification against the corresponding proposed or retained pair.
- `TRANSITION-PARTIAL-001`: Unexplained, ambiguous, or unrecoverable partial transitions block lifecycle continuation and require human reconciliation.
