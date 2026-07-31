# Startup Protocol

This document is normative. `MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, and `SHALL NOT` define mandatory behavior. Explanatory text and examples are informative.

This protocol is mandatory whenever a new operator or chat session begins work in the repository. All paths are repository-root-relative.

## Read order

1. Read `.flywheel/manifest.yaml`.
2. Resolve every manifest path relative to the repository root.
3. Read `.flywheel/state.yaml`.
4. Read every file listed in `required_files` in manifest order.
5. Read the active mission and active goal identified by state.
6. Read records for the active goal from the canonical locations defined in `.flywheel/operating-model/guidance/records.md`, oldest first.
7. When `active_execution` is not null, read that execution last and resume its recorded `lifecycle_stage`.
8. Do not inspect the target repository until startup is complete.

## Operating validation

Before producing the opening report, the operator MUST verify:

- Every manifest-required file exists.
- State, mission, goal, and any active execution satisfy their schemas when validation is available.
- Active references resolve uniquely and agree.
- Any requested goal-directed work belongs to the active mission and goal. A startup-only request is authorized by this protocol and ends after the opening report and execution decision.
- Required approvals, blockers, evidence rules, and application-work permission are understood.

Operating validation concerns Flywheel artifacts only. Repository build, test, dependency, architecture, or source inspection belongs to goal execution.

During onboarding, before a repository-specific validator exists, Operating Validation SHALL be performed manually using the published validation contract. Manual validation performed according to that contract is authoritative and equivalent to automated validation for governance decisions until a repository-specific validator becomes available.

## Required opening report

The opening report SHALL use these headings in this exact order:

1. `Current Phase`
2. `Status`
3. `Readiness`
4. `Application Missions Permitted`
5. `Active Mission`
6. `Active Goal`
7. `Active Execution`
8. `Lifecycle Stage`
9. `Known Blockers`
10. `Required Approvals`
11. `Operating Validation`
12. `Repository Validation`
13. `Implementation Validation`
14. `Next Authorized Action`

The report MUST state whether an existing execution will be resumed or a new execution must be created.

At startup, before repository inspection or implementation work begins, the expected validation states are:

- `Operating Validation`: `passed`, or `failed` with a deterministic recovery action.
- `Repository Validation`: `pending` when execution has not started.
- `Implementation Validation`: `not-applicable` when no implementation work has occurred.

The operator MUST NOT report Repository Validation or Implementation Validation as passed without evidence gathered during an authorized execution.

## Startup completion checkpoint

Startup is complete only when:

- All required operating artifacts have been read.
- Operating validation has passed or a deterministic recovery action has been selected.
- The opening report has been produced.
- The execution decision has been made.

No goal-directed action may occur before this checkpoint.

## Execution boundary

A goal-directed action is any action that advances, investigates, validates, records, or changes the active goal. It includes repository inspection, onboarding questions, commands, analysis of repository content, validation, evidence collection, approval requests, and file changes.

Reading the operating contract and producing the opening report are startup actions, not goal-directed actions.

Immediately before the first goal-directed action, the operator MUST either:

- Resume the execution identified by state when it is resumable and consistent; or
- Create the first or next execution record, initialize all lifecycle stages, set it to `in-progress`, and atomically update state to `status: active`, the new `active_execution`, and `lifecycle_stage: execute`.

If no execution records exist for the active goal, that absence is expected for the first execution and is not a blocker.

## Resuming an existing execution

An execution may be resumed only when all of the following are true:

- State identifies exactly one active execution.
- The referenced execution exists at its canonical path and no other execution for the active goal is represented as active by durable state.
- The execution status is `in-progress`, `blocked`, or `interrupted`.
- Mission ID, goal ID, execution ID, state status, and state lifecycle stage agree with the execution.
- Exactly one lifecycle stage is `in-progress`, every predecessor is `completed` or `not-applicable`, and every successor is `pending`.
- Every reference required by the active stage resolves to durable content.
- The execution and state revisions used for the decision are still current.

The operator MUST reconstruct the next action only from durable artifacts. Chat history, prior-session memory, or an unpersisted plan MUST NOT be used as authority.

Before the first resumed goal-directed action, the operator MUST resolve the stable identity for the new session using the operator-identity rule in `execution-model.md` and perform a resume transition using the durable lifecycle-transition sequence in that document.

The resume transition MUST preserve the execution ID, mission ID, goal ID, `started_at`, lifecycle history, completed actions, evidence, observations, evaluations, classifications, adaptations, validations, blockers, and all durable references. It MUST NOT repeat, delete, rewrite, or re-time a completed lifecycle action.

For an `in-progress` execution, the resume transition updates only state and execution metadata needed to record the new operator and resume event; the active lifecycle stage remains unchanged.

For an `interrupted` execution, the resume transition MUST:

- Require a nonempty durable interruption reason in `outcome` before resume is permitted.
- Preserve that reason in a durable action or referenced record before clearing `outcome`.
- Change execution status from `interrupted` to `in-progress`.
- Keep `completed_at` and completion disposition and rationale null.
- Keep the same sole in-progress lifecycle stage and preserve all stage timestamps and references.
- Set state status to `active`, retain the same active execution and lifecycle stage, and update `last_durable_update` with the new operator identity and resume reason.

A `blocked` execution MUST NOT be changed to `in-progress` until its blockers have been durably reconciled or an authorized human disposition permits continuation. Merely starting a new session does not resolve a blocker.

Both execution and state updates MUST use retained-revision compare-and-swap. If either retained revision is stale, write nothing and restart startup resolution from durable state. If the execution update succeeds but the state update fails, apply the partial-transition recovery rules in `execution-model.md`; do not continue lifecycle work until the durable pair is restored or reconciled.

The exact next authorized action is the first incomplete action required by the currently in-progress lifecycle stage after considering all durable actions, evidence, references, approvals, blockers, and stage completion rules. Already completed actions MUST NOT be repeated merely because the operator session changed.

Required semantic rule identifiers:

- `RESUME-DURABLE-001`: Resume authority and next action are derived only from durable artifacts.
- `RESUME-IDENTITY-001`: Resume preserves the existing execution identity and lifecycle history.
- `RESUME-REASON-001`: Interrupted execution resume requires and durably preserves the interruption reason.
- `RESUME-STAGE-001`: Resume retains the sole active lifecycle stage and selects its first incomplete authorized action.
- `RESUME-CAS-001`: Resume updates execution and state using retained-revision compare-and-swap and partial-transition recovery.
- `RESUME-BLOCKED-001`: Blocked work cannot resume until blockers are durably reconciled or continuation is authorized.

## Invalid active-execution states

Operating Validation MUST fail and goal-directed work MUST stop when:

- State points to a missing execution.
- State points to a terminal execution.
- State and execution disagree on mission, goal, execution ID, status, or lifecycle stage.
- An interrupted execution lacks a nonempty interruption reason.
- No lifecycle stage or multiple lifecycle stages are `in-progress` for a resumable execution.
- Multiple executions appear active for the same goal and durable state does not resolve the ambiguity uniquely.
- Any active-stage reference is missing, stale, ambiguous, or not durable.

The operator MUST report the contradiction and select deterministic reconciliation under `failure-handling.md`. The operator MUST NOT choose an execution based on recency, filename ordering, chat history, or convenience, and MUST NOT overwrite any conflicting revision.

## Repository inspection scope

When repository inspection is authorized by the active goal, it MUST consider applicable repository structure, documentation, configuration, build, tests, automation, tooling, dependencies, standards, constraints, and authoritative external references. The operator MUST record inspected areas, evidence sources, unknowns, and intentionally uninspected areas.

## Stop conditions

Stop and apply `.flywheel/operating-model/guidance/failure-handling.md` when:

- State and mission, goal, execution, or approval records disagree.
- The active mission or goal cannot be found.
- A required operating file is missing.
- Artifact validation makes authority or active work ambiguous.
- Requested goal-directed work falls outside the active mission or goal.
- A material decision lacks required approval.
- Proceeding would weaken governance or validation merely to obtain success.

A missing implementation tool does not suspend this protocol. Operate the same process manually and record the capability limitation.
