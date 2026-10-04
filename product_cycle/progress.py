"""Project recorded attempts and evidence onto the dashboard's small steps."""

import json
from pathlib import Path

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
    work = next((attempt for attempt in reversed(attempts) if attempt["phase"] == "work"), None)
    definitions = work_steps(task["role"], config.get("screen_design_required", False))
    if work:
        recorded_valid = False
        try:
            recorded = json.loads((Path(work["directory"]) / "context.json").read_text()).get("work_steps")
            if (isinstance(recorded, list) and len(recorded) == len(definitions) and
                    all(isinstance(step, dict) and all(isinstance(step.get(key), str) for key in ("id", "title", "description")) for step in recorded) and
                    {step["id"] for step in recorded} == {step["id"] for step in definitions}):
                definitions = recorded
                recorded_valid = True
        except (OSError, ValueError, AttributeError, KeyError):
            pass
        # Older screen-image attempts without a context packet did not specify each action.
        if task["role"] == "design" and config.get("screen_design_required", False) and not recorded_valid:
            definitions[3] = dict(id="S4", title="Hoàn thiện trạng thái và tài nguyên", description="Thiết kế trạng thái cần thiết, bố cục theo thiết bị và hình minh họa dùng trong sản phẩm.")
            definitions[4] = dict(id="S5", title="Chốt quy tắc và cách nghiệm thu", description="Ghi màu, font, khoảng cách, bố cục thích ứng và tiêu chí so sánh.")
    steps = []
    for definition in definitions:
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

    artifact_refs = [item["id"] for item in evidence if item["kind"] == "artifact"]
    add("outputs", "Kiểm tra đầu ra", "Đối chiếu cấu trúc, file bắt buộc và liên kết bằng chứng.",
        "done" if task.get("result") else "blocked" if work and work["status"] == "failed" else base,
        "Đã kiểm tra đủ tài liệu và liên kết. Chất lượng thiết kế được đánh giá riêng; bước này không xác nhận giao diện giống mẫu." if task.get("result") else "", refs=artifact_refs)
    commands = task["checks"] if task["stage"] in {"build", "setup", "project_setup"} else config.get("verification_commands", []) if task["stage"] == "verify" else []
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
    if task.get("owner_gate") or task["stage"] in config["gates"] or task["id"] in config.get("task_gates", []):
        decision = next((item for item in reversed(decisions) if item["task_id"] == task["id"] and item["revision"] == task["revision"]), None)
        status = "done" if decision and decision["action"] == "approve" and task["status"] == "done" else "rework" if decision and decision["action"] == "reject" else "awaiting_approval" if task["status"] == "awaiting_approval" else "untracked" if task["status"] == "done" else base
        add("approval", "Chủ sản phẩm duyệt kết quả", "Xem đầu ra, bằng chứng và hạn chế trước khi chấp nhận.", status,
            decision["note"] if decision else "", source="operator")
    return steps


def stage_progress(tasks, config):
    stages = []
    for stage in STAGES:
        children = [task for task in tasks if task["stage"] == stage and task["status"] != "superseded"]
        if stage == "setup" and not children and not config.get("service_setup_required"):
            continue
        steps = [step for task in children for step in task["steps"]]
        if not children:
            steps = [dict(step, status="waiting", source="controller", note="", evidence=[], updated_at=None) for step in work_steps(stage, config.get("screen_design_required", False))]
            if stage == "setup" and any(task["id"] == "plan" and task["status"] == "done" for task in tasks):
                steps = [dict(step, status="not_required", source="controller", note="Kế hoạch không cần dịch vụ bên thứ ba.", evidence=[], updated_at=None) for step in work_steps(stage, config.get("screen_design_required", False))]
        counted = [step for step in steps if step["status"] != "not_required"]
        completed = sum(step["status"] == "done" for step in counted)
        status = "pending"
        if stage == "setup" and not children and steps[0]["status"] == "not_required":
            status = "not_required"
        elif children and all(task["status"] == "done" for task in children):
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


