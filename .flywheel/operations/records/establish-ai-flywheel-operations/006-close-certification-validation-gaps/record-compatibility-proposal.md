# Record Compatibility Proposal

## Finding

The onboarding record inventory contains two contracts:

1. Canonical records conforming to `record.schema.yaml`.
2. Earlier bootstrap evidence using heterogeneous legacy shapes created before schema-backed enforcement existed.

The legacy records are durable historical evidence and should not be rewritten casually. Requiring an immediate bulk migration would alter many historical artifacts and create avoidable provenance risk. Ignoring them entirely would make certification incomplete.

## Proposed policy

Adopt a bounded legacy compatibility profile for this onboarding mission:

- Canonical JSON Schema validation is mandatory for missions, goals, executions, state, manifest, certification records, approvals, and every new general record.
- Existing legacy evidence records created before Goal 006 may be validated through a dedicated `legacy-bootstrap-evidence.schema.yaml` compatibility schema.
- The compatibility schema validates identity, parent references when present, timestamps, summary, source information, and stable placement without pretending that legacy evidence has the full canonical record shape.
- No new legacy-shaped record may be created after the Goal 006 approval timestamp.
- Legacy compatibility is limited to the `establish-ai-flywheel-operations` onboarding mission and must be listed as a known certification limitation.
- A future migration may convert historical evidence only through a separately approved, provenance-preserving process.
- Readiness may proceed when all legacy records pass the compatibility schema, all new records pass canonical schemas, and all cross-reference and completion invariants pass.

## Alternatives considered

### Bulk migration now

Rejected as the default because it would rewrite a large historical evidence set, increase review volume, and risk changing provenance during certification.

### Exclude legacy records from validation

Rejected because it would leave evidence completeness unverifiable.

### Treat every legacy shape as canonical

Rejected because it would weaken `record.schema.yaml` and normalize inconsistent historical structures for future work.

## Approval requested

Approve the bounded legacy compatibility profile above for historical onboarding evidence only. Approval does not waive schema validation, cross-reference checks, completion rules, or the deferred pre-release Ruff, mypy, and Hatchling gates.
