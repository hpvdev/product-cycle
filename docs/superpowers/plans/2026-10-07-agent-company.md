# Product Cycle Agent Company Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation and a fresh final review. User/repository instructions override skill defaults about extra approvals, commits, worktrees and testing cadence.

**Goal:** Implement the reviewed discovery-to-learning agent company workflow without silently changing historical cycles.

**Architecture:** Extend the existing controller, installer, supervisor and evidence contracts. Keep deterministic lifecycle decisions in Python and use separately reviewed worker artifacts for semantic decisions. Isolate feature changes, explicitly integrate them, and verify the canonical product version.

**Tech Stack:** Python 3.9+, standard library, SQLite, Git, existing Codex App Server/native adapters and unittest.

**Spec:** docs/superpowers/specs/2026-10-07-agent-company-design.md

## Global Constraints

- Keep existing cycles and demo fixtures on their recorded contract until an explicit idle upgrade.
- No new dependency, real Codex product run, installed-project mutation, commit, push or deployment for validation.
- Use English for skill and role instructions. Keep Image Gen baseline and no HTML/CSS design prototype rules.
- Unknown execution outcomes retain reservations until reconciled.
- Product evidence and checks identify actual source and environment; synthetic tests do not prove product quality.

## Review Focus

- Concurrent workers modifying the same canonical file must not overwrite or partially integrate either change.
- Restart after partial workspace/integration transitions must reconcile state and retain unlanded work.
- Policy/context edits must not manufacture approval or apply stale accepted inputs.
- Missing runtime capabilities and exhausted budgets must wait/block instead of rerouting silently or looping.
- Learning judges must not infer variant identity from labels, paths or author rationale; stale results cannot be adopted.

## Execution record

Implementation is authorized by the owner's request following the in-chat flow and reviews. Execute in this checkout, using a durable task ledger below. Preserve the current Git history and request no repeated implementation approval.

### Task 1: Policy and workflow contracts (R1, compatibility)

Files: product_cycle/contracts.py, product_cycle/store.py, product_cycle/runner.py, product_cycle/desktop.py, product_cycle/cli.py, skills/product-cycle/references/contracts.md, affected role/skill instructions.

Interfaces: policy_packet(store, task) provides authoritative mode/gate/scope/budget data; agent-workflow contract flag selects additional stage/output validation.

- [x] Add versioned policy packet, feature-map stage contracts and idle upgrade operation.
- [x] Preserve legacy/demo behavior and gate authority; remove conflicting unconditional approval instructions.
- [x] Validate mode-specific work/review/repair packets and idle-upgrade preservation using existing focused controller tests.

### Task 2: Feature map and verification procedures (R2, R6)

Files: product_cycle/features.py, product_cycle/store.py, product_cycle/resources/roles/feature_map.md, product_cycle/resources/verification.md, skills/product-cycle-feature-map/SKILL.md, design/architecture/plan/build/verify skill references, installer and fixtures.

Interfaces: validate_feature_map(value, requirement_ids, screen_targets) returns stable features; validate_verification(value) returns launch/doctor/drive/evidence/cleanup contract; task_features(store, task) binds task feature IDs.

- [x] Validate draft and observed feature maps and feature-linked plans.
- [x] Require product-specific verification contract and current-version runtime observations for applicable completed outputs.
- [x] Extend worker inputs and skill installation with the new stage and maintained map guidance.
- [x] Exercise invalid links, missing evidence, target coverage and legacy compatibility.

### Task 3: Versioned context packs (R3)

Files: product_cycle/context_packs.py, product_cycle/runner.py, product_cycle/team.py, product_cycle/desktop.py.

Interfaces: build_pack(store, task, phase, directory) returns version/hash, pinned authority, feature inputs, source and original evidence provenance.

- [x] Select accepted inputs deterministically by ancestry and requirements; keep originals linked.
- [x] Supply distinct builder, reviewer and repair views; record exact pack hash in controller events.
- [x] Exercise pinned criteria, stale revisions, changed source and reviewer claim/evidence separation.

### Task 4: Capability-aware routing (R4)

Files: product_cycle/dispatch.py, product_cycle/team.py, product_cycle/runner.py, product_cycle/cli.py.

