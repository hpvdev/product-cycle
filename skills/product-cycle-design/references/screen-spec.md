# Functional and screen specification

The design output must explain both what the UI looks like and how it behaves, so implementation does not invent product behavior from an image. This is a Product Cycle output convention, not a claim of a universal design standard. Keep detail within the approved iteration and reuse established product rules.

## Stage boundaries

Analysis establishes users, goals, scope, business rules, main journeys and observable requirements. It identifies screens/interactions implied by those journeys without prematurely fixing their visual layout. Design resolves the screen inventory, layout, interaction behavior and visual references. Architecture maps that behavior to components, data, APIs and shared technical services; it must not silently change the approved behavior.

If design exposes a consequential requirement gap or contradiction, discuss it with the owner and reconcile the requirements through the supported workflow before dependent coding. Distinguish confirmed decisions, proposals and unresolved choices. Keep the configured owner gate; do not invent approval or make the owner approve every minor implementation choice.

## Output in design.md

Use readable headings and action tables, not a generic checklist or an unreadable JSON dump. No extra file is required. Link actual artifacts using project-relative paths. Give screens, meaningful states and actions stable identifiers shared with design-baseline.json when its screens contract is enabled.

**Shared specification:** cross-screen business and interaction rules, shared data meanings, navigation/back behavior, validation, feedback and reusable component behavior where applicable. Link the accepted requirement for each consequential rule. Define a shared rule once and cite it from screens; record exceptions explicitly. Visual common rules belong in baseline.rules; technical conventions and code structure belong in architecture/project setup.

**Screen index and navigation:** list each in-scope screen's ID, name, purpose, requirement links, entry/exit conditions and destination screens/states. Show the main transitions as a readable diagram or table. Use the same IDs and destinations throughout the specification and visual bundle.

**Per-screen specification:** include the following for each screen:

- Purpose, applicable requirements and entry conditions; data shown, initial values and information source, without inventing unchosen API contracts.
- Layout regions, content hierarchy and controls, with links to exact reference images/prototype views and their version/state/viewport. Describe responsive behavior relevant to supported devices. An image still awaiting approval is a proposed reference.
- Each actionable control or gesture: trigger, availability/preconditions, input validation, processing/business rule, data/state changes, visible feedback and destination. Include keyboard/touch alternatives where supported. Name which shared rule applies rather than repeating it.
- Applicable loading, empty, disabled, error, success and recovery behavior. Specify repeated submissions, pending actions, cancellation/back navigation or persistence when they can affect this screen's intended outcome. Explain meaningful omissions; do not invent every possible state or unsupported features.
- Observable acceptance examples covering the important actions and states. Keep functional expectations separate from visual comparison; a screenshot cannot prove a click works.

For example, if vocabulary gameplay has been approved:

| Action | Available when | Processing and state change | Feedback / destination | Acceptance |
|---|---|---|---|---|
| PLAY-TYPE: type a character | Active round, focused game; not paused | Compare against the next expected character using the accepted matching rule; advance word progress on a match | Fire the approved effect and mark progress; remain on PLAY | A matching character advances once; input while paused leaves progress unchanged |

The example is not a default feature requirement. Specify wrong input and completed-word behavior from this product's accepted requirements; do not invent scoring, timing or learning claims.

## Ready for dependent implementation

The owner can inspect the screen references and understand what each interaction does. Requirements, shared rules, screen behavior and visual targets agree. Required art is registered and assigned to its intended screen; it cannot disappear during coding. Keep unresolved decisions visible and block only the work that depends on them. Do not mark a behavior specified when the text merely says “handle appropriately” or leaves the result of a primary action for the coding worker to decide.

Planning cites the relevant screen/action IDs and shared spec sections for each increment, alongside its exact visual targets. Build reads those sections plus architecture and coding rules, implements behavior from the spec and appearance from the accepted reference, and reports contradictions for resolution. Independent design review assesses whether the actions and rules are implementable and testable, not only whether headings or images exist. Code and final verification must still prove the implemented behavior and visual fidelity on the actual product.

## Game screen specifications

For games, read the design and compact-spec sections in [game output guidance](../../product-cycle-game-design/references/output-guide.md). Add a readable concept/loop overview and stable gameplay rules to design.md, then link screen/actions to those rules, accepted visual targets and feedback sequences. Screen navigation alone does not define gameplay: specify entities, player decisions, rule resolution, time/turn behavior, world consequences, tunable values and recovery as applicable. Keep runtime/experience validation distinct from approval of the proposed design.
