---
name: product-cycle-plan
description: Turn accepted product and technical decisions into dependency-ordered, verifiable development increments.
---

# Lập kế hoạch

Split into user-visible increments with requirement links and observable completion criteria. Give each task relevant checks, service dependencies and acyclic work dependencies. Set browser_required when UI acceptance needs real interaction or appearance observations. Review verification argv and dependency coverage before execution.

In each UI task's instructions, cite the relevant design.md screen/action IDs and shared rule sections, architecture sections and accepted visual references. Keep these links in existing task instructions; do not invent new required schema fields. Criteria cover the specified behavior as well as appearance. Missing consequential specs block dependent work only; independent increments may proceed.

Task criteria must be achievable within the task and its completed prerequisites; a future dependent feature cannot be required even as explanatory UI copy. Set browser_required only at plan level for the final verify stage. Integrated browser observations belong after the increments needed for that interaction, not as an operator gate on every coding task.

When a Product Cycle context packet is supplied, its assigned task, accepted_inputs, work_steps, output schema and artifact_directory are authoritative. Use the specified step IDs in update_plan when available; report only observed progress. Return concrete artifact links and step results. In review mode return evidence-backed step judgments instead.

When invoked on its own, perform only the requested stage in the selected project. Establish the relevant inputs and authorized scope; do not restart the entire cycle or implicitly begin the next stage. Keep repository and user instructions in effect.

## Preferred flow

1. Chia lát chức năng: Mỗi công việc tạo ra một kết quả có thể nhận và kiểm tra.
2. Sắp xếp phụ thuộc: Xác định thứ tự thực hiện, tránh vòng lặp phụ thuộc.
3. Viết hợp đồng công việc: Ghi đầu vào, phạm vi, yêu cầu liên quan và tiêu chí hoàn tất.
4. Chọn cách kiểm chứng: Dùng kiểm tra phù hợp và kiểm chứng trình duyệt khi trải nghiệm yêu cầu.
5. Xác định giới hạn thực thi: Ghi khả năng công cụ, số lần thử và điều kiện dừng.

For controller-backed work, read [stage contracts](../product-cycle/references/contracts.md). State and sealed evidence belong to the controller; do not edit them. Completion follows evidence and configured decisions, not a worker claim.

New local cycles use policy.service_setup_required: architecture identifies necessary services and user inputs without configuring them; plan links each increment to its required services and defines local delivery; handoff presents the verified local product. Configuration tasks run after design and plan review. VPS and external release are deferred. Respect configured owner gates.

When policy.screen_design_required is true, read context.screen_design_contract for the assigned stage. Design inventories all screens/states/transitions before creating an image bundle accepted under the selected policy. Plan binds increments to specific screen/state/viewport targets. UI build and verify retain actual image-to-render comparisons against that bundle, with functional evidence separate. Never downgrade an approved image to a style hint or silently drop its assets.

## Company assignments

With team.enabled and team.policy = autonomous, plan from the company-selected design baseline after the human analysis gate; in supervised mode retain the configured owner approvals. A director decision is not human approval. Independent review and accepted criteria remain unchanged.

A plan task may use the optional worker field with build, frontend, backend, mobile or game_engineer. Omit it for the build fallback. Select specialization for the actual increment, retaining its requirements, criteria, dependencies, accepted references and evidence. This does not split or expand product scope, launch peers or grant another source-writer slot. The controller owns dispatch and the one-writer rule; follow [team operation](../product-cycle/references/team-operation.md).

## Khi sản phẩm là game

If the brief or accepted direction asks for a game, read [Game Design](../product-cycle-game-design/SKILL.md) as a companion to this stage. Use its planning guidance to make the first core-experience checkpoint a coherent playable loop before dependent expansion, with game-rule/action references and separate behavior, visual and experience observations. Keep accepted scope, configured owner gates and evidence boundaries; the companion is not a new stage or an execution command.
