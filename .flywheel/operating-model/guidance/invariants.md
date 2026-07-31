# Operator Invariants

This document is normative. These invariants MUST hold at every persisted state boundary.

1. Exactly one mission is active when `state.active_mission` is not null.
2. Exactly one goal is active within the active mission when `state.active_goal` is not null.
3. Zero or one execution is active.
4. An active execution belongs to the active goal and active mission.
5. `state.lifecycle_stage` equals the active execution lifecycle stage.
6. `state.status` is `active` when an execution is active.
7. Every goal belongs to exactly one mission.
8. Every execution belongs to exactly one goal.
9. Every execution records all eight lifecycle stages.
10. Every acceptance criterion has stable identity and mapped evidence before goal completion.
11. Every material fact, inference, decision, approval, deferral, and rejection has provenance.
12. Material inferred values are not authoritative until confirmed or approved.
13. Application work is prohibited unless `readiness` is `ready-for-missions` and `application_missions_allowed` is true.
14. No operator may weaken governance, validation, evidence, or history to make work appear successful.
15. Conflicting authoritative artifacts block affected work until reconciled.
16. Readiness transitions require validation evidence and human approval.

The validator MUST report every violated invariant with the affected artifact and required recovery action.
