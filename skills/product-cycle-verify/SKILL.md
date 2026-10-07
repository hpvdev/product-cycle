---
name: product-cycle-verify
description: Evaluate a built product against accepted requirements and its design baseline using observed evidence.
---

# Verify the product

Keep accepted criteria unchanged. Match observations to the current product version. Compare the visual reference and rendered UI at the same viewport and state, and test the main interactions when the approved plan requires it. If browser tools are absent, record pending observation and wait for operator evidence. Never equate compilation or a screenshot with complete product acceptance.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

1. Map every acceptance criterion to its verification procedure.
2. Inspect actual evidence and identify the exact source version.
3. Exercise the journey and compare the rendered UI to its baseline; record missing observations.
4. Separate defects, accepted limitations and unverified behavior.
5. Conclude from evidence while preserving approved criteria.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

When policy.screen_design_required is true, read context.screen_design_contract for the assigned stage. Design inventories all screens/states/transitions before creating an image bundle accepted under context.authority. Plan binds increments to specific screen/state/viewport targets. UI build and verify retain actual image-to-render comparisons against that bundle, with functional evidence separate. Never downgrade an approved image to a style hint or silently drop its assets.

## Game products

If the brief or accepted direction asks for a game, read [Game Design](../product-cycle-game-design/SKILL.md) as a companion to this stage. Use its verification guidance for actual play observations, controls, feedback, timing/turn resolution and recovery/replay. Keep behavior, visual fidelity, owner experience judgment and learning effectiveness distinct. Keep accepted scope, configured owner gates and evidence boundaries; the companion is not a new stage or an execution command.

## Whole-product acceptance

For agent_workflow_version=1, inspect the maintained feature observations and exercise the complete verification contract on canonical source after integration. Produce runtime-observations.json covering every feature plus main_journey, cross_feature, ux_consistency, visual_consistency, performance and error_recovery. Justify non-applicable categories; the main journey always applies. Evidence must identify the actual instance and exact handoff source. A missing tool is blocked, an observed defect is fail, and pass requires observed behavior plus independent review. Preserve proof during cleanup.
