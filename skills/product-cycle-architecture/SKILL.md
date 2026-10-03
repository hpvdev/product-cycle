---
name: product-cycle-architecture
description: Design scoped data contracts, component boundaries and technical decisions from accepted requirements and design.
---

# Thiết kế kỹ thuật

Reuse existing structures. Record consequential choices and unresolved risks. Verify uncertain technical assumptions with focused experiments when useful; do not add architecture or infrastructure without a concrete requirement.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

1. Đọc cấu trúc hiện có: Xác định phần code và quy tắc liên quan; dùng lại thành phần phù hợp.
2. Thiết kế dữ liệu và giao tiếp: Mô tả dữ liệu, ranh giới thành phần và hợp đồng giao tiếp.
3. Chọn cách triển khai: Ghi lựa chọn phù hợp phạm vi và lý do đánh đổi.
4. Xử lý điểm chưa chắc: Kiểm chứng phần kỹ thuật có rủi ro hoặc ghi rõ điều còn bị chặn.
5. Xác định cách kiểm tra và khôi phục: Nêu cách chứng minh tính đúng và khôi phục khi cần.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

New local cycles use policy.service_setup_required: architecture identifies necessary services and user inputs without configuring them; plan links each increment to its required services and defines local delivery; handoff presents the verified local product. Configuration tasks run after design and plan review. VPS and external release are deferred. Respect configured owner gates.
