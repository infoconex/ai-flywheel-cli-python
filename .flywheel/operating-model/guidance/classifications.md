# Classifications

This document is normative. `MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, and `SHALL NOT` define mandatory behavior.

Material outcomes may have more than one classification.

- **Defect**: Existing behavior fails an expected requirement and requires correction.
- **Finding**: Relevant information discovered during work that may affect current or future decisions.
- **Decision**: A choice made between alternatives, including rationale, authority, and consequences.
- **Improvement**: A proposed or completed change that strengthens the application or Flywheel operating system.
- **Risk**: A possible future event or condition that could negatively affect outcomes.
- **Uncertainty**: Material information is missing, ambiguous, inferred, or insufficiently validated.
- **Failure**: An attempted action did not achieve its intended result.
- **Validated learning**: A reusable conclusion supported by completed validation.

## Structured classification contract

Every material classification MUST use the structured classification model in `execution.schema.yaml`.

Each classification MUST include:

- A stable `CLASS-NNN` identifier unique within the execution.
- One permitted classification type.
- A concise statement of the classified outcome.
- At least one reference to a supporting evaluation.
- At least one evidence reference.
- A rationale.
- A certainty value.
- Explicit uncertainty when certainty is provisional or disputed.
- Conflict and related-classification references.
- Type-specific record references required by the schema.

Classification identifiers, evaluation references, evidence references, conflict references, related-classification references, decision references, finding references, and validation references MUST resolve to existing artifacts or entries in the same proposed transition set.

## Semantic rules

- `CLASSIFICATION-PROVENANCE-001`: A classification MUST be supported by at least one evaluation and traceable evidence.
- `CLASSIFICATION-IDENTITY-001`: Classification identifiers MUST be unique within an execution.
- `CLASSIFICATION-TYPE-001`: Classification types MUST use the published enum and MUST NOT be encoded as free-form labels.
- `CLASSIFICATION-CERTAINTY-001`: An inconclusive or conflicted evaluation MUST NOT produce a confirmed defect, failure, decision, improvement, or validated-learning classification.
- `CLASSIFICATION-UNCERTAINTY-001`: Material uncertainty MUST remain explicit and MUST NOT be silently promoted to a confirmed classification.
- `CLASSIFICATION-BOUNDARY-001`: Recommendations and adaptations MUST NOT be represented as classifications.
- `CLASSIFICATION-DECISION-001`: A decision classification MUST reference an existing decision record.
- `CLASSIFICATION-FINDING-001`: Defect, finding, improvement, risk, uncertainty, and failure classifications MUST reference an existing finding record.
- `CLASSIFICATION-LEARNING-001`: Validated learning MUST reference completed validation evidence and MUST NOT be asserted before Validate completes.

An operator or validator MUST reject any classification that violates these rules even when the individual execution document satisfies its schema.

## Evaluate completion

Evaluate MUST NOT be completed unless:

- At least one structured evaluation exists.
- The Evaluate stage contains at least one reference.
- Every material conclusion is represented by a structured evaluation.
- Every evaluation references existing observations and evidence.
- No classification has been asserted as an evaluation output.

If no material evaluation exists, Evaluate MUST be marked `not-applicable` with a concrete reason rather than `completed` with an empty evaluation set.

## Classify completion

Classify MUST NOT be completed unless:

- At least one structured classification exists.
- The Classify stage contains at least one reference.
- Every classification satisfies provenance, identity, certainty, boundary, and type-specific rules.
- All referenced records and entries resolve.

If no material outcome requires classification, Classify MUST be marked `not-applicable` with a concrete reason.

Classifications describe the outcome; they do not replace the underlying evidence. Record relationships among classifications when, for example, a failure exposes a defect and produces validated learning after validation.