Interfaces: route(store, task, phase) returns configured model/effort/runtime/skill/capabilities and reason or an actionable blocker.

- [x] Validate configured runtime/model profiles and plan execution metadata.
- [x] Route work and review through supported runtimes; record selection and observed capabilities separately.
- [x] Exercise absent capabilities, invalid model choices, budgets and unchanged legacy model selection.

### Task 5: Workspaces and integration (R5)

Files: product_cycle/workspaces.py, product_cycle/store.py, product_cycle/team.py, product_cycle/runner.py, product_cycle/desktop.py, product_cycle/contracts.py.

Interfaces: workspace_for(store, task) identifies actual source; prepare/integrate/reconcile persist baseline and transition journal; task_source(store, task) is the source used by checks, review and fingerprinting.

- [x] Create durable isolated Git workspaces and preserve canonical/uncommitted source baselines.
- [x] Expand integration DAG nodes, prerequisites and feature checkpoint gates.
- [x] Integrate reviewed changes with conflict detection and recoverable transitions; run/review canonical checks.
- [x] Exercise two independent workers, conflicting changes, deletion/untracked files, interrupted integration and unknown-run reservations using temporary local Git repositories.

### Task 6: Verified-product outcomes and supervision (R6, R7)

Files: product_cycle/features.py, product_cycle/store.py, product_cycle/team.py, product_cycle/company.py, product_cycle/server.py, relevant dashboard views and instructions.

Interfaces: workflow_summary(store) exposes actionable waits and feature verification states; runtime observations remain tied to actual task source and accepted contracts.

- [x] Enforce PASS/FAIL/BLOCKED evidence and whole-product validation on handoff source.
- [x] Summarize outcomes/waits, wake on relevant transitions and preserve existing supervision backoff/unknown handling.
- [x] Choose consultations by declared task needs; retain mandatory independent review.
- [x] Exercise stale integration evidence, resource contention and exhausted repair budgets.

### Task 7: Blinded learning and knowledge (R8)

Files: product_cycle/improvements.py, product_cycle/company_learning.py, product_cycle/context_packs.py, skills/product-cycle-improve and supporting learning instructions.

Interfaces: immutable variant packets use opaque labels; judge input excludes author rationale/variant identity; recorded evaluation resolves labels controller-side and requires evidence/current hashes.

- [x] Preserve lessons and project knowledge with provenance; make reviewed knowledge available to later context packs.
- [x] Add opaque variant judging and held-out case/budget handling to behavioral evaluations.
- [x] Preserve stable application, customization protection and rollback.
- [x] Exercise label leakage, swapped/stale outputs, regressions, budget exhaustion and adoption constraints.

### Task 8: Integration review and delivery

- [x] Inspect requirements R1–R8 against current code, packaged skills and test evidence.
- [x] Run the full controller suite once after implementation is stable; inspect failures and fix relevant causes.
- [x] Conduct fresh read-only review, address material findings and recheck affected behavior.
- [x] Report implemented behavior, validation and any genuine runtime limitations; leave Git publication to a user request.

## Implementation evidence — 2026-10-07

- R1: authority packet, per-mode gates and journaled explicit idle upgrade are implemented. Synthetic upgrade interruption replays configuration without a second revision increment. Legacy stages remain absent until explicit upgrade.
- R2/R6: reviewed feature map, product-specific verification contract, procedure-linked task subsets and full-plan coverage are implemented. Accepted integration observations feed later context without rewriting the planned baseline.
- R3: hashed builder/reviewer/fix packs retain sealed inputs and concrete repair feedback. Current owner decisions and accepted-input revisions are checked; authenticated refresh changes delivered context, never approval.
- R4/R7: configured routing, declared specialists and complexity-based consultations are implemented. Admission errors are contained per mission. Exclusive runtime/device leases cover team and native jobs and persist through unknown outcomes.
- R5: isolated snapshot/detached worktree preparation, integration DAG, conflict repair/review and resumable journals are implemented. Targeted synthetic fixtures cover independent changes, conflicts, dirty/untracked baselines, interrupted preparation/integration and two scheduler-admitted roots.
- R8: evidence-backed project lessons, immutable neutral before/after trials, opaque judging, registered holdouts, budget checks, optional shared guidance and rollback are implemented. Exact orphaned trial reconciliation never duplicates a candidate turn. Raw input copies live outside scored trial artifacts.
- The first full synthetic controller run executed 234 tests: two historical assertions required updates for the intentional skill-count/autonomous-policy contract; server tests were blocked by sandbox localhost binding. All 9 HTTP tests subsequently passed with local-port permission.
- Focused rechecks: 83 tests passed before final-review changes; 50 tests passed covering the subsequent scheduler and judged-input collision regressions. Native provider connectivity and actual product/learning quality have not been claimed or validated.
- Fresh reviewer found five initial issues, all fixed and rechecked. Final audit found two additional issues (per-job routing exception and judged input.json overwrite), fixed with focused regressions. Final recheck and completion audit remain pending.
- No real product cycle, installed test-workflow mutation, project publication, commit or push was performed.

