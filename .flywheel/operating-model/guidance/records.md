# Record Locations and Naming

This document is normative. All paths are repository-root-relative.

## Canonical goal record root

Records for a goal are stored under:

`.flywheel/operations/records/<mission-id>/<goal-id>/`

Required subdirectories are:

- `executions/`
- `evidence/`
- `decisions/`
- `findings/`
- `approvals/`
- `persistence/`
- `reuse/`
- `certification/`
- `readiness/`

## Naming

Use UTC timestamps and stable identifiers:

- Execution: `executions/<execution-id>.yaml`
- Evidence: `evidence/<evidence-id>.yaml`
- Decision: `decisions/<decision-id>.yaml`
- Finding: `findings/<finding-id>.yaml`
- Approval: `approvals/<approval-id>.yaml`
- Persistence plan: `persistence/<persistence-plan-id>.yaml`
- Reuse assessment: `reuse/<reuse-assessment-id>.yaml`
- Certification record: `certification/<certification-record-id>.yaml`
- Readiness validation: `readiness/<readiness-validation-id>.yaml`

Approval identifiers MUST use `APPROVAL-NNN` and be unique within the goal record set. Select the lowest unused counter. A create collision requires re-listing before selecting the next unused identity.

New approval records MUST validate against `.flywheel/operating-model/schemas/approval-record.schema.yaml` instead of the generic `record.schema.yaml`. The generic approval shape retained in `record.schema.yaml` is legacy compatibility only and MUST NOT be applied as a second validator to a new structured approval record. The approval boundary contract in `approval-boundaries.md` is authoritative for authority, exact scope, effective time, delegation, supersession, and revocation.

Persistence plan identifiers MUST use `PERSIST-YYYYMMDDTHHMMSSZ-NNN`. The counter begins at `001`; select the lowest unused counter for the captured second. A create collision requires re-listing and selecting the next unused counter. Counter exhaustion is an operating-validation failure.

Reuse assessment identifiers MUST use `REUSE-NNN` and be unique within the execution. The identity remains stable while the assessment moves from `planned` to `completed`. A materially revised conclusion after completion requires a new assessment identity that references the prior assessment in rationale and any governing decision or superseding knowledge.

Certification identifiers MUST use `CERT-YYYYMMDDTHHMMSSZ-NNN`. Readiness-validation identifiers MUST use `READINESS-YYYYMMDDTHHMMSSZ-NNN`. For each type, capture one whole-second UTC timestamp and select the lowest unused counter in its canonical directory. A create collision requires re-listing before selecting the next unused identity.

Certification records MUST validate against `.flywheel/operating-model/schemas/certification-record.schema.yaml`. Readiness validation records MUST validate against `.flywheel/operating-model/schemas/readiness-validation.schema.yaml`.

## Record mutability

Evidence, decisions, findings, and approvals are create-only history. They MUST NOT be overwritten after creation. Corrections or changed conclusions require a new record that references or supersedes the earlier record.

Approval renewal, delegation, revocation, rejection, deferral, corrected scope, and supersession each require a new `APPROVAL-NNN` record. An existing approval record MUST NOT be edited to change its authority, decision, scope, effective time, expiration, evidence, delegation, revocation, or supersession relationships.

A reuse assessment is created once with `status: planned`, may be updated only through retained-SHA compare-and-swap from `planned` to `completed`, and becomes immutable when completed. A completed assessment MUST NOT return to planned or change disposition, provenance, scope, or rationale. Corrections require a new assessment identity.

A certification record may move through retained-SHA compare-and-swap from `draft` to `ready-for-approval`, and then to `approved` or `rejected`. A `failed`, `approved`, `rejected`, or `superseded` certification record is immutable. Corrected certification requires a new identity that preserves the prior record as source evidence.

A readiness validation may move through retained-SHA compare-and-swap from `pending` to `passed` or `failed`. A terminal readiness validation is immutable. A readiness transition requires the terminal `passed` record and its referenced approval to be durable before state changes.

A persistence plan is created once before its governed writes, may be updated only through compare-and-swap while `planned` or `applying`, and becomes immutable when terminal. The plan is the transaction controller and MUST NOT enumerate itself as a persistence target or write-order item.

Execution records are mutable only while resumable and MUST use compare-and-swap updates. Terminal execution records are immutable.

Goal, mission, state, and context artifacts are mutable only through compare-and-swap against retained blob SHAs.

Knowledge uses create-only identity. A revision MUST use a new identity and preserve a `supersedes` relationship.

## Ordering and discovery

Read records by their `created_at` or assessment timestamp, oldest first. File names are a secondary ordering signal only. Records MUST identify `mission_id` and `goal_id`. Execution, persistence-plan, reuse-assessment, certification, and readiness-validation records MUST also identify the execution they govern.

Approval resolution MUST also read later approval records that delegate, supersede, or revoke earlier approval identities before treating an earlier approval as current authorization.

## Active execution

`.flywheel/state.yaml` is the authoritative pointer to an active execution. It MUST match an existing execution record under the active mission and goal. A missing or mismatched record is a stop condition.

## Referential integrity

A durable artifact MUST NOT reference a record that is absent from its canonical location. Supporting records MUST be created and verified before an execution, goal, mission, context, or state artifact that references them is updated.

An approval record's source evidence, evidence references, delegation reference, supersession reference, revocation reference, target references, and governing persistence plan MUST resolve before the approval may authorize work.

A certification record's scenario evidence, validator references, findings, corrective actions, self-hosting references, and approval reference MUST resolve before it may be treated as approved. A readiness validation's certification, gate evidence, and approval references MUST resolve before it may authorize a readiness transition.

Planned reuse assessments required for Reuse activation MUST be created and verified before the transaction commits the execution/state pair that activates Reuse. The later Reuse transaction updates those same assessments to `completed` using retained-SHA compare-and-swap before creating knowledge that references them.

A persistence plan MUST enumerate every governed record creation and every governed mutable-artifact update performed by its transaction. Plan creation and plan-status updates are mandatory control operations but are excluded from the plan's `targets` and `write_order`.

Reuse outputs are durable only after a Reuse persistence plan has applied and verified completed reuse assessments, proposed knowledge, execution, goal, mission, and state updates. Reuse MUST NOT complete based on in-memory assessments alone.

Unplanned governed writes are prohibited.

## Durability

Do not rely on chat transcripts as records. Persist material observations, commands, outputs, decisions, approvals, failures, lifecycle results, persistence plans, reuse assessments, certification records, readiness validations, and promoted knowledge before ending a session.
