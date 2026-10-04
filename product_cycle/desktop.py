"""Native Codex handoff. This module never starts or resumes a model turn."""

from pathlib import Path

from .codex import CodexClient
from .contracts import WorkflowError, require, json_object
from .store import write_json, now, digest


def enabled(store):
    # Old cycles keep their executor until an explicit migration.
    return store.config.get("executor", "codex-app-server") == "codex-desktop"


def latest(store, tid):
    task = store.task(tid)
    row = store.db.execute("SELECT * FROM attempts WHERE task_id=? AND revision=? AND number=? ORDER BY rowid DESC LIMIT 1",
                           (tid, task["revision"], task["attempts"])).fetchone()
    return dict(row) if row else None


def packet(store, attempt):
    directory = Path(attempt["directory"])
    return {"status": "native_handoff", "task": attempt["task_id"], "attempt": attempt["id"],
            "phase": attempt["phase"], "thread_id": attempt["thread_id"],
            "title": json_object(directory / "request.json")["title"],
            "prompt_path": str(directory / "prompt.md"), "request_path": str(directory / "request.json"),
            "result_path": str(directory / "result.json"),
            "message": "Tiếp tục trong Codex. Dashboard theo dõi trạng thái và kết quả."}


def prepare(store, tid, review=False, resume=False):
    from .runner import prompt_for, thread_title
    require(enabled(store), "Dự án chưa chọn thực thi trong ứng dụng Codex.")
    require(store.config["mode"] == "live", "Dữ liệu minh họa không có phiên Codex thực tế.")
    require(store.snapshot()["state"] == "active", "Quy trình đang tạm dừng.")
    task = store.task(tid)
    require(all(store.task(dep)["status"] == "done" for dep in task["deps"]), "Các bước phụ thuộc chưa được chấp nhận.")
    require(not review or task["status"] == "reviewing" and task["result"] is not None, "Cần kết quả đã kiểm tra trước khi review độc lập.")
    require(store.config.get("max_cycle_tokens") is None or (store.snapshot()["tokens"] or 0) < store.config["max_cycle_tokens"], "Quy trình đã đạt ngân sách token đã cấu hình.")
    phase = "review" if review else "work"
    attempt = latest(store, tid)
    if attempt and attempt["phase"] == phase and attempt["status"] in {"queued", "running"}:
        return packet(store, attempt)  # Repeated run calls cannot dispatch a duplicate.
    if resume and attempt and attempt["phase"] == phase:
        aid, directory = attempt["id"], Path(attempt["directory"])
        feedback = {"reason": task["reason"], "review": task["review"], "previous_outputs": [
            {"path": str(store.root / item["object_path"]), "original_path": item["source"]}
            for item in store.current_evidence(tid) if item["kind"] == "artifact"]}
        store.event(tid, "attempt.continued", {"id": aid, "attempt_id": aid, "feedback": feedback})
        store.update(tid, status="reviewing" if review else "running", reason=None, review=None if not review else task["review"])
    else:
        aid, directory = store.begin(tid, phase)
    try:
        prior_result = digest(directory / "result.json") if (directory / "result.json").is_file() else None
        prompt_for(store, store.task(tid), directory, review)
        from .contracts import RESULT_SCHEMA, REVIEW_SCHEMA
        write_json(directory / "request.json", {"attempt_id": aid, "task_id": tid, "phase": phase,
                   "executor": "codex-desktop", "read_only": review, "title": thread_title(store.config, task, review),
                   "model": store.config["models"]["review" if review else task["role"]],
                   "schema": REVIEW_SCHEMA if review else RESULT_SCHEMA,
                   "result_path": str(directory / "result.json"), "prior_result_sha256": prior_result, "prepared_at": now()})
        store.attempt_update(aid, status="queued", ended_at=None)
        store.event(tid, "desktop.queued", {"attempt_id": aid, "phase": phase})
        return packet(store, latest(store, tid))
    except (WorkflowError, OSError):
        store.attempt_update(aid, status="failed", ended_at=now())
        store.update(tid, status="blocked", reason="Chưa chuẩn bị được công việc cho Codex. Kiểm tra đầu vào rồi tiếp tục.")
        raise


def bind(store, tid, aid, thread_id, client_factory=CodexClient):
    """Bind before native execution, including the current turn if already in progress."""
    require(enabled(store) and store.snapshot()["state"] == "active", "Cần chọn Codex và bỏ tạm dừng trước khi gắn chat.")
    attempt = latest(store, tid)
    require(attempt and attempt["id"] == aid and attempt["status"] in {"queued", "running"}, "Yêu cầu thực thi đã thay đổi; đọc lại công việc hiện tại.")
    if attempt["status"] == "running":
        require(attempt["thread_id"] == thread_id, "Phiên đang chạy đã gắn với chat khác.")
        return packet(store, attempt)
    with client_factory(Path(attempt["directory"])) as client:
        thread = client.read_thread(thread_id)
    require(thread.get("id") == thread_id and Path(thread.get("cwd", "")).resolve() == store.project,
            "Chat được chọn không thuộc dự án này.")
    # A fresh reviewer may inspect the worker's output, but cannot be that worker.
    conflict = store.db.execute("SELECT task_id,phase FROM attempts WHERE thread_id=? AND id!=?", (thread_id, aid)).fetchall()
    require(all(row["phase"] == attempt["phase"] for row in conflict), "Review cần một chat độc lập với phiên thực hiện.")
    require(not store.db.execute("SELECT id FROM attempts WHERE thread_id=? AND id!=? AND status IN ('queued','running')", (thread_id, aid)).fetchone(),
            "Chat này đang phụ trách công việc khác.")
    previous = store.db.execute("SELECT * FROM attempts WHERE thread_id=? AND id!=? ORDER BY rowid DESC LIMIT 1", (thread_id, aid)).fetchone()
    if previous:
        update_usage(store, dict(previous), thread)
    if attempt["thread_id"]:
        require(attempt["thread_id"] == thread_id, "Tiếp tục bằng chat đã ghi nhận hoặc mở revision mới.")
    terminal = [turn for turn in thread.get("turns", []) if turn.get("status") in {"completed", "failed", "interrupted"}]
    store.attempt_update(aid, thread_id=thread_id, turn_id=terminal[-1]["id"] if terminal else None)
    store.attempt_update(aid, status="running")
    store.event(tid, "desktop.bound", {"attempt_id": aid, "thread_id": thread_id,
                "baseline_tokens": thread.get("usage_total", 0 if not any(turn.get("status") == "completed" for turn in thread.get("turns", [])) else None), "previous_tokens": attempt["tokens"] or 0})
    store.event(tid, "thread.observed", {"attempt_id": aid, "thread_id": thread_id,
                "active": any(turn.get("status") == "inProgress" for turn in thread.get("turns", []))})
    return packet(store, latest(store, tid))


