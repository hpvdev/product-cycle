"""Sequential work/review loop; independent context, bounded retries, real checks."""

import json
import os
import signal
import subprocess
import time
from pathlib import Path

from .codex import CodexClient
from .contracts import FILES, RESOURCES, RESULT_SCHEMA, REVIEW_SCHEMA, WorkflowError, require, work_steps
from .store import fingerprint, now, write_json, runner_lock


def context(store, task):
    # Durable accepted artifacts are the source of truth; brief and relevant dependencies only.
    deps = set(task["deps"]) | {"analysis", "design", "architecture", "plan"}
    packets = []
    for other in store.tasks():
        if other["id"] in deps and other["status"] == "done":
            records = store.current_evidence(other["id"])
            store.intact(records)
            packets.append({"task": other["id"], "summary": other["result"]["summary"],
                            "artifacts": [{"id": item["id"], "path": str(store.root / item["object_path"]),
                                           "original_path": item["source"], "sha256": item["sha256"]}
                                          for item in records if item["kind"] == "artifact"]})
    return {"brief_path": str(store.root / "brief.md"), "task": task,
            "accepted_inputs": packets, "policy": store.config,
            "source_fingerprint": fingerprint(store.project)}


def prompt_for(store, task, directory, review=False):
    role = "review" if review else task["stage"]
    guide = (RESOURCES / "roles" / (role + ".md")).read_text()
    installed_skill = store.project / ".agents" / "skills" / ("product-cycle-" + role) / "SKILL.md"
    if installed_skill.is_file():
        guide = installed_skill.read_text() + "\n\n" + guide
    packet = context(store, task)
    packet["artifact_directory"] = str(directory)
    packet["required_files"] = FILES.get(task["stage"], [])
    packet["work_steps"] = work_steps(task["stage"])
    packet["skill"] = {"name": "product-cycle-" + role, "path": str(installed_skill) if installed_skill.is_file() else None}
    if not review:
        aid = task["id"] + ":r" + str(task["revision"]) + ":a" + str(task["attempts"]) + ":work"
        starts = store.db.execute("SELECT data FROM events WHERE task_id=? AND type='attempt.started' ORDER BY id DESC", (task["id"],))
        packet["feedback"] = next((data.get("feedback") for row in starts for data in [json.loads(row[0])] if data.get("id") == aid), None)
    if review:
        packet["current_evidence"] = store.current_evidence(task["id"])
        packet["work_result"] = task["result"]
    if task["stage"] == "retro":
        packet["cycle_history"] = store.snapshot(full_history=True)
    write_json(directory / "context.json", packet)
    prompt = (RESOURCES / "policy.md").read_text() + "\n\n" + guide + "\n\n" + json.dumps(packet, ensure_ascii=False, indent=2)
    if not review:
        prompt += "\nCreate the required files in artifact_directory. Build tasks may also change product code within the project. Return the supplied result schema with project-relative artifact paths. Do not run verification commands from the plan: the controller runs those once after your work. Do not change controller state, policy, databases, evidence objects, or skills."
        prompt += "\nUse update_plan when available, with exactly the work_steps and step text beginning with the ID followed by a space (for example S1 Read inputs). Update pending/in_progress/completed as work actually progresses. These reports are advisory and do not approve work. Include every work step in result.steps with a concrete summary and project-relative artifact paths drawn from result.artifacts. Do not mark a step completed based only on intended work."
        prompt += "\nWhen feedback is present, address the recorded reviewer findings and operator reason. Previous outputs are repair context, not accepted inputs. Preserve the approved criteria and scope."
    else:
        prompt += "\nThis is an independent read-only review. Inspect actual artifact content and relevant product code. Use the recorded evidence IDs. Return the supplied review schema; do not change files or treat a worker's claims as observations."
        prompt += "\nAssess each work_result.steps entry independently against work_steps. Return all IDs in review.steps with passed, real evidence IDs, and an inspected-content reason. Approve only when each step is supported. For historical results without steps, return an empty steps array and review the original criteria."
    (directory / "prompt.md").write_text(prompt)
    return prompt


def run_checks(store, task, aid, directory):
    commands = task["checks"] if task["stage"] == "build" else store.approved_plan().get("verification_commands", []) if task["stage"] == "verify" else []
    for index, command in enumerate(commands):
        log = directory / ("check-" + str(index + 1) + ".log")
        started = time.monotonic()
        with log.open("wb") as output:
            process = subprocess.Popen(command, cwd=store.project, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=store.config["turn_timeout_seconds"])
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                code = -1
        report = {"argv": command, "exit_code": code, "duration_seconds": round(time.monotonic() - started, 3),
                  "source_fingerprint": fingerprint(store.project), "log_sha256": __import__("hashlib").sha256(log.read_bytes()).hexdigest(),
                  "executed_at": now(), "executor": "controller", "log_path": str(log.relative_to(store.project))}
        path = directory / ("check-" + str(index + 1) + ".json")
        write_json(path, report)
        criteria = ["C" + str(i + 1) for i in range(len(task["criteria"]))]
        store.record_file(task["id"], str(path.relative_to(store.project)), "Kết quả lệnh kiểm tra", criteria, task["requirements"], "check", "controller", aid)
        if log.stat().st_size:
            store.record_file(task["id"], str(log.relative_to(store.project)), "Nhật ký lệnh kiểm tra", kind="artifact", producer="controller", attempt_id=aid)
        store.event(task["id"], "check.completed", report)
        require(code == 0, "Lệnh kiểm tra chưa thành công; xem bằng chứng để xử lý.")


