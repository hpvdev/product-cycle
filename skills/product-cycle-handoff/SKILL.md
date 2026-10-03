---
name: product-cycle-handoff
description: Prepare delivery instructions and evidence for the exact product version that passed acceptance.
---

# Bàn giao

Tie delivery to the accepted version and recorded checks. Include setup, usage, known limitations and suitable recovery instructions. Controller packaging happens after required decisions and retro. Delivery does not authorize deployment or publication.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

1. Xác định phiên bản bàn giao: Liên kết bản bàn giao với đúng phiên bản đã nghiệm thu.
2. Viết hướng dẫn chạy và sử dụng: Ghi cách thiết lập và thao tác để người nhận sử dụng được.
3. Tập hợp đầu ra và bằng chứng: Liên kết tài liệu, source và kết quả kiểm chứng.
4. Ghi cách khôi phục: Nêu phương án khôi phục phù hợp với cách bàn giao.
5. Chốt hạn chế và việc tiếp theo: Ghi rõ những phần chưa thực hiện hoặc chưa kiểm chứng.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.
