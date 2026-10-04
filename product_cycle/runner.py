"""Sequential work/review loop; independent context, bounded retries, real checks."""

import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path

from .codex import CodexClient, ModelCapacityError
from .contracts import FILES, RESOURCES, RESULT_SCHEMA, REVIEW_SCHEMA, STAGE_TITLES, WorkflowError, require, work_steps
from .store import fingerprint, now, write_json, runner_lock, digest
from . import desktop


def thread_title(config, task, review=False):
    # One thread covers a work item, including its small steps; keep that distinction.
    def short(text, limit):
        text = " ".join(text.split())
        if len(text) <= limit:
            return text
        return text[:limit - 1].rsplit(" ", 1)[0] + "…" if " " in text[:limit - 1] else text[:limit - 1] + "…"

    project = short(config["name"].split(" · ", 1)[0], 24)
    stage = STAGE_TITLES[task["stage"]]
    item = short(task["title"], 36)
    phase = "Review" if review else "Thực hiện"
    return f"Dự án: {project} · Bước lớn: {stage} · Công việc: {item} · {phase}"


def context(store, task):
    # Durable accepted artifacts are the source of truth; brief and relevant dependencies only.
    deps = set(task["deps"]) | {"analysis", "design", "architecture", "plan", "project_setup", "setup"}
    if task["stage"] in {"verify", "handoff"}:
        deps |= {other["id"] for other in store.tasks() if other["stage"] == "setup"}
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
            "source_fingerprint": fingerprint(store.project),
            "owner_inputs": store.owner_inputs(task["id"]),
            "repository": store.foundation()["repository"],
            "common_rules_path": str(store.project / "PRODUCT_CYCLE_RULES.md"),
            "coding_rules_path": str(store.project / "CODING_RULES.md") if (store.project / "CODING_RULES.md").is_file() else None}


