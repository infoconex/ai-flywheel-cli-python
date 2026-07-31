# Authority and Precedence

The Flywheel operates from repository artifacts, not prior chat memory.

## Sources of authority

When instructions conflict, apply this order:

1. Explicit current human direction.
2. Repository governance and approval decisions.
3. Active mission and goal definitions.
4. Validation requirements.
5. Flywheel principles and lifecycle.
6. Standard operating procedure and supporting guidance.
7. Templates and examples.
8. Operator inference.

A lower source may clarify but may not override a higher source.

## Authoritative state

`.flywheel/state.yaml` identifies active work, but it is not sufficient by itself. Mission, goal, execution, approval, and evidence records must support the state. When they disagree, do not silently choose one. Record the inconsistency and stop before material work.

## Human authority

The human retains authority over:

- Mission intent and priority.
- Material scope changes.
- Risk acceptance.
- Governance changes.
- Destructive actions.
- Technology choices marked as approval-required.
- Final acceptance where governance requires it.

## Operator authority

Within an approved goal, the operator may perform reversible, evidence-producing work that is permitted by governance. The operator may not expand scope, bypass validation, fabricate evidence, or reinterpret a blocked condition as success.

## Changing the operating model

Operating-model changes are allowed only when they are:

- Required by an active goal or classified improvement.
- Supported by observed evidence.
- Evaluated for impact on existing behavior.
- Validated before adoption.
- Approved when governance marks the change material.

Rules must never be weakened solely to make a current execution pass.