def submit(store, tid, aid, path):
    """Submit an explicit result from the bound native session; checks/review still apply."""
    from .runner import finish_work
    require(enabled(store), "Dự án chưa chọn thực thi trong Codex.")
    attempt = latest(store, tid)
    require(attempt and attempt["id"] == aid and attempt["thread_id"], "Chưa gắn kết quả với phiên Codex của công việc này.")
    require(attempt["status"] == "running", "Phiên này đã kết thúc hoặc chưa được tiếp tục.")
    task = store.task(tid)
    require(all(store.task(dep)["status"] == "done" for dep in task["deps"]), "Đầu vào được chấp nhận đã thay đổi.")
    expected = Path(attempt["directory"]) / "result.json"
    require(store.safe_path(path) == expected.resolve(), "Ghi kết quả trong thư mục được giao cho phiên hiện tại.")
    result = json_object(expected)
    if attempt["phase"] == "review":
        store.review_finished(tid, aid, result)
    else:
        store.work_finished(tid, aid, result)
        if not result.get("blocker") and store.snapshot()["state"] == "active":
            try:
                finish_work(store, tid, aid, Path(attempt["directory"]), CodexClient)
            except (WorkflowError, OSError) as exc:
                store.update(tid, status="blocked", reason=str(exc))
                store.event(tid, "task.blocked", {"reason": str(exc)})
                raise
    store.event(tid, "desktop.submitted", {"attempt_id": aid, "phase": attempt["phase"]})
    return {"task": tid, "status": store.task(tid)["status"], "message": "Đã lưu kết quả; trạng thái theo kiểm chứng và quyết định thực tế."}


def advance(store):
    """Prepare one native handoff; an active Codex orchestrator performs the actual work."""
    require(store.snapshot()["state"] == "active", "Quy trình đang tạm dừng.")
    for task in store.tasks():
        attempt = latest(store, task["id"])
        if attempt and attempt["status"] in {"queued", "running"}:
            return packet(store, attempt)
        if task["status"] == "reviewing":
            from .runner import finish_work
            work = store.db.execute("SELECT * FROM attempts WHERE task_id=? AND revision=? AND phase='work' ORDER BY rowid DESC LIMIT 1",
                                    (task["id"], task["revision"])).fetchone()
            if work:
                try:
                    finish_work(store, task["id"], work["id"], Path(work["directory"]), CodexClient)
                except (WorkflowError, OSError) as exc:
                    store.update(task["id"], status="blocked", reason=str(exc))
                    store.event(task["id"], "task.blocked", {"reason": str(exc)})
                else:
                    return packet(store, latest(store, task["id"]))
    task = store.next_task()
    if task:
        return prepare(store, task["id"])
    return {"status": "waiting", "message": "Đang chờ quyết định, đầu vào hoặc kết quả kiểm chứng; xem trạng thái từng công việc."}


def update_usage(store, attempt, thread):
    if "usage_total" not in thread:
        return
    row = store.db.execute("SELECT data FROM events WHERE task_id=? AND type='desktop.bound' ORDER BY id DESC", (attempt["task_id"],)).fetchall()
    import json
    bound = next((json.loads(item[0]) for item in row if json.loads(item[0]).get("attempt_id") == attempt["id"]), None)
    if not bound or not isinstance(bound.get("baseline_tokens"), int):
        return  # An unknown baseline cannot become a precise per-attempt measurement.
    total = thread["usage_total"]
    if isinstance(total, int) and total >= bound["baseline_tokens"]:
        store.attempt_update(attempt["id"], tokens=bound["previous_tokens"] + total - bound["baseline_tokens"])


def sync_usage(store, client_factory=CodexClient):
    # Only the latest bound attempt for each thread can accrue new usage.
    rows = store.db.execute("SELECT * FROM attempts WHERE thread_id IS NOT NULL ORDER BY rowid DESC").fetchall()
    seen = set()
    for row in rows:
        attempt = dict(row)
        if attempt["thread_id"] in seen:
            continue
        seen.add(attempt["thread_id"])
        if not (Path(attempt["directory"]) / "request.json").is_file():
            continue
        try:
            with client_factory(Path(attempt["directory"])) as client:
                thread = client.read_thread(attempt["thread_id"])
        except (WorkflowError, OSError):
            continue  # A missing usage source must not stop result reconciliation for other chats.
        if thread.get("id") == attempt["thread_id"] and Path(thread.get("cwd", "")).resolve() == store.project:
            update_usage(store, attempt, thread)
