# Deterministic Operation Candidate Assessment

## Decision model

Candidates were evaluated for repetition, structural stability, error risk, validation sensitivity, AI reasoning cost, and reuse potential. Deterministic tooling remains optional and AI remains the operator.

## Candidate inventory

| Activity | Recommended disposition | Rationale |
|---|---|---|
| Read and validate repository state | Deterministic tool | Repeated, stable, validation-sensitive, and already substantially implemented. |
| Create an execution and activate goal/state references | Select for implementation | Repeated multi-file mutation with high reference, timestamp, identity, and consistency risk. |
| Advance or terminate a lifecycle stage and synchronize execution/state | Select for implementation | Highly repetitive structured mutation with ordering and partial-write risk. |
| Create typed evidence and attach references | Defer | Valuable, but record shapes and judgment about evidence meaning vary; first prove shared mutation primitives. |
| Create missions and decompose goals | AI-executed | Requires purpose interpretation, scope judgment, sequencing, and human collaboration. |
| Evaluate, classify, and adapt | AI-executed | These are reasoning stages whose value comes from contextual judgment. |
| Approve governed transitions | Human-authorized, AI-mediated | Human authority cannot be replaced by deterministic tooling. Tools may validate persisted approval but cannot create authority. |
| Complete goals and missions | Hybrid | AI determines sufficiency; a tool may safely persist the approved completion transition. |
| List and filter missions, goals, executions, and records | Defer | Low mutation risk and useful later, but less valuable than protecting coordinated writes. |
| Install, upgrade, doctor, status, and repository validation | Retain existing tools | Already deterministic and aligned with the moving determinism boundary. |

## Minimal selected scope

### 1. Start execution

Create a schema-valid execution record and atomically synchronize the goal and repository state.

Expected benefit: eliminate repeated manual identity, timestamp, path, active-reference, and initial-lifecycle mistakes.

AI fallback: AI may create the artifacts directly under existing governance when the tool is unavailable or the operation is outside its supported shape.

Approval boundary: starting goal-directed work still requires any kickoff or goal approval required by governance.

### 2. Transition lifecycle stage

Apply a supported lifecycle stage status change, update required summaries/references/reasons, and synchronize execution and repository state.

Expected benefit: eliminate ordering, status, timestamp, reference, and partial-persistence errors across repeated lifecycle updates.

AI fallback: AI may perform the transition directly when judgment or an unsupported artifact shape requires it, followed by normal validation.

Approval boundary: the tool must reject transitions requiring human approval unless matching durable authorization exists.

### 3. Shared validate-before-persist mutation service

Stage proposed changes, validate the complete affected artifact set, detect stale source revisions, and apply or recover the mutation deterministically.

Expected benefit: provide one reusable safety boundary for the two selected operations and later candidates without prematurely automating all Flywheel work.

## Explicitly excluded from the first implementation

- Mission creation and mission design
- Goal decomposition and acceptance-criteria authoring
- Evaluate, classify, adapt, and reuse reasoning
- General record CRUD
- General mission, goal, execution, or record query APIs
- A claim of complete programmatic Flywheel operation

## Measures for the proving mission

- Number of coordinated artifact writes delegated to tools
- Validation defects prevented or detected before persistence
- Duplicate or inconsistent references produced
- Recovery behavior after injected interruption or stale revision
- AI fallback use and reason
- Human approval boundaries preserved
