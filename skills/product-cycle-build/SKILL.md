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

Before feature work, read CODING_RULES.md and the accepted project_setup output. Keep its stack, shared conventions and tools in effect; report mismatches rather than replacing project foundations inside a feature task.
