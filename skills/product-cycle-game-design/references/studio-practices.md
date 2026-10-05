# Studio practices adapted for Product Cycle

Use this reference only for a game assignment. These are section shapes to help write existing artifacts, not files that every game must create. Keep detail proportional to the approved mechanic and iteration. Preserve the stage contracts, owner decisions and independent review from Product Cycle.

## Analysis: concept and system boundaries

State the player role, desired experience, repeatable actions, consequences and reason to return in analysis.md. Connect each proposed feature to the core loop; decorative rewards do not establish gameplay. Explain the smallest version that still delivers the accepted appeal and which assumption is riskiest.

Identify the few systems that matter for this version, such as input, target resolution, round state or learning prompts. Link each to accepted requirements and note what it consumes, changes and supplies to another system. Do not create an engine-specific department hierarchy or exhaustive systems index for a small game. Clearly mark interfaces that are still proposals.

## UI/UX: implementable mechanics

Extend design.md's shared rules with a compact section per consequential system:

| Section | Useful content |
|---|---|
| Purpose | Player experience and accepted requirements served; what this system owns. |
| Rules | Inputs, preconditions, rule order, resulting state and observable examples, using stable rule/action IDs. |
| Quantities, when relevant | Formula or exact calculation, variables with units and valid range, initial values and rounding/clamping policy where consequential. A constant or lookup table may suffice; do not invent a formula for qualitative rules. |
| Boundary cases | Applicable simultaneous/repeated input, interruption, exhausted resources, invalid data and recovery. |
| Dependencies | State/data read from other systems, events/results supplied and authoritative owner of shared values. |
| Trial and acceptance | Observable rule examples plus provisional tuning assumptions and the observation that would support or disprove them. |

Keep shared quantities in one place. For example, if a chosen game has a round timer, specify whether pause suspends it and how a final answer resolves at expiry; the HUD must display that same rule. Do not silently use different numbers in screen copy, architecture and code.

Detailed designs should resolve behavior rather than dictate implementation classes. Architecture chooses internal structures. Do not add economy, combat, progression or numeric balancing merely to fill these sections.

## UI/UX: active-play HUD versus menus

Menu screens describe navigation and explicit interactions. The HUD describes information presented during active play. Link both to the existing screen/state IDs and exact visual baseline; an overlay does not automatically require a new screen ID or image.

For each consequential HUD element, specify:

- What the player needs it for and whether it is persistent, contextual, on demand or conveyed in the world.
- The owning game rule/data, when it changes and what it shows when unavailable; display widgets must not invent game state.
- Placement relative to the play area, legibility, overlap priority and behavior across supported viewport/input targets.
- Visibility and transformation for the contexts this game actually has, such as active, paused, feedback or completed.
- Transition/feedback timing and a non-color cue where color carries meaning. For interactive elements, link to the existing action specification.

Walk a moment when several cues compete: a target response, an instruction and a status update, for example. State which cue stays visible and which waits or recedes. Preserve the player focus area and readable game objects. Choose margins and visual density from actual target layouts; do not import universal screen percentages, element counts or combat contexts from another game's template.

## UI/UX: art direction that can survive coding

Record a short visual rule and its implications for world/actors, shape hierarchy, semantic color, typography, HUD and feedback. References should say which compositional or asset property to carry forward, rather than merely naming a genre or palette.

Attach these decisions to the approved screen/state references and asset inventory. Identify which actors/objects must remain readable against which backgrounds, and what visible response reinforces the mechanic. Define meaningful asset sizes/crops/layers and motion/audio needs where in scope. Distinguish a draft, a reviewed proposal and actual owner approval.

During build, use the exact accepted reference and asset version. If a technical constraint conflicts with it, surface the tradeoff and reconcile through the existing workflow before changing the visual target. A new simpler HTML mockup must not quietly supersede approved game art.

## Development / verification: focused prototype and playtest

When authorized, try the riskiest control, interaction or pacing assumption with the smallest suitable prototype. Choose paper, browser or engine according to what is being tested. A paper flow cannot establish latency; a browser prototype may not establish engine-specific performance. Temporary art is acceptable for a declared behavior trial, not final fidelity acceptance.

In the existing task evidence or verification output, record:

1. The tested rule/experience assumption and what observation would change the decision.
2. Build/source version, prototype/product path, platform/input, actual operator or player role, tested scope and deliberate shortcuts.
3. What was done and observed; attach available trace/capture and distinguish observed behavior from player statements and AI inference. Leave unsupported judgments unassessed.
4. Whether the evidence supports, partly supports, contradicts or cannot assess the assumption, with relevant limitations. One session cannot prove general enjoyment or learning retention.
5. A scoped next action: keep the proposal, tune a provisional value, repair a defect, or propose a design change. Update affected spec/task links through the existing workflow; sealed evidence and owner decisions remain protected.

Classify findings by consequence, not only by heading: implementation defects need repair; tuning issues need a relevant balance trial; design issues need reconciliation with the accepted intent; presentation issues need comparison with the visual target. A readability or accessibility problem can block an assigned criterion and must not be dismissed as optional polish. Do not add a fixed participant count, session length, metrics list or approval per section.

## Independent review

Read the actual concept, mechanics, HUD/reference and relevant trial evidence. Walk an opening action, a boundary case and a repeated attempt appropriate to the assigned stage. Check shared values and visual intent across those outputs. Design review asks whether the proposal can be implemented coherently; runtime verification asks what was actually observed. A specialist perspective, static template, screenshot or passing controller test does not establish that players enjoy the game.

Return concrete findings within the existing assigned criteria and fresh read-only reviewer session. No extra director agent, model family, review mode, state store or per-section permission rule is introduced by this reference.

## Provenance and adaptation

Adapted from [Donchitos / Claude Code Game Studios](https://github.com/Donchitos/Claude-Code-Game-Studios), revision `b21fa0f7f289fc3e726cf36fb12b9bc1e7a51e4d`, consulted 2026-10-04:

- [System design authoring](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/b21fa0f7f289fc3e726cf36fb12b9bc1e7a51e4d/.claude/skills/design-system/SKILL.md): explicit rules, applicable calculations, dependencies, tuning and acceptance.
- [HUD design](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/b21fa0f7f289fc3e726cf36fb12b9bc1e7a51e4d/.claude/docs/templates/hud-design.md): distinguish active-play information from menu navigation; specify visibility, data and hierarchy.
- [Art direction](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/b21fa0f7f289fc3e726cf36fb12b9bc1e7a51e4d/.claude/skills/art-bible/SKILL.md): connect a visual identity to actionable world, HUD and asset choices.
- [Prototype report](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/b21fa0f7f289fc3e726cf36fb12b9bc1e7a51e4d/.claude/docs/templates/prototype-report.md) and [playtest report](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/b21fa0f7f289fc3e726cf36fb12b9bc1e7a51e4d/.claude/skills/playtest-report/SKILL.md): hypothesis, actual observations, limitations and actionable findings.

The upstream MIT notice is retained in [LICENSE.upstream](LICENSE.upstream). This adaptation is maintained by Product Cycle; it is not an official OpenAI standard or a complete Codex port of the studio. No upstream executables, hooks, settings, model identifiers, slash commands, project registry or alternative pipeline are installed. The upstream's self-reported game comparison is not treated as independent proof of quality.
