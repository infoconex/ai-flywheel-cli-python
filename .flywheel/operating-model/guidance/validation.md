# Validation

This document is normative. `MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, and `SHALL NOT` define mandatory behavior.

Validate proves or disproves the outcome claimed for an implemented adaptation. Command completion alone is not proof.

## Structured validation contract

Every material validation MUST use the `validation_result` model in `execution.schema.yaml` and a stable `VAL-NNN` identifier unique within the execution.

A validation entry MUST identify:

- Whether it is a `planned` validation or an `executed` result.
- One or more target adaptations.
- At least one acceptance criterion or operating rule.
- The validation domain, severity, method, and immutable scope.
- The expected outcome and expected evidence established before execution.
- Eligibility or a concrete exclusion reason.
- The actual outcome, execution time, and collected evidence after execution.
- A finding and recovery action when validation fails.
- The prior validation it supersedes when a revised plan is required.

## Planning and activation

Before Validate becomes `in-progress`, every validation-eligible adaptation MUST have at least one planned validation entry. A planned entry uses:

- `phase: planned`
- `status: pending`
- `actual_outcome: null`
- `evidence_refs: []`
- `executed_at: null`

`VALIDATION-ELIGIBILITY-001`: An adaptation is validation-eligible only when it is approved when approval is required and its `implementation_status` is `completed`. Rejected, deferred, pending-approval, new-goal-required, not-started, or partially implemented adaptations MUST NOT pass validation.

`VALIDATION-COVERAGE-001`: Every eligible adaptation MUST be covered by at least one validation entry, and every validation entry MUST reference an existing adaptation.

`VALIDATION-BASIS-001`: Every validation MUST reference at least one acceptance criterion or operating rule and MUST define its method, scope, expected outcome, and expected evidence before execution.

## Execution and evidence

An executed validation MUST preserve the planned adaptation references, criterion and rule references, method, scope, expected outcome, and expected evidence. A revised validation MUST receive a new identity and use `supersedes_ref`; prior failed evidence MUST remain intact.

`VALIDATION-EVIDENCE-001`: A passed or failed validation MUST include evidence proving the actual outcome. A command exit code or assertion that a command ran is insufficient unless the expected outcome specifically concerns command execution.

`VALIDATION-RESULT-001`: `passed` requires an eligible implemented adaptation, a supported actual outcome, and sufficient evidence. `failed` requires evidence, a finding reference, and a recovery action. `not-applicable` requires `eligible: false` and a concrete exclusion reason.

`VALIDATION-STRENGTH-001`: After failure, the operator MUST NOT weaken the criterion, rule, scope, expected outcome, or expected evidence merely to obtain a pass. Any legitimate change requires a new validation entry, explicit rationale in the associated finding or decision, and `supersedes_ref` to the prior validation.

`VALIDATION-IDENTITY-001`: Validation identifiers MUST be unique within the execution.

## Failed-validation disposition

A failed required validation remains failed and immutable. Any later authorization MUST be represented by a decision record using `decision.validation_disposition` from `record.schema.yaml`; the failed validation result itself is not rewritten.

The finite permitted dispositions are:

- `retry-required`: The validation must be rerun after the stated recovery action. Persistence is blocked.
- `adaptation-required`: Work must return to Classify or Adapt. Persistence is blocked.
- `accepted-risk`: The authorized decision accepts the failed condition for the exact recorded scope. Persistence is permitted.
- `waived`: The authorized decision explicitly waives the failed requirement for the exact recorded scope. Persistence is permitted.

Every failed-validation disposition MUST:

- Reference exactly one failed validation through `validation_ref`.
- Reference that validation's `finding_ref` through `finding_ref`.
- Repeat the applicable scope and recovery action.
- State whether persistence is permitted consistently with the disposition status.
- Be stored in a decision record whose `source_refs` contain both the validation ID and finding ID.
- Be referenced by the execution's `decision_refs`.
- Include approval references when `approval_required: true`; those approval records MUST resolve, authorize the same validation and scope, and also appear in execution `approval_refs`.

`VALIDATION-DISPOSITION-001`: `retry-required` and `adaptation-required` MUST use `permits_persistence: false`; `accepted-risk` and `waived` MUST use `permits_persistence: true`.

`VALIDATION-DISPOSITION-LINK-001`: The decision's `validation_ref`, `finding_ref`, scope, recovery action, execution, mission, and goal MUST agree with the exact failed validation and its finding. An execution-level decision reference without this direct structured link does not authorize persistence.

`VALIDATION-DISPOSITION-AUTH-001`: When approval is required, every referenced approval MUST be approved, resolve to the same execution, validation, finding, and scope, and be included in the execution's `approval_refs`.

`VALIDATION-DISPOSITION-SUPERSESSION-001`: A changed disposition requires a new decision record that references the prior decision in `source_refs`. The prior decision remains immutable. The latest accepted non-superseded decision governs.

## Adaptation status synchronization

`VALIDATION-SYNC-001`:

- An eligible adaptation with planned but unexecuted validations uses `validation_status: pending`.
- An adaptation uses `validation_status: passed` only when every required validation covering it has passed and none remains pending or failed.
- An adaptation uses `validation_status: failed` when any required validation covering it has failed and no later approved validation supersedes and passes it.
- An ineligible adaptation uses `validation_status: not-applicable` with corresponding not-applicable validation coverage when the reason must remain traceable.

An accepted-risk or waived disposition does not change the adaptation's `validation_status` from `failed`; it only determines whether Persist may begin.

## Validate completion

Validate MUST NOT be completed unless:

- At least one structured validation entry exists.
- The Validate stage references its validation entries.
- Every validation identifier and reference resolves.
- Every eligible adaptation has complete validation coverage.
- No required validation remains `pending`.
- Every passed or failed result has sufficient evidence.
- Every failed result has a finding and recovery action.
- Adaptation validation statuses agree with their covering validation results.
- Stage summary and timestamps exist.

Validate may complete with a failed result when its evidence, finding, and recovery action are complete. Validate completion alone does not authorize Persist.

If no adaptation is eligible for validation, Validate MUST be `not-applicable` with a concrete reason. Validation entries MAY record explicit exclusions when traceability is material.

## Lifecycle boundaries

Validate MUST NOT claim persistence or reuse. Persist cannot begin while any required validation is pending. A failed required validation blocks Persist unless the latest accepted non-superseded linked disposition is `accepted-risk` or `waived` and all required authorization rules pass. Failed validation returns work to classification or adaptation when its disposition is `retry-required` or `adaptation-required`; it does not erase the failed result or silently rewrite the original validation basis.
