# Dashboard design QA — 2026-10-04

final result: passed

## Visual truth and rendered evidence

- Selected visual: `.runtime/dashboard-design/reference.png` (Quiet Workspace, first displayed concept). The user delegated visual selection and authorized implementation.
- Implementation: `http://127.0.0.1:8787/`, `.runtime/dashboard-design/overview.jpg`.
- Full comparison: `.runtime/dashboard-design/comparison.jpg`; both images are included together in one comparison.
- Focused table comparison: `.runtime/dashboard-design/comparison-focus.jpg`. This additional crop checks readable typography, row rhythm, status labels and counts.
- CSS viewport: 1440 × 1024, devicePixelRatio 1. Source image: 1487 × 1058; returned browser screenshot: 1425 × 1013. Both were proportionally fitted into 1440 × 1024 comparison regions; no browser bezel was included.
- State: overview, all planned work items. Live pilot at final capture: 2/4 work items verified, 52/93 confirmed steps, third work item running, product handoff pending. The reference contains illustrative counts and invented content; these were replaced by actual controller data.

## Findings and comparison history

1. **[P2, fixed] Overview evidence was pushed below the desktop viewport.** The initial full-view comparison showed an oversized activity panel. Moved execution status into the project header, reduced overview table details and placed evidence under the plan in the left grid column. The final combined comparison shows the evidence heading and cards in the first viewport.
2. **[P2, fixed] HTML reference rendered an empty main area.** Initial prototype capture showed that removing all scripts also removed the reference's screen rendering. The reader now permits inline prototype behavior in an opaque-origin sandbox, without same-origin access. External scripts, embedded frames, forms and links are removed; the frame's CSP restricts resource loading. The saved prototype capture shows the pause screen, and changing the screen selector was observed.
3. **[P2, fixed] Narrow layout overflowed the page.** At a 390 × 844 override, the document's width was 604px while its available content width was 375px. Added zero-minimum grid tracks and child minimum widths. Post-fix measured page width and content width both equal 375px. Evidence: `narrow.jpg` and `narrow-reader.jpg`.
4. **[P2, fixed] Polling could close expanded specification sections.** Specification and document-library rendering now retain their DOM until their relevant data changes. The evidence reader remains separate from polling; its selected content and scroll position are preserved.

## Required fidelity surfaces

| Surface | Assessment |
| --- | --- |
| Fonts and typography | System sans serif with Vietnamese support. Navy headings, restrained weights, 13–15px dashboard content and larger document headings. Table crop confirms labels and wrapping remain readable. |
| Spacing and layout | Sidebar, three summary metrics, plan at left, stages at right, evidence below plan. Separate workflow and document views reduce nested content. Header accommodates genuine activity status and last update. |
| Colors and tokens | Light neutral canvas, white surfaces, indigo selection/action, green verification and amber attention. Restrained borders and 8–10px radii. |
| Images and assets | Actual registered image evidence is displayed without cropping or stretching. No invented avatar, brand mark, document size, PDF preview or decorative illustration from the generated mock was carried into the live product. Navigation uses clear text labels rather than substitute artwork. |
| Copy and content | Real project titles, criteria, dependencies, revisions and evidence replace generated examples. Task verification and product acceptance remain distinct. Original document content is preserved; the reader changes presentation only. |

## Primary interactions observed

- Sidebar navigation and filtering the plan to active work.
- Selecting a planned task opens its stage, work item and micro steps, with criteria and evidence alongside.
- Evidence-library stage filter.
- JSON displayed as requirements and acceptance lists; Markdown displayed as headings, lists and tables.
- Registered image displayed in the reader.
- HTML prototype displayed in a sandbox; switching its screen selector changes the rendered screen.
- Reader close, original-file links and evidence URL selection.
- Narrow-screen document reader has visible close/original controls and independently scrollable content.
- Captured browser error log was empty.

## Validation and limits

- 61 existing/controller server tests passed. These use synthetic products and do not establish game quality or autonomous product delivery.
- JavaScript syntax checks passed; targeted formatting/escaping checks covered raw markup, unsafe Markdown links and structured data.
- A temporary wheel build includes dashboard HTML, CSS and JavaScript.
- Codex links contain the real recorded thread IDs. Continuous native Codex chat streaming and the browser's protocol launch were not verified by this dashboard QA.
- Remote-resource-dependent HTML, PDFs and arbitrary diagram languages are not converted into standalone interactive models. PDF evidence opens in the browser's reader; self-contained HTML and image models are previewed here.
- No delivery approval, real product cycle, account configuration or deployment was triggered to validate the dashboard.

## Implementation checklist

- [x] Resolve visual direction and replace illustrative content with genuine data.
- [x] Preserve macro stage → work item → micro step hierarchy.
- [x] Implement readable evidence previews and retain original provenance.
- [x] Repair identified P2 issues and compare revised rendered evidence.
- [x] Keep the local dashboard open; restore the browser viewport.

## Follow-up polish

No blocking visual findings remain. A later iteration may add more document-format-specific layouts if actual project evidence requires them.
