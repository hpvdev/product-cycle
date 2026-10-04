# Dashboard canvas design QA

Source visual truth: `docs/design/workflow-canvas-concept.png`.
Implementation: http://127.0.0.1:8787/, Quy trình, selected UI/UX stage.
Full-view evidence: `.runtime/ui-design/comparison-final.png`.
Focused evidence: `.runtime/ui-design/comparison-detail.png`.
Implementation screenshot: `.runtime/ui-design/dashboard-qa-final.png`.
Expanded canvas evidence: `.runtime/ui-design/dashboard-wide.png`.

## Comparison scope

The source is a direction concept, not a literal screenshot of a real cycle. Its illustrative tasks, statuses, icons and parallel branches must not replace recorded workflow data. The implementation keeps the stage frames, connected work/step cards, light blue palette, minimap and right inspector, and adds the requested independent panel controls. Real dependency arrows and sequential steps replace invented branches. The existing token and execution summary is intentionally retained.

Source pixels: 1487 × 1058. Final implementation capture: 1035 × 879; measured CSS viewport: 1050 × 892. Native screenshots exclude some surrounding scroll area. Earlier captures used 1280 × 720 and a wider desktop viewport. Browser dimensions changed during inspection; these are explicitly different responsive states, not a pixel-perfect comparison. The combined inputs preserve aspect ratio and letterbox into common frames without claiming a numeric similarity score. Diagram zoom is 85%; nodes can be enlarged individually or inspected in fullscreen.

## Findings and fixes

- [P1, fixed] The expanded execution report and duplicate overview placed the canvas below the fold. Full reports remain available in Overview; the graph pages now keep a compact status header.
- [P2, fixed] Initial stage fitting reduced text to 57%. Initial focus now retains a readable minimum zoom; fit-all remains available for orientation. Work and step cards were increased in height to avoid clipped names.
- [P2, fixed] The screen gallery initially stacked its inspector beneath the canvas. The layout now uses two columns and honors its empty/hidden state.
- [P2, fixed] The canvas minimum height pushed its minimap below the viewport. Available height is now measured from its visible position, and the inspector follows the canvas height. The expanded-canvas screenshot shows the minimap and controls in view.
- [P2, fixed] New screen-design wording described legacy completed work as a completed image bundle. Progress labels now follow the legacy contract when that policy is absent; sealed cycle evidence was not rewritten.

## Required fidelity surfaces

- Typography: native system sans-serif is retained deliberately. Stage, work and step names have distinct weights and sizes; longer names wrap and exact text remains available in the inspector. The concept did not supply an authoritative font file. No claim of exact font matching.
- Spacing/layout: outlined stage frames contain a larger work card and connected step cards. Readable node sizes take priority over squeezing all recorded nodes onto one screen. At narrow desktop widths, pan/zoom, fit, fullscreen and hiding either panel keep the full graph reachable.
- Colors: pale blue stage backgrounds, white cards, blue selection borders and distinct green/amber recorded states preserve the selected direction. State colors follow actual results rather than the concept's illustrative pending states.
- Image quality: diagram geometry is a code-native data visualization. Concept icons were intentionally omitted rather than copied as decorative raster content. The separate screen gallery displays registered reference/render images without flattening the workflow into an image; opening an image uses the existing evidence reader.
- Content: all recorded stages, tasks and small steps are shown. The current cycle's legacy design is not presented as a newly approved image bundle. The gallery clearly distinguishes proposal/approval, worker comparison, independent review and historical captures.

## Comparison history and checks

Initial screenshot: `.runtime/ui-design/dashboard-before.png`. First rendered comparison and fixes are above; intermediate capture: `.runtime/ui-design/dashboard-after.png`. Post-fix combined source/render input and focused input were inspected together before this report. Final expanded-panel capture verifies the viewport repair.

Browser checks: select an actual small step and inspect its evidence; hide/restore each panel; fit; zoom; pan; enter/exit fullscreen; navigate to the legacy gallery empty state. On an isolated synthetic cycle, inspect a registered reference/render pair, a self-transition, an evidence image dialog and a linked build task. Browser error logs were empty. The synthetic fixture verifies dashboard bindings, not actual product fidelity, interaction quality or autonomous delivery.

## Remaining limits

The real Vocab Blaster cycle predates the per-screen image contract. Its visual quality has not been repaired or reaccepted by this dashboard change. It still needs a newly reviewed screen bundle to use the gallery as its design source of truth. Group collapsing and a user-edited graph are outside this read-only dashboard scope.

Final result: passed

No remaining actionable P0/P1/P2 finding within the requested dashboard capability. This is a design-direction and interaction review, not a claim of pixel-perfect replication or approval of Vocab Blaster.

## Inspector follow-up

[P1, fixed] Fullscreen previously expanded only the diagram element, excluding the inspector. It now expands the diagram layout and inspector together. A visible “Hiện chi tiết / Ẩn chi tiết” toolbar button works in normal and fullscreen views. Selecting a work/step node also restores its inspector. Browser verification covered selecting an actual small step with the inspector initially hidden, showing its description and evidence within fullscreen, toggling the inspector twice, and exiting fullscreen with the selection retained. No browser errors observed. Evidence: `.runtime/ui-design/dashboard-detail-fullscreen.png`. JavaScript syntax checks and diff whitespace checks passed. No cycle task was resumed or evidence changed for this verification.