def prompt_for(store, task, directory, review=False):
    role = "review" if review else task["role"]
    guide = (RESOURCES / "roles" / (role + ".md")).read_text()
    installed_skill = store.project / ".agents" / "skills" / ("product-cycle-" + role) / "SKILL.md"
    if installed_skill.is_file():
        guide = installed_skill.read_text() + "\n\n" + guide
    packet = context(store, task)
    ui_work = role == "design"
    if role in {"build", "verify"}:
        for accepted in packet["accepted_inputs"]:
            if accepted["task"] == "design":
                for artifact in accepted["artifacts"]:
                    if Path(artifact["original_path"]).name == "design-baseline.json":
                        ui_work = json.loads(Path(artifact["path"]).read_text()).get("has_ui") is True
    if ui_work:
        frontend = store.project / ".agents" / "skills" / "frontend-app-builder" / "SKILL.md"
        if not frontend.is_file():
            frontend = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills" / "frontend-app-builder" / "SKILL.md"
        packet["frontend_skill"] = {"name": "frontend-app-builder", "path": str(frontend) if frontend.is_file() else None}
        guide += ("\nFor UI work, read frontend_skill.path when available and only its references relevant to this surface. "
                  "In design, use concept guidance; in build, reuse the owner-approved baseline and use implementation guidance; "
                  "in verify, use the concept-to-render comparison guidance. Skip it for products without UI. "
                  "The assigned stage, accepted scope, stack, checks and owner decisions remain authoritative. "
                  "Do not regenerate accepted concepts or restart design in a build/verify task. "
                  "Retain registered evidence; do not delete it as temporary QA. A subjective fidelity score never establishes acceptance. "
                  "Record missing tools or observations honestly instead of claiming visual verification.")
    packet["artifact_directory"] = str(directory)
    packet["required_files"] = list(FILES.get(task["role"], []))
    if store.config.get("screen_design_required"):
        packet["screen_design_contract"] = str(RESOURCES / "screen-design.md")
        if task["role"] in {"build", "verify"}:
            packet["screen_targets"] = store.screen_targets(task["id"])
            if packet["screen_targets"]:
                packet["required_files"] += ["screen-comparisons.json"]
        guide += "\nRead screen_design_contract for the assigned stage. Use the accepted screen/state references exactly; never demote approved images to style exploration or replace them with a simpler prototype. Report tool gaps as blockers; do not fabricate screen captures or owner approval."
    if task["stage"] == "analysis" and store.config.get("collaborative_product"):
        packet["required_files"] += ["product-direction.json"]
    if store.config.get("service_setup_required") and task["stage"] == "architecture":
        packet["required_files"] = packet["required_files"] + ["services.json"]
    if store.config.get("project_setup_required") and task["stage"] == "architecture":
        packet["required_files"] = packet["required_files"] + ["project-setup.json"]
    if task["role"] == "project_setup":
        packet["project_setup"] = store.project_setup_contract()
    if task["stage"] == "setup":
        packet["service"] = next(service for service in store.services() if "setup-" + service["id"] == task["id"])
    packet["work_steps"] = work_steps(task["role"])
    packet["skill"] = {"name": "product-cycle-" + role, "path": str(installed_skill) if installed_skill.is_file() else None}
    if not review:
        aid = task["id"] + ":r" + str(task["revision"]) + ":a" + str(task["attempts"]) + ":work"
        starts = store.db.execute("SELECT data FROM events WHERE task_id=? AND type IN ('attempt.started','attempt.continued') ORDER BY id DESC", (task["id"],))
        packet["feedback"] = next((data.get("feedback") for row in starts for data in [json.loads(row[0])] if data.get("id") == aid), None)
    if review:
        packet["current_evidence"] = store.current_evidence(task["id"])
        packet["work_result"] = task["result"]
    if task["stage"] == "retro":
        packet["cycle_history"] = store.snapshot(full_history=True)
    write_json(directory / "context.json", packet)
    common = (RESOURCES / "common-rules.md").read_text()
    project_rules = store.project / "PRODUCT_CYCLE_RULES.md"
    if project_rules.is_file():
        common += "\n\n# Project common rules\n" + project_rules.read_text()
    packet["output_schema"] = REVIEW_SCHEMA if review else RESULT_SCHEMA
    write_json(directory / "context.json", packet)
    prompt = (RESOURCES / "policy.md").read_text() + "\n\n" + common + "\n\n" + guide + "\n\n" + json.dumps(packet, ensure_ascii=False, indent=2)
    if not review:
        prompt += "\nCreate the required files in artifact_directory. Build and project_setup tasks may also change product code within the project. Return the supplied result schema with project-relative artifact paths. Do not run final checks: the controller runs those once after your work. Do not change controller state, policy, databases, evidence objects, common rules, AGENTS.md, or skills."
        prompt += "\nUse update_plan when available, with exactly the work_steps and step text beginning with the ID followed by a space (for example S1 Read inputs). Update pending/in_progress/completed as work actually progresses. These reports are advisory and do not approve work. Include every work step in result.steps with a concrete summary and project-relative artifact paths drawn from result.artifacts. Do not mark a step completed based only on intended work."
        prompt += "\nWhen feedback is present, address the recorded reviewer findings and operator reason. Previous outputs are repair context, not accepted inputs. Preserve the approved criteria and scope."
    else:
        prompt += "\nThis is an independent read-only review. Inspect actual artifact content and relevant product code. Use only IDs from context.current_evidence in criteria.evidence and steps.evidence. Accepted inputs may inform the reasons, but their evidence IDs are not valid for this task. Return the supplied review schema; do not change files or treat a worker's claims as observations."
        prompt += "\nAssess each work_result.steps entry independently against work_steps. Return all IDs in review.steps with passed, real evidence IDs, and an inspected-content reason. Approve only when each step is supported. For historical results without steps, return an empty steps array and review the original criteria."
    (directory / "prompt.md").write_text(prompt)
    return prompt


