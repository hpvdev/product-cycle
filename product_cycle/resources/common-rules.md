# Common development rules

These rules apply to every Product Cycle stage. Explicit user requests and applicable repository instructions take precedence. Adapt the amount of work to the task; do not add ceremony merely to fill a stage.

## Before working

- Read the project's AGENTS.md, relevant nested instructions, accepted inputs and the assigned task. Separate confirmed facts, assumptions and missing inputs.
- Inspect Git status and the relevant diff before editing. Preserve existing work, including uncommitted and untracked files. Work in the selected repository; do not borrow an unrelated parent repository.
- Resolve routine reversible choices yourself. Request information only when it affects scope, access or a decision that cannot be inferred. Missing services block only dependent tasks.

## Implementation

- Complete a small, usable increment that meets its approved requirements and criteria. Reuse existing patterns; inspect direct callsites before changing shared behavior.
- Reproduce a reported bug when practical. Finish a coherent implementation before final validation. Avoid unrelated refactors, new dependencies and test infrastructure without a concrete need.
- Keep product-facing text natural and actionable. Put diagnostics in internal logs, not user interfaces.
- Keep credentials in secure provider/OS storage or excluded environment files. Commit only a safe .env.example containing names and non-secret examples. Never put secret values in artifacts, traces, screenshots or command arguments.

## Git and changes

- Git initialization is local preparation, not a commit or publication. Preserve existing branches, remotes, history and identity settings.
- Create branches, commits, worktrees, pull requests and pushes only when the user or applicable repository instructions authorize them. Use small, coherent commits with relevant validation when authorized. Do not use destructive Git operations to obtain a clean working tree.
- Record the actual commit, branch and working-tree state alongside the source fingerprint. An uncommitted source snapshot is a valid local version; never describe it as a committed release.
- Do not edit controller state, registered evidence, installed workflow skills or common rules to pass a task. Changes to the workflow itself require an explicitly scoped request.

## Verification and completion

- The controller runs approved final checks; workers may perform focused investigation but must not repeat a passing suite without a relevant change or concern. Follow repository-required checks.
- Prefer existing tests. Add a focused regression test for a realistic bug; do not create tests that merely repeat the implementation. Add E2E or visual test infrastructure only when acceptance requires it.
- Review actual changed code and outputs in a separate read-only session. Neither a worker claim, a plan marked complete, an image nor a review opinion proves that the product runs.
- A task is complete only after required outputs, applicable checks and evidence-backed review succeed on the current version. Keep task verification separate from whole-product acceptance.
- On failure, retain logs and outputs, describe the blocker and repair the affected scope. Preserve previous attempts; do not fabricate progress or silently retry actions whose external outcome is unknown.

## Delivery and external actions

- Design enough for the current iteration, then build and verify usable increments. Update the plan when observed behavior changes the assumptions.
- State third-party needs during technical design. Configure within the authorized account, environment and scope after design and plan review. A logged-in tab alone does not establish access or authorization.
- Develop and hand over locally in the current workflow. VPS, deployment and external distribution remain deferred. Describe how to run, configure and verify the delivered source, together with actual limitations.
- Record missing capabilities honestly. Browser availability in Codex Desktop does not prove availability in a separate app-server worker. Never use an unidentified Chrome profile or the hungpv@hblab.vn / HungPV profile.
