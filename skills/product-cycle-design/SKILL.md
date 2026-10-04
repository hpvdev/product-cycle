---
name: product-cycle-design
description: Specify screen behavior, shared interaction rules and a concrete visual design baseline for owner review before product implementation.
---

# Thiết kế UX/UI

Preserve an existing design system. For new directions, use Product Design and Image Gen when available; choose a real visual target before coding. Save flows, states, design rules and acceptance criteria in design-baseline.json. A picture is a visual reference; functional and usability acceptance require a running product. The owner approves the baseline before downstream implementation. Record tool gaps instead of fabricating generations.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

Read [functional and screen specification](references/screen-spec.md) for UI design outputs. Write the shared rules and per-screen behavior in design.md alongside the registered visual baseline; images alone are not the specification. This uses existing outputs, not an additional controller stage or JSON schema.

1. Vẽ luồng thao tác: Liên kết hành trình, danh sách màn hình và đường chuyển với yêu cầu đã chốt.
2. Khảo sát hướng thiết kế: Dùng thiết kế hiện có hoặc tạo phương án bằng Product Design và Image Gen khi công cụ sẵn có.
3. Đề xuất mốc thiết kế: Lưu hình tham khảo hoặc prototype cụ thể để chủ sản phẩm duyệt.
4. Đặc tả màn hình và thao tác: Ghi bố cục, nội dung, điều kiện thao tác, xử lý, thay đổi dữ liệu, phản hồi và chuyển màn; bao phủ các trạng thái cần thiết.
5. Chốt quy tắc và cách nghiệm thu: Ghi màu, font, khoảng cách, bố cục thích ứng và tiêu chí so sánh.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

Collaborate with the owner in Codex on journeys and concrete visual/prototype alternatives. Iterate on their feedback and await actual approval of the baseline before dependent implementation.

For new UI or an approved redesign, use the concept guidance in [Frontend App Builder](../frontend-app-builder/SKILL.md) alongside Product Design and Image Gen when available. Design the full core surface, not just its header. Create additional section/state concepts when details or a new layout are unclear; routine screens can reuse a common prototype, but every declared screen/state still needs a viewable image when screen_design_required is enabled. Reuse the chosen visual system for familiar screens, preserving real content and interactions. Record reference coverage, tokens and component variants in the baseline's rules and design.md so coding can reuse them. An approved reference remains the implementation target; later tasks must not silently replace it.

When policy.screen_design_required is true, read context.screen_design_contract for the assigned stage. Design inventories all screens/states/transitions before creating an owner-approved image bundle. Plan binds increments to specific screen/state/viewport targets. UI build and verify retain actual image-to-render comparisons against that bundle, with functional evidence separate. Never downgrade an approved image to a style hint or silently drop its assets.