def execute(store, tid, client_factory=CodexClient):
    task = store.task(tid)
    require(store.config["mode"] == "live", "Dữ liệu minh họa không chạy Codex; khởi tạo dự án live riêng.")
    tokens_used = store.snapshot()["tokens"] or 0
    require(tokens_used < store.config["max_cycle_tokens"], "Quy trình đã đạt ngân sách token.")
    aid, directory = store.begin(tid, "work")
    try:
        task = store.task(tid)
        run_phase(store, task, aid, directory, False, client_factory)
        task = store.task(tid)
        run_checks(store, task, aid, directory)
        store.update(tid, fingerprint=fingerprint(store.project))
        if task["stage"] == "verify" and store.approved_plan().get("browser_required", False) and not any(item["kind"] == "browser" for item in store.current_evidence(tid)):
            raise WorkflowError("Chờ bằng chứng kiểm chứng trình duyệt thực tế. Ghi nhận bằng lệnh browser-evidence rồi dùng review.")
        review_task(store, tid, client_factory)
    except BaseException as exc:
        current = store.db.execute("SELECT status FROM attempts WHERE id=?", (aid,)).fetchone()[0]
        if current == "running":
            store.attempt_update(aid, status="failed" if isinstance(exc, Exception) else "interrupted", ended_at=now())
        store.update(tid, status="blocked", reason=str(exc) or "Phiên bị gián đoạn.")
        store.event(tid, "task.blocked", {"reason": str(exc)})
        raise


def run_phase(store, task, aid, directory, review, client_factory):
    config = store.config
    role = "review" if review else task["stage"]
    selected = config["models"][role]

    def observe(message):
        method = message.get("method", "")
        params = message.get("params", {})
        if method == "client/threadReady":
            store.attempt_update(aid, **params)
        elif method == "client/turnReady":
            store.attempt_update(aid, **params)
        elif method == "thread/tokenUsage/updated":
            value = params.get("tokenUsage", {}).get("total", {}).get("totalTokens")
            if value is not None:
                store.attempt_update(aid, tokens=value)
        elif method == "model/rerouted":
            store.attempt_update(aid, observed_model=params.get("toModel"))
            store.event(task["id"], method, params)
        elif method == "turn/plan/updated":
            attempt = store.db.execute("SELECT thread_id,turn_id FROM attempts WHERE id=?", (aid,)).fetchone()
            if not review and params.get("threadId") == attempt["thread_id"] and params.get("turnId") == attempt["turn_id"]:
                store.step_progress(aid, params.get("plan"))
            store.event(task["id"], method, params)
        elif method in {"item/started", "item/completed", "turn/started", "turn/completed", "warning", "error", "turn/plan/updated"} or "request" in method.lower():
            # Stream meaningful activity without filling the journal with text deltas.
            store.event(task["id"], method, params)

    prompt = prompt_for(store, task, directory, review)
    remaining = config["max_cycle_tokens"] - (store.snapshot()["tokens"] or 0)
    require(remaining > 0, "Quy trình đã đạt ngân sách token.")
    with client_factory(directory, on_event=observe) as client:
        output = client.run(store.project, prompt, selected["model"], selected["effort"],
                            REVIEW_SCHEMA if review else RESULT_SCHEMA, readonly=review,
                            network=config["network_access"] and not review,
                            timeout=config["turn_timeout_seconds"], max_tokens=min(config["max_turn_tokens"], remaining))
    result = output["result"]
    write_json(directory / "result.json", result)
    store.attempt_update(aid, tokens=output.get("tokens"), thread_id=output.get("thread_id"), turn_id=output.get("turn_id"))
    if review:
        store.review_finished(task["id"], aid, result)
    else:
        store.work_finished(task["id"], aid, result)


def review_task(store, tid, client_factory=CodexClient):
    task = store.task(tid)
    require(task["result"] is not None and task["status"] in {"reviewing", "blocked"}, "Công việc chưa có kết quả để review.")
    store.update(tid, status="reviewing")
    aid, directory = store.begin(tid, "review")
    try:
        run_phase(store, store.task(tid), aid, directory, True, client_factory)
    except BaseException as exc:
        store.attempt_update(aid, status="failed", ended_at=now())
        store.update(tid, status="blocked", reason=str(exc))
        raise


def run_cycle(store, max_tasks=50, client_factory=CodexClient):
    with runner_lock(store):
        for _ in range(max_tasks):
            task = store.next_task()
            if task is None:
                return
            print("Đang thực hiện: " + task["title"], flush=True)
            execute(store, task["id"], client_factory)
            status = store.task(task["id"])["status"]
            print("Trạng thái: " + status, flush=True)
            if status in {"awaiting_approval", "blocked"}:
                return
