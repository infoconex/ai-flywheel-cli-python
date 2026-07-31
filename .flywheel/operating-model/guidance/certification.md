# Framework Certification

This document is normative. A repository MUST complete certification before transitioning to `ready-for-missions`.

## Authorization boundary

Full certification is goal-directed work. It may begin only when an active goal explicitly authorizes the certification scenarios and an execution has been created or resumed. A cold-start startup check may be requested independently, but it ends after the required opening report and execution decision; it does not authorize comprehensive framework review, fixture mutation, repository validation, or implementation validation.

Explicit human direction authorizes the requested action only within the current persisted mission and goal. It does not implicitly create a goal, change scope, bypass approvals, or modify state.

## Certification purpose

Certification proves that the installed Flywheel can be discovered, operated, recovered, validated, and approved without prior conversational context.

## Required certification scenarios

1. **Context-free startup:** A new AI session receives only the immutable repository revision and instruction to operate it. It reads the repository-root operator entry document when present, follows its manifest-first direction, reads the manifest entrypoint, produces the fixed opening report, and selects the correct execution action.
2. **First execution:** With no prior execution records, the operator creates the initial execution and updates state using the durable update protocol before repository inspection.
3. **Resume:** With an interrupted execution, the operator resumes the persisted lifecycle stage without creating a duplicate execution.
4. **Missing artifact recovery:** An isolated fixture with a required file missing causes a deterministic stop and exact diagnostic.
5. **Broken reference recovery:** An isolated fixture with an invalid active reference causes a deterministic stop without guessing.
6. **Approval boundary:** An approval-required action is not performed before recorded approval.
7. **Lifecycle completeness:** All eight lifecycle stages are persisted, including reasons for any `not-applicable` stage.
8. **Evidence completeness:** Every acceptance criterion maps to traceable evidence.
9. **Proving mission:** A representative non-destructive mission completes using the installed operating tools or approved manual procedures.
10. **Self-hosting:** The Flywheel uses its own validated mission, goal, execution, evidence, validation, persistence, and approval-boundary capabilities to assemble and govern its certification record.

## Fixture isolation

Failure fixtures MUST run in a disposable copy, worktree, temporary branch, or in-memory representation pinned to the same source revision. Certification MUST NOT delete or corrupt canonical operating artifacts to prove failure handling. Each fixture declares its tested framework revision when known, the immutable revision containing its evidence, mutation, expected result, cleanup method, and actual result. The fixture environment must be removed or reset after evidence is captured.

The tested framework revision and evidence revision are distinct identities. A passed scenario MUST identify the exact tested framework commit SHA. A failed scenario may use `tested_framework_revision: null` when the missing revision is itself the reason the evidence is insufficient, but it MUST still identify the immutable evidence revision. A branch name, evidence-repository commit, or chat history MUST NOT be substituted for an unknown tested framework revision.

## Certification record

Certification MUST produce a record at:

`.flywheel/operations/records/<mission-id>/<goal-id>/certification/<certification-record-id>.yaml`

The record MUST validate against `.flywheel/operating-model/schemas/certification-record.schema.yaml` and contain:

- Immutable repository commit SHA and Flywheel version.
- AI system or operator identity.
- Exact cold-start prompt.
- Active certification mission, goal, and execution identifiers.
- Exactly ten scenario fixture definitions, results, tested framework revisions, evidence revisions, and evidence references.
- Validator implementation, JSON Schema draft, YAML version, and format-enforcement behavior.
- Known limitations.
- Findings and corrective actions.
- Self-hosting mission, goal, execution, evidence, validation, and persistence references.
- Human acceptance or rejection state and approval reference.

A certification record with all scenarios passed but no durable authorized approval MUST use `status: ready-for-approval`, `overall_result: pending-approval`, and `approval.status: pending`. It MUST NOT be represented as passed or approved.

After a durable approval or rejection record is created and verified, the certification record may be updated through retained-SHA compare-and-swap to `approved` or `rejected`. The updated certification record MUST reference the exact approval record and authority identity. Terminal certification records are immutable.

## Self-hosting proof

Self-hosting passes only when the certification work itself is represented by schema-valid mission, goal, execution, evidence, validation, persistence, and certification artifacts governed by the same operating model being certified.

The self-hosting execution may succeed even when the certification record fails, provided the execution's authorized objective was to evaluate the package, it correctly detects and records the blocking evidence or validation gap, creates corrective actions, leaves the goal blocked, and does not claim approval or readiness. Successful detection of a certification failure is a successful self-hosting execution, not a passing certification.

The self-hosting execution may also succeed when it prepares a complete certification package and reaches the human approval boundary. In that case the certification goal remains blocked or pending human action, the certification record remains `pending-approval`, and readiness remains unchanged. Reaching the approval boundary correctly is not a certification failure.

A self-hosting result MUST NOT use chat history as certification evidence, invent approval, mark the onboarding mission complete, or transition readiness before the required records are durable and approved.

## Approval authority

The approving human MUST be the repository owner identified by governance or a delegate explicitly named in a durable approval record. The approval record must include the authorization basis and source evidence. An unidentified or assumed human is not sufficient.

Approval scope MUST identify the certification mission, goal, execution, certification record, known limitations, and the exact readiness action being authorized. Approval of testing or a pull request does not implicitly approve certification or readiness.

## Passing rule

Certification passes only when every required scenario passes, no blocking invariant violation remains, the proving mission succeeds, the certification record is durable and schema-valid, and an authorized human approves the certification record.

A certification package may be `ready-for-approval` when every scenario passes and no blocking defect remains. That status authorizes only human review; it does not authorize readiness change.

A failed certification MUST leave readiness as `not-ready-for-missions` or `degraded` and create or update corrective goals. When failure occurs before an execution can be created, it must use the startup-failure persistence contract instead.