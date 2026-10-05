---
name: product-cycle-company-worker
description: Execute authorized company capability jobs in the current native Codex Desktop chat using actual ImageGen or computer-use tools, preserving evidence for controller review.
---

# Native company capability worker

Use this skill when the owner authorizes this Codex Desktop chat to service native tool requests from an explicitly enabled autonomous Product Cycle company. Confirm team.enabled and team.policy = autonomous in the selected project; a supervised worker follows its existing execution and approval policy instead. The separate supervisor owns dispatch; this skill services actual queued jobs, not company dispatch. A queued prompt requests a capability; it grants no additional account, publication, messaging, purchase, destructive-action, or source-edit permission. Read the selected project's AGENTS.md, common rules, current task and accepted references. Stay within the owner's existing authorization. Do not launch App Server turns, a second supervisor, new chats, or scheduled automations to service the queue.

Work in the current project chat. Obtain its actual thread identity from the host and give this current chat a clear title such as “Product name · Native tools” when the host supports renaming. Do not invent a thread ID or bind a different chat. If the host cannot expose the current identity, report the gap before tool execution. A controller metadata read confirms that the bound chat belongs to the selected project; it does not make another project's chat suitable.

Use the installed `product-cycle` CLI, or `python3 -m product_cycle` from the Product-Cycle checkout. Read `--help` for the installed command if its interface differs from this source skill. Run commands for the exact selected project; do not edit controller databases, job status, or evidence objects directly.

1. `product-cycle company-work --project /absolute/project` lists pending jobs and their history. Read the job's capability, exact prompt, task revision, source fingerprint and relevant task inputs. An ImageGen request needs the actual built-in image tool. A computer-use request needs the native CUA tools. If unavailable, leave the job queued and report the specific missing tool; a CLI substitute or synthetic screenshot does not fulfill it.
2. At the source worker's task boundary, claim a queued job with `company-claim --project ... --job ... --actor "Native worker"`, then bind this actual chat with `company-bind --project ... --job ... --actor "Native worker" --thread ...`. Claiming waits for the source worker to finish with `Chờ công cụ: ...` and for source writers to stop. Do not perform the external tool action before both claim and bind succeed. A repeated claim from the same actor reuses the claim; it does not authorize another invocation.
3. Perform only the requested tool work. For `image_generation`, read the available ImageGen skill, inspect any referenced image before editing, and use built-in ImageGen. Preserve the generated original and copy the selected result into `.product-cycle/capabilities/<job_id>/` in the project. Request genuine alpha when required and inspect the saved output. Record the exact executed prompt, original generated path, source references, actual dimensions, and observed limitations. Do not substitute CSS, SVG, hand drawing, or a placeholder for the requested generated reference.
4. For `computer_use`, use the native CUA APIs and inspect actual rendered behavior. Follow their entry-point and documentation requirements. Verify the browser profile; never operate the `hungpv@hblab.vn` / HungPV profile, or an unidentified profile. Scope actions to the requested authorized app/account. Save genuine captures and a concise observation record in the assigned job directory. Record observed behavior, URLs or local app context when safe, viewport, and the tested source fingerprint. A planned check, mockup, or prose description cannot replace the real observation.
5. Save a JSON manifest in the assigned directory with this shape, using actual values:

   ```json
   {
     "source_fingerprint": "fingerprint returned by the job",
     "observations": ["What was actually observed, including any limitation or failure"],
     "tool": {
       "name": "image_gen.imagegen",
       "prompt": "Exact prompt or computer-use task actually executed"
     },
     "artifacts": [
       {"path": ".product-cycle/capabilities/JOB/output.png", "sha256": "actual SHA-256 of saved bytes", "purpose": "Concrete output or observation"}
     ]
   }
   ```

   For CUA use `mcp__cua_repl.js` as the tool name. Add truthful provenance fields such as `source_references`, `original_output`, dimensions, viewport, observed URL, or individual executed actions. All submitted artifact paths must resolve to files within this job's assigned directory, with matching hashes. Never submit credentials, private account data, or unrelated files. Report discrepancies honestly; no `passed`, `matched`, approval, or owner selection should be fabricated.
6. Submit with `company-submit --project ... --job ... --actor "Native worker" --thread ... --file /absolute/project/.product-cycle/capabilities/JOB/manifest.json`. The controller checks revision, source fingerprint, claim identity, paths and hashes, then preserves immutable output bytes. This fulfills a tool request only. It grants no accepted design status, test pass, stage approval, or product acceptance; the normal worker and independent review assess the outputs. A source change requires a current request rather than relabeling old captures as current.

After submission, continue servicing queued jobs in this same authorized chat at task boundaries. Refresh `company-work` after the supervisor advances; use short, interruptible waits when waiting is needed, and report meaningful progress or a missing owner decision. Do not leave the user with a promise that an inactive chat, timer, or scheduler will execute native tools. End at an owner gate, an explicit pause/stop, loss of required authorization or tool capability, or when no ready job or ongoing company work remains.

An expired or interrupted claim has an unknown outcome and must not be requeued or executed again automatically. Inspect the bound chat's existing outputs and actual tool history first. If complete outputs already exist, reconcile them through the same bound identity and submission path. If the outcome remains uncertain, preserve the claim and files, explain the uncertainty, and wait for a controller/owner recovery decision. Stopping a chat does not erase a completed submission. New scope revisions retain old jobs as stale history.
