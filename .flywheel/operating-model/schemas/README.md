# Artifact Contracts

These contracts define the semantic expectations for Flywheel artifacts. Formal schemas are authoritative for single-artifact shape and allowed values. This document is authoritative for cross-artifact, repository-layout, transition, identity, and persistence invariants that JSON Schema cannot express.

A narrative requirement and its formal schema MUST agree. A discrepancy is an operating-model defect: startup validation MUST fail, no execution may be created, and no target-repository inspection may begin until the discrepancy is reconciled.

## Validator semantics

Schema validation SHALL use JSON Schema Draft 2020-12 semantics after parsing YAML 1.2. The validator MUST enforce `format`, including `date-time`. Timestamps MUST be RFC 3339 UTC values ending in `Z`. Execution-activation, persistence-plan, startup-failure, certification, and readiness-validation timestamps MUST use whole-second precision with no fractional component.

Validation has two required layers:

1. Schema validation checks one artifact's required shape, allowed fields, values, and local conditionals.
2. Invariant validation checks paths, uniqueness, references, ordering, transitions, cross-artifact agreement, and repository state.

Passing schema validation alone is never sufficient for Operating Validation.

## Canonical identity and paths

Identifiers are case-sensitive. Symlinks are not followed. Only regular files beneath manifest-declared canonical locations participate in identity resolution.

Canonical paths are:

- Mission: `.flywheel/operations/missions/<mission-id>/mission.yaml`
- Goal: `.flywheel/operations/missions/<mission-id>/goals/<goal-id>.yaml`
- Execution: `.flywheel/operations/records/<mission-id>/<goal-id>/executions/<execution-id>.yaml`
- Evidence: `.flywheel/operations/records/<mission-id>/<goal-id>/evidence/<record-id>.yaml`
- Decision: `.flywheel/operations/records/<mission-id>/<goal-id>/decisions/<record-id>.yaml`
- Finding: `.flywheel/operations/records/<mission-id>/<goal-id>/findings/<record-id>.yaml`
- Approval: `.flywheel/operations/records/<mission-id>/<goal-id>/approvals/<record-id>.yaml`
- Persistence plan: `.flywheel/operations/records/<mission-id>/<goal-id>/persistence/<persistence-plan-id>.yaml`
- Reuse assessment: `.flywheel/operations/records/<mission-id>/<goal-id>/reuse/<reuse-assessment-id>.yaml`
- Certification record: `.flywheel/operations/records/<mission-id>/<goal-id>/certification/<certification-record-id>.yaml`
- Readiness validation: `.flywheel/operations/records/<mission-id>/<goal-id>/readiness/<readiness-validation-id>.yaml`
- Knowledge: `.flywheel/operations/knowledge/<knowledge-id>.yaml`
- Startup failure: `.flywheel/operations/records/startup-failures/<startup-failure-id>.yaml`

A path segment derived from an identifier MUST equal the identifier exactly. Duplicate identifiers, duplicate canonical paths, case-only collisions, or an artifact found outside its canonical location fail Operating Validation.

Record directories are lazy. Their absence is valid until the first record of that kind is persisted.

## Manifest

The manifest identifies schema version, framework name and version, fixed canonical locations, fixed startup entrypoint, required operating files, onboarding state, implementation state, and compatibility expectations. Every listed file must exist exactly once as a regular file.

## State

State identifies readiness, phase, status, active mission, active goal, active execution when present, lifecycle stage, application-work permission, blockers, and the last durable update.

Required combinations are:

- An active goal requires an active mission.
- An active execution requires an active goal and active mission.
- A lifecycle stage requires an active execution.
- `status: active` requires an active execution.
- No active execution requires a null lifecycle stage.
- Non-ready readiness requires `application_missions_allowed: false`.
- A blocked state requires at least one blocker.

Every active reference must resolve to exactly one canonical artifact, and all reciprocal identifiers must agree.

## Mission and goal

A mission contains its objective, status, success criteria, and ordered goal references. Goal list order is authoritative unless dependencies block progress.

A goal contains its mission identifier, objective, status, acceptance criteria, and required-evidence mappings. Every acceptance criterion must have exactly one evidence mapping.

## Execution

An execution contains identifiers, status, intended outcome, acceptance-criterion snapshot, timestamps, all eight lifecycle stages, actions, observations, classifications, adaptations, validation results, references, blockers, outcome, and completion disposition.

The acceptance-criterion list must exactly equal the active goal's criterion identifiers in goal order at execution creation and is immutable for that execution.

`in-progress`, `blocked`, and `interrupted` executions are resumable and mutable. Each MUST have exactly one `in-progress` lifecycle stage. Stages before it must be `completed` or `not-applicable`; stages after it must be `pending`. State lifecycle stage MUST equal that sole in-progress stage.

`succeeded`, `partially-succeeded`, `failed`, and `abandoned` executions are terminal and immutable. They MUST have no pending or in-progress lifecycle stages and require completion timestamp, outcome, disposition, and rationale.

`in-progress` requires `outcome: null`. `blocked` requires at least one blocker. `interrupted` requires a nonempty interruption reason in `outcome`.

## Certification and readiness

