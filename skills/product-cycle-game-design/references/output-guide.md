# Game outputs and evidence

Use the existing analysis.md, requirements.json, product-direction.json when required, design.md, design-baseline.json, architecture and plan outputs. No new controller schema or mandatory GDD file is introduced. A readable game-design section in the existing documents is sufficient. Additional prototypes/assets are registered through the normal artifact contract only when authorized and actually produced.

## Analysis: a gameplay decision, not only a feature list

Write the intended player experience, selected/alternative concepts, player role, verbs, agency and core/session loop in analysis.md. Explain what makes the next attempt worth doing, risks, and how to test the proposed experience. A familiar game can be appropriate; do not insist on novel mechanics. Carry behavior into stable requirement IDs and experience tests into quality_targets. Keep unchosen mechanics as proposals/open questions rather than freezing them into requirements.

For learning, connect learning activity → game action → observable response. Define what cue is visible and what the player must retrieve. State which outcomes can be observed during a session and which need later player/learning evaluation. Ask only consequential owner questions; reuse prior answers and any explicit delegation to choose for a workflow trial.

## Design: gameplay specification and art direction

Before generating references, map gameplay states as well as setup/pause/results screens. Give the chosen game an identifiable world/arena or interaction space; define focal actors/objects, camera/view, play area versus HUD hierarchy and supported device controls. Avoid oversized onboarding prose competing with active play. Sparse presentation is valid when it conveys the accepted genre and behavior.

Extend design.md's existing shared-rule and screen/action sections with applicable game rules:

- Entities, state and resources; player action/preconditions, targeting/selection, outcomes and invalid input.
- Update/time model as behavior: turn order or active time, spawning, movement, boundaries/collisions when relevant, pause/resume, completion/failure and restart. Explain how simultaneous/repeated events avoid double outcomes.
- Pacing/difficulty and adjustable parameters with rationale. Distinguish defaults for trial from measured balance; do not impose lives, scores, combo, levels or win/lose on genres that do not need them.
- Action-to-feedback table: accepted input, immediate cue, visible world consequence, motion/effect/sound if applicable, timing, interruption and accessibility. A bullet animation alone does not establish that an action affects the game.
- Art inventory and references: actor/target states, scenery, projectile/effects where relevant, crop/scale/layer, HUD and controls. Use the existing screen asset registry and exact state/viewport references. Static art cannot specify runtime behavior by itself.
- Onboarding during play, recovery and an observable acceptance example for consequential rules. Keep shared game rules linked from each screen, avoiding inconsistent copies.

Design acceptance confirms a concrete proposal is coherent and implementable. It does not establish fun, responsiveness, balance, sound quality or learning effectiveness from still images. Record these planned observations for the core trial and verification; do not demand finished product code to pass design review.

## A compact, usable game spec

Use the relevant [studio-practice sections](studio-practices.md) to make mechanics, HUD and playtest findings actionable. Keep their content in the existing assigned artifacts; these section shapes do not introduce additional controller gates.

Put a short concept overview before the detailed screen spec: the game in one sentence, experience pillars with design implications, player role/verbs, core-loop diagram, and the playable scene with its key visual reference. Keep the overview readable at a glance, then link to detailed rules. Do not enforce a literal one-page limit, copy another game's mechanics without explanation, or create a separate design bible that drifts from design.md.

For each consequential mechanic, use a stable rule/action ID that tasks, screens and tests can cite. Specify:

| Part | What coding needs |
|---|---|
| Intent and requirement | The player experience this rule serves, and the accepted requirement. |
| Trigger and input | Exactly which input/event starts it; mapping, focus/availability and invalid input policy. |
| State and rule resolution | Preconditions, affected entities/resources, update/order rules and the resulting state. Include relevant repeat/concurrent-event examples, not pseudocode for every implementation detail. |
| World and HUD response | What visibly changes, what stays readable, feedback priority and when the player can act next. Identify intentional delay versus an unresponsive control. |
| Tunable values | Units, initial proposed value, meaningful bounds if known, effect on play and a test to tune it. Keep one authoritative table; do not duplicate inconsistent timings across screens. |
| Recovery and completion | Applicable failure, interruption, pause/resume, completion and replay behavior; which state is preserved or cleared. |
| Reference and example | Exact screen/state/art reference, motion/feedback description and observable acceptance examples; mark untested experience assumptions. |

Example shape for a chosen typing shooter: selecting a target establishes which entity receives the next typed input; a letter resolves using the approved answer rule; firing and impact correspond to that resolution; completing a word changes the target/world state exactly once; next-target selection and feedback priority are explicit. Specify the approved rule for wrong letters and paused input as well. Do not invent damage, ammo or combo if they were not chosen. A generic instruction to add a shooting animation is not this specification.

For real-time games, carry game feel through input, response, spatial context, presentation, metaphor and rules. Define the actual control-to-response sequence and readable timing; decorative particles cannot repair a poor control model. For turn-based games, adapt this to choice clarity and action resolution rather than imposing physics. Art, motion and sound should reinforce the mechanic and remain consistent with accessibility and the accepted tone.

