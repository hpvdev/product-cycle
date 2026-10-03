---
name: product-cycle-retro
description: Analyze recorded workflow outcomes and propose small, evaluable improvements for the next cycle.
---

# Cải thiện quy trình

Use actual attempts, check results, review findings and owner feedback. Choose changes based on recurring or consequential failures. Every improvement needs referenced evidence and an input/expected evaluation case. Do not automatically modify active rules or add overlapping skills.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

1. Đọc lịch sử và phản hồi: Dùng bằng chứng của lần chạy để xác định điều thực sự xảy ra.
2. Tìm nguyên nhân phải làm lại: Xác định thiếu đầu vào, lỗi quy trình và can thiệp cần thiết.
3. Chọn cải tiến có tác động: Ưu tiên thay đổi nhỏ giải quyết vấn đề đã quan sát.
4. Thiết kế tình huống đánh giá: Nêu đầu vào và kết quả mong đợi để kiểm chứng cải tiến.
5. Đề xuất cho vòng sau: Đưa đề xuất có bằng chứng; chưa tự thay đổi quy trình đang chạy.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.