Final completion audit additions: source/test navigation and a bounded local-import graph are now included in hashed context packs, with parser confidence and unsupported-language limits; feature IDs/procedure subsets are hashed explicitly. Workspace review seals both file hashes and modes so executable-permission changes require fresh review. Duplicate raw-case bytes do not count as held-out cases. The final full suite passed 249 tests before these audit additions; their focused checks and final reviewer recheck are pending.

## Completion audit

- R1 / compatibility: inspected authority.py, Store.begin/owner_gate, native prompts and upgrade journals. Tests cover autonomous/supervised authority, original model/gate retention, active-upgrade refusal, interrupted replay and unchanged legacy stage visibility. Explicit max_repairs is included in the authority budget.
- R2: inspected features.py, architecture/feature-map/plan contracts, fixtures and installed skill outputs. Requirement/screen/procedure coverage, DAG reachability, partial increment procedure allocation and maintained integration provenance are enforced.
- R3: inspected context_packs.py and source_context.py. Hashes cover authority, decisions, selected feature/procedure scope, sealed accepted inputs, repair feedback and bounded source/test/import navigation. Static graph limits are explicit; original paths remain available. Tests cover changed decisions/revisions/procedures and privacy-directory exclusion.
- R4: inspected dispatch.py, CLI configuration and per-mission admission. Runtime/profile/capability selection precedes execution, configured model authority is preserved and missing capability blocks only the affected task. Selected routing and observed capability are distinct.
- R5: inspected workspace manifests, review inventory (hashes and modes), task expansion and integration journals. Tests cover detached Git and unborn snapshots, dirty/untracked source, independent workers, conflicts, rebase/fresh review, preparation/integration interruption and executable-mode changes after review.
- R6: inspected runtime reports, independent review validation, source comparisons, final verify/handoff and coordinator outcomes. PASS needs registered observations, FAIL/BLOCKED remain distinct and whole-product categories are validated on current canonical source. Focused negative checks reject stale versions, wrong surfaces, absent proof and self-referential reports.
- R7: inspected scheduler, consultant preparation, native/team instance reservations and bounded repair. Missing routing and failed preflight requests cannot strand an unstarted writer; unknown runs retain reservations. Tests cover concurrent private admissions, complex integration consultations and exhausted repair budgets without reopening scope.
- R8: inspected immutable trials, exact reconciliation, opaque judge resolution, held-out deduplication, project knowledge, opt-in shared-guidance locking and stable-point application/rollback. Tests cover lost responses, wrong turn identity, tampering, skill mutation, input.json output collisions, case/trial budgets, heldouts and protected existing installations.
- Packaging: pyproject package discovery includes new Python modules/resources; BuildWithSkills copies the source bundle; live-init test confirms 20 installed skills including feature-map/integration. No installed user project was updated.
- Validation: full synthetic suite passed 249 tests; after audit additions, the relevant 72-test suite passed; the final three authority/runtime/repair-budget checks passed. JS syntax checks and git diff --check passed. No redundant passing broad suite was rerun after localized audit changes.
- Independent review: fresh read-only reviewer rechecked all material findings and R1–R8, reporting no remaining Critical/Important finding. Native/provider connectivity, actual product quality and behavioral learning efficacy were explicitly excluded from synthetic controller claims.
- Delivery: changes are present in the source checkout; no commit, push, external publication or test-workflow synchronization was requested or performed for this implementation.
