"""Project recorded attempts and evidence onto the dashboard's small steps."""

import json

from .contracts import STAGES, STAGE_TITLES, work_steps


def task_progress(task, tasks, config, events, decisions, root):
    aid = task["id"] + ":r" + str(task["revision"]) + ":a" + str(task["attempts"]) + ":work"
    events = [event for event in events if event["task_id"] == task["id"] and event["data"].get("attempt_id") == aid]
    tracked = any(event["type"] == "steps.started" for event in events)
    attempts = [attempt for attempt in task["attempt_history"] if attempt["revision"] == task["revision"] and attempt["number"] == task["attempts"]]
    evidence = [item for item in task["evidence"] if item["attempt_id"] and item["attempt_id"].startswith(aid.rsplit(":", 1)[0] + ":")]
    accepted = {other["id"] for other in tasks if other["status"] == "done"}
    waiting = bool(set(task["deps"]) - accepted)
    base = "stale" if task["status"] == "stale" else "waiting" if waiting else "pending"
    result_steps = {step["id"]: step for step in (task.get("result") or {}).get("steps", [])}
    review_steps = {step["id"]: step for step in (task.get("review") or {}).get("steps", [])}
    steps = []
    for definition in work_steps(task["stage"]):
        step = dict(definition, status=base, source="controller", note="", evidence=[], updated_at=None)
        for event in events:
            if event["type"] == "step.progress" and event["data"].get("step") == step["id"]:
                step.update(status=event["data"]["status"], source="worker", updated_at=event["created_at"])
        output = result_steps.get(step["id"])
        review = review_steps.get(step["id"])
        if output:
            step.update(status="reported", source="worker", note=output["summary"],
                        evidence=[item["id"] for item in evidence if item["source"] in output["artifacts"]])
        if review and review.get("passed") is True and (task.get("review") or {}).get("decision") == "approve":
            step.update(status="done", source="reviewer", note=review["reason"], evidence=review["evidence"])
        elif review and review.get("passed") is False:
            step.update(status="rework", source="reviewer", note=review.get("reason", "Cần bổ sung kết quả."), evidence=review.get("evidence", []))
        if task["attempts"] and not tracked and not output:
            step.update(status="untracked", note="Lần chạy này chưa ghi trạng thái từng bước nhỏ.")
        if task["status"] == "blocked" and step["status"] == "running":
            step.update(status="blocked", note=task.get("reason") or "Phiên làm việc bị gián đoạn.")
        steps.append(step)

    def add(sid, title, description, status=base, note="", refs=None, source="controller"):
        steps.append({"id": sid, "title": title, "description": description, "status": status,
                      "source": source, "note": note, "evidence": refs or [], "updated_at": None})

    work = next((attempt for attempt in reversed(attempts) if attempt["phase"] == "work"), None)
    artifact_refs = [item["id"] for item in evidence if item["kind"] == "artifact"]
    add("outputs", "Kiểm tra đầu ra", "Đối chiếu cấu trúc, file bắt buộc và liên kết bằng chứng.",
        "done" if task.get("result") else "blocked" if work and work["status"] == "failed" else base,
        refs=artifact_refs)
    commands = task["checks"] if task["stage"] == "build" else config.get("verification_commands", []) if task["stage"] == "verify" else []
    for index, command in enumerate(commands):
        reports = []
        for item in evidence:
            if item["kind"] == "check":
                try:
                    report = json.loads((root / item["object_path"]).read_text())
                except (OSError, ValueError):
                    continue
                if report.get("argv") == command and report.get("source_fingerprint") == task.get("fingerprint"):
                    reports.append((item, report))
        status, refs, note = base, [], ""
        if reports:
            item, report = reports[-1]
            status, refs = ("done" if report["exit_code"] == 0 else "blocked"), [item["id"]]
            note = "Kiểm tra thành công." if status == "done" else "Kiểm tra chưa thành công; xem bằng chứng để xử lý."
        elif work and task.get("result"):
            status = "blocked" if task["status"] == "blocked" else "running"
        add("check-" + str(index + 1), "Kiểm tra đã lên kế hoạch " + str(index + 1),
            " ".join(command), status, note, refs)
    if task["stage"] == "verify":
        required = config.get("browser_required", False)
        plan_done = any(other["id"] == "plan" and other["status"] == "done" for other in tasks)
        refs, covered = [], set()
        expected = {rid for other in tasks if other["stage"] == "build" and other["status"] != "superseded" for rid in other["requirements"]}
        for item in evidence:
            if item["kind"] == "browser" and item["producer"] == "operator":
                try:
                    report = json.loads((root / item["object_path"]).read_text())
                except (OSError, ValueError):
                    continue
                if report.get("source_fingerprint") == task.get("fingerprint"):
                    refs.append(item["id"])
                    covered.update(report.get("requirements", []))
        status = "not_required" if plan_done and not required else "done" if refs and expected <= covered else "blocked" if required and task["status"] == "blocked" else base
        add("browser", "Kiểm chứng giao diện và thao tác", "Quan sát sản phẩm thật, đúng phiên bản, bao phủ yêu cầu đã chốt.", status,
            "Theo phạm vi kiểm chứng của kế hoạch." if status == "not_required" else "", refs, "operator")
    latest_review = next((attempt for attempt in reversed(attempts) if attempt["phase"] == "review"), None)
    review = task.get("review") or {}
    status = {"approve": "done", "rework": "rework", "blocked": "blocked"}.get(review.get("decision"),
        "running" if latest_review and latest_review["status"] == "running" else "blocked" if latest_review else base)
    add("review", "Review độc lập", "Đánh giá từng bước và tiêu chí trên đầu ra thực tế.", status, review.get("summary", ""), source="reviewer")
    if task["stage"] in config["gates"]:
        decision = next((item for item in reversed(decisions) if item["task_id"] == task["id"] and item["revision"] == task["revision"]), None)
        status = "done" if decision and decision["action"] == "approve" and task["status"] == "done" else "rework" if decision and decision["action"] == "reject" else "awaiting_approval" if task["status"] == "awaiting_approval" else "untracked" if task["status"] == "done" else base
        add("approval", "Chủ sản phẩm duyệt kết quả", "Xem đầu ra, bằng chứng và hạn chế trước khi chấp nhận.", status,
            decision["note"] if decision else "", source="operator")
    return steps


def stage_progress(tasks, config):
    stages = []
    for stage in STAGES:
        children = [task for task in tasks if task["stage"] == stage and task["status"] != "superseded"]
        steps = [step for task in children for step in task["steps"]]
        if not children:
            steps = [dict(step, status="waiting", source="controller", note="", evidence=[], updated_at=None) for step in work_steps(stage)]
        counted = [step for step in steps if step["status"] != "not_required"]
        completed = sum(step["status"] == "done" for step in counted)
        status = "pending"
        if children and all(task["status"] == "done" for task in children):
            status = "done"
        else:
            for candidate in ["blocked", "rework", "awaiting_approval", "reviewing", "running", "stale"]:
                if any(task["status"] == candidate for task in children):
                    status = candidate
                    break
        stages.append({"id": stage, "title": STAGE_TITLES[stage], "status": status,
                       "task_ids": [task["id"] for task in children], "steps": steps,
                       "completed": completed, "total": len(counted),
                       "untracked": sum(step["status"] == "untracked" for step in counted),
                       "percent": round(100 * completed / len(counted)) if counted else 0})
    return stages
