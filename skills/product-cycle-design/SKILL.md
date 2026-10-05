---
name: product-cycle-design
description: Specify screen behavior, shared interaction rules and a concrete accepted visual design baseline before product implementation.
---

# UX/UI design

Preserve an existing design system. For new directions, use Product Design and Image Gen when available; choose a real visual target before coding. Save flows, states, design rules and acceptance criteria in design-baseline.json. A picture is a visual reference; functional and usability acceptance require a running product. The baseline must be accepted under the selected policy before downstream implementation. Use reference images and design.md for this stage; do not build HTML/CSS prototypes or run a server to generate design images. Interface implementation and checks belong to build/verify. Record tool gaps instead of fabricating generations.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

Read [functional and screen specification](references/screen-spec.md) for UI design outputs. Write the shared rules and per-screen behavior in design.md alongside the registered visual baseline; images alone are not the specification. This uses existing outputs, not an additional controller stage or JSON schema.

1. Map user flows: link journeys, screens and transitions to accepted requirements.
2. Explore visual directions: reuse the existing design or create alternatives with Product Design and Image Gen when available.
3. Propose a baseline: save a concrete reference image for selection under the configured policy.
4. Specify screens and interactions: describe layout, content, action conditions, processing, data changes, feedback, navigation and applicable states.
5. Define shared rules and acceptance: specify colors, typography, spacing, responsive behavior and comparison criteria.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

In supervised mode, collaborate with the owner in Codex on journeys and concrete visual alternatives, iterate on actual feedback and await the configured baseline approval. Only when team.enabled and team.policy = autonomous, Design Director and Art Director choose and assess the baseline within independently reviewed analysis under delegated company authority. Keep the chosen image, decision rationale and actor traceable in existing outputs; do not record a director decision as human approval. Independent design review and screen reference coverage remain required; comparison against the running interface belongs to build/verify. Escalate a changed business scope or missing external authorization, not routine visual choices. Read [team operation](../product-cycle/references/team-operation.md) for these boundaries.

If required image-generation tools are absent in the assigned runtime, use team_request_capability only when that tool is actually exposed, with the exact task and accepted reference. A queued request is not a generated image. Finish independent source work before making the request, then leave source unchanged and return the dependent blocker as Waiting for tool: ... until the native result is submitted. The authorized native chat uses [company capability worker](../product-cycle-company-worker/SKILL.md); this design worker does not start another chat or replace the requested art with fabricated output.

For new UI or an approved redesign, use only the concept guidance in [Frontend App Builder](../frontend-app-builder/SKILL.md) alongside Product Design and Image Gen when available. Its implementation, browser verification and rendered-screenshot handoff rules apply to build/verify, not this design stage. Design the full core surface, not just its header. Reuse the chosen visual system for familiar screens, preserving real content and interactions. Record reference coverage, tokens and component variants in the baseline's rules and design.md so coding can reuse them. An approved reference remains the implementation target; later tasks must not silently replace it.

## Visual baseline

An Image Gen image can directly serve as the canonical design baseline when it clearly communicates layout, hierarchy, colors and components. Figma is optional; its absence does not block design. Exact image dimensions or aspect ratio are not absolute acceptance conditions. Record target screen dimensions, responsive rules and any mapping from the image to the target layout in design.md. No browser capture is required to complete design; existing captures may be reused without constructing a prototype to produce them.

Describe every applicable state, but reuse the same reference image when only numbers, text, messages or button states change. Create a separate image only when layout or presentation changes materially. There is no fixed image count per product. When screen_design_required is enabled, map each declared screen/state/viewport to one canonical reference in screen.references; multiple entries may point to the same image. Explain their differences in design.md and keep target keys unique.

Images guide visual appearance; design.md specifies exact labels, symbols, behavior and layout rules. Document minor text, symbol or size discrepancies in design.md so implementation follows the specified values. Correct or regenerate an image only when a discrepancy obscures the layout or forces implementation to guess the design. Do not require Figma merely because Image Gen cannot reproduce every label or exact pixel dimensions. Build/verify compares the running interface with the accepted image together with these documented rules and corrections.

When policy.screen_design_required is true, read context.screen_design_contract for the assigned stage. Design inventories all screens/states/transitions before creating an image bundle accepted under the selected policy. Plan binds increments to specific screen/state/viewport targets. UI build and verify retain actual image-to-render comparisons against that bundle, with functional evidence separate. Never downgrade an approved image to a style hint or silently drop its assets.

## Game products

If the brief or accepted direction asks for a game, read [Game Design](../product-cycle-game-design/SKILL.md) as a companion to this stage. Use its game-spec guidance alongside the screen specification: define gameplay rules and game feel, an arena/world plus HUD, timing/feedback and registered game art. The concept overview and detailed rules belong in design.md; still images do not prove the loop is playable. Keep accepted scope, configured owner gates and evidence boundaries; the companion is not a new stage or an execution command.