A certification record contains exactly the ten required certification scenarios, source revisions, fixture definitions, evidence, validator identity, limitations, findings, corrective actions, self-hosting references, and approval state. The scenario ID and name mapping defined by `certification-validation.yaml` is exact and ordered.

A certification record may be `ready-for-approval` only when all ten scenarios pass and no blocking defect remains. It remains `pending-approval` until a durable authorized approval record is referenced. It may be `approved` and `passed` only when that approval resolves and remains current.

A readiness validation maps each readiness gate to evidence and references the governing certification. A pending or failed record cannot carry a proposed ready-for-missions state. A passed record requires all gates passed, no blockers, a durable approval reference, and the complete proposed terminal state.

Certification and readiness records MUST NOT use chat history, an unpersisted test result, or assumed human intent as evidence or approval.

## Persistence plan

A persistence plan is the transaction controller for one Persist activation or completion attempt. It contains the mission, goal, execution, operator, timestamp, complete governed target set, exact governed write order, target preconditions, proposed digests, rollback or compensation behavior, and whole-set verification state.

Every governed target is represented exactly once. Create targets require confirmed absence. Update targets require a retained blob SHA and complete retained content. Target dependencies and canonical type precedence determine one total governed write order.

The persistence plan MUST NOT include itself in `targets` or `write_order`, and it MUST NOT carry a digest of its own content. Its integrity is enforced separately: create it before governed writes, re-read it, update it only through compare-and-swap while `planned` or `applying`, and make it immutable when terminal.

Governed target digests use SHA-256 over the exact UTF-8 bytes to be written after LF line-ending normalization and without a byte-order mark. Digests are lowercase hexadecimal.

## Deterministic identities

Execution IDs use `EX-YYYYMMDDTHHMMSSZ-NNN`. Persistence-plan IDs use `PERSIST-YYYYMMDDTHHMMSSZ-NNN`. Startup-failure IDs use `SF-YYYYMMDDTHHMMSSZ-NNN`. Certification IDs use `CERT-YYYYMMDDTHHMMSSZ-NNN`. Readiness-validation IDs use `READINESS-YYYYMMDDTHHMMSSZ-NNN`. For each type, capture one whole-second UTC timestamp and select the lowest unused three-digit counter beginning at `001` in the canonical directory. The filename equals `<id>.yaml`.

If create-only persistence collides, re-list the directory and retry with the next lowest unused counter for the same timestamp. Counter exhaustion at `999` is a blocking Operating Validation failure.

## Operator identity

Use the authenticated repository actor when tooling exposes it. Otherwise use the literal identity `chatgpt-session`. The same resolved identity is used for the complete transition and any associated failure record.

## Multi-artifact durable update protocol

Repository files cannot provide a true multi-file transaction. Therefore Persist durability means:

1. Construct one schema-valid persistence plan covering every governed new or changed durable artifact.
2. Validate the plan and all governed proposed artifacts.
3. Create and verify the plan before governed writes.
4. Retain complete content and blob SHAs for all governed update targets; prove absence for governed create targets.
5. Move the plan to `applying` through compare-and-swap.
6. Recheck every governed precondition before the first governed write.
7. Apply governed targets in dependency order and canonical type precedence.
8. Re-read and verify every governed artifact immediately after its write.
9. Keep state as the final operational pointer after all referenced artifacts and execution are durable.
10. Re-read and exactly verify the complete governed target set.
11. Finalize the plan through compare-and-swap to a terminal status and verify that finalization.
12. On failure, stop forward writes and perform reverse-order rollback or explicit compensation without overwriting concurrent changes.
13. Persist a finding and block continuation when complete restoration or terminal plan finalization cannot be proven.

The execution/state pair compare-and-swap protocol remains mandatory within the larger transaction.

For final readiness, approval records precede certification and readiness-validation updates; those records precede goal, mission, execution, and state updates; state remains the final pointer.

## Startup-failure persistence

A startup-failure ID uses the deterministic identity rule above. Its canonical filename is `<startup-failure-id>.yaml`. Recording a startup defect is a startup action, not goal-directed work. The record contains the observed revision, branch, operator, timestamp, failed rules, artifact paths, evidence, recovery action, and orphaned execution identifier when applicable.

State may change to blocked only when its existing hash still matches and the failure directly prevents active work from starting.

## Revision consistency

At startup, resolve and report the immutable commit SHA when tooling makes it available. All artifacts used for one validation result must come from that revision. State transitions and certification records must include that revision in their evidence.

## Validation invariants

- Identifiers are stable and unique within their artifact type.
- References resolve and agree in both directions where both artifacts carry the relationship.
- Manifest locations and entrypoint equal canonical paths.
- Every manifest-required file exists.
- Active and resumable executions have exactly one in-progress stage.
- Terminal executions have no pending or in-progress stages.
- Goal completion requires evidence mapped to every acceptance criterion.
- Approved status requires approval evidence.
- Certification pass requires all ten scenarios and durable authorized approval.
- Readiness pass requires a passed certification, readiness validation, completion evidence, and exact approval.
- Application missions require readiness `ready-for-missions`.
- Historical records are immutable except through explicit supersession metadata.
- Validation results use the structure and allowed values defined by the execution schema.
- Persist requires a complete schema-valid persistence plan, no plan self-target or self-digest, and exact whole-set verification.
