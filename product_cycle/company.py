"""Project-director recovery decisions, separate from product acceptance."""

import hashlib
import json

from .contracts import WorkflowError, require
from .store import fingerprint, now


def migrate(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS company_decisions(
          run_id TEXT PRIMARY KEY REFERENCES team_runs(id), task_id TEXT NOT NULL,
          revision INTEGER NOT NULL, signature TEXT NOT NULL, action TEXT,
          reason TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL);
    """)


def recovery_signature(store, task):
    value = {key: task.get(key) for key in ("id", "revision", "attempts", "reason", "status")}
    value.update(source=fingerprint(store.project), inputs=store.owner_inputs(task["id"]))
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def management_jobs(store):
    from .company_questions import snapshot
    from .capability_jobs import snapshot as capability_snapshot
    questions = snapshot(store)["open"]
    native_jobs = capability_snapshot(store)["pending"]
    for task in store.tasks():
        if task["status"] != "blocked" or any(q["task_id"] == task["id"] for q in questions):
            continue
        if any(job["task_id"] == task["id"] and job["status"] in {"queued", "claimed", "bound", "unknown"} for job in native_jobs):
            continue
        if store.db.execute("SELECT id FROM team_runs WHERE task_id=? AND revision=? AND status IN ('preparing','dispatching','running','checking','unknown','backoff')", (task["id"], task["revision"])).fetchone():
            continue
        signature = recovery_signature(store, task)
        if not store.db.execute("SELECT run_id FROM company_decisions WHERE task_id=? AND signature=?", (task["id"], signature)).fetchone():
            yield task, signature


def reserve_management(store, run, signature):
    with store.db:
        store.db.execute("INSERT INTO company_decisions VALUES(?,?,?,?,NULL,NULL,'running',?)",
                         (run["id"], run["task_id"], run["revision"], signature, now()))


def complete_management(team, run, result):
    from .company_questions import ask
    require(isinstance(result, dict) and result.get("action") in {"repair", "wait", "ask_owner"}
            and isinstance(result.get("summary"), str) and result["summary"].strip()
            and isinstance(result.get("reason"), str) and result["reason"].strip(),
            "Giám đốc dự án cần nêu cách xử lý và lý do cụ thể.")
    require(team.store.task(run["task_id"])["status"] == "blocked", "Công việc đã đổi trạng thái; không áp dụng quyết định cũ.")
    if result["action"] == "ask_owner":
        ask(team.store, run, result.get("question"), result.get("options"), result.get("recommendation"),
            result["reason"], "director-question")
        team.store.update(run["task_id"], reason="Cần bạn trả lời: " + result["question"])
    with team.db:
        team.db.execute("UPDATE company_decisions SET action=?,reason=?,status='pending' WHERE run_id=?",
                        (result["action"], result["reason"], run["id"]))
    team.event("director.decision", run, **result)


def apply_repairs(store):
    """Apply terminal decisions at a stable scope boundary; never manufacture review."""
    rows = store.db.execute("SELECT d.* FROM company_decisions d JOIN team_runs r ON r.id=d.run_id WHERE d.status='pending' AND r.status='completed'").fetchall()
    for row in rows:
        task = store.task(row["task_id"])
        if task["revision"] != row["revision"] or task["status"] != "blocked":
            status = "superseded"
        elif row["action"] != "repair":
            status = "waiting" if row["action"] == "wait" else "awaiting_answer"
        else:
            from .capability_jobs import snapshot as capability_snapshot, source_in_use
            if source_in_use(store) or any(job["task_id"] == task["id"] for job in capability_snapshot(store)["pending"]):
                continue
            if any(item["status"] in {"running", "reviewing"} for item in store.tasks()) or store.db.execute(
                    "SELECT id FROM team_runs WHERE status IN ('preparing','dispatching','running','checking','unknown')").fetchone():
                continue
            store.reopen(task["id"], "Giám đốc dự án giao sửa: " + row["reason"])
            status = "applied"
            store.event(task["id"], "company.repair_scheduled", {"run_id": row["run_id"], "reason": row["reason"]})
        with store.db:
            store.db.execute("UPDATE company_decisions SET status=? WHERE run_id=?", (status, row["run_id"]))


def management_prompt(store, task):
    from .runner import context
    history = [dict(row) for row in store.db.execute("SELECT * FROM company_decisions WHERE task_id=? ORDER BY created_at DESC LIMIT 5", (task["id"],))]
    return ("You are the AI project director responsible for delivery. Diagnose this blocked current task from actual "
            "outputs, traces and accepted inputs. Resolve routine choices within accepted scope yourself. "
            "Use a specific read-only consultation if expertise is missing; poll for real answers. "
            "Return action=repair only with a concrete next correction, not a blind repetition. "
            "A repair opens a new revision and preserves failed history and dependent checks. "
            "Do not change accepted product goals, budgets, permissions, evidence or acceptance rules. "
            "Return ask_owner only for a genuinely unresolved product decision, missing access or unsupported execution "
            "capability; include an actionable question, options, recommendation and why staff cannot resolve it. "
            "Use wait only for an identified external condition; state how it will be resolved. "
            "Inspect previous failed approaches; if no new correction is available, explain the need for owner help. "
            "Never mark a task done or claim provider/browser capability based on a job title.\n" +
            json.dumps({"context": context(store, task), "previous_decisions": history}, ensure_ascii=False))
