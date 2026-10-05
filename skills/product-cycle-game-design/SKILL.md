---
name: product-cycle-game-design
description: Design and review gameplay concepts, playable loops, game presentation and playtest evidence when a Product Cycle product is a game. Use alongside the assigned stage skill; do not apply to ordinary apps merely using points or badges.
---

# Thiết kế game trong Product Cycle

Activate when the brief or accepted product direction asks for a game, including educational games. Infer from the owner's intent, not the repository name, a decorative illustration or a scoring widget. If the request is ambiguous, establish whether they want a playable game or an app with game-like rewards. Preserve an explicitly chosen genre, controls and audience.

This is a domain companion to the existing stages, not a new controller stage or executor. The assigned task, accepted inputs, output schema, tools and owner decisions remain authoritative. Never reopen sealed work, generate art, build a prototype or advance a live cycle merely by loading this skill. Perform only the assigned authorized work. Do not make the owner approve every tuning value; distinguish AI proposals from actual approval.

## Begin with play

Describe who the player is in the game, what they do repeatedly, what changes in the world, and why the next attempt differs. Choose the intended experience first: for example mastery, discovery, expression, relaxation or excitement. Explain how the rules create it. MDA's aesthetics concerns emotional experience, not only visual styling.

Compare gameplay concepts using [concept patterns](references/concepts.md) when direction is unsettled. Prefer variations within an owner-selected mechanic over replacing it. Alternatives must differ in player decisions, challenge or world response, not just colors. Recommend a bounded version whose core appeal survives scoping. Do not force novelty, punishment, competition, a boss, progression systems or multiplayer into every game.

Walk one concrete opening and a repeat attempt: player input → rule resolution → visible/audible response → changed situation → next decision. Identify the player's agency, uncertainty/challenge appropriate to the genre, recovery and reason to replay. A quiz with a decorative weapon is not automatically a shooter; explain what targeting, firing and consequences mean in this product. Turn-based, text and cozy games can be valid games without real-time action.

For learning games, explain how the learning activity drives play instead of interrupting it. Separate copying visible text, retrieval without a cue and longer-term learning. Do not infer retention from completing a round. Record excessive time pressure, divided attention and reading difficulty as design risks when applicable, not reasons to remove all challenge by default.

## Work within the assigned stage

Use [output and review guidance](references/output-guide.md), reading only the section for the current stage.

For concrete game-system, HUD, art-direction and playtest sections, use [adapted studio practices](references/studio-practices.md). Select only the portion needed for the assigned output; it supplies Codex-readable authoring guidance, not another pipeline, mandatory document set or Claude command.

| Stage | Game-specific work within existing outputs |
|---|---|
| Analysis | In analysis.md, compare play concepts, select experience pillars, describe the core loop and consequential assumptions. Map observable game behavior to requirements.json and the existing direction/quality-target fields. |
| UX/UI design | In design.md, specify gameplay rules, arena/world composition, HUD, controls, timing, feedback, state transitions and applicable assets. Provide actual references for all declared screens/states using the existing baseline contract. |
| Architecture | Choose rendering/engine and state ownership appropriate to the approved mechanic and devices; assess animation, input, timing, assets and performance risks without redesigning the game. |
| Plan | Put a playable core loop before dependent content expansion. Bind work to approved game rules, screen/state targets, asset needs and separate functional, visual and experience checks. |
| Build | Implement the loop as a coherent slice. Use accepted game references and art; validate interaction and temporal behavior independently of screen fidelity. Report missing observations honestly. |
| Verify | Play the actual loop, check important transitions, readable feedback, responsiveness and approved experience targets. Keep operator/player judgments separate from AI observations and learning claims. |
| Independent review | Add a game-design perspective to BA/UX/technical review. Walk counterexamples and inspect evidence appropriate to the stage; do not rubber-stamp a screen inventory as proof of gameplay. |

## Visual concept is not gameplay proof

After the game concept is selected, use Product Design / Frontend App Builder and Image Gen when applicable and available for game art and exact visual references. A gameplay concept needs a scene showing the activity: actors, targets/world, spatial relationships, readable HUD and input feedback. Avoid turning the play screen into a marketing hero or a form surrounded by explanatory cards. Setup and results may use normal UI; the playable scene must serve the approved game.

Specify motion and sound separately from still images: trigger, duration/sequence, interruption, reduced-motion alternative and mute policy where sound is in scope. Register required sprites, backgrounds, effects and other assets with intended roles. Use native text/controls for readable HUD and suitable engine/vector geometry for their actual purpose; never replace approved production art with easier placeholders. Do not regenerate approved references during coding.

A static proposal can pass design review with playability risks and their planned tests explicit. Use an isolated interaction prototype only when authorized for the current task; do not disguise it as product implementation or a completed playtest. The first usable core-experience checkpoint tests the real loop in Development before broad expansion. Screenshots establish appearance; observed play establishes behavior; the owner's experience judgment remains distinct.
