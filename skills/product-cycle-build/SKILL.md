---
name: product-cycle-build
description: Implement an assigned Product Cycle increment using accepted inputs and report its concrete outputs for verification.
---

# Phát triển

Inspect direct callsites and applicable instructions. Reproduce bugs before patching. Finish a coherent change before relevant validation. The controller runs approved commands; do not duplicate them in worker mode. Do not expand scope or introduce test infrastructure unless the task needs it.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

1. Đọc đầu vào và tái hiện: Đọc yêu cầu, mốc thiết kế và code liên quan; tái hiện lỗi nếu đang sửa bug.
2. Triển khai trong phạm vi: Dùng mẫu hiện có và chỉ sửa phần phục vụ công việc.
3. Hoàn thiện hành vi và trạng thái: Đáp ứng luồng chính cùng các trường hợp cần thiết.
4. Đối chiếu thay đổi: Xem lại phần code đã sửa, đầu ra và hạn chế trước khi gửi kiểm chứng.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

Read the contract sections and accepted input sections relevant to this increment; use artifact paths to locate specific requirements rather than loading every document, log and earlier stage in full.

For UI work, read the assigned screen/action specification and shared rules in accepted design.md, the matching accepted visual reference, and the relevant architecture contract. Implement control availability, validation, processing, data/state changes, feedback, navigation and applicable recovery as specified. Do not infer business logic from an image or substitute a visually similar inert control. If a consequential behavior is missing or contradictory, report the exact decision and affected scope; do not block unrelated work or autonomously redesign the product. Verify behavior separately from image-to-render fidelity.

On a retry, inspect existing source, tests and recorded feedback first. Preserve usable work and finish the missing behavior or result; do not restart design, regenerate assets or rewrite accepted foundations merely because a previous turn was interrupted.

Register the actual changed source and tests with concise requirement, criterion and step mappings. Add supporting reports only when the assigned contract needs them. Return the structured result once the increment is ready for controller checks; do not prolong the turn with redundant documentation or repeated inspection of unchanged files. Token limits belong to the configured controller policy; do not invent a separate token budget in the skill.

Do not import a future dependent feature or the plan-level final browser gate as a blocker on this increment. Record unobserved UI behavior in limitations for final verification. If an assigned criterion itself depends on later work, return the specific planning conflict rather than inventing a passing result or implementing the later task.

Before feature work, read CODING_RULES.md and the accepted project_setup output. Keep its stack, shared conventions and tools in effect; report mismatches rather than replacing project foundations inside a feature task.

For frontend work, read [Frontend App Builder](../frontend-app-builder/SKILL.md), focusing on implementation and comparison of the approved design. Reuse accepted references and project components; do not restart concepting or change the stack. During authorized UI verification, compare the reference with the rendered increment in the same viewport/state, fix observed layout, typography, color, asset and interaction deviations, and retain comparison evidence. If browser work is reserved for verification or unavailable here, report the pending comparison rather than claiming a visual pass. Use the existing result schema and artifact mappings; never remove registered evidence or equate a subjective score with owner acceptance.

When policy.screen_design_required is true, read context.screen_design_contract for the assigned stage. Design inventories all screens/states/transitions before creating an image bundle accepted under the selected policy. Plan binds increments to specific screen/state/viewport targets. UI build and verify retain actual image-to-render comparisons against that bundle, with functional evidence separate. Never downgrade an approved image to a style hint or silently drop its assets.

In screen-comparisons.json, each status is exactly matched or needs_changes. Actual acceptable fidelity may be matched with minor differences retained in observations. Outstanding material drift requires needs_changes and result.blocker. Do not invent a third status or declare an unverified match to pass validation.

## Company assignments and tools

With team.enabled and team.policy = autonomous, use the company-selected accepted design after independently reviewed analysis; retain supervised owner gates in other modes. Do not seek fresh human permission for an already delegated routine implementation choice or represent company acceptance as human approval. The assigned build, frontend, backend, mobile or game_engineer worker implements the same increment contract and shares the one-source-writer boundary; it does not launch additional writers.

When an assigned requirement needs an unavailable native image or browser tool, request it through team_request_capability only when actually exposed. Identify the task, current source and exact required output; return Chờ công cụ: ... for dependent work when waiting is required. Finish independent source work before making the request, then leave source unchanged until the native result is submitted. A queue entry is not output or a passing comparison. The authorized native chat follows [company capability worker](../product-cycle-company-worker/SKILL.md); never fabricate images, captures or activity, and do not turn the plan-level final browser gate into a new blocker on this increment.

## Khi sản phẩm là game

If the brief or accepted direction asks for a game, read [Game Design](../product-cycle-game-design/SKILL.md) as a companion to this stage. Use its build guidance to implement accepted game-rule/action sections and art as a playable loop, preserving input, temporal behavior and world consequences. Do not substitute a form or decorative animation for the approved mechanic. Keep accepted scope, configured owner gates and evidence boundaries; the companion is not a new stage or an execution command.