def development_progress(tasks, plan, cycle_state):
    """Expose every plan item without granting execution before plan approval."""
    by_id = {task["id"]: task for task in tasks}
    plan_task = by_id["plan"]
    approved = plan_task["status"] == "done"
    proposal = plan is not None and not approved
    items = plan["tasks"] if plan is not None else [task for task in tasks if task["stage"] == "build" and task["id"] != "project_setup" and task["status"] != "superseded"]
    rows = []
    for item in items:
        task = by_id.get(item["id"]) if not proposal else None
        deps = item.get("depends_on", []) if proposal else task["deps"] if task else item.get("depends_on", [])
        dependency_rows = [{"id": tid, "title": by_id[tid]["title"] if tid in by_id else next((other["title"] for other in items if other["id"] == tid), tid),
                            "status": by_id[tid]["status"] if not proposal and tid in by_id else "awaiting_plan"}
                           for tid in deps]
        status = "awaiting_plan" if proposal else task["status"] if task else "pending"
        if status == "pending":
            status = "waiting" if any(dep["status"] != "done" for dep in dependency_rows) else "ready"
        steps = task.get("steps", []) if task else []
        current = None
        for candidate in ["running", "awaiting_approval", "blocked", "rework", "reported", "stale", "waiting", "pending"]:
            current = next((step for step in steps if step["status"] == candidate), None)
            if current:
                break
        if status == "done":
            current = None
        review = (task.get("review") or {}) if task else {}
        evidence = {record["id"] for record in task["evidence"] if record["revision"] == task["revision"] and
                    record["attempt_id"] and record["attempt_id"].startswith(task["id"] + ":r" + str(task["revision"]) + ":a" + str(task["attempts"]) + ":")} if task else set()
        criteria = []
        for index, criterion in enumerate(item["criteria"]):
            cid = "C" + str(index + 1)
            assessment = next((row for row in review.get("criteria", []) if row["id"] == cid), None)
            refs = [eid for eid in assessment.get("evidence", []) if eid in evidence] if assessment else []
            criterion_status = "done" if assessment and assessment.get("passed") is True and refs and review.get("decision") == "approve" else "rework" if assessment and assessment.get("passed") is False else "pending"
            criteria.append({"id": cid, "description": criterion, "status": criterion_status, "evidence": refs})
        checks = [step for step in steps if step["id"].startswith("check-")]
        check_count = len(item.get("checks", []))
        integration_tasks = [by_id[tid] for tid in deps if tid in by_id and by_id[tid]["stage"] == "setup"]
        service_status = "not_required" if not item.get("services") and not integration_tasks else "done" if integration_tasks and all(t["status"] == "done" for t in integration_tasks) else "pending"
        rows.append({"id": item["id"], "task_id": task["id"] if task else None,
                     "title": item["title"], "instructions": item["instructions"], "status": status,
                     "dependencies": dependency_rows, "requirements": item["requirements"],
                     "criteria": criteria, "criteria_passed": sum(row["status"] == "done" for row in criteria),
                     "criteria_total": len(criteria),
                     "current_step": {key: current[key] for key in ["id", "title", "status"]} if current else None,
                     "steps_completed": sum(step["status"] == "done" for step in steps),
                     "steps_total": len([step for step in steps if step["status"] != "not_required"]),
                     "checks": {"total": check_count, "passed": sum(step["status"] == "done" for step in checks),
                                "failed": sum(step["status"] == "blocked" for step in checks)},
                     "review_status": {"approve": "done", "rework": "rework", "blocked": "blocked"}.get(review.get("decision"),
                                      "running" if task and task["status"] == "reviewing" else "pending"),
                     "service_status": service_status,
                     "reason": task.get("reason") if task else None})
    counts = {status: sum(row["status"] == status for row in rows)
              for status in ["awaiting_plan", "ready", "waiting", "running", "reviewing", "awaiting_approval", "done", "rework", "blocked", "stale"]}
    active = [task for task in tasks if task["status"] != "superseded"]
    focus = None
    for status in ["running", "reviewing", "awaiting_approval", "blocked", "rework", "stale"]:
        focus = next((task for task in active if task["status"] == status), None)
        if focus:
            break
    if focus is None:
        focus = next((task for task in active if task["status"] == "pending" and all(by_id[tid]["status"] == "done" for tid in task["deps"])), None)
    current = {"task_id": focus["id"], "title": focus["title"], "status": focus["status"],
               "step": next((step["title"] for step in focus["steps"] if step["status"] == "running"), None),
               "reason": focus["reason"]} if focus else None
    return {"plan_status": plan_task["status"], "plan_revision": plan_task["revision"],
            "proposal": proposal, "items": rows, "total": len(rows), "counts": counts,
            "completed": counts["done"], "current": current, "paused": cycle_state == "paused"}


def service_progress(services, tasks, readiness, architecture_status):
    """A worker's readiness claim is not a passed connectivity check."""
    by_id = {task["id"]: task for task in tasks}
    rows = []
    for service in services:
        task = by_id.get("setup-" + service["id"])
        if task and task["status"] == "superseded":
            task = None
        report = readiness.get(task["id"], {}) if task else {}
        item = next((row for row in report.get("services", []) if row["id"] == service["id"]), {})
        status = "planned"
        if architecture_status != "done":
            status = "proposed"
            task, item = None, {}
        elif task:
            status = {"done": "ready", "running": "configuring", "reviewing": "checking",
                      "blocked": "failed", "rework": "failed", "stale": "stale"}.get(task["status"], "planned")
            if task["status"] == "blocked" and item.get("status") == "needs_input":
                status = "needs_input"
        refs = [e["id"] for e in task["evidence"] if e["revision"] == task["revision"] and
                e["attempt_id"] and e["attempt_id"].startswith(task["id"] + ":r" + str(task["revision"]) + ":a" + str(task["attempts"]) + ":") and e["kind"] == "check"] if task else []
        rows.append(dict(service, status=status, task_id=task["id"] if task else None,
                         note=item.get("note") or (task.get("reason") if task else None), evidence=refs))
    return rows
