---
name: product-cycle-reset
description: Restart an existing Product Cycle from analysis or a selected major stage for workflow iteration, preserving code, history and evidence through controller reopen commands.
---

# Làm lại quy trình Product Cycle

Use when the human requests a workflow restart, a reset from a major stage, or a repeated workflow experiment. Creating or explaining this skill does not authorize resetting a live product. A failed task that only needs continuation belongs to the normal orchestration flow, not an automatic reset.

Reset means creating new revisions and invalidating their dependent results, then preparing a fresh execution context. It does not mean deleting the project, starting Git again, clearing usage totals, erasing conversations or undoing provider configuration. Preserve source, uncommitted changes, immutable evidence, old attempts, decisions and feedback as history. Do not automatically carry earlier feedback, AI conclusions or approvals into the new execution context.

Operate as the project orchestrator. If already assigned a worker/reviewer context packet, report the requested scope change to the orchestrator instead of recursively running the controller. Read the selected project's instructions and the [operating guide](../product-cycle/references/operating-guide.md).

## Select the restart boundary

Resolve the absolute project path and inspect `status --project ...`. Use the actual task IDs, titles, stages and `deps`; never infer the target solely from a browser port, an old project name or a hardcoded task list.

- “Làm lại từ đầu” / “reset toàn bộ workflow”: reopen `analysis`, including its actual transitive dependents. Git/bootstrap preparation is preserved.
- “Làm lại từ bước lớn X”: reopen the task roots of that stage and their dependents. Earlier accepted stages remain inputs.
- “Làm lại riêng công việc X”: reopen that task, not the entire stage.
- “Reset nhưng giữ các bước sau đã hoàn tất”: explain that dependent results require revalidation; do not override controller invalidation to retain green statuses.

When project or boundary cannot be inferred, ask one concise question. An explicit reset request authorizes the corresponding non-destructive reopen; do not ask for a second approval merely because the task says reset. Briefly state the selected boundary and expected impact before mutation.

| Bước lớn | Controller stage / roots |
|---|---|
| 01 · Phân tích sản phẩm | `analysis` |
| 02 · Thiết kế UX/UI | `design` |
| 03 · Thiết kế kỹ thuật | `architecture` |
| 04 · Lập kế hoạch | `plan` |
| 05 · Cấu hình dịch vụ | Current tasks with stage `setup`; not a task named `setup` |
| 06 · Phát triển | Current tasks with stage `build`, including `project_setup` when present |
| 07 · Nghiệm thu | `verify` |
| 08 · Bàn giao | `handoff` |
| 09 · Cải thiện quy trình | `retro` |

For a stage with multiple tasks, select the smallest set of current roots whose dependency descendants cover that stage. Exclude superseded tasks as starting targets. In a DAG, these are the selected-stage tasks with no selected-stage ancestor, including ancestry through another stage. Compute affected descendants using all recorded task dependencies, as `reopen` does. Do not reopen every child separately and increment its revision twice unnecessarily.

If service setup is not required, report that there is nothing to reset there. If planned tasks have not been created yet, do not invent IDs; use an existing stage root such as `project_setup`, or explain that planning must first provide the missing tasks. Reopening service work changes recorded readiness, not actual accounts or resources.

## Ensure no writer is active

Read controller execution/attempts and, when available, the actual bound Codex chat or runner status. A stale `running` label is not proof of an active model, and an idle controller is not proof that a Desktop chat stopped writing.

1. Record the prior paused/active state and relevant task revisions. Issue `pause --project ...` to prevent new dispatch while preparing the reset. Pause takes effect at boundaries; it does not interrupt an active turn.
2. If a real worker/reviewer is active, let it stop at a safe boundary or use a supported stop operation within the user's authorization. If no safe stop mechanism is available, tell the user which chat/process must be stopped; do not reset under a live writer or kill arbitrary processes.
3. If no writer remains but controller attempts are genuinely interrupted, inspect the actual worktree and use `recover --project ...` before reopen. Recovery is global: it marks all unfinished attempts interrupted/blocked. Use it only when those affected attempts are genuinely stopped and recovery fits the authorized scope; never use it to clear a live writer or merely bypass a lock. Otherwise report the specific conflict.

Do not remove lock files or directly update SQLite/config/evidence to force readiness. Re-read status immediately before reopening. If a controller command fails, inspect its current outcome before retrying; do not repeat a successful reopen and create an extra revision.

## Reopen and verify

Run commands from the Product-Cycle checkout using `python3 -m product_cycle`, or use the installed `product-cycle` executable. Replace paths and task IDs with the selected values and quote human-supplied notes safely.

```sh
product-cycle status --project /absolute/project
product-cycle pause --project /absolute/project
# Only when verified interrupted, as described above:
product-cycle recover --project /absolute/project
product-cycle reopen --project /absolute/project --task analysis --note "Làm lại phân tích để thử hướng dẫn workflow mới; giữ lịch sử cũ."
product-cycle status --project /absolute/project
```

