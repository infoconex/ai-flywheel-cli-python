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
3. Record material discoveries and decisions as they occur.
4. Do not perform application work during Flywheel onboarding unless the active goal explicitly authorizes it.
5. Do not assume the target repository's language, framework, or test framework must be used for Flywheel operating tools.
6. Treat approval to start the goal as authorization to continue through implementation, correction, validation, evidence persistence, lifecycle completion, and the completion summary.
7. Treat progress updates as non-blocking; continue immediately after the update unless a documented stop condition exists.
8. Correct implementation, test, and validation failures within the approved scope and rerun the affected checks without requesting renewed approval.
9. Stop only for an approval boundary, unresolved blocker, required material scope expansion, prohibited or unsafe action, failure requiring human disposition, or goal completion.
10. Before stopping, verify whether the goal is complete, a blocker exists, an approval boundary exists, or scope expansion is required. If none applies, continue execution.

## Failure Handling

1. Preserve the command, inputs, output, and relevant environment information.
2. Classify the failure.
3. Determine whether the cause belongs to application code, Flywheel tooling, configuration, guidance, validation, or external conditions.
4. Adapt only within the active goal's authority.
5. Re-run validation after adaptation.
6. Persist failed approaches when they provide reusable evidence or learning.
7. Do not stop for a correctable failure within the approved scope.

## Completion

1. Check every acceptance criterion.
2. Link each criterion to evidence.
3. Confirm required approvals.
4. Persist records and validated learning.
5. Update goal, mission, and global state.
6. Produce the goal completion summary.
7. Identify follow-up work without silently executing it outside the active goal.
