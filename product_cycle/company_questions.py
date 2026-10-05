"""Durable owner questions. Responses are input, never approval decisions.

The caller authenticates the owner endpoint and runtime tool origin. The supervisor
holds runner_lock when calling resume_answered for tasks blocked on these questions.
"""

import json
import uuid

from .contracts import require
from .store import now


BLOCKER_PREFIX = "Cần bạn trả lời: "


def migrate(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS company_questions(
          id TEXT PRIMARY KEY, source_run_id TEXT NOT NULL REFERENCES team_runs(id),
          source_agent_id TEXT NOT NULL, task_id TEXT NOT NULL REFERENCES tasks(id),
          revision INTEGER NOT NULL, question TEXT NOT NULL, options TEXT NOT NULL,
          recommendation TEXT, reason TEXT NOT NULL, client_key TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('open','answered')), created_at TEXT NOT NULL,
          answered_at TEXT, actor TEXT, answer TEXT, owner_input_id INTEGER REFERENCES events(id),
          consumed_at TEXT, UNIQUE(source_run_id,client_key));
    """)


def _text(value, message):
    require(isinstance(value, str) and value.strip(), message)
    return value.strip()


def _read(store, question_id):
    row = store.db.execute("""SELECT q.*, t.revision AS current_revision,
        t.title AS task_title, t.stage AS stage,r.thread_id AS source_thread_id
        FROM company_questions q JOIN tasks t ON t.id=q.task_id
        JOIN team_runs r ON r.id=q.source_run_id WHERE q.id=?""", (question_id,)).fetchone()
    require(row is not None, "Không tìm thấy câu hỏi cần phản hồi.")
    value = dict(row)
    value["options"] = json.loads(value["options"])
    value["owner_thread_id"] = store.config.get("owner_chat", {}).get("thread_id")
    value["is_current"] = value["revision"] == value["current_revision"]
    value["recorded_status"] = value["status"]
    if not value["is_current"]:
        value["status"] = "stale"
    return value


def ask(store, run, question, options, recommendation, reason, client_key):
    """Create/replay a question from an authenticated, current running mission."""
    question = _text(question, "Cần ghi rõ câu hỏi muốn chủ sản phẩm trả lời.")
    reason = _text(reason, "Cần giải thích vì sao nhóm cần quyết định của chủ sản phẩm.")
    client_key = _text(client_key, "Cần mã yêu cầu để tránh gửi trùng câu hỏi.")
    require(isinstance(options, list) and all(isinstance(item, str) and item.strip() for item in options),
            "Các lựa chọn trả lời cần là danh sách nội dung rõ ràng.")
    options = [item.strip() for item in options]
    require(recommendation is None or isinstance(recommendation, str), "Đề xuất trả lời chưa hợp lệ.")
    recommendation = (recommendation.strip() or None) if recommendation is not None else None
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        origin = store.db.execute("""SELECT r.*, t.revision AS current_revision,
            t.attempts AS current_attempt, t.status AS task_status, a.number AS attempt_number,
            a.revision AS attempt_revision FROM team_runs r JOIN tasks t ON t.id=r.task_id
            LEFT JOIN attempts a ON a.id=r.attempt_id WHERE r.id=?""", (run.get("id"),)).fetchone()
        require(origin is not None and all(run.get(key) == origin[key] for key in ("agent_id", "task_id", "revision")),
                "Câu hỏi cần xuất phát từ phiên được giao công việc này.")
        require(origin["status"] == "running" and origin["revision"] == origin["current_revision"]
                and origin["task_status"] != "done", "Phiên này không còn nhận câu hỏi cho phạm vi hiện tại.")
        require(origin["attempt_id"] is None or (origin["attempt_number"] == origin["current_attempt"]
                and origin["attempt_revision"] == origin["current_revision"]), "Câu hỏi thuộc lần thực hiện đã kết thúc.")
        previous = store.db.execute("SELECT id FROM company_questions WHERE source_run_id=? AND client_key=?",
                                    (origin["id"], client_key)).fetchone()
        if previous:
            existing = _read(store, previous["id"])
            require(all(existing[key] == value for key, value in
                        (("question", question), ("options", options), ("recommendation", recommendation), ("reason", reason))),
                    "Yêu cầu này đã được dùng cho câu hỏi khác.")
            return existing
        question_id = "question-" + uuid.uuid4().hex
        store.db.execute("""INSERT INTO company_questions(id,source_run_id,source_agent_id,task_id,
            revision,question,options,recommendation,reason,client_key,status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,'open',?)""",
            (question_id, origin["id"], origin["agent_id"], origin["task_id"], origin["revision"],
             question, json.dumps(options, ensure_ascii=False), recommendation, reason, client_key, now()))
        return _read(store, question_id)


def answer(store, question_id, actor, text):
    """Record one immutable owner response; identical retries do not duplicate input."""
    actor = _text(actor, "Cần ghi người trả lời câu hỏi.")
    text = _text(text, "Cần ghi nội dung trả lời.")
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        question = _read(store, question_id)
        require(question["is_current"], "Phạm vi đã thay đổi; hãy trả lời câu hỏi của phạm vi hiện tại.")
        task = store.db.execute("SELECT status FROM tasks WHERE id=?", (question["task_id"],)).fetchone()
        require(task["status"] != "done", "Công việc đã chốt; cần mở lại trước khi thay đổi định hướng.")
        if question["answered_at"]:
            require(question["actor"] == actor and question["answer"] == text,
                    "Câu hỏi đã có câu trả lời. Hãy trao đổi tiếp bằng một câu hỏi mới.")
            return question
        timestamp = now()
        data = {"revision": question["revision"], "actor": actor,
                "note": question["question"] + "\nPhản hồi: " + text,
                "question_id": question_id, "source_run_id": question["source_run_id"],
                "source_agent_id": question["source_agent_id"], "answer": text}
        event = store.db.execute("INSERT INTO events(task_id,type,data,created_at) VALUES(?,'owner.input',?,?)",
                                 (question["task_id"], json.dumps(data, ensure_ascii=False), timestamp))
        store.db.execute("""UPDATE company_questions SET status='answered',answered_at=?,actor=?,
            answer=?,owner_input_id=? WHERE id=?""", (timestamp, actor, text, event.lastrowid, question_id))
        return _read(store, question_id)


def snapshot(store):
    """Return current open questions and complete answered/stale history, newest first."""
    rows = [_read(store, row["id"]) for row in store.db.execute(
        "SELECT id FROM company_questions ORDER BY rowid DESC")]
    return {"open": [row for row in rows if row["status"] == "open"],
            "answered": [row for row in rows if row["answered_at"]], "history": rows}


def resume_answered(store, task_id=None):
    """Consume responses once and resume a question-blocked task in its same revision.

    Only tasks carrying BLOCKER_PREFIX may resume. Source attempts must still be current;
    management runs without attempts are also eligible. Existing attempt budgets,
    acceptance evidence and owner approval gates remain the controller's policy.
    """
    resumed = []
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        tasks = store.db.execute("SELECT id,revision,attempts,reason FROM tasks WHERE status='blocked'"
                                 + (" AND id=?" if task_id is not None else ""),
                                 (task_id,) if task_id is not None else ()).fetchall()
        for task in tasks:
            if not (task["reason"] or "").startswith(BLOCKER_PREFIX):
                continue
            if store.db.execute("""SELECT 1 FROM company_questions WHERE task_id=? AND revision=?
                    AND status='open' LIMIT 1""", (task["id"], task["revision"])).fetchone():
                continue
            if store.db.execute("""SELECT 1 FROM team_runs WHERE task_id=? AND revision=?
                    AND status IN ('preparing','dispatching','running','checking','unknown','backoff') LIMIT 1""",
                    (task["id"], task["revision"])).fetchone():
                continue
            if store.db.execute("""SELECT 1 FROM attempts WHERE task_id=? AND revision=?
                    AND status IN ('running','queued') LIMIT 1""", (task["id"], task["revision"])).fetchone():
                continue
            questions = store.db.execute("""SELECT q.id FROM company_questions q
                JOIN team_runs r ON r.id=q.source_run_id LEFT JOIN attempts a ON a.id=r.attempt_id
                WHERE q.task_id=? AND q.revision=? AND q.status='answered' AND q.consumed_at IS NULL
                AND (r.attempt_id IS NULL OR (a.number=? AND a.revision=?))""",
                (task["id"], task["revision"], task["attempts"], task["revision"])).fetchall()
            if not questions:
                continue
            timestamp = now()
            ids = [row["id"] for row in questions]
            from .team_discussions import pending, BLOCKER_PREFIX as discussion_prefix
            discussion = pending(store, task["id"])
            pending_native = store.db.execute("""SELECT prompt FROM capability_jobs WHERE task_id=? AND revision=?
                AND status IN ('queued','claimed','bound','unknown') ORDER BY rowid LIMIT 1""",
                (task["id"], task["revision"])).fetchone()
            if pending_native:
                from .capability_jobs import BLOCKER_PREFIX as capability_prefix
                store.db.execute("UPDATE tasks SET reason=? WHERE id=?",
                                 (capability_prefix + pending_native["prompt"][:240], task["id"]))
            elif discussion:
                store.db.execute("UPDATE tasks SET reason=? WHERE id=?", (discussion_prefix + discussion["title"], task["id"]))
            else:
                store.db.execute("UPDATE tasks SET status='rework',reason=NULL WHERE id=?", (task["id"],))
            store.db.executemany("UPDATE company_questions SET consumed_at=? WHERE id=?",
                                 [(timestamp, question_id) for question_id in ids])
            result = {"task_id": task["id"], "revision": task["revision"], "question_ids": ids}
            if pending_native or discussion:
                result["status"] = "blocked"
            store.db.execute("INSERT INTO events(task_id,type,data,created_at) VALUES(?,'company.questions.resumed',?,?)",
                             (task["id"], json.dumps(result), timestamp))
            resumed.append(result)
    return resumed
