---
name: product-cycle-review
description: Independently review a Product Cycle stage and its small-step outputs using real evidence, without modifying files.
---

# Independent review

Use fresh context and remain read-only. Assess every C-numbered criterion and every reported S-numbered step against inspected content. When controller evidence is supplied, cite its registered IDs for the relevant output; in a standalone review, cite inspected files without inventing evidence IDs. Distinguish worker claims, controller checks and operator observations. Return actionable rework or blocked findings when support is missing. A completed worker plan does not prove correctness.

Run review in a separate reviewer session; the worker cannot independently review its own output. For analysis and screen specs, apply an AI BA perspective: challenge alignment with the approved outcome, walk concrete journeys/counterexamples, and inspect shared rules, preconditions/effects, data meaning and cross-screen consistency. Add a UX perspective for design and the relevant technical perspective for architecture/build. These are specialist lenses, not proof of human specialists or multiple reviewers. Cite separate reviews only when they actually ran. Findings explain a concrete issue, its impact and what needs correction; a checklist or a worker's self-review is insufficient. Keep actual owner approval separate.

For a coding increment, assess only its assigned scope and completed prerequisites. The plan's browser_required gate belongs to final product verification; do not add it to each coding review. Identify criteria that accidentally require a future dependent feature as a planning conflict. Preserve unobserved UI limitations and require the actual observations at final verification.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

## Reviewing product analysis

For an analysis assignment, read the substance rubric in [discovery guidance](../product-cycle-analysis/references/discovery.md). Assess whether the user/context/outcome, concrete journey, recommendation and scope are useful for an informed product decision, not just whether files exist. Check unsupported assumptions and consistency between owner feedback, narrative and open_questions. Map findings to the assigned C/S criteria; do not add gates or demand a finished product. A sound proposal can pass review before owner approval when its remaining choices are explicit and the owner gate is preserved.

Do not equate honest limitations with sufficient discovery. If intended use, desired progress or core appeal remains generic, identify which product decision cannot be assessed and return rework for a missing proposal/follow-up, or blocked when a necessary owner answer is unavailable. Lack of market validation alone is not a failure. A concrete proposed answer awaiting owner selection can pass; a disclaimer substituting for that answer cannot. Treat misleading user-facing outcome labels and contradictions across artifacts as findings to repair, rather than approving them with a warning. Do not demand a fixed number of questions, novel features or research participants.

## Reviewing screen specifications

For UI design, read [screen specification guidance](../product-cycle-design/references/screen-spec.md). Inspect design.md's shared rules and per-screen actions alongside requirements and the actual visual references. Check that primary controls have clear preconditions, processing, state/data effects, feedback, destinations and observable acceptance; applicable recovery and responsive behavior must be usable, not checklist filler. Return specific rework for omissions or contradictions rather than approving an image-only output. Do not demand implementation/API internals at design or retrospectively apply new requirements to sealed historical work without an authorized reopening. For architecture/plan/build, assess traceability to the relevant spec sections and assigned scope; product behavior and actual visual fidelity require separate evidence.

## Company decisions and improvement review

Read the selected policy in the supplied context. With team.enabled and team.policy = autonomous, follow context.authority for analysis acceptance and assess later Design Director / Art Director decisions against that accepted scope, their delegated authority and actual reference/evidence. Do not add a human design or final-acceptance gate that this policy does not require, or call a company decision human approval. In supervised mode, preserve existing configured owner gates. Independent review and current-version evidence remain required in both modes.

For an assigned improve_review mission, use [bounded guidance improvement](../product-cycle-improve/SKILL.md) and its experiment contract. Inspect the exact sealed before/after candidate, same raw case outputs, check logs and limitations in fresh read-only context. The Improvement Reviewer is separate from both Skill Engineer and Evaluation Engineer. Reject unsupported benefit, regressions, permission expansion, changed product goals or weaker acceptance; approval is a review result, not permission to edit installed skills or declare adoption.

## Game products

If the brief or accepted direction asks for a game, read [Game Design](../product-cycle-game-design/SKILL.md) as a companion to this stage. Use its independent-review guidance as an additional game-design perspective within the assigned criteria. Assess the concept, rules and evidence appropriate to this stage; do not demand finished gameplay at design or claim fun from an image. Keep accepted scope, configured owner gates and evidence boundaries; the companion is not a new stage or an execution command.

For agent_workflow_version=1, read the reviewer context pack and actual source_root. Keep worker claims separate from registered observations; inspect the assigned procedures, source fingerprint and instance. Review integration on canonical source and whole-product evidence on the handoff version. Missing runtime evidence cannot be replaced by a passing build, a screenshot or a confidence score. Review only the task's assigned feature_verification subset; full feature coverage belongs to whole-product verification.
