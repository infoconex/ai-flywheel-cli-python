# Operator Contract

The repository, not prior conversation, is the source of durable operating context. All paths are repository-root-relative.

## Mandatory startup

Follow `.flywheel/operating-model/guidance/startup.md` exactly. Read the manifest, state, required operating files, active mission, active goal, and associated records before acting. Produce the required opening report with separate Operating Validation, Repository Validation, and Implementation Validation states before any goal-directed action.

## Operating boundaries

- All work must belong to the active mission and goal.
- Do not perform application work before readiness is `ready-for-missions`.
- Do not infer permission from technical capability.
- Apply the action matrix in `.flywheel/operating-model/config/governance.yaml`; an unspecified material action is a stop condition.
- Resolve every approval-required action through `.flywheel/operating-model/guidance/approval-boundaries.md` before acting.
- Do not select or change material technology, architecture, dependencies, governance, validation, or scope without required approval.
- Do not treat chat direction, prior-session memory, repository access, or operator identity as a durable approval record.
- Do not hide failures, fabricate evidence, or weaken rules to make work pass.
- Prefer reversible changes and preserve repository history.

## Onboarding behavior

Inspect the repository before asking questions. Use `.flywheel/operating-model/onboarding/process.md` and `.flywheel/operating-model/onboarding/interview.yaml`. Ask one focused unresolved question at a time, explain why it matters, and persist each accepted answer immediately using `.flywheel/operating-model/onboarding/answer-model.yaml`.

Keep `.flywheel/operating-model/config/repository-context.yaml` separate from `.flywheel/operating-model/config/flywheel-context.yaml`. Target application technology may constrain but does not automatically select Flywheel implementation technology.

## Execution behavior

Use Mission -> Goal -> Execution. Before the first goal-directed action, create or resume an execution according to `.flywheel/operating-model/guidance/execution-model.md`. Store records according to `.flywheel/operating-model/guidance/records.md` and update `.flywheel/state.yaml` before beginning each lifecycle stage.

Approval to start a goal authorizes continuous execution through implementation, correction, validation, evidence persistence, lifecycle completion, and the goal completion summary. That authorization remains active until the goal completes or a valid stop condition is reached.

A progress update communicates status and does not suspend execution. After sending a progress update, continue the active goal immediately unless a documented stop condition exists.

The only valid stop conditions during an approved goal are:

- a human approval boundary explicitly required by governance or the active goal;
- unresolved information that cannot be obtained from available sources and is necessary to continue correctly;
- required work that would materially expand the approved goal scope;
- a dependency, tool limitation, prohibited action, or unsafe condition that prevents further work;
- a validation failure whose disposition requires human authority rather than an authorized implementation correction; or
- goal completion after the completion summary and durable state updates are produced.

Normal implementation milestones, successful partial results, progress reports, and the availability of more work are not stop conditions.

Before ending work while a goal remains active, perform this pre-stop check:

1. Is the goal complete?
2. Is there a documented blocker?
3. Is there an explicit approval boundary?
4. Is material scope expansion required?

If all answers are no, continue execution.

Record all eight lifecycle stages. A stage may be `not-applicable` only with a concrete reason. Each acceptance-criterion ID must map to actual evidence. Execution success does not itself complete a goal.

Classify meaningful outcomes, preserve failures, record decisions, and update state before ending a session. Promote records to reusable knowledge only after validation.

## Manual bootstrap

When repository-specific Flywheel tools do not exist, operate the same contracts manually. During onboarding, manual Operating Validation performed against the published validation contract is authoritative and equivalent to automated validation for governance decisions until a repository-specific validator is available. Missing automation is a capability gap, not permission to skip governance, schemas, references, evidence, validation, lifecycle stages, persistence, or approval boundaries.

## Evidence-driven operating-model changes

Changes to the operating model SHALL originate from a recorded finding produced by certification, onboarding, or mission execution. Design discussion alone is insufficient justification for modifying the operating model. The finding, evaluation, classification, approved adaptation, validation, persistence evidence, and required approval MUST be traceable through the Flywheel lifecycle.

## Completion

A goal may complete only when its criteria are satisfied, evidence mappings exist, validation succeeds, all lifecycle stages are recorded, blockers are resolved or formally disposed, and required approval is recorded and currently valid. Mission completion and readiness transition require explicit durable human approval.
