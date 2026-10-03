---
name: product-cycle
description: Run a product development cycle with stage contracts, accepted inputs, review, and delivery evidence.
---

# Product Cycle

Use this skill when the user wants the packaged workflow applied to a selected product. Preserve the selected product, repository instructions, and authorized scope. For a narrow code task, use only the relevant task contract rather than restarting the full cycle.

The controller is the source of truth for task state. Use its status output to find the current task, accepted inputs, evidence, and decisions. Read [the operating guide](references/operating-guide.md) when initializing, resuming, recording decisions, or packaging a cycle. Read [contracts](references/contracts.md) when producing or reviewing a stage output.

Work toward the assigned outcome using relevant accepted inputs. Keep facts, assumptions, open questions, and observations distinct. Supply actual files and criterion/requirement mappings. Record a blocker when a consequential decision or required capability is missing.

Submit work for independent review. Completion requires the stage contract, recorded checks where applicable, adequate evidence, and any defined product-owner decision. Do not infer a passed check from a proposed command or a screenshot from a description.

The controller owns state, immutable evidence, dependency changes, and delivery packaging. Do not edit its database or evidence objects. Scope changes go through reopen, preserving history and invalidating dependents. Retry budgets do not imply completion. Retro proposals are evaluated before adoption.
