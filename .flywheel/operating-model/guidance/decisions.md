# Decision Model

A decision record preserves a consequential choice and its basis.

## Record a decision when

- Selecting Flywheel implementation language, runtime, architecture, storage, or testing approach.
- Accepting risk or a known limitation.
- Changing mission scope, governance, validation, or operating behavior.
- Choosing between materially different approaches.
- Deferring or rejecting a required capability.
- Resolving conflicting repository evidence or human preferences.

## Required fields

A decision must identify:

- Mission, goal, and execution context.
- Decision statement.
- Status: `proposed`, `approved`, `rejected`, `superseded`, or `deferred`.
- Options considered.
- Evidence and constraints.
- Rationale and consequences.
- Required approver and approval evidence when applicable.
- Superseded decision when replacing an earlier choice.

## Approval

An operator recommendation is not approval. Approval exists only when recorded from an authorized human or when governance explicitly delegates that decision class.

## Reconsideration

A decision may be revisited when new evidence invalidates its assumptions, constraints materially change, or execution demonstrates unacceptable consequences. Do not silently rewrite history; create a new decision that supersedes the prior one.