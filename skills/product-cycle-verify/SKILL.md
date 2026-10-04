---
name: product-cycle-verify
description: Evaluate a built product against accepted requirements and its design baseline using observed evidence.
---

# Nghiệm thu

Keep accepted criteria unchanged. Match observations to the current product version. Compare the visual reference and rendered UI at the same viewport and state, and test the main interactions when the approved plan requires it. If browser tools are absent, record pending observation and wait for operator evidence. Never equate compilation or a screenshot with complete product acceptance.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

1. Lập đối chiếu yêu cầu: Liên kết từng tiêu chí nghiệm thu với cách kiểm chứng.
2. Kiểm tra kết quả đã ghi: Đọc kết quả thực tế và xác định đúng phiên bản sản phẩm.
3. Đánh giá trải nghiệm: So sánh giao diện với mốc thiết kế và thử hành trình; ghi thiếu bằng chứng khi chưa thể quan sát.
4. Ghi sai lệch và hạn chế: Phân biệt lỗi, giới hạn được chấp nhận và phần chưa kiểm chứng.
5. Kết luận nghiệm thu: Kết luận dựa trên bằng chứng, giữ nguyên tiêu chí đã chốt.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

When policy.screen_design_required is true, read context.screen_design_contract for the assigned stage. Design inventories all screens/states/transitions before creating an owner-approved image bundle. Plan binds increments to specific screen/state/viewport targets. UI build and verify retain actual image-to-render comparisons against that bundle, with functional evidence separate. Never downgrade an approved image to a style hint or silently drop its assets.
