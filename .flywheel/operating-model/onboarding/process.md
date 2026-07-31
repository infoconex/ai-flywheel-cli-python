# Adaptive Onboarding Process

Onboarding prepares the Flywheel to operate future missions. It does not perform application work.

All paths in this document are repository-root-relative.

## Two contexts

Onboarding must keep separate:

- Target repository context: purpose, application technologies, architecture, build, tests, standards, constraints, and domain knowledge. Persist this in `.flywheel/operating-model/config/repository-context.yaml`.
- Flywheel implementation context: language, runtime, architecture, tests, storage, logging, command interface, dependencies, and deployment of the operating tools. Persist this in `.flywheel/operating-model/config/flywheel-context.yaml` and `.flywheel/operating-model/config/capabilities.yaml`.

Target repository technologies are evidence, not automatic Flywheel implementation choices.

## Process

1. Inspect the repository before interviewing the human.
2. Record direct discoveries with source and confidence.
3. Load existing configuration and documentation.
4. Identify contradictions, unknowns, decisions, and approval requirements.
5. Execute applicable questions from `.flywheel/operating-model/onboarding/interview.yaml` one at a time.
6. Explain why each question matters and present discovered options when useful.
7. Persist each confirmed answer immediately using `.flywheel/operating-model/onboarding/answer-model.yaml`.
8. Reconcile answers with repository evidence.
9. Record unresolved items as unknown, deferred, rejected, or blocked rather than guessing.
10. Validate onboarding completeness against the next readiness gate.

## Question behavior

Do not ask for information already established by strong evidence unless confirmation is required. Prefer contextual questions such as:

> I found .NET and PowerShell in the repository. These describe available technologies but do not determine the Flywheel implementation. Which runtimes are acceptable for the Flywheel tools?

## Provenance

Every material value must use one of the provenance values authorized by `.flywheel/operating-model/config/validation.yaml`:

- `discovered`: directly inspected from repository or environment evidence.
- `provided`: supplied by the human.
- `inferred`: reasoned from evidence and awaiting confirmation when material.
- `defaulted`: supplied by framework policy.
- `approved`: explicitly accepted by an authorized human.
- `deferred`: intentionally postponed with rationale.
- `rejected`: explicitly considered and not selected, with rationale.

## Completion

Onboarding context discovery is complete only when required repository context, governance, validation expectations, capability requirements, and unresolved decisions are sufficient to enter reconciliation. Tool implementation and application work remain separate later stages.
