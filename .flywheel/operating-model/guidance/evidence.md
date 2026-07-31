# Evidence Model

Evidence is the recorded basis for claims, decisions, validation, and completion.

## Evidence requirements

Evidence must be:

- Traceable to a mission, goal, and execution.
- Specific enough to reproduce or independently inspect.
- Captured from actual results rather than expected results.
- Stored or referenced durably.
- Clearly distinguished from interpretation.

## Evidence types

- `repository-observation`: files, configuration, structure, or behavior directly inspected.
- `command-result`: command, environment, exit status, and relevant output.
- `test-result`: test command, scope, counts, failures, and result.
- `validation-result`: rule checked, method, and outcome.
- `change-reference`: changed files, commit, patch, or artifact.
- `human-approval`: decision, approver, date, and approved scope.
- `external-reference`: authoritative external source and relevance.
- `manual-verification`: steps performed, observer, and observed result.

## Claims

Claims such as `build succeeded`, `tests passed`, `requirement met`, or `human approved` are invalid unless linked to evidence.

Summaries may cite evidence but must not replace it. Raw output may be shortened when large, provided the command, outcome, significant errors, and durable source are retained.

## Evidence quality

Evidence is insufficient when it is ambiguous, stale, unrelated to the criterion, generated from an unapproved environment, or contradicted by stronger evidence.

## Completion proof

Each acceptance criterion must map to one or more evidence records. Unmapped criteria remain incomplete. Validation must evaluate the evidence, not merely repeat the operator's completion claim.