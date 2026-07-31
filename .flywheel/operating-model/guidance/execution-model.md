# Execution Model

This document is normative. `MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, and `SHALL NOT` define mandatory behavior.

An execution is one traceable attempt to advance an active goal. Every goal-directed action belongs to exactly one execution.

## Creation boundary

Immediately before the first goal-directed action, create a new execution unless `.flywheel/state.yaml` identifies an active resumable execution.

If no execution records exist for the active goal, this is the first execution. The absence of prior execution records is expected.

## Operator identity

Before selecting an execution identifier, the operator MUST resolve one stable identity string for the current session. Use the authenticated repository actor when tooling exposes it. Otherwise use `chatgpt-session`. The same identity MUST be used in state metadata and any startup-failure record created by this transition.

## Timestamp and identity

The creation instant MUST be captured once in UTC at whole-second precision using `YYYY-MM-DDTHH:MM:SSZ`. Fractional seconds are prohibited for execution activation. The compact form is produced by removing `-` and `:` from that exact timestamp.

Execution identifiers MUST use `EX-YYYYMMDDTHHMMSSZ-NNN`, where `NNN` begins at `001`. The operator MUST inspect the canonical execution directory and choose the lowest unused counter for the captured second. The filename MUST equal `<execution-id>.yaml`.

If create-only persistence reports that the selected path already exists, re-list the directory, select the next lowest unused counter for the same captured second, and retry. Repeat until creation succeeds or the counter would exceed `999`. Counter exhaustion is an Operating Validation failure and MUST be persisted as a startup-failure record.

## Initial activation snapshot

The execution artifact created before the state update MUST already contain the activation snapshot state will reference:

- `status: in-progress`
- `started_at`: the captured whole-second UTC creation instant
- `completed_at: null`
- `intended_outcome`: the active goal objective exactly
- `acceptance_criteria`: the active goal acceptance-criterion IDs in goal order
- `lifecycle.execute.status: in-progress`
- `lifecycle.execute.started_at`: exactly equal to execution `started_at`
- The other seven lifecycle stages: `pending` with null timestamps, summary, and reason
- `actions`, `observations`, `evaluations`, `classifications`, `adaptations`, `blockers`, `approval_refs`, `evidence_refs`, `decision_refs`, `finding_refs`, and `validation_results`: empty arrays
- `outcome: null`
- Completion disposition and rationale: null

Required approvals are represented by the active goal's `approvals_required` values. Approval records are added to `approval_refs` only after they exist.

The corresponding state update MUST set:

- `status: active`
- `active_execution`: the new execution ID
- `lifecycle_stage: execute`
- `last_durable_update.at`: exactly equal to execution `started_at`
- `last_durable_update.by`: the resolved operator identity
- `last_durable_update.reason`: `Activated execution <execution-id> for goal <goal-id>.`

All other state fields remain unchanged.

## Durable creation sequence

1. Resolve the stable operator identity.
2. Capture one whole-second UTC creation instant.
3. Read and retain the current state blob SHA.
4. Select the deterministic execution ID.
5. Create the fully valid activation-snapshot execution using create-only semantics, applying the same-second counter retry rule on path collision.
6. Re-read state and verify its SHA is unchanged.
7. Update state using compare-and-swap against the retained SHA.
8. If state changed, do not overwrite it. Persist a startup-failure record using `startup-failure.schema.yaml`, identifying the created execution as orphaned, and stop.

A finding record is not used for a creation collision because no execution became active.

## Template use

`.flywheel/operating-model/templates/execution.yaml` is a schema-valid example, not an execution record. Before persistence, replace its example identity, timestamps, mission, goal, objective, and acceptance criteria using the rules above. The resulting artifact MUST validate before create-only persistence.

## During execution

Record goal-directed actions, observations, commands, outputs, changes, assumptions, evidence, and deviations as they occur. Do not reconstruct evidence from memory.

Every execution records all eight lifecycle stages: execute, observe, evaluate, classify, adapt, validate, persist, and reuse.

Before beginning a later stage, update the execution and state together so exactly that stage is `in-progress`; every predecessor is `completed` or `not-applicable`; every successor is `pending`; and state `lifecycle_stage` equals the execution's sole `in-progress` stage.

## Observation contract

An observation records an actual result, absence of an expected result, environmental fact, failure, or human feedback. It MUST NOT present an inferred cause, conclusion, classification, recommendation, adaptation, validation conclusion, persist decision, or reuse decision as a directly observed fact.

Each observation MUST use the structured observation model in `execution.schema.yaml` and MUST include a stable identifier, statement, type, status, observation timestamp, source or method, evidence references, uncertainty disposition, and conflict references.

A complete observation MUST reference at least one evidence item. An incomplete, uncertain, or conflicting observation MAY omit evidence only when its uncertainty field explicitly states what is unavailable and why.

Observe MUST NOT be completed unless:

- At least one observation exists.
- At least one execution-level evidence reference exists.
- The Observe stage contains at least one reference.
- Every complete observation references evidence.
- The stage summary and timestamps exist.
- Observations contain actual results rather than evaluation conclusions.

## Evaluation contract

Evaluate interprets and compares observations against acceptance criteria, expected outcomes, governance rules, and validation requirements. Evaluate MAY form conclusions or identify limitations, but it MUST NOT introduce a fact that is not traceable to an observation and supporting evidence.

Each material evaluation MUST use the structured evaluation model in `execution.schema.yaml` and MUST include:

- A stable evaluation identifier.
- A statement and result.
- At least one observation reference.
- At least one evidence reference.
- Any applicable acceptance-criterion or rule references.
- Limitations and rationale.

Evaluate MUST NOT be completed unless at least one structured evaluation exists, the Evaluate stage contains at least one reference, and every evaluation reference resolves to existing observations and evidence. If no material evaluation exists, the stage MUST be `not-applicable` with a concrete reason.

Classifications, recommendations, adaptations, persist decisions, and reuse decisions MUST NOT be asserted as evaluation outputs before their lifecycle stages begin.

## Classification contract

Every material classification MUST use the structured classification model in `execution.schema.yaml` and the semantic rules in `classifications.md`.

Each classification MUST have a unique stable identifier, a permitted type, evaluation and evidence provenance, rationale, certainty, uncertainty disposition, relationship references, and any type-specific record or validation references.

Classify MUST NOT be completed unless at least one structured classification exists, the Classify stage contains at least one reference, all references resolve, and all classification semantic rules pass. If no material outcome requires classification, the stage MUST be `not-applicable` with a concrete reason.

## Adaptation contract

Every material adaptation MUST use the structured adaptation model in `execution.schema.yaml` and the semantic rules in `adaptation.md`.

Each adaptation MUST have a unique stable identifier and MUST remain traceable to classifications, evaluations, observations, and evidence. It MUST explicitly record affected scope, rationale, intended effect, alternatives, certainty, uncertainty, scope disposition, approval and decision requirements, disposition, and downstream lifecycle statuses.

At Adapt activation, an adaptation MAY remain proposed while approval or a decision is pending, but it MUST remain unimplemented and MUST NOT claim validation, persistence, or reuse outcomes.

Adapt MUST NOT be completed unless at least one structured adaptation exists, the Adapt stage contains at least one reference, all references resolve, all adaptation semantic rules pass, and every adaptation matches a completion-permitted row in the authoritative matrix in `adaptation.md`.

The matrix is enforced as follows:

- `approved` requires completed implementation and validation status `pending`.
- `rejected` requires implementation and validation status `not-applicable` plus the resolving decision and applicable approval record.
- `deferred` requires a resolving decision, implementation `not-started`, and validation `not-applicable`.
- `proposed` never permits Adapt completion.
- `implementation_status: in-progress` never permits Adapt completion.
- `scope_disposition: new-goal-required` permits completion only when the adaptation is deferred by a recorded decision and remains unimplemented.

When any adaptation does not match the matrix, the operator MUST continue Adapt or set the execution to `blocked` or `interrupted`; Validate MUST NOT begin.

Required Adapt semantic rule identifiers are defined in `adaptation.md` and MUST be enforced even when individual YAML documents satisfy schema validation.

## Validation contract

Every material validation MUST use the structured validation model in `execution.schema.yaml` and the semantic rules in `validation.md`.

Before Validate begins, each approved and fully implemented adaptation MUST have at least one planned validation entry. The plan MUST identify adaptation targets, acceptance criteria or rules, method, immutable scope, expected outcome, and expected evidence.

Validate MUST NOT begin for a proposed, rejected, deferred, pending-approval, new-goal-required, not-started, or partially implemented adaptation. These adaptations are validation-ineligible and MUST use `validation_status: not-applicable`, except unresolved proposed or incomplete adaptations that already prevent Adapt completion.

Validate MUST NOT complete unless all eligible adaptations have complete validation coverage, every required result is executed, no required result remains pending, passed and failed results contain sufficient evidence, failed results identify a finding and recovery action, and adaptation validation statuses agree with the results.

## Durable lifecycle-transition sequence

Every non-initial lifecycle transition that changes both an existing execution artifact and `.flywheel/state.yaml` MUST use this sequence:

1. Resolve the stable operator identity and capture one whole-second UTC transition instant.
2. Read and retain the current execution blob SHA and complete execution content.
3. Read and retain the current state blob SHA and complete state content.
4. Verify state and execution currently agree on mission, goal, execution ID, status, and sole in-progress lifecycle stage.
5. Construct the complete proposed execution and state artifacts in memory using the same transition instant.
6. Validate both proposed artifacts, all cross-artifact references, lifecycle ordering, timestamps, semantic rules, and state-execution invariants before writing either artifact.
7. Re-read both artifacts and verify both retained SHAs are unchanged. If either changed, write nothing and stop with a stale-transition result.
8. Update the execution first using compare-and-swap against the retained execution SHA.
9. Re-read state and verify its SHA still equals the retained state SHA.
10. Update state using compare-and-swap against the retained state SHA.
11. Re-read both artifacts and verify the durable pair exactly matches the validated proposed transition.

Both artifact updates MUST use compare-and-swap. A force update is prohibited.

### Partial-transition recovery

If the execution update succeeds but the state update does not:

1. Do not retry the state update against a new SHA and do not overwrite concurrent state changes.
2. Re-read the execution and verify its SHA equals the SHA returned by the successful execution update.
3. Attempt to restore the retained pre-transition execution content using compare-and-swap against that post-update execution SHA.
4. Persist a finding record describing the attempted transition, retained SHAs, successful write, failed write, rollback result, current artifact SHAs, and required human recovery.
5. If rollback succeeds, verify state and execution again match the retained pre-transition pair and stop with the transition not applied.
6. If rollback fails, mark the condition as a blocker in the finding, perform no further lifecycle work, and require human reconciliation before resume.

Rollback MUST restore only the exact retained pre-transition execution content. Rollback of state is prohibited because the failed state update did not establish ownership of the current state revision.

The operator MUST NOT report a lifecycle transition as durable until the final pair verification succeeds.

Required semantic rule identifiers:

- `TRANSITION-CAS-001`: Both existing artifacts use retained-SHA compare-and-swap.
- `TRANSITION-PRECHECK-001`: Both retained SHAs are rechecked before the first write.
- `TRANSITION-ORDER-001`: Execution is updated before state.
- `TRANSITION-PAIR-001`: Final state and execution must equal the validated proposed pair.
- `TRANSITION-ROLLBACK-001`: A state-update failure after execution success triggers exact-content execution rollback.
- `TRANSITION-PARTIAL-001`: Every partial transition produces a durable finding and blocks continuation when consistency cannot be restored.

## Lifecycle and timestamp invariants

These rules are required semantic validation rules even when a schema implementation cannot express them directly:

- `LIFECYCLE-ORDER-001`: A stage may start only when every predecessor is `completed` or `not-applicable` and every successor is `pending`.
- `LIFECYCLE-SOLE-ACTIVE-001`: Exactly one stage is `in-progress` for a resumable execution.
- `TIME-EXECUTION-001`: Execution `started_at` MUST be no later than any stage `started_at`.
- `TIME-STAGE-001`: A stage `completed_at` MUST be equal to or later than its `started_at`.
- `TIME-TRANSITION-001`: A successor stage `started_at` MUST be equal to or later than its predecessor `completed_at`.
- `TIME-STATE-001`: State `last_durable_update.at` for a lifecycle transition MUST be equal to or later than the transition instant.
- `STATE-STAGE-001`: State `lifecycle_stage` MUST equal the execution's sole `in-progress` stage.

An operator or validator MUST reject an artifact or transition that violates any rule above, even when both individual YAML documents satisfy their schemas.

## Outcomes and resumability

Allowed execution statuses are `in-progress`, `blocked`, `succeeded`, `partially-succeeded`, `failed`, `abandoned`, and `interrupted`.

`in-progress`, `blocked`, and `interrupted` are resumable and mutable. `in-progress` requires `outcome: null`. `blocked` requires at least one blocker and may use `outcome` to state the blocking condition. `interrupted` requires a nonempty interruption reason in `outcome`. All resumable statuses require `completed_at` and completion disposition and rationale to remain null.

`succeeded`, `partially-succeeded`, `failed`, and `abandoned` are terminal and immutable. They require all lifecycle stages to be completed or justified as not applicable, plus `completed_at`, outcome, disposition, and rationale.

Continue an execution only when state identifies it, its status is resumable, its mission and goal match state, and exactly one lifecycle stage is in progress.

## Closure

When closing a terminal execution:

1. Record its outcome and rationale.
2. Complete all lifecycle stage records, including justified `not-applicable` stages.
3. Persist referenced evidence, decisions, findings, approvals, and learning.
4. Clear `state.active_execution` and `state.lifecycle_stage`.
5. Set state status to `ready`, `blocked`, or `suspended` as supported by evidence.
6. Update `last_durable_update` for the same durable transition.
7. Update goal and mission state only when their transition rules are satisfied.
