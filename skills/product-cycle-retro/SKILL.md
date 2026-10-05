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

## Company improvement assignments

In ordinary retro or supervised mode, return evidence-backed proposals; do not apply them. Only under team.enabled and team.policy = autonomous may the controller assign the bounded improvement cycle: Process Lead selects an observed failure, Skill Engineer authors a candidate, Evaluation Engineer forward-tests the same raw cases against before/after guidance, and a separate Improvement Reviewer inspects the exact candidate and results in fresh read-only context. Read [bounded guidance improvement](../product-cycle-improve/SKILL.md) for an assigned mission and [team operation](../product-cycle/references/team-operation.md) for role boundaries. This does not add a product stage or change the retro schema.

The controller applies eligible reviewed guidance only at a stable point, with original versions, backups, evidence and rollback retained. Retro workers do not edit installed skills, invoke this cycle recursively or weaken scope, permissions, owner gates or acceptance to pass. Structural or synthetic checks alone do not show improved product judgment; missing actual forward outputs leave the candidate pending or rejected. Skills can improve instructions and tool use, not enlarge model ability or guarantee quality. No live product run is authorized merely to test an improvement.