def run_checks(store, task, aid, directory):
    commands = store.check_commands(task)
    for index, command in enumerate(commands):
        store.event(task["id"], "check.started", {"attempt_id": aid, "index": index + 1, "total": len(commands)})
        log = directory / ("check-" + str(index + 1) + ".log")
        started = time.monotonic()
        with log.open("wb") as output:
            try:
                process = subprocess.Popen(command, cwd=store.project, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            except OSError:
                code = -1
                output.write(b"Could not start the planned check. Verify the executable and local environment.\n")
            else:
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
        store.event(task["id"], "check.completed", {**report, "attempt_id": aid})
        require(code == 0, "Lệnh kiểm tra chưa thành công; xem bằng chứng để xử lý.")


def execute(store, tid, client_factory=CodexClient):
    task = store.task(tid)
    require(store.config["mode"] == "live", "Dữ liệu minh họa không chạy Codex; khởi tạo dự án live riêng.")
    if desktop.enabled(store):
        return desktop.prepare(store, tid)
    tokens_used = store.snapshot()["tokens"] or 0
    cycle_limit = store.config.get("max_cycle_tokens")
    require(cycle_limit is None or tokens_used < cycle_limit, "Quy trình đã đạt ngân sách token.")
    aid, directory = store.begin(tid, "work")
    try:
        task = store.task(tid)
        run_phase(store, task, aid, directory, False, client_factory)
        task = store.task(tid)
        if task["status"] == "blocked":
            raise WorkflowError(task["reason"])
        finish_work(store, tid, aid, directory, client_factory)
    except BaseException as exc:
        current = store.db.execute("SELECT status FROM attempts WHERE id=?", (aid,)).fetchone()[0]
        if current == "running":
            store.attempt_update(aid, status="failed" if isinstance(exc, Exception) else "interrupted", ended_at=now())
        store.update(tid, status="blocked", reason=str(exc) or "Phiên bị gián đoạn.")
        store.event(tid, "task.blocked", {"reason": str(exc)})
        raise


def browser_ready(store, task):
    if task["stage"] != "verify" or not store.approved_plan().get("browser_required", False):
        return True
    from .contracts import json_object
    records = store.current_evidence(task["id"])
    store.intact(records)
    covered = set()
    for record in records:
        if record["kind"] == "browser" and record["producer"] == "operator":
            report = json_object(store.root / record["object_path"])
            if report.get("source_fingerprint") == fingerprint(store.project):
                covered.update(report.get("requirements", []))
    return covered >= store.requirement_ids()


def finish_work(store, tid, aid, directory, client_factory):
    task = store.task(tid)
    # Reuse successful checks only while their source version is unchanged.
    from .contracts import json_object
    records = store.current_evidence(tid)
    store.intact(records)
    checks = [json_object(store.root / item["object_path"]) for item in records if item["kind"] == "check"]
    current = fingerprint(store.project)
    if any(not any(report.get("argv") == command and report.get("exit_code") == 0 and
                   report.get("source_fingerprint") == current for report in checks)
           for command in store.check_commands(task)):
        run_checks(store, task, aid, directory)
    store.update(tid, fingerprint=fingerprint(store.project), status="reviewing", reason=None)
    require(browser_ready(store, store.task(tid)),
            "Còn thiếu bằng chứng nghiệm thu trình duyệt cho phiên bản hiện tại. Kết quả làm tiếp trong Codex có thể được đồng bộ; các tiêu chí còn thiếu vẫn cần kiểm chứng.")
    review_task(store, tid, client_factory)


def sync_task(store, tid, client_factory=CodexClient):
    """Read a recorded chat; import work products, never convert prose into approval."""
    task = store.task(tid)
    require(task["status"] in {"blocked", "running", "reviewing"}, "Công việc này không cần khôi phục kết quả.")
    row = store.db.execute("SELECT * FROM attempts WHERE task_id=? AND revision=? AND number=? ORDER BY rowid DESC LIMIT 1",
                           (tid, task["revision"], task["attempts"])).fetchone()
    require(row is not None and row["thread_id"], "Chưa có chat Codex để đồng bộ cho công việc này.")
    attempt = dict(row)
    directory = Path(attempt["directory"])
    with client_factory(directory) as client:
        thread = client.read_thread(attempt["thread_id"])
    require(thread.get("id") == attempt["thread_id"] and Path(thread.get("cwd", "")).resolve() == store.project,
            "Chat Codex không thuộc dự án của công việc này.")
    desktop.update_usage(store, attempt, thread)
    turns = thread.get("turns", [])
    active = any(turn.get("status") == "inProgress" for turn in turns)
    previous = store.db.execute("SELECT data FROM events WHERE task_id=? AND type='thread.observed' ORDER BY id DESC LIMIT 1", (tid,)).fetchone()
    if active or previous and json.loads(previous[0]).get("active"):
        store.event(tid, "thread.observed", {"attempt_id": attempt["id"], "thread_id": thread["id"], "active": active})
    if active:
        return {"updated": False, "active": True, "message": "Chat Codex vẫn đang làm việc. Chờ phiên kết thúc rồi đồng bộ lại."}
    anchor = -1 if attempt["turn_id"] is None else next((i for i, turn in enumerate(turns) if turn.get("id") == attempt["turn_id"]), None)
    require(anchor is not None, "Chưa đọc được đầy đủ lịch sử chat để đồng bộ an toàn.")
    seen = {json.loads(row[0]).get("turn_id") for row in store.db.execute(
        "SELECT data FROM events WHERE task_id=? AND type='thread.synced'", (tid,))}
    candidates = [turn for turn in turns[anchor + 1:] if turn.get("status") == "completed"]
    if desktop.enabled(store) and turns[anchor + 1:] and turns[-1].get("status") in {"failed", "interrupted"}:
        failure = turns[-1]
        reason = "Phiên Codex đã dừng trước khi hoàn tất. Mở chat để xử lý và tiếp tục công việc."
        error = failure.get("error") or {}
        if "capacity" in str(error.get("message", "")).lower():
            reason = "Model đang quá tải. Tiếp tục trong Codex khi sẵn sàng hoặc chọn model khác."
        if attempt["status"] != "failed" or task["reason"] != reason:
            store.attempt_update(attempt["id"], status="failed", ended_at=now())
            store.update(tid, status="blocked", reason=reason)
            store.event(tid, "task.blocked", {"reason": reason})
        return {"updated": False, "active": False, "message": reason}
    if not candidates or candidates[-1].get("id") in seen:
        return {"updated": False, "active": False, "message": "Không có kết quả làm tiếp mới trong chat Codex."}
    turn = candidates[-1]
    require(isinstance(turn.get("id"), str) and re.fullmatch(r'[A-Za-z0-9-]+', turn["id"]), "Mã phiên làm tiếp chưa hợp lệ.")
    messages = [item.get("text", "") for item in turn.get("items", [])
                if item.get("type") == "agentMessage" and item.get("phase") != "commentary"]
    require(messages, "Phiên làm tiếp chưa có kết quả để đồng bộ.")
    result = None
    try:
        candidate = json.loads(messages[-1])
        if isinstance(candidate, dict):
            if attempt["phase"] == "work":
                store.validate_outputs(tid, candidate)
            else:
                store.validate_review(tid, candidate)
            result = candidate
    except (ValueError, WorkflowError):
        pass
    if result is None and (directory / "request.json").is_file() and (directory / "result.json").is_file():
        from .contracts import json_object
        request = json_object(directory / "request.json")
        candidate = json_object(directory / "result.json")
        fresh = digest(directory / "result.json") != request.get("prior_result_sha256")
        if not fresh:
            candidate = None
        if candidate is not None and attempt["phase"] == "work":
            store.validate_outputs(tid, candidate)
        elif candidate is not None:
            store.validate_review(tid, candidate)
        result = candidate
    path = directory / ("continuation-" + turn["id"] + ".json")
    write_json(path, {"thread_id": thread["id"], "turn_id": turn["id"], "phase": attempt["phase"],
                      "completed_at": turn.get("completedAt"),
                      "messages": messages, "source_fingerprint": fingerprint(store.project), "received_at": now()})
    store.record_file(tid, str(path.relative_to(store.project)), "Kết quả làm tiếp trong chat Codex", attempt_id=attempt["id"])
    if result is not None:
        if attempt["phase"] == "work":
            store.update(tid, review=None)
            store.work_finished(tid, attempt["id"], result)
        else:
            store.review_finished(tid, attempt["id"], result)
    else:
        if desktop.enabled(store):
            store.attempt_update(attempt["id"], status="completed", ended_at=now())
        # Only explicit local artifact links are ingested. They remain worker claims.
        links = [(link, store.project, 0) for link in re.findall(r'\]\(<?([^\n)]+)>?\)', "\n".join(messages))]
        visited = set()
        for link, base, depth in links:
            relative = link.strip().strip("<>")
            try:
                artifact = store.safe_path(str(base / relative))
            except WorkflowError:
                continue
            if artifact in visited:
                continue
            visited.add(artifact)
            store.record_file(tid, str(artifact.relative_to(store.project)), "Bổ sung từ chat Codex: " + artifact.name,
                              attempt_id=attempt["id"])
            if artifact.suffix.lower() == ".md" and depth < 2:
                links.extend((child, artifact.parent, depth + 1) for child in
                             re.findall(r'\]\(<?([^\n)]+)>?\)', artifact.read_text(errors="replace")))
        reason = "Đã nhận kết quả làm tiếp trong Codex. Báo cáo và bằng chứng đã được lưu; cần tiếp tục kiểm chứng các tiêu chí còn thiếu trước khi hoàn tất."
        if desktop.enabled(store) and task["stage"] in {"analysis", "design"}:
            reason = "Trao đổi đang được lưu trong Codex. Cần hoàn thiện phương án và ghi nhận quyết định của bạn trước khi chuyển bước."
        store.update(tid, status="blocked", review=None, reason=reason)
    store.event(tid, "thread.synced", {"attempt_id": attempt["id"], "thread_id": thread["id"], "turn_id": turn["id"],
                                      "structured": result is not None})
    return {"updated": True, "active": False,
            "message": "Đã đồng bộ kết quả từ Codex. Kết quả vẫn cần kiểm tra và review trước khi được công nhận hoàn tất."}


def continue_task(store, tid, client_factory=CodexClient):
    require(store.snapshot()["state"] == "active", "Quy trình đang tạm dừng. Bỏ tạm dừng trước khi tiếp tục công việc.")
    if desktop.enabled(store):
        attempt = desktop.latest(store, tid)
        if attempt and attempt["status"] in {"queued", "running"}:
            return dict(desktop.packet(store, attempt), active=attempt["status"] == "running")
        if attempt and attempt["thread_id"]:
            sync = sync_task(store, tid, client_factory)
            if sync["active"] or store.task(tid)["status"] in {"done", "awaiting_approval", "rework"}:
                return sync
        task = store.task(tid)
        if task["status"] == "reviewing" and browser_ready(store, task):
            if attempt and attempt["phase"] == "review":
                return dict(desktop.prepare(store, tid, review=True, resume=True), active=False)
            finish_work(store, tid, attempt["id"], Path(attempt["directory"]), client_factory)
            return dict(desktop.packet(store, desktop.latest(store, tid)), active=False)
        if attempt and attempt["phase"] == "review" and attempt["status"] != "completed":
            store.update(tid, status="reviewing")
            return dict(desktop.prepare(store, tid, review=True, resume=True), active=False)
        return dict(desktop.prepare(store, tid, resume=bool(attempt and attempt["phase"] == "work")), active=False)
    task = store.task(tid)
    require(all(store.task(dep)["status"] == "done" for dep in task["deps"]), "Các công việc phụ thuộc chưa hoàn tất.")
    latest = store.db.execute("SELECT * FROM attempts WHERE task_id=? AND revision=? AND number=? ORDER BY rowid DESC LIMIT 1",
                              (tid, task["revision"], task["attempts"])).fetchone()
    require(latest is not None, "Công việc chưa có phiên để khôi phục; cần mở lại sau khi xử lý nguyên nhân.")
    sync = sync_task(store, tid, client_factory) if latest["thread_id"] else {
        "updated": False, "active": False, "message": "Tiếp tục công việc sau khi kết nối Codex bị gián đoạn."}
    if sync["active"]:
        return sync
    task = store.task(tid)
    if task["status"] in {"done", "awaiting_approval", "rework"}:
        return sync
    row = store.db.execute("SELECT * FROM attempts WHERE task_id=? AND revision=? AND number=? ORDER BY rowid DESC LIMIT 1",
                           (tid, task["revision"], task["attempts"])).fetchone()
    # Completed review findings require a worker repair, not another review of unchanged output.
    repair = row["phase"] == "review" and row["status"] == "completed" and task["status"] == "blocked"
    if repair:
        row = store.db.execute("SELECT * FROM attempts WHERE task_id=? AND revision=? AND number=? AND phase='work' ORDER BY rowid DESC LIMIT 1",
                               (tid, task["revision"], task["attempts"])).fetchone()
        require(row is not None, "Chưa có phiên phát triển để xử lý nhận xét review.")
    aid, directory = row["id"], Path(row["directory"])
    try:
        if row["phase"] == "review":
            store.update(tid, status="reviewing", reason=None)
            store.attempt_update(aid, status="running", ended_at=None)
            run_phase(store, store.task(tid), aid, directory, True, client_factory, row["thread_id"])
        else:
            browser_pending = not browser_ready(store, task)
            if repair or browser_pending or not task["result"] or task["result"].get("blocker") or (sync["updated"] and task["status"] == "blocked"):
                feedback = {"reason": task["reason"], "review": task["review"], "previous_outputs": [
                    {"path": str(store.root / item["object_path"]), "original_path": item["source"]}
                    for item in store.current_evidence(tid) if item["kind"] == "artifact"]}
                if browser_pending:
                    feedback["browser_evidence_pending"] = True
                    feedback["next_action"] = ("Tiếp tục kiểm chứng những phần có thể thực hiện với công cụ hiện có. "
                                               "Đọc báo cáo bổ sung trước khi làm lại; ghi rõ các kịch bản còn thiếu và khả năng cần bổ sung. "
                                               "Không tự nhận là người nghiệm thu hoặc sửa bằng chứng đã ghi. "
                                               "Nếu không thể kiểm chứng thêm, nêu cụ thể điều cần cung cấp; không tuyên bố hoàn tất.")
                store.update(tid, status="running", reason=None, review=None)
                store.attempt_update(aid, status="running", ended_at=None)
                store.event(tid, "attempt.continued", {"id": aid, "attempt_id": aid, "thread_id": row["thread_id"], "feedback": feedback})
                run_phase(store, store.task(tid), aid, directory, False, client_factory, row["thread_id"])
                require(store.task(tid)["status"] != "blocked", store.task(tid)["reason"])
            finish_work(store, tid, aid, directory, client_factory)
    except (WorkflowError, OSError) as exc:
        if store.db.execute("SELECT status FROM attempts WHERE id=?", (aid,)).fetchone()[0] == "running":
            store.attempt_update(aid, status="failed", ended_at=now())
        store.update(tid, status="blocked", reason=str(exc))
        store.event(tid, "task.blocked", {"reason": str(exc)})
        raise
    return sync


def run_phase(store, task, aid, directory, review, client_factory, thread_id=None):
    require(not desktop.enabled(store), "Phiên này thực thi trong Codex; kết nối riêng chỉ đồng bộ kết quả.")
    config = store.config
    role = "review" if review else task["role"]
    selected = config["models"][role]
    last_activity = 0
    session = {}

    def observe(message):
        nonlocal last_activity
        method = message.get("method", "")
        params = message.get("params", {})
        if method == "client/threadReady":
            session["threadId"] = params.get("thread_id")
        elif method == "client/turnReady":
            session["turnId"] = params.get("turn_id")
        elif any(params.get(key) is not None and session.get(key) is not None and params[key] != session[key]
                 for key in ("threadId", "turnId")):
            return
        if method.startswith(("item/", "turn/", "thread/tokenUsage/")):
            current = time.monotonic()
            if current - last_activity >= 5 or method in {"item/started", "item/completed", "turn/completed"}:
                # Keep liveness without storing raw command output or reasoning text in the dashboard.
                store.event(task["id"], "runtime.activity", {"attempt_id": aid, "phase": "review" if review else "work",
                            "method": method, "item_type": params.get("item", {}).get("type")})
                last_activity = current
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
    cycle_limit = config.get("max_cycle_tokens")
    remaining = None if cycle_limit is None else cycle_limit - (store.snapshot()["tokens"] or 0)
    require(remaining is None or remaining > 0, "Quy trình đã đạt ngân sách token.")
    limits = [limit for limit in (config.get("max_turn_tokens"), remaining) if limit is not None]
    for retry in range(3):
        try:
            with client_factory(directory, on_event=observe) as client:
                options = {"thread_id": thread_id} if thread_id else {}
                output = client.run(store.project, prompt, selected["model"], selected["effort"],
                            REVIEW_SCHEMA if review else RESULT_SCHEMA, readonly=review,
                            network=config["network_access"] and not review,
                            timeout=config["turn_timeout_seconds"], max_tokens=min(limits) if limits else None,
                            title=None if thread_id else thread_title(config, task, review), **options)
            break
        except ModelCapacityError:
            if retry == 2:
                raise ModelCapacityError("Model vẫn đang quá tải sau các lần thử lại. Bạn có thể bấm Tiếp tục để thử lại với model đã chọn; các công việc độc lập vẫn có thể tiếp tục.")
            delay = 15 * (retry + 1)
            thread_id = session.get("threadId") or thread_id
            store.event(task["id"], "runtime.retry", {"attempt_id": aid, "retry": retry + 1, "delay_seconds": delay,
                                                       "model": selected["model"], "reason": "model_capacity"})
            time.sleep(delay)
            require(store.snapshot()["state"] == "active", "Quy trình đã tạm dừng; chưa bắt đầu lần thử lại.")
    result = output["result"]
    write_json(directory / "result.json", result)
    store.attempt_update(aid, tokens=output.get("tokens"), thread_id=output.get("thread_id"), turn_id=output.get("turn_id"))
    if review:
        store.review_finished(task["id"], aid, result)
    else:
        store.work_finished(task["id"], aid, result)


def review_task(store, tid, client_factory=CodexClient):
    store.validate_foundation()
    if desktop.enabled(store):
        return desktop.prepare(store, tid, review=True)
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


def run_cycle(store, max_tasks=50, client_factory=CodexClient, continue_blocked=False):
    with runner_lock(store):
        if desktop.enabled(store):
            if continue_blocked:
                for task in store.tasks():
                    if task["status"] == "blocked" and all(store.task(dep)["status"] == "done" for dep in task["deps"]):
                        return continue_task(store, task["id"], client_factory)
            return desktop.advance(store)
        require(store.snapshot()["state"] == "active", "Quy trình đang tạm dừng. Bấm Tiếp tục sau khi bỏ tạm dừng.")
        if continue_blocked:
            store.recover()
            for task in store.tasks():
                if task["status"] == "blocked":
                    try:
                        outcome = continue_task(store, task["id"], client_factory)
                        print(outcome["message"], flush=True)
                        if outcome["active"]:
                            return
                    except (WorkflowError, OSError) as exc:
                        store.event(task["id"], "continuation.waiting", {"reason": str(exc)})
            if any(task["status"] == "awaiting_approval" for task in store.tasks()):
                store.event(None, "cycle.waiting", {"reason": "owner_approval"})
        for _ in range(max_tasks):
            task = store.next_task()
            if task is None:
                return
            print("Đang thực hiện: " + task["title"], flush=True)
            try:
                execute(store, task["id"], client_factory)
            except WorkflowError:
                if store.task(task["id"])["status"] != "blocked":
                    raise
            status = store.task(task["id"])["status"]
            print("Trạng thái: " + status, flush=True)