The example resets from analysis. For another boundary, substitute each selected root once, sequentially. Use a note describing the human's reason and what is being reconsidered; never store credentials. Keep the command's returned affected IDs and verify:

- Selected roots and dependent tasks have new revisions and no current accepted result/review; `stale` means ready for rework after prerequisites, not an error.
- Earlier/unrelated accepted tasks outside the affected set remain accepted.
- Historical attempts/evidence/decisions remain visible; old approval does not approve the new revision.
- No old worker is submitting into the reopened revision. A new dispatch must use its new request/attempt IDs.

Do not run `init` over the existing cycle, remove `.product-cycle` or the external state directory, execute destructive Git commands, or clear tokens/events. Code and deployed resources stay as they are until explicitly scoped work changes them. If the user truly needs a clean-source experiment, clarify that separate scope; this skill does not silently erase source.

## Prepare a fresh execution context

Reopening state cannot remove messages from the current chat. For a restart, use a new empty chat for the affected work, not a fork, a resumed old thread or an instruction to “forget” previous messages. The old chat may perform the reset and prepare the handoff, but must not execute the restarted work there. App Server work must likewise start a new session, not resume an old thread.

Write a concise handoff in `.product-cycle/restarts/<root>-r<revision>/handoff.md`, outside product source. Include only:

- Absolute project path, restart boundary, new revisions and whether the controller is paused.
- The original human brief and latest human request, or their precise file references. Keep project instructions and existing authorization constraints. If the original brief conflicts with the requested restart, resolve that conflict before dispatch; do not silently treat the old brief as current or rewrite controller files.
- For a partial restart, references to the still-accepted upstream inputs returned by the new context packet. For a full restart from analysis, do not import the old analysis, design, architecture or plan as decisions to follow.
- Any previous product choices the human explicitly asks to retain, identified as such. Do not paste the old conversation, conclusions, rejected designs, reports or full event history into the handoff.
- How to read current status, resume when requested, obtain the new request/prompt and bind the new chat through the normal native loop. Use the newly prepared paths and attempt IDs, never old context.json or prompt.md files.

Controller packets select owner inputs by current revision and accepted evidence by current status. If the human explicitly retains a past answer, record its safe summary through `owner-input` in the new analysis/design revision; old approval never approves the new revision. Historical files and chats remain available for a specifically requested audit, not as default product inputs. Existing code is an implementation to assess against the new requirements, not proof of the intended scope or design.

Give the human the handoff path and a short opening message, for example: “Dùng $product-cycle trong dự án này. Đọc <absolute handoff path>, rồi tiếp tục từ ranh giới đã ghi bằng đầu vào hiện tại.” Create a new user-owned chat only if the human explicitly requests a new chat; otherwise leave paused and let them open it. Do not claim a clean execution context has started until work actually runs in that new session. A fresh chat does not erase source, project instructions or host-provided context.

## Workflow updates and continuation

A reset does not reinstall skills or cause an existing chat to forget its context. Check the requested instruction versions before continuing. If the human explicitly asks to test changed workflow instructions, preview `update-skills --project ... --skill <name>` and inspect relevant differences; use `--apply` for authorized updates after writers stop. Conflicts require reconciliation or an explicit choice to replace selected customizations with the backed-up `--replace-customized` option. Re-read the updated skills in the active chat. Otherwise report any mismatch; do not overwrite installed skills or policy as a side effect of reset. Missing bundled skills can be installed by the same update command without replacing unrelated skills.

If the human also requests uninstall/reinstall, use `uninstall-skills --project ...` to preview, then `--apply` after writers stop, followed by `install-skills --project ...` from the desired workflow version. Use `--force` only for explicitly authorized removal of customized/unknown bundled skills, retaining the returned backup. This changes installed skills, not source, state or approvals. Do not bootstrap between removal and reinstall; it would reinstall missing skills. Reopening and preparing the fresh-context handoff remain separate operations.

By default, reset only and leave the cycle paused at the new boundary so the owner can change instructions or inspect the result. Say explicitly that no worker has started. When the human also requests continuation, resume and execute through the normal loop in the new chat/session described above. If it is not available, provide the handoff and leave paused rather than continue in the old chat. Desktop `run` prepares a request; the new project chat must bind and execute it. It does not automatically launch a model. Keep the configured owner decisions and independent review.

If only an earlier stage was requested, continue only that stage and its review; do not silently run through later stages. Do not create/message Codex chats, start monitoring schedules, purchase services, redeploy, or change model/effort as reset side effects. Any such action needs the corresponding human authorization.

Finish with a short report: project, restart boundary, actual affected work, preserved history/source, clean handoff path and retained inputs, instruction version caveat if relevant, and whether the cycle is paused or execution really resumed in a new session. Distinguish controller reopening from a successfully completed rerun.
