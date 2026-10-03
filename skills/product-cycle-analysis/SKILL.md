---
name: product-cycle-analysis
description: Analyze product goals, user problems, assumptions and testable requirements before design or implementation.
---

# Phân tích sản phẩm

Separate facts from hypotheses. Ask only for decisions that materially affect scope. Do not treat AI-generated user opinions as research evidence.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

1. Xác định người dùng và mục tiêu: Nêu ai sử dụng sản phẩm và kết quả họ cần đạt.
2. Làm rõ vấn đề: Mô tả tình huống sử dụng, khó khăn và nhu cầu chính.
3. Đối chiếu dữ kiện và giả định: Ghi nguồn, giả định và câu hỏi còn ảnh hưởng tới quyết định.
4. Chốt phạm vi: Xác định phiên bản đầu tiên, giới hạn và những phần để sau.
5. Viết yêu cầu và tiêu chí: Mỗi yêu cầu có hành vi quan sát được để nghiệm thu.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.
