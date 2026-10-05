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

In analysis.md and requirements.json, establish business rules and observable interaction outcomes, including the screens and transitions implied by the core journey. Leave visual layout and the full per-control screen specification to design. Explicitly carry unresolved consequential behavior into that discussion rather than allowing coding to choose it silently.

Ask the next question that can change the product decision, in small conversational rounds. Follow up on answers instead of advancing through a fixed questionnaire. Reuse explicit choices; do not ask the owner to authorize them again. A new product needs clarity about user, outcome, core experience and quality expectations, not merely platform/content preferences. A bounded improvement with accepted discovery needs only the relevant gaps.

When the owner gives a broad audience or says they do not know, help them make progress with a concrete use scenario and explain the choices it exposes. Do not immediately turn platform/mode answers into the final scope. Resolve the most consequential missing intent through a follow-up or a concrete proposal the owner can assess; do not treat recording “unknown” as doing that discovery. For a creative or educational product, explain what makes the core experience worth using and what progress is intended, rather than only listing mechanics. Do not require novelty or new features when the owner deliberately wants a familiar product.

Before requesting final scope approval, summarize what is confirmed, proposed, unresolved and deferred. Invite correction to the product understanding before treating a detailed feature list as settled. Do not require the owner to approve every minor tuning parameter. If a consequential decision remains unavailable, ask or report the specific gap; do not fill it with an unacknowledged default.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

In supervised mode, interview the owner in Codex and preserve actual feedback through owner-input when supported. Produce the collaborative product direction contract when required. Review evaluates the substance and evidence of analysis; owner approval precedes downstream work only when a configured owner gate requires it.

In product-direction.json, open_questions lists unanswered product choices, not the formal approval gate. Close a choice only from an explicit answer or recorded owner delegation, with truthful provenance; an empty list does not grant gate approval. A delegated AI decision is not direct human feedback. Keep remaining tuning and research hypotheses in analysis.md with their evaluation or deferment.

## Company policy

This section takes precedence over the interview flow above. With team.enabled and team.policy = autonomous, analyze the brief, select reasonable reversible defaults within scope and record them as AI decisions under the selected policy. Do not require a human interview, past-use example or analysis approval when the brief supports a coherent product. Ask only for an indispensable scope decision, access, spending or unavailable execution capability; preserve independent review. In supervised mode, retain the configured human product-direction gate. When the assigned session exposes team_ask_owner, record the question, reason, meaningful options and recommendation through that tool and use only an actual recorded owner answer; an open question requires the matching Cần bạn trả lời: ... blocker for dependent work. Otherwise use the supported owner workflow in Codex. An answer resolves that question; it does not by itself approve the stage. Director delegation for later design cannot substitute for accepted product scope or authorize a new requirement. Read [team operation](../product-cycle/references/team-operation.md) for the selected policy.

## Khi sản phẩm là game

If the brief or accepted direction asks for a game, read [Game Design](../product-cycle-game-design/SKILL.md) as a companion to this stage. Use its concept and analysis guidance to establish player agency, world consequences, the core loop and chosen appeal before freezing features. Keep accepted scope, configured owner gates and evidence boundaries; the companion is not a new stage or an execution command.
