---
name: product-cycle-project-setup
description: Set up a Product Cycle project's runtime, source structure, coding rules, shared components and verification tools from accepted architecture before feature development.
---

# Thiết lập dự án trước khi code tính năng

Read the accepted project-setup.json, plan and repository instructions. Write CODING_RULES.md before features, with conventions/tools appropriate to the stack. Preserve existing code and rules. Do not modify AGENTS.md, PRODUCT_CYCLE_RULES.md or workflow skills.

Set up the runtime, source structure, dependencies, local commands, format/lint/typecheck/test tools and shared components specified in the design. Explain unnecessary tooling. Include a safe .env.example when environment names are required. External services have their own setup tasks.

Return project-setup.md and concrete code/configuration artifacts. In controller mode follow work_steps and the output schema; the controller runs checks and independent review. Feature tasks depend on this stage. Do not invoke the controller recursively or implement unrelated features. Standalone use performs only explicitly requested setup.

Graphify may be proposed for complex existing code relationships, with a reason and available capabilities. It is not mandatory or proof of correctness; direct inspection is sufficient for a new small project.