Treat the document as versioned working design: record why consequential choices change, update affected rules/references/task links through the supported workflow, preserve sealed evidence and obtain owner decisions where required. Playtest findings can tune provisional values; changes that alter accepted mechanics or visual targets require reconciliation, not an unrecorded coding shortcut.

## Architecture / plan: make the core trial reachable

Choose rendering and a proven domain library/engine where it materially fits approved rules; do not impose Phaser, Three.js or a new dependency on every game. Explain the tradeoff versus DOM/canvas/native rendering. Account for input/focus, time/pause, state transitions, assets and supported device performance where consequential.

Plan the first usable increment around a complete small gameplay loop, with the approved core-experience checkpoint before dependent content expansion. Define input → meaningful world response → changed situation → continuation/completion → recovery/replay; a setup page or static arena alone is not that checkpoint. Bind each task to relevant game-rule/action IDs, requirements, accepted art and screen/state/viewport targets. Do not make every task depend on final playtest evidence or later mechanics. Early behavior prototypes may use explicit temporary art; they cannot pass final visual acceptance against production art.

## Build / verify: separate evidence types

Use the approved spec and baseline. A playable trial needs actual input, changing game state and response over time or turns. Compare visual composition/art with exact references separately. Where authorized and available, observe the running product and record the actions, resulting state/feedback, version and limitations. A short capture or play trace may support temporal behavior; a still image or script success alone does not.

Check the selected genre's consequential behavior: controls and focus, target/action effects, timing or turn order, pause/resume, recovery and one complete replay. For learning games, additionally inspect cue/answer exposure, repeated attempts, hint use and the accuracy of outcome labels. Use relevant performance/readability observations instead of invented numeric quality scores.

Keep four conclusions distinct: specified behavior; observed functional/temporal behavior; image-to-render fidelity; player experience/learning evaluation. AI may observe response and surface risks, but cannot manufacture a player saying it was fun. Ask the owner to play the core trial through the existing checkpoint. Feedback drives a scoped revision; do not keep broadening the game until a subjective score is reached.

## Independent review: game-design perspective

Add this perspective to the existing BA/UX/technical reviewer; a new perspective is not a claim that another agent or human reviewer ran. Use the assigned C/S criteria and actual current evidence. No new approval gate or universal feature requirements are created.

- Analysis: does a concrete scenario explain player agency, consequences and chosen appeal, and serve the accepted outcome? Are alternatives meaningful and decisions honest?
- Design: walk an opening, a mistake and a repeat attempt. Can the primary mechanic be implemented without inventing consequential rules? Do the visual references depict the playable experience and preserve the approved genre? Return rework for a mismatch, explaining its impact; do not demand runtime proof at this stage.
- Architecture/plan: can the first coherent loop be tried before broad expansion? Are rendering/input/timing risks addressed proportionally, without binding a current task to later work?
- Build: inspect only the assigned increment and completed prerequisites. A claimed observed loop needs real behavioral evidence; unobserved behavior stays pending according to that task's criteria.
- Verify: require observations for assigned gameplay criteria and distinguish visual match from behavior and owner acceptance. Do not award a fun or learning pass from files, automated checks, screenshots or model confidence.

A missing design proposal or contradictory rule is rework. An unavailable necessary tool/owner decision may be blocked; block only dependent work. Newly added guidance does not invalidate sealed historical stages without an authorized reopening.

## Sources and scope of recommendation

Primary references, consulted 2026-10-04:

- [Hunicke, LeBlanc, Zubek — MDA](https://www.cs.northwestern.edu/~hunicke/MDA.pdf): link rules, runtime dynamics and intended emotional experience; evaluate their interaction iteratively.
- [GDC — Prototyping Based Design](https://www.gdcvault.com/play/1012473/Prototyping-Based-Design-A-Better): focused functional prototypes can expose design assumptions before production.
- [Stone Librande — One-Page Designs, GDC](https://www.gdcvault.com/play/1012356/One-Page): communicate the core design concisely and visually rather than relying on a monolithic document.
- [Steve Swink — Game Feel: The Secret Ingredient](https://www.gamedeveloper.com/design/game-feel-the-secret-ingredient): prototype control and response early; presentation alone does not establish the feel of play.
- [Game Developer — Design Docs: Crafting a GDD](https://www.gamedeveloper.com/design/design-docs---crafting-a-gdd): describe gameplay and consequential tunable variables so contributors can act on the document. This is practitioner advice, not an empirical guarantee.
- [OpenAI — Frontend prompt instructions](https://developers.openai.com/api/docs/guides/frontend-prompt): domain-appropriate playable presentation, actual usable experience instead of a marketing wrapper, and suitable established libraries for domain logic.

The concept patterns, artifact mapping and review guidance above are this repository's adaptation of these ideas, not an official OpenAI end-to-end game-development standard. Public frontend guidance and a visual-generation skill do not substitute for game design or playtesting. Preserve owner-selected art and project constraints when choosing tools.
