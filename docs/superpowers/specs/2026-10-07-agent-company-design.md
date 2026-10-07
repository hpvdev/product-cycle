# Product Cycle agent company

## Intent and scope

Implement the owner's proposed discovery-to-learning workflow in Product Cycle. The controller owns state, authority, dependency resolution and evidence. Agents implement and judge within task contracts. Keep Image Gen references valid design baselines; design does not construct HTML/CSS prototypes. Keep all skill instructions in English.

The owner has requested implementation after reviewing this architecture. Work in the current checkout, preserve existing work, and do not commit, push, deploy, contact third parties or change an installed project without a separate request. Use local synthetic controller cases to validate mechanics; do not start a real product cycle as a test.

## Compatibility

New live cycles use the new versioned agent-workflow contract. Existing and demonstration cycles preserve their contract unless explicitly upgraded while idle. A contract upgrade must record affected revisions and preserve old evidence, decisions, gates, model preferences and custom skills. It must not silently accept historical results under new criteria.

## Requirements

### R1 — Authority and lifecycle

Build a single policy packet that states the selected autonomous/supervised mode, task gate authority, scope, external-action boundaries and execution budgets. Worker, reviewer and repair prompts consume that packet. Remove unconditional owner-approval requirements from instructions that apply to delegated autonomous decisions. Keep unknown execution outcomes distinct from known failure, and never retry an unknown external outcome blindly.

### R2 — Feature map and verification contract

Introduce a reviewed feature-map stage after architecture and before plan. Its draft maps stable feature IDs to requirements, screen/state targets, dependencies, expected code entry points and executable verification procedures. Planned entry points are explicitly unconfirmed.

Technical design supplies a product-specific verification contract: surface, launch/readiness, read-only doctor, environment needs, isolated-instance constraints, feature driving procedures, expected observable effects, evidence and cleanup. Use argv commands, trusted project scope and secret-free references. Build updates confirmed feature information from actual code. Verification uses the real user-facing path and retains evidence after cleanup.

### R3 — Context packs

Construct versioned builder, reviewer and repair packs with task/revision identity, selected feature IDs, source fingerprint and provenance for accepted inputs. Pin scope, authority, acceptance and applicable decisions. Select supplementary inputs deterministically by dependency and requirement links; retain access to sealed originals. Reviewer receives original evidence and worker claims separately. Repair receives concrete failed checks and findings. A context hash identifies the precise packet delivered.

### R4 — Dispatcher

Route within explicitly configured profiles by capability, runtime, domain and complexity before considering model/effort. Default to the configured role model; never invent tools or silently change model families. Persist selected routing and observed runtime separately. Missing capabilities produce an actionable wait. Allow configuration of local runtime/device capabilities and bounded concurrency; no remote account or device provisioning is implied.

### R5 — Isolated execution and integration

For authorized isolated execution, each feature builder writes a managed detached Git worktree and its own artifacts. Record baseline source, task/revision, workspace ownership and status durably. Shared canonical source remains protected by a single integration writer. Read-only review and local checks inspect the actual worker workspace.

Materialize integration tasks in the DAG. Dependent features wait for their prerequisites' integration. Integrate only the independently reviewed workspace version. Detect simultaneous changes and reject conflicting writes without partial application or lost work. Keep a recoverable integration journal. Run the assigned checks on canonical source after integration and review the integrated result before it becomes a verified feature. Preserve unlanded work and reconcile interrupted transitions.

### R6 — Verification and completion

Distinguish workspace-verified, integrated, product-verified and whole-product-accepted outcomes. Runtime reports name the actual source version, environment, actions and observable results, with registered evidence. PASS requires applicable evidence and independent review; FAIL returns bounded repair; BLOCKED preserves missing capability/input. Screenshots and successful builds alone do not prove interaction correctness.

Whole-product verification covers the main journey, cross-feature behavior, UX/visual consistency, applicable performance and error recovery on the exact handoff source. User gates follow policy. Delivery remains local unless separately authorized. Learning remains pending after product completion where appropriate; do not misreport queued learning as applied.

### R7 — Supervision

Expose one coordinator summary of outcomes, current work and actionable decisions. Classify waits with an owner, condition and clearing action. Drive scheduling and wake classification in Python, not repeated LLM polling. Reconcile durable session identity, revision and provider state. Use bounded backoff, attempt/time/token budgets and consult only relevant specialists. No activity is fabricated to animate the office.

### R8 — Learning

Extract lessons from actual history and evidence, separating project knowledge from portable guidance. Preserve independent author, trial/evaluator and reviewer identities. Compare immutable guidance versions with identical raw cases and opaque variant labels, add held-out cases where available, record actual outcomes and regressions, and retain a bounded evaluation budget. Keep structural checks distinct from behavioral benefit. Adopt only independently reviewed improvements at stable points with backup, monitoring and rollback; never weaken scope, authority or acceptance.

## Completion evidence

Inspect the implementation and use focused tests for each contract, plus the full controller suite once at the end because the change crosses shared contracts. Include interrupted/unknown runs, legacy cycles, invalid provenance, missing capability, concurrent workspace edits, stale evaluation/context, and integration failures. Package all new skills/resources through the existing installer. Conduct a fresh read-only review of the final diff. Controller tests establish controller behavior only, not real provider connectivity or autonomous product quality.
