# Office dashboard design QA

## Visual truth and state

- Source: `product_cycle/web/assets/office/company-wide-base.png` (1774 × 887 pixels), regenerated transparent assets in `product_cycle/web/assets/office/departments/`. The previous `docs/design/agent-company-final.png` remains historical reference.
- Implementation: `http://127.0.0.1:8790/`, read-only office projection.
- Final evidence: `docs/design/company-wide-1920.jpg` (1920 × 1080), `docs/design/company-wide-1440.jpg` (1440 × 1000), `docs/design/company-wide-panel.jpg` (580 × 791, actual in-app panel and focused engineering view).
- CSS viewports match screenshot pixels, devicePixelRatio 1. Source room content was compared within the implementation canvas, excluding native dashboard chrome. Source and screenshots were opened together in the same comparison input.
- State: synthetic preview, 31 roster positions, 0 working sessions, supervisor stopped. The static artwork does not establish actual agent activity.
- Original cool palette retained at the user's request. Native labels, panels and semantic status controls are intentional additions to the illustration.

## Comparison history and findings

1. Earlier 1920 capture: long titles broke inside words. [P2] Corrected to word wrapping, full titles without ellipsis. Post-fix evidence: `company-final-1920.jpg`.
2. Employee/team selection changed camera unexpectedly. [P2] Removed automatic pan/zoom and panel refitting. Browser checked unchanged camera transform after employee and department selection; explicit Fit remained available.
3. The source cutouts retained considerably more detail than the displayed engineering region; zoomed scene and its text appeared blurred. [P2] Removed parent bitmap scaling and persistent `will-change`; image dimensions and coordinates are rendered natively. Source engineering image and final actual-panel screenshot were opened together: faces and text now remain clear at the readable starting view.
4. At Fit, title fonts shrank and labels were crowded. [P2] Added a genuinely regenerated wider base, a 3600 × 1800 logical room, enlarged team clusters (engineering 800px), native 11px full titles, local placement and semantic overview. Actual small-panel starting view contains eight readable employee titles; whole-office overview intentionally shows departments with full roster access, rather than scattering role labels across the floor.
5. A first local-placement attempt put DEV's label far above its head because the department heading blocked the nearby band. [P2] Shifted department headings upward and removed all distant/global placement fallbacks. Recaptured actual 580 × 791 view shows all eight titles close to their employees without the long detour. Partly clipped department headings no longer overlap the bottom toolbar.

## Fidelity surfaces

- Typography: native system font, clear header hierarchy, full role names at a fixed 11px readable-view size; no employee ellipsis. Overview is intentionally department-level, with complete names retained in the roster.
- Layout rhythm: eight team zones, wide central paths and three amenity areas retained; local label bands and wider personnel spacing prevent the previous crossing-line clutter.
- Colors: original cool white/blue room and native chrome retained; no warm alternative selected.
- Imagery: all eight department groups and three amenities are actual generated raster assets, with transparency and aspect ratio preserved. No decorative illustration was replaced by CSS or SVG. Native rendered source comparison confirms clear staff imagery in the actual panel. The generated backdrop is 1774 × 887 despite a higher-resolution prompt; it is not described as a native 4K image. Extreme magnification remains limited by raster source resolution.
- Copy/content: full actual company role titles, explicit synthetic preview marker and stopped supervisor state; no invented active work.

## Interaction and technical evidence

- Browser verified employee selection, department filtering and inspector close while preserving camera, and reverified WEB selection after the native-layout changes.
- All 12 scene image paths loaded (base plus 11 cutouts); 31 employee controls present.
- Browser error/warning log empty during the 1440 check.
- Separate read-only source review verified camera preservation, keyboard/focus behavior and stale-state handling. It does not replace rendered visual QA.

## Implementation checklist

- [x] Render images at native CSS destination sizes rather than scaling the whole world bitmap.
- [x] Use legible local labels at detail scale and a coherent department overview at small scale.
- [x] Regenerate and widen the office; preserve asset aspect ratios.
- [x] Recapture desktop and actual narrow-panel views; compare source and implementation together.

## Limitations

Desktop is the requested target. Mobile acceptance and a full autonomous product delivery are outside this visual check. Real agent communication is being tested separately following the user's explicit request.

## Additional spacing iteration

- User requested additional physical seating separation so full role titles can sit close to each employee.
- Enlarged the room from3600×1800 to4800×2400; increased all department cluster widths. Regenerated the engineering group using built-in ImageGen as eight separate desk islands, preserving cool colors and actual alpha. Asset is1536×1024, not claimed as4K. Exact prompt/source: `docs/design/company-assets-spaced-engineering.json`.
- Engineering minimum head-center distance is275 logical pixels, compared with roughly168 in the previous cluster. Lower-row workers now face forward, and their titles sit above their heads rather than over chairs. Department titles moved further upward to free this label band.
- A label that cannot fit near a viewport edge no longer hides other employees' valid labels. Whole-office Fit continues to show department overview rather than densely stacking31 full titles. Narrow panels show the visible part of a team and can be panned explicitly.
- Captured `company-spaced-panel.jpg` (580×791) and `company-spaced-desktop.jpg` (1920×1080). Opened generated source and final desktop render in the same comparison input: eight distinct desks, aspect ratio preserved, all eight engineering role titles close to the corresponding heads; no actionable P0/P1/P2 visual mismatch. Original background preserved.
- Actual desktop DOM check found18 visible labels and no pairwise label intersections. Browser selected WEB, opened its correct full-title inspector and confirmed camera style unchanged; closing inspector also left the view intact. Browser error/warning log empty. Independent source review found no actionable geometry, mapping or camera issue.
- These latest captures show the live disposable test project, not the earlier synthetic preview. Activity reflects the actual controller; the artwork itself remains illustrative. Full agent/product-cycle evaluation is separate from this visual acceptance.

final result: passed
