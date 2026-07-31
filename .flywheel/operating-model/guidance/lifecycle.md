# AI Flywheel Lifecycle

Every execution follows and records all eight lifecycle stages. Stages may iterate internally, but none may be omitted or entered out of order.

Each stage record must include a status, summary, timestamps, and relevant references. Allowed stage statuses are `pending`, `in-progress`, `completed`, and `not-applicable`. A `not-applicable` stage requires a concrete reason.

A stage may become `in-progress` only when every predecessor is `completed` or `not-applicable`, every successor is `pending`, and state identifies the same active execution and lifecycle stage.

## 1. Execute

Perform only work authorized by the active goal, using the approved plan and constraints.

## 2. Observe

Capture actual results, evidence, unexpected behavior, failures, environmental facts, and human feedback.

Observations must use the structured observation model. A direct observation must not contain an inferred cause, conclusion, classification, recommendation, adaptation, validation conclusion, persist decision, or reuse decision.

Observe may complete only when at least one observation exists, complete observations reference evidence, the execution and stage contain required evidence references, and the stage summary and timestamps are present.

## 3. Evaluate

Compare observations with acceptance criteria, expected outcomes, governance, and validation requirements.

Material evaluation conclusions must use structured evaluation entries and remain traceable to observations and evidence. Evaluate may interpret supported facts and identify limitations, but it must not introduce unsupported facts or prematurely assert later-stage classifications, adaptations, persistence decisions, or reuse decisions.

Evaluate may complete only when at least one structured evaluation exists, the Evaluate stage references its outputs, and all observation and evidence references resolve. When no material evaluation exists, mark the stage `not-applicable` with a concrete reason.

## 4. Classify

Classify material outcomes such as defects, findings, decisions, improvements, risks, uncertainties, failures, and validated learning.

Classifications must use the structured classification model and remain traceable to evaluations and evidence. Certainty and uncertainty must be explicit, related classifications must be linked, and decision, finding, and validation references must satisfy the type-specific rules in `classifications.md`.

Classify may complete only when at least one structured classification exists, the Classify stage references its outputs, and all classification semantic and reference checks pass. When no material classification exists, mark the stage `not-applicable` with a concrete reason.

## 5. Adapt

Define and apply justified changes to the plan, implementation, tooling, configuration, guidance, or operating model.

Every material adaptation must use the structured adaptation model and remain traceable to classifications, evaluations, observations, and evidence. Affected scope, intended effect, alternatives, certainty, approval requirement and status, decision references, disposition, and downstream lifecycle statuses must be explicit.

At Adapt activation, an approval-required adaptation may be proposed with approval still pending, no approval or decision references yet, and implementation not started. Proposed work must not claim implementation, validation, persistence, or reuse outcomes. Approval and an authorizing decision are required before the adaptation may become approved or implementation may begin.

The authoritative Adapt completion matrix is defined in `adaptation.md`. Adapt may complete only when every adaptation matches a permitted row in that matrix:

- Approved work is fully implemented and moves to Validate with validation pending.
- Rejected work is unimplemented and validation is not applicable.
- Deferred work has a final decision, remains unimplemented, and validation is not applicable.
- Proposed work, pending decisions, and incomplete implementation remain unresolved and prevent Adapt completion.

An unresolved adaptation requires continued Adapt work or a formally blocked or interrupted execution. At least one structured adaptation and Adapt-stage reference are required when Adapt completes. When no adaptation is warranted, mark the stage `not-applicable` with a concrete reason.

## 6. Validate

Define and execute evidence-based checks proving or disproving implemented adaptation outcomes.

Every material validation must use the structured `VAL-NNN` model and the rules in `validation.md`. Before Validate begins, each validation-eligible adaptation must have a planned validation entry identifying its targets, criteria or rules, method, immutable scope, expected outcome, and expected evidence.

Only approved and fully implemented adaptations are validation-eligible. Rejected, deferred, new-goal-required, not-started, or partially implemented adaptations cannot pass validation.

Validate may complete only when all eligible adaptations have complete coverage, no required validation remains pending, every pass or failure has sufficient evidence, failures have findings and recovery actions, adaptation validation statuses agree with results, and all validation references resolve. Command execution alone is not proof. When no adaptation is eligible, mark Validate `not-applicable` with a concrete reason.

## 7. Persist

Make the complete execution outcome durable using the multi-artifact contract in `persistence.md`.

Persist must not begin while required validation remains pending or failed without an authorized disposition. Before Persist becomes `in-progress`, a schema-valid persistence plan must enumerate every new or changed durable artifact, canonical path, operation, mutability rule, dependency, precondition, proposed digest, write order, and recovery action.

Supporting records must be written and verified before mutable artifacts that reference them. Execution must be durable before state, and state remains the final operational pointer. Every existing mutable target uses retained-SHA compare-and-swap; every create target requires a final absence check.

Persist may complete only after every planned target is written in deterministic order, each write is re-read and verified, the complete durable set passes final cross-artifact verification, no unplanned artifact changed, and the persistence plan records a successful final result. Partial persistence must be rolled back or explicitly compensated; unrecoverable inconsistency creates a finding, blocks continuation, and requires human reconciliation.

Persist must not claim Reuse completion or promote knowledge that has not met the Reuse requirements.

## 8. Reuse

Assess validated learning and existing validated knowledge using the structured contract in `reuse.md` and `reuse-assessment.schema.yaml`.

Reuse MUST NOT begin until Persist is completed, its persistence plan is terminal `applied`, final verification passed, all references resolve, and no persistence blocker remains.

Every material candidate learning item and every existing knowledge item considered for use MUST have a structured assessment referenced by the Reuse stage. Promotions require evidence, passed validation provenance, applicability, limitations, actionable guidance, duplicate and conflict resolution, and required decisions or approvals. Existing knowledge use or rejection must record an applicability-based disposition.

Reuse may complete only when every required assessment is completed, all references and proposed knowledge artifacts validate, duplicate and conflict checks pass, adaptation reuse statuses agree, and the stage has references, summary, and timestamps. When no candidate or existing knowledge requires assessment, mark Reuse `not-applicable` with a concrete reason.

## Durable transitions

Every transition that changes both an existing execution and state must follow the dual-artifact compare-and-swap, final-pair verification, and partial-transition recovery sequence in `execution-model.md`. During Persist, that pair sequence is nested within the complete multi-artifact transaction defined in `persistence.md`.

## Timestamp rules

Execution and lifecycle timestamps must satisfy the semantic validation rules defined in `execution-model.md`:

- Execution start is no later than any stage start.
- Stage completion is no earlier than stage start.
- A successor stage does not start before its predecessor completes.
- State durable-update time is not earlier than the transition instant.

Violations must be rejected even when timestamp strings independently satisfy schema format validation.

## Completion rule

An execution may close only after every stage is `completed` or justified as `not-applicable`. A goal may complete only after all acceptance-criterion IDs map to sufficient evidence, required validation passes, blockers are resolved or formally disposed, required approvals exist, and the completion state is persisted.
