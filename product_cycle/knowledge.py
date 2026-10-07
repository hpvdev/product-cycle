"""Reviewed project lessons and opt-in portable workflow guidance."""

import hashlib
import contextlib
import json
import os
from pathlib import Path

from .contracts import require
from .store import now, write_json, state_root


def migrate(db):
    db.execute("""CREATE TABLE IF NOT EXISTS project_knowledge(
        id TEXT PRIMARY KEY, task_id TEXT NOT NULL, revision INTEGER NOT NULL,
        finding TEXT NOT NULL, evidence TEXT NOT NULL, created_at TEXT NOT NULL)""")
    db.commit()


def extract(store, task):
    migrate(store.db)
    retro = store.sealed_document(task["id"], "retro.json")
    known = {row["id"] for row in store.db.execute("SELECT id FROM evidence")}
    for observation in retro["observations"]:
        require(isinstance(observation, dict) and isinstance(observation.get("finding"), str)
                and observation["finding"].strip() and isinstance(observation.get("evidence_ids"), list)
                and observation["evidence_ids"] and set(observation["evidence_ids"]) <= known,
                "Project lesson cần finding và bằng chứng thực tế đã đăng ký.")
        identity = hashlib.sha256(json.dumps({"task_id": task["id"], "revision": task["revision"],
                                              "observation": observation}, sort_keys=True).encode()).hexdigest()
        with store.db:
            store.db.execute("INSERT OR IGNORE INTO project_knowledge VALUES(?,?,?,?,?,?)",
                             (identity, task["id"], task["revision"], observation["finding"], json.dumps(observation["evidence_ids"]), now()))


def project_packet(store):
    migrate(store.db)
    lessons = []
    for raw in store.db.execute("SELECT k.* FROM project_knowledge k JOIN tasks t ON t.id=k.task_id WHERE t.status='done' AND t.revision=k.revision ORDER BY k.created_at"):
        row = dict(raw)
        ids = json.loads(row["evidence"])
        records = [dict(store.db.execute("SELECT * FROM evidence WHERE id=?", (eid,)).fetchone()) for eid in ids]
        store.intact(records)
        lessons.append({"id": row["id"], "finding": row["finding"], "task_id": row["task_id"], "revision": row["revision"],
                        "evidence": [{"id": item["id"], "path": str(store.root / item["object_path"]), "sha256": item["sha256"]} for item in records]})
    return lessons


def library_path(project):
    return state_root(Path(project).resolve()).parent / "shared-guidance.json"


def read_library(project):
    path = library_path(project)
    require(not path.is_symlink(), "Shared guidance registry không được là symlink.")
    if not path.exists():
        return {"version": 1, "entries": {}}
    value = json.loads(path.read_text())
    require(value.get("version") == 1 and isinstance(value.get("entries"), dict), "Shared guidance registry chưa hợp lệ.")
    return value


@contextlib.contextmanager
def library_lock(project):
    import fcntl
    path = library_path(project).with_suffix(".lock")
    require(not path.is_symlink(), "Shared guidance lock không được là symlink.")
    with path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def publish(improvements, candidate):
    if not improvements.store.config.get("share_learned_guidance"):
        return
    require(candidate["status"] == "applied" and candidate["review"] and candidate["review"]["accepted"],
            "Chỉ chia sẻ guidance đã review và áp dụng.")
    improvements._intact(candidate)
    project = improvements.store.project
    with library_lock(project):
        value = read_library(project)
        for change in candidate["bundle"]["changes"]:
            value["entries"][change["target_id"]] = {"guidance": change["guidance"],
                "sha256": hashlib.sha256(change["guidance"].encode()).hexdigest(),
                "candidate_hash": candidate["candidate_hash"], "candidate_id": candidate["id"],
                "reviewed": True, "published_at": now()}
        write_json(library_path(project), value)


def unpublish(improvements, candidate):
    if not library_path(improvements.store.project).exists():
        return
    with library_lock(improvements.store.project):
        value = read_library(improvements.store.project)
        selected = [name for name, entry in value["entries"].items() if entry.get("candidate_id") == candidate["id"]]
        if selected:
            for name in selected:
                del value["entries"][name]
            write_json(library_path(improvements.store.project), value)


def import_guidance(project, folder):
    entry = read_library(project)["entries"].get(folder.name)
    if not entry:
        return False
    from .improvements import _guidance, GUIDANCE, LINK
    require(entry.get("reviewed") is True and isinstance(entry.get("guidance"), str)
            and hashlib.sha256(entry["guidance"].encode()).hexdigest() == entry.get("sha256")
            and isinstance(entry.get("candidate_hash"), str), "Shared guidance cần phiên bản review và nội dung nguyên vẹn.")
    _guidance(entry["guidance"])
    path = folder / GUIDANCE
    path.parent.mkdir(exist_ok=True)
    path.write_text(entry["guidance"])
    skill = folder / "SKILL.md"
    if "[references/learned-guidance.md](references/learned-guidance.md)" not in skill.read_text():
        skill.write_text(skill.read_text() + LINK)
    return True
