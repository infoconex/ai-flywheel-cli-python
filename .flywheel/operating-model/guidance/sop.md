# Standard Operating Procedure

## Startup

1. Read `.flywheel/manifest.yaml` and `.flywheel/state.yaml`.
2. Read all operating-model configuration and guidance.
3. Read the active mission, active goal, relevant records, and applicable knowledge.
4. Confirm the requested work is authorized by the active goal.
5. Identify required approvals, validation, evidence, and constraints before changing the repository.

## Execution

1. Create or continue an execution record for the active goal.
2. Follow the lifecycle: Execute, Observe, Evaluate, Classify, Adapt, Validate, Persist, Reuse.
3. Treat approval to start the goal as authorization to continue through implementation, correction, validation, evidence persistence, lifecycle completion, and the goal completion summary.
4. Record material discoveries and decisions as they occur.
5. Provide progress updates when useful, but continue immediately after each update unless a valid stop condition exists.
6. Do not perform application work during Flywheel onboarding unless the active goal explicitly authorizes it.
7. Do not assume the target repository's language, framework, or test framework must be used for Flywheel operating tools.
8. Stop only when a human approval boundary, unresolved necessary information, material scope expansion, prohibited or unsafe action, blocking dependency or tool limitation, human-disposition validation failure, or goal completion is reached.
9. Do not stop merely because implementation reached a milestone, partial work succeeded, or a status update was produced.

## Pre-stop check

Before ending work on an active goal, answer:

1. Is the goal complete?
2. Is there a documented blocker?
3. Is there an explicit approval boundary?
4. Is material scope expansion required?

If every answer is no, continue execution.

## Failure Handling

1. Preserve the command, inputs, output, and relevant environment information.
2. Classify the failure.
3. Determine whether the cause belongs to application code, Flywheel tooling, configuration, guidance, validation, or external conditions.
4. Adapt only within the active goal's authority.
5. Correct implementation and validation failures that are within the approved goal without requesting renewed approval.
6. Re-run validation after adaptation.
7. Persist failed approaches when they provide reusable evidence or learning.
8. Stop only when failure disposition requires human authority or continued work is blocked by a valid stop condition.

## Completion

1. Check every acceptance criterion.
2. Link each criterion to evidence.
3. Confirm required approvals.
4. Persist records and validated learning.
5. Update goal, mission, and global state.
6. Produce the goal completion summary.
7. Identify follow-up work without silently executing it outside the active goal.
