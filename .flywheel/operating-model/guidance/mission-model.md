# Mission and Goal Model

## Hierarchy

Work is organized as Mission -> Goal -> Execution.

- A mission defines an outcome worth achieving.
- A goal defines a bounded, testable step toward the mission.
- An execution records one attempt to complete a goal.

## Invariants

- No repository-changing work may occur outside an active mission.
- No execution may occur outside an active goal.
- Every goal must belong to exactly one mission.
- Every execution must identify exactly one goal.
- A goal must define objective, scope, acceptance criteria, required evidence, and validation before execution begins.
- Only one goal is active unless governance explicitly permits concurrency.
- Application goals are prohibited until readiness is `ready-for-missions`.
- A mission cannot complete while any required goal is incomplete, blocked without disposition, or unsupported by evidence.

## Goal states

Allowed states are `proposed`, `ready`, `active`, `blocked`, `completed`, `cancelled`, and `failed`.

Transitions:

- `proposed -> ready` after definition is complete.
- `ready -> active` when state selects the goal.
- `active -> blocked` when progress requires unresolved external action.
- `blocked -> active` when the blocker is resolved.
- `active -> completed` only after acceptance and validation succeed.
- `active -> failed` only when the goal is no longer reasonably achievable as defined.
- Any nonterminal state may become `cancelled` by human authority.

An execution failure does not automatically fail its goal. It normally produces findings and another execution or adaptation.

## Scope control

New work discovered during execution must be classified as:

- Required to satisfy the current goal.
- A defect or blocker preventing the current goal.
- A separate future goal.
- Out of scope.

The operator may not silently absorb material new scope.