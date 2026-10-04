# Product discovery within analysis

Use these techniques to improve decisions, not to fill a template. Scale depth to uncertainty and consequence. Keep the existing S1–S5 steps and output schema. Research or technical probes requiring additional access remain subject to the project's permissions and stage boundaries.

## Interview for intent and context

Use Jobs to Be Done as a lens: who wants to make what progress, in which situation, and what currently prevents it? Include emotional or experiential goals where relevant. For a creative product, enjoyment or expression can be the intended outcome; do not invent a business pain to justify it.

When the owner has relevant firsthand experience, ask for a specific recent occasion: what triggered it, what they tried, where it failed and what happened next. For example: “Lần gần nhất bạn học một nhóm từ mới, bạn học thế nào và phần nào khiến bạn bỏ dở?” Follow their story rather than suggesting the desired answer.

When the owner is commissioning for other people, distinguish their vision from those users' experience. Ask which observations or references support it. If none exist, keep a working hypothesis and propose a proportionate later test; do not fabricate interviews, simulate users as evidence, or automatically require a recruitment campaign.

Ask one focused question or a small related group at a time. Explain why a difficult choice matters. Offer choices when helpful, with room for a different answer; avoid leading defaults that silently set scope. Do not repeat answered questions or impose a question quota. End a round by reflecting the understanding and inviting correction.

If an answer is “everyone” or “not sure”, propose a representative situation to anchor the discussion without claiming it is researched or narrowing the audience unasked. For example, ask which outcome matters most in that situation: recognizing a new word, recalling its meaning/spelling, or practicing typing. Reuse an already chosen pair of modes; the remaining question may be their purpose or priority, not whether to select them again. When the owner has no past episode to share, explore their intended experience or a reference and its appeal instead of fabricating a customer story.

Before final scope review, the owner should be able to assess a concrete intended use, the proposed progress/value, and why the core experience is worth using. If these remain unspecified, present the useful alternatives or targeted question first. A proposal may still await owner selection; distinguish that from having no substantive answer. Later empirical validation can be deferred, but a generic hypothetical persona and a disclaimer alone do not establish shared product understanding.

## Connect outcomes, needs and solutions

Use an opportunity-to-solution outline when there are several plausible directions: desired outcome → unmet need or desired experience → possible solution → assumption to test. A short list is sufficient. Without customer evidence this is a hypothesis map, not a validated opportunity tree.

Describe a concrete end-to-end use episode: entry context, core action, feedback, result and reason to return when relevant. This exposes gaps that a list of buttons hides. Preserve the owner's chosen core mechanic; alternatives may vary how it delivers value, without replacing it unasked.

Compare materially different approaches when uncertainty warrants it. Explain which need each serves, experiential value, tradeoffs and what could make it fail. Recommend one with reasons. One direction is enough when the owner already selected it; do not invent alternatives or claim uniqueness without evidence.

For a game, describe the moment-to-moment loop in experiential terms: action, understandable feedback, reason to continue or return, and how it serves the chosen outcome. A mode toggle or visual theme alone does not explain appeal. Where the owner wants more depth, explore variations within their selected core mechanic and discuss the tradeoffs before adding features. Neither a longer feature list nor declaring the interaction “fun” answers that question.

For a vocabulary game, distinguish copying visible spelling from recalling meaning or spelling without a cue. Describe the intended learning outcome and how the mechanic supports it. Treat educational benefit and replay appeal as hypotheses to evaluate, not facts inferred from feature completeness. This example is not a mandatory game template.

## Make assumptions and scope explicit

Separate four kinds of support in analysis.md: owner-confirmed intent, reported observations with provenance, AI proposals and unknowns. Record the few assumptions whose failure would change the chosen product. For each, give its basis, consequence and a practical test or an explicit reason to defer it. Do not imply the test has happened.

Challenge arbitrary defaults such as item counts, scoring, time limits or feature exclusions. Explain what they serve; label illustrative values as adjustable proposals. Ask the owner about consequential tradeoffs, not every implementation detail. Do not turn “version one” into permission to remove the product's core appeal.

Distinguish functional acceptance from experience and outcome evaluation. A working animation proves behavior, not enjoyment; a screenshot proves appearance, not learning or retention. Quality targets should identify an observable evaluation, its requirement and any owner judgment still needed. Explain the basis for numeric thresholds, or mark them provisional for the core-experience trial.

Keep proposed user-facing labels consistent with those limits. A correct response in one round supports “answered without a hint”, not “learned” or “remembered permanently”. A disclaimer elsewhere does not correct a misleading label in the journey. Review the narrative, requirements and direction together for such contradictions.

## Fit the existing artifacts

- analysis.md: user/context/outcome; relevant episode or evidence gap; desired experience; alternatives and recommendation; why the proposed scope serves it; consequential assumptions and tests; confirmed/proposed/deferred decisions. Keep this concise and specific to the product.
- requirements.json: preserve stable IDs and testable behaviors. Explain in analysis.md how core requirements support the chosen need and journey. Do not freeze unresolved concept choices as accepted requirements.
- product-direction.json: use the existing users, problem, desired_experience, differentiation, options, recommendation and quality_targets fields. open_questions must contain specific consequential questions still awaiting resolution, consistent with the narrative and recorded feedback. Keep later tuning and research hypotheses in analysis.md with their evaluation/deferment; do not block on every unknown.

A proposal can be ready for owner selection without final scope approval. Keep any choices awaiting that selection visible in open_questions; the reviewer does not manufacture the owner's decision. An empty list is appropriate only when no consequential direction/scope question remains, not merely because the worker finished writing. Preserve the configured owner gate.

## Review substance

Map findings to the existing criteria and steps rather than inventing acceptance conditions:

- S1/C1: Is the intended user/context and desired outcome actionable enough to guide choices? “People who want this app” does not explain who benefits or how. Demographic detail is needed only if it changes the experience.
- S2/C1: Does a concrete journey explain the user's problem or desired experience, current alternative where known, and the proposed value? A mechanic alone does not establish that value.
- S3/C2: Are claims supported or honestly labeled, and consequential assumptions paired with a plausible test or deferment? A declaration of uncertainty does not cure a missing decision that changes the whole direction.
- S4/C1: Are recommendation and scope justified, material tradeoffs visible, and unresolved choices consistent across artifacts? The original appeal must survive scoping; avoid cosmetic alternatives and unexplained limits.
- S5/C2: Do requirements and quality targets evaluate the intended outcome and experience alongside behavior? Distinguish a planned test, an observed result and owner acceptance.

Return rework for unsupported analysis or contradictory records; blocked for a necessary unavailable input/capability. A proposed direction with clearly disclosed choices awaiting the configured owner gate can pass review. Do not demand market validation, a finished UI or product code at this stage, and do not pass shallow content solely because required files and fields exist.
