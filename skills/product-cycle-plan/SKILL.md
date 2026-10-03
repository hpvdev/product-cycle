---
name: product-cycle-plan
description: Turn accepted product and technical decisions into dependency-ordered, verifiable development increments.
---

# Lập kế hoạch

Split into user-visible increments with requirement links and observable completion criteria. Give each task only relevant checks and acyclic dependencies. Set browser_required when UI acceptance needs real interaction or appearance observations. Read and assess verification argv before owner approval.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

1. Chia lát chức năng: Mỗi công việc tạo ra một kết quả có thể nhận và kiểm tra.
2. Sắp xếp phụ thuộc: Xác định thứ tự thực hiện, tránh vòng lặp phụ thuộc.
3. Viết hợp đồng công việc: Ghi đầu vào, phạm vi, yêu cầu liên quan và tiêu chí hoàn tất.
4. Chọn cách kiểm chứng: Dùng kiểm tra phù hợp và kiểm chứng trình duyệt khi trải nghiệm yêu cầu.
5. Xác định giới hạn thực thi: Ghi khả năng công cụ, số lần thử và điều kiện dừng.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.
