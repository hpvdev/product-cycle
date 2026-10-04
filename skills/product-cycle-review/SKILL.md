---
name: product-cycle-review
description: Independently review a Product Cycle stage and its small-step outputs using real evidence, without modifying files.
---

# Review độc lập

Use fresh context and remain read-only. Assess every C-numbered criterion and every reported S-numbered step against inspected content. Cite registered evidence for the relevant output. Distinguish worker claims, controller checks and operator observations. Return actionable rework or blocked findings when support is missing. A completed worker plan does not prove correctness.

For a coding increment, assess only its assigned scope and completed prerequisites. The plan's browser_required gate belongs to final product verification; do not add it to each coding review. Identify criteria that accidentally require a future dependent feature as a planning conflict. Preserve unobserved UI limitations and require the actual observations at final verification.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.
