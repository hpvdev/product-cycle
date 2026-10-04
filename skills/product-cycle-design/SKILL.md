---
name: product-cycle-design
description: Prepare user flows and a concrete visual design baseline for owner review before product implementation.
---

# Thiết kế UX/UI

Preserve an existing design system. For new directions, use Product Design and Image Gen when available; choose a real visual target before coding. Save flows, states, design rules and acceptance criteria in design-baseline.json. A picture is a visual reference; functional and usability acceptance require a running product. The owner approves the baseline before downstream implementation. Record tool gaps instead of fabricating generations.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

1. Vẽ luồng thao tác: Liên kết hành trình chính với yêu cầu đã chốt.
2. Khảo sát hướng thiết kế: Dùng thiết kế hiện có hoặc tạo phương án bằng Product Design và Image Gen khi công cụ sẵn có.
3. Đề xuất mốc thiết kế: Lưu hình tham khảo hoặc prototype cụ thể để chủ sản phẩm duyệt.
4. Bổ sung trạng thái màn hình: Mô tả dữ liệu, trống, tải, lỗi và hoàn thành theo tính năng.
5. Chốt quy tắc và cách nghiệm thu: Ghi màu, font, khoảng cách, bố cục thích ứng và tiêu chí so sánh.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

Collaborate with the owner in Codex on journeys and concrete visual/prototype alternatives. Iterate on their feedback and await actual approval of the baseline before dependent implementation.
