# Screen design contract

Applies when policy.screen_design_required=true. These are Product Cycle conventions, not a universal OpenAI standard. Existing sealed cycles retain their original contract unless the owner explicitly enables this policy and reopens affected stages.

## Design

Before producing images, derive the current iteration's screen inventory, tabs, states and transitions from accepted requirements and user journeys. Discuss consequential experience choices with the owner in Codex. Each screen has a stable ID and human-readable name. Represent tabs and changed layouts as named states. Describe actions, data and animation/feedback in design.md; a static image does not specify behavior.

design.md contains shared business/interaction rules and a functional spec per screen: purpose, requirement links, entry conditions, layout/content and reference links, plus each action's availability, validation, processing, data/state effects, feedback and destination. Include applicable failure/recovery and observable acceptance examples. Reuse shared rules by reference. Architecture adds technical contracts; it must not change the behavior silently. Screen/action IDs also link plan instructions and coding to these sections. This detail lives in the existing Markdown output, not new JSON fields.

Choose a primary screen with the owner, extract reusable tokens and component variants, and design the other screens from that system. A selected Image Gen image can directly serve as the canonical baseline when it clearly communicates layout, hierarchy, colors and components. Figma is optional; its absence does not block design. Exact image pixel dimensions or aspect ratio are not absolute acceptance conditions. Record target screen dimensions, responsive rules and the mapping to the reference in design.md; reference.viewport describes the intended runtime viewport. Describe every applicable state, reusing the same image when only numbers, text, messages or button states change. Create separate images only for materially different layouts or presentation; there is no fixed image count. Keep one reference entry per screen/state/target viewport, allowing multiple entries to share the same image. Do not build HTML/CSS prototypes or run a server solely to generate the design image bundle; selected images can directly be canonical references without browser captures. Do not invent screens beyond this iteration or fabricate images when tools are unavailable.

Keep approved images authoritative for visual composition, hierarchy, layers, color and illustration; design.md determines exact labels, symbols, behavior and layout rules. Document minor text, symbol or size discrepancies and intended corrections there. Correct or regenerate an image only when the discrepancy obscures layout or forces implementation to guess. Do not require Figma merely to obtain exact pixel dimensions or every label. Existing prototype captures can supplement the images without silently replacing the baseline; do not create HTML/CSS prototypes during design. Code-native text, buttons and layouts are implemented in code. Prepare illustrations/backgrounds as separately registered assets before feature coding, using original assets or matching Image Gen edits when needed. Image Gen recreation is not lossless extraction; inspect the result. List each asset's use. Empty assets is valid for screens needing no separate art. Record licensing/source limitations in design.md without inventing rights.

Add version and screens to design-baseline.json, preserving has_ui, visual_reference, flows, states, rules and acceptance. Example screen structure:

```json
{
  "version": "1",
  "screens": [{
    "id": "play", "name": "Màn chơi", "requirements": ["R1"],
    "states": [{"id": "ready", "name": "Sẵn sàng", "description": "Nội dung, dữ liệu và hành vi đã chốt"}],
    "references": [{"state": "ready", "image": "project-relative/design/play-ready.png", "viewport": {"width": 1280, "height": 800}}],
    "transitions": [{"from_state": "ready", "action": "Bắt đầu", "to_screen": "play", "to_state": "ready"}],
    "assets": [{"name": "Nền màn chơi", "path": "project-relative/design/background.png", "usage": "Nền phía sau các mục tiêu"}]
  }]
}
```

Transitions may connect screens or states within a screen; an empty transitions array is valid for a terminal/passive screen. Register every image and asset in result.artifacts and map them to relevant requirements and steps. Non-UI products use screens:[] and a version. Describe responsive rules, meaningful error/empty/loading/success states and accessibility. Include only applicable states; explain omissions rather than adding filler screens. Design remains proposed until the owner approves the exact registered bundle. Controller structural validation does not establish aesthetic quality or owner approval.

## Plan and implementation

Each plan task adds screen_targets:[{screen_id,state,viewport:{width,height}}], or [] for backend-only work. All accepted screen/state/viewport references must be covered across the plan. Assign only targets implemented within that increment and prerequisites. Keep logic requirements/criteria separate from visual targets. Set browser_required=true for UI products. Plan real render comparison capability during development, separate from the final operator browser/interaction gate; do not turn each coding increment into a human approval gate. If the runtime lacks visual capability, record the missing capability and arrange an authorized observation rather than skipping comparison.

Build uses the exact assigned targets in context.screen_targets and the sealed reference images/hashes in accepted_inputs together with the responsive rules, state differences and corrections documented in design.md. Do not start new design exploration in a task. Implement a slice, capture at the target viewport/state, inspect the reference and render side by side, repair unintended drift, then recapture. Cover layout, proportions, typography, spacing, color/layers, asset treatment and interactions against the combined image and specification. Documented corrections to generated labels or sizes are expected, not visual failures. Do not ship a screenshot as functioning UI. Changing an approved composition or dropping an asset requires the owner's revised design decision and reopening affected work.

For UI build work and final verify, register screen-comparisons.json and the actual rendered images:

```json
{
  "baseline_version": "1",
  "source_fingerprint": "actual-current-source-fingerprint",
  "comparisons": [{
    "screen_id": "play", "state": "ready", "viewport": {"width": 1280, "height": 800},
    "reference_sha256": "hash-of-the-accepted-reference-evidence",
    "rendered_image": "project-relative/observed/play-ready.png",
    "status": "matched",
    "observations": ["Concrete inspected comparison points, remaining differences and repairs"]
  }]
}
```

The only allowed status values are matched and needs_changes. Use matched only after actual comparison; keep minor differences in observations. needs_changes records outstanding material drift and requires result.blocker until repaired. Do not invent another status or mark an unverified comparison matched to pass validation. A blocked task may retain partial comparisons or report the missing tool without a comparison report. A complete task cannot omit assigned targets, use another reference version, reuse the reference as a fake capture or claim a pass against stale source. Compute source_fingerprint using product_cycle.store.fingerprint after product changes; controller files are excluded. Final verify recaptures all targets for the final product version; earlier increments alone do not prove the final UI.

## Independent review

Inspect the pair of images and concrete observations for each target, alongside design.md and code/functional evidence. Assess whether the accepted layout and assets were preserved while applying documented responsive rules, state differences and corrections; structural existence, hashes, worker status and subjective scores do not prove fidelity. Return rework for meaningful unintended drift or missing observations, not for following specified corrections to generated text or dimensions. Keep visual comparison separate from functional/interaction acceptance and owner decisions. Reviewers must not rewrite references or evidence to obtain a pass.
