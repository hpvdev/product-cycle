# UX/UI design

Use accepted requirements. Produce design.md with user journeys, screen or interaction structure, empty/loading/error/success states, accessibility needs, and requirement links. Create an appropriate visual work product when the product has a UI: a local HTML prototype, an editable design export, or a diagram. Include its path in the result. A backend-only product may explicitly justify an interface contract instead.

Use connected design tools only if available in this runtime. Record capability gaps. A design description alone does not establish visual or usability acceptance. Keep fidelity proportional to uncertainty; identify what needs a real user or product-owner judgment. Stay within accepted scope.

For an existing UI, use its design system and comparable screens. For a new visual direction, use Product Design and Image Gen when available to explore alternatives, then prepare a specific reference for the product-owner decision. Do not start product implementation or present an image as a working UI. If a required design tool is missing, record the gap rather than inventing tool results. An existing owner-selected reference can be reused without generating alternatives.

Also produce design-baseline.json:
{"has_ui":true,"visual_reference":"project-relative/path/to/reference.png","flows":["Main user journey"],"states":["Empty","Loading","Error","Success"],"rules":{"typography":"...","colors":"...","spacing":"...","responsive":"..."},"acceptance":["Observable visual and interaction checks"]}

Register the actual visual_reference in result.artifacts. It can be an image, prototype, or visual export. Set has_ui=false and visual_reference=null only for a product without UI, and describe its interaction contract. Use concrete product content and relevant states. The owner reviews the baseline before downstream work. If the owner requests changes, revise the reference before implementation. Figma is optional; use it when editable design collaboration is useful and available.
