---
name: product-cycle-analysis
description: Discover product intent and user needs through adaptive interviews, compare meaningful directions, and write evidence-aware requirements before design or implementation.
---

# Phân tích sản phẩm

Establish why this product should exist and what a successful experience means before detailing features. Separate owner intent, reported user experience, external evidence and AI hypotheses. Owner agreement chooses a direction; it does not validate user demand or product effectiveness.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

Read [discovery guidance](references/discovery.md) when conducting product analysis or reviewing its depth. Use its interview and decision guidance within the existing five steps; it does not add controller stages or new artifact schemas.

1. Xác định người dùng và mục tiêu: Làm rõ người dùng, hoàn cảnh sử dụng, kết quả và cảm giác họ mong muốn; phản ánh lại để chủ sản phẩm sửa hiểu nhầm.
2. Làm rõ vấn đề: Khai thác tình huống cụ thể, cách đang giải quyết, khó khăn và điều khiến sản phẩm có giá trị.
3. Đối chiếu dữ kiện và giả định: Gắn nhận định với nguồn; xác định giả định quan trọng và cách kiểm chứng phù hợp.
4. Chốt phạm vi: So sánh hướng trải nghiệm, giải thích đánh đổi và ghi quyết định còn cần chốt; giữ sức hấp dẫn cốt lõi.
5. Viết yêu cầu và tiêu chí: Liên kết nhu cầu với hành trình, yêu cầu và cách đánh giá sản phẩm chạy thật.

Ask the next question that can change the product decision, in small conversational rounds. Follow up on answers instead of advancing through a fixed questionnaire. Reuse explicit choices; do not ask the owner to authorize them again. A new product needs clarity about user, outcome, core experience and quality expectations, not merely platform/content preferences. A bounded improvement with accepted discovery needs only the relevant gaps.

Before requesting final scope approval, summarize what is confirmed, proposed, unresolved and deferred. Invite correction to the product understanding before treating a detailed feature list as settled. Do not require the owner to approve every minor tuning parameter. If a consequential decision remains unavailable, ask or report the specific gap; do not fill it with an unacknowledged default.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

Interview the owner in Codex and preserve actual feedback through owner-input when supported. Produce the collaborative product direction contract when required. Review evaluates whether the proposed analysis is ready for an informed owner decision; owner approval precedes downstream work.
