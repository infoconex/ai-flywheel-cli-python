# Approval Boundaries

This document is normative. `MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, and `SHALL NOT` define mandatory behavior.

Approval is a durable authorization boundary. Technical capability, operator confidence, prior chat context, and an unrecorded human statement do not satisfy an action that governance marks `approval_required` or `finding_and_approval_required`.

## Normative relationship

`authority.md` defines precedence, `governance.yaml` defines action classes and authorized identities, `records.md` defines canonical storage, and `approval-record.schema.yaml` defines the durable approval record. This document provides the specific rules for deciding whether an approval authorizes an action.

For `kind: approval`, `approval-record.schema.yaml` is authoritative. The generic approval shape retained in `record.schema.yaml` MUST NOT be used as the sole validator for a new approval record.

## Authority registry

The operator MUST resolve the approving identity from `.flywheel/operating-model/config/governance.yaml`.

A repository-owner approval is valid only when:

- `authority_id` exactly matches the configured repository owner authority.
- The durable identity source matches the configured owner identity.
- `authority_role` is `repository-owner`.
- `authorization_basis` is `repository-ownership`.

A delegate approval is valid only when:

- `authority_id` exactly matches one configured delegate.
- The delegate has a durable, currently effective delegation approval.
- The delegation approval was issued by the repository owner or another delegate whose own delegation permits delegation.
- The delegation scope contains the requested action, mission, goal, execution, targets, and constraints.
- The delegation is not rejected, deferred, expired, superseded, revoked, or otherwise inactive.

The operator MUST NOT infer authority from a display name, email resemblance, chat identity, repository access, commit authorship, or technical ability.

## Approval record

Every durable approval MUST conform to `approval-record.schema.yaml` and be stored at:

`.flywheel/operations/records/<mission-id>/<goal-id>/approvals/<approval-id>.yaml`

Approval IDs MUST use `APPROVAL-NNN` and be unique within the goal record set.

Approval records are create-only history. A changed decision, corrected scope, renewal, delegation, revocation, or supersession requires a new approval record. Existing approval content MUST NOT be overwritten.

The approval record MUST identify:

- The exact authority identity and role.
- The authorization basis.
- One decision: `approved`, `rejected`, or `deferred`.
- The exact mission, goal, execution, action, targets, and constraints.
- Decision, effective, and optional expiration timestamps.
- Evidence references supporting the human decision and identity.
- Delegation, supersession, and revocation relationships when applicable.

The top-level mission, goal, and execution MUST equal the corresponding values in `approval.scope`.

## Durable-before-action rule

When governance requires approval:

1. The operator MAY describe or record the proposed action.
2. The operator MUST NOT perform the action yet.
3. The human decision and identity evidence MUST be captured.
4. The approval record MUST be created through a persistence plan, re-read, schema-validated, reference-validated, and verified.
5. The plan MUST be terminal `applied` with final verification `passed`.
6. The operator MUST re-resolve the approval immediately before the authorized action.
7. Only then may the exact approved action begin.

An approval created after the action began cannot retroactively authorize the action.

Current human direction can supply decision evidence, but it does not bypass durable recording when governance requires recorded approval. The direction authorizes only the requested action within the active persisted mission and goal.

## Exact scope matching

An approval authorizes only the exact action represented by `approval.scope`.

The operator MUST verify all of the following:

- Approval mission equals the active mission.
- Approval goal equals the active goal.
- Approval execution equals the active execution when the action is execution-scoped.
- Approval action exactly equals the governance action being attempted.
- Every material target is included in `target_refs`.
- No unlisted material target is changed.
- Every constraint is satisfied.
- The action remains inside the active goal unless separately approved scope expansion exists.

A wildcard, vague phrase, implied permission, adjacent action, prior similar action, or broader technical capability MUST NOT be treated as exact scope.

One approval MAY authorize multiple targets only when every target is explicitly listed and the action and constraints apply to all of them. It MUST NOT be reused for a different action or execution.

## Decision and time validity

Only `decision: approved` can authorize an action.

- `rejected` prohibits the action.
- `deferred` does not authorize the action in the current execution.
- An approval is inactive before `effective_at`.
- An approval is inactive at or after `expires_at` when expiration is present.
- A superseded approval is inactive.
- A revoked approval is inactive from the effective time of the valid revocation record.
- A record whose top-level status conflicts with its decision is invalid.

The action timestamp MUST be at or after `effective_at`, before `expires_at` when present, and after durable approval-plan completion.

## Revocation and supersession

Revocation requires a new approval record with:

- `decision: approved`.
- `scope.action: revoke_approval`.
- `revokes_ref` identifying the approval being revoked.
- Authority that is equal to or higher than the original approving authority.
- Evidence of the revocation decision.

Supersession requires a new approval record with `supersedes_ref`. The superseded approval no longer authorizes new work once the superseding record becomes effective.

A rejected or deferred record does not revoke a separate earlier approval unless it explicitly and validly revokes or supersedes it.

## Finding-and-approval actions

For `finding_and_approval_required` actions, both conditions are mandatory:

- A durable finding exists and supports the proposed action.
- A valid durable approval exactly authorizes the action and targets.

Approval cannot replace the finding, and a finding cannot replace approval.

## Fresh-session resolution

A fresh operator session MUST derive authorization only from:

- The active mission, goal, and execution.
- The governance action matrix and authority registry.
- Canonical approval, delegation, supersession, and revocation records.
- Their governing persistence plans and referenced evidence.
- Current repository revisions and timestamps.

Chat history, prior-session memory, uncommitted files, drafts, screenshots without durable evidence, and reconstructed approvals are not authorization.

When authority, scope, time, record status, persistence, evidence, delegation, supersession, or revocation cannot be resolved deterministically, the action is blocked and the operator MUST request direction or reconciliation.

## Required semantic rules

- `APPROVAL-AUTHORITY-001`: Approver identity resolves exactly to the repository owner or a currently authorized delegate.
- `APPROVAL-DELEGATION-001`: Delegate authority is backed by a valid durable delegation whose scope contains the requested authorization.
- `APPROVAL-DURABLE-001`: Approval-required work begins only after the approval record and governing persistence plan are durable, applied, re-read, and verified.
- `APPROVAL-SCOPE-001`: Mission, goal, execution, action, targets, and constraints match the attempted action exactly.
- `APPROVAL-DECISION-001`: Only an effective `approved` decision authorizes work; rejected or deferred decisions do not.
- `APPROVAL-TIME-001`: The approval is effective, unexpired, and predates the authorized action.
- `APPROVAL-REFERENCE-001`: Evidence, delegation, supersession, revocation, decision, and artifact references resolve from canonical locations.
- `APPROVAL-STATUS-001`: Top-level record status and approval decision are semantically consistent.
- `APPROVAL-HISTORY-001`: Approval history is create-only; correction, renewal, revocation, and supersession use new identities.
- `APPROVAL-REVOCATION-001`: A valid effective revocation or supersession prevents further use of the prior approval.
- `APPROVAL-FINDING-001`: A finding-and-approval action requires both a supporting durable finding and an exact valid approval.
- `APPROVAL-CHAT-001`: Human direction or chat evidence does not replace the required durable approval record.
- `APPROVAL-UNSPECIFIED-001`: An unspecified material action remains a stop condition even when another approval exists.

## Continuation boundary

When approval is missing, invalid, pending, rejected, deferred, expired, superseded, revoked, ambiguous, or outside scope:

- Do not perform the action.
- Preserve the proposed work and evidence.
- Keep implementation `not-started` when the approval gates implementation.
- Keep the relevant adaptation or execution unresolved, blocked, interrupted, rejected, or deferred according to its governing lifecycle contract.
- Report the exact missing or invalid authorization condition and the next required human action.
