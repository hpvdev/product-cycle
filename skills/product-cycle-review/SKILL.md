---
name: product-cycle-review
description: Independently review a Product Cycle stage and its small-step outputs using real evidence, without modifying files.
---

# Review độc lập

Use fresh context and remain read-only. Assess every C-numbered criterion and every reported S-numbered step against inspected content. Cite registered evidence for the relevant output. Distinguish worker claims, controller checks and operator observations. Return actionable rework or blocked findings when support is missing. A completed worker plan does not prove correctness.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.
