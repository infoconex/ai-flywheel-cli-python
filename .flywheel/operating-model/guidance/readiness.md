# Phase, Status, and Readiness Model

This document is normative. The Flywheel separates lifecycle position, current operability, and permission to begin application missions. These concepts MUST NOT be collapsed into one field.

## Phase

Allowed `state.phase` values are `onboarding`, `operating`, `upgrading`, and `suspended`. Detailed onboarding progression is represented by the active mission and goal, not by inventing additional phase or readiness values.

## Status

Allowed `state.status` values are:

- `ready`: no execution is active and the active goal may begin or continue.
- `active`: an execution is currently active.
- `blocked`: progress requires unresolved information, approval, access, dependency, or correction.
- `suspended`: work is intentionally paused.

## Readiness

Allowed `state.readiness` values are:

- `not-ready-for-missions`: application missions are prohibited because onboarding or certification is incomplete.
- `ready-for-missions`: the repository may accept application missions.
- `degraded`: the repository was previously ready, but a material operating defect or missing capability prevents reliable operation.

`state.application_missions_allowed` MUST be false unless readiness is `ready-for-missions`.

## Ready-for-missions gate

Every condition MUST be satisfied:

- Repository context is sufficient for future mission planning.
- Flywheel implementation context is approved.
- Governance and approval boundaries are explicit.
- Required capabilities are implemented or have an approved manual procedure.
- Operating artifacts validate against their schemas and invariants.
- Formal certification defined in `.flywheel/operating-model/guidance/certification.md` passes.
- A proving mission completes with traceable evidence.
- Known limitations are recorded and accepted.
- State, mission, goal, executions, records, approvals, certification records, readiness validations, and knowledge are internally consistent.

## Readiness validation record

The readiness decision MUST be represented at:

`.flywheel/operations/records/<mission-id>/<goal-id>/readiness/<readiness-validation-id>.yaml`

The record MUST validate against `.flywheel/operating-model/schemas/readiness-validation.schema.yaml`. It maps each readiness and transition gate to exact durable evidence, identifies blockers, references the governing certification record, and carries the readiness approval reference when one exists.

A readiness validation with unresolved human approval, incomplete onboarding, or any other unresolved gate MUST use `status: pending`, include at least one pending gate and blocker, use `approval_ref: null`, and use `proposed_state: null`.

A readiness validation may use `status: passed` only when every gate passes, the certification record is approved, the exact readiness approval is durable and current, blockers are empty, and the complete proposed terminal state is present.

A failed gate requires `status: failed`, at least one failed gate, blockers, and no proposed state.

## Readiness transition procedure

A transition to `ready-for-missions` requires:

1. A terminal `passed` readiness validation record mapping every gate to evidence.
2. Successful schema, reference, invariant, lifecycle, evidence, certification, readiness, and approval validation.
3. A durable approved certification record covering cold start, first execution, resume, recovery, approval boundary, lifecycle completeness, evidence completeness, proving mission, and self-hosting.
4. Recorded human approval of the certification, known limitations, and exact readiness transition.
5. Completion of the onboarding mission and its active goal.
6. A persistence plan containing the certification update, readiness validation update, approval, terminal onboarding mission and goal updates, execution update, and state update in dependency order.
7. An atomic state update setting `phase: operating`, `readiness: ready-for-missions`, `status: ready`, clearing active onboarding mission, goal, execution, and lifecycle stage, and setting `application_missions_allowed: true`.

The readiness validation, certification approval, and terminal onboarding artifacts MUST be durable and verified before state is written as the final operational pointer.

Readiness is not established merely by changing a field. A validator MUST reject a readiness transition without the required certification, readiness-validation, completion, and approval evidence.

A self-hosting execution that prepares a complete certification package but awaits human approval MUST leave readiness unchanged and may leave the certification goal blocked or pending human action. That is the required approval boundary, not a failed readiness transition.

## Degradation

Set readiness to `degraded` when a material failure undermines reliable operation or invalidates a prior certification assumption. Existing application work may continue only when governance explicitly permits it and the risk is recorded. Restore readiness only after corrective validation, affected certification scenarios are rerun, and required approval is recorded.
