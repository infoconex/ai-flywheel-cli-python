# Failure Handling and Recovery

This document is normative. Failure is information to evaluate, not permission to bypass the operating model.

## Failure classes

- `tool-failure`
- `validation-failure`
- `implementation-defect`
- `framework-defect`
- `dependency-blocker`
- `assumption-invalidated`
- `repository-inconsistency`
- `approval-blocker`
- `unsafe-operation`

## Required response

For every material failure the operator MUST preserve evidence, classify the failure, determine impact, record the selected recovery, update state when blocked, and revalidate after correction.

## Startup recovery matrix

| Condition | Required response |
|---|---|
| Required operating file missing | Stop. Set or recommend `status: blocked`. Identify the exact missing path. Do not invent the artifact. |
| Manifest or state schema invalid | Stop. Preserve validation output. Correct only when the active goal and governance authorize framework repair; otherwise request human direction. |
| Mission, goal, or execution reference broken | Stop. Do not guess the intended target. Report all candidates and request reconciliation. |
| More than one active mission or goal | Stop. Preserve both artifacts and require an authorized selection. |
| State and active execution disagree | Stop. Prefer no artifact automatically. Reconcile from persisted evidence and approval. |
| Unknown phase, status, readiness, or lifecycle value | Stop. Do not normalize silently. Record a framework defect. |
| Required approval missing | Stop before the approval-required action. Record the pending decision and requested approver. |
| Validator unavailable | Continue manually only when authority and active work remain unambiguous. Record the capability limitation and perform all feasible checks. |
| Non-authoritative repository inconsistency | Continue only when it does not affect authority, scope, safety, or acceptance criteria; record it as a finding. |
| Unsafe or destructive operation | Stop and request explicit human authorization or a safer alternative. |

## Continue or stop

The operator may continue only when the failure is understood, the corrective action remains within approved scope, invariants still hold, and governance permits it.

The operator MUST stop when safety or authorization is uncertain, required approval is missing, corrective action materially changes scope or architecture, authoritative records conflict, or repeated attempts produce no new learning.

## Prohibited responses

Do not suppress errors, weaken validation, delete contrary evidence, fabricate missing records, mark a blocked goal complete, or claim success based on partial execution.