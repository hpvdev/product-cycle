---
name: product-cycle
description: Run a product development cycle with stage contracts, accepted inputs, review, and delivery evidence.
---

# Product Cycle

Use this skill when the user wants the packaged workflow applied to a selected product. Preserve the selected product, repository instructions, and authorized scope. For a narrow code task, use only the relevant task contract rather than restarting the full cycle.

The controller is the source of truth for task state. Use its status output to find the current task, accepted inputs, evidence, and decisions. Read [the operating guide](references/operating-guide.md) when initializing, resuming, recording decisions, or packaging a cycle. Read [contracts](references/contracts.md) when producing or reviewing a stage output.

The bundle includes product-cycle-analysis, product-cycle-design, product-cycle-architecture, product-cycle-plan, product-cycle-build, product-cycle-verify, product-cycle-handoff, product-cycle-retro, and product-cycle-review. Load only the skill for the assigned stage; review uses its own skill. Do not start parallel agents merely because the skills are separate.

If you are already a worker inside a controller-supplied context packet, complete that assigned contract and return its result. Do not invoke the controller recursively. Use work_steps to report advisory progress; every completed step must link concrete outputs. The controller and independent review establish confirmed status.

Work toward the assigned outcome using relevant accepted inputs. Keep facts, assumptions, open questions, and observations distinct. Supply actual files and criterion/requirement mappings. Record a blocker when a consequential decision or required capability is missing.

Submit work for independent review. Completion requires the stage contract, recorded checks where applicable, adequate evidence, and any defined product-owner decision. Do not infer a passed check from a proposed command or a screenshot from a description.

The controller owns state, immutable evidence, dependency changes, and delivery packaging. Do not edit its database or evidence objects. Scope changes go through reopen, preserving history and invalidating dependents. Retry budgets do not imply completion. Retro proposals are evaluated before adoption.
