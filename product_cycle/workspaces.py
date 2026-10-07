"""Owned feature workspaces and recoverable, conflict-checked integration."""

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from .contracts import WorkflowError, require
from .store import digest, fingerprint, now, source_files


def migrate(db):
    db.execute("""CREATE TABLE IF NOT EXISTS workspaces(
        task_id TEXT NOT NULL REFERENCES tasks(id), revision INTEGER NOT NULL,
        root TEXT NOT NULL, base_path TEXT NOT NULL, baseline TEXT NOT NULL,
        kind TEXT NOT NULL, status TEXT NOT NULL, reviewed_fingerprint TEXT,
        journal TEXT, created_at TEXT NOT NULL, PRIMARY KEY(task_id,revision))""")
    if "reviewed_inventory" not in {row[1] for row in db.execute("PRAGMA table_info(workspaces)")}:
        db.execute("ALTER TABLE workspaces ADD COLUMN reviewed_inventory TEXT")
    db.commit()


def isolated(store, task):
    return bool(store.config.get("agent_workflow_version") and store.config.get("workspace_mode") == "isolated"
                and task["role"] == "build")


def record(store, task):
    row = store.db.execute("SELECT * FROM workspaces WHERE task_id=? AND revision=?", (task["id"], task["revision"])).fetchone()
    return dict(row) if row else None


def inventory(root):
    result = {}
    for path in source_files(root):
        relative = path.relative_to(root)
        require(not path.is_symlink() and path.resolve().is_relative_to(root), "Workspace không được có source symlink.")
        if path.name.startswith(".env") and path.name != ".env.example":
            continue
        result[str(relative)] = {"sha256": digest(path), "mode": path.stat().st_mode & 0o777}
    return result


def _copy(source, target, relative):
    origin = source / relative
    destination = target / relative
    require(origin.resolve().is_relative_to(source) and destination.resolve().is_relative_to(target),
            "Workspace file phải nằm trong source được giao.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    scratch = target / ".product-cycle" / "copies"
    require(scratch.resolve().is_relative_to(target), "Workspace scratch phải nằm trong source được giao.")
    scratch.mkdir(parents=True, exist_ok=True)
    temporary = scratch / uuid.uuid4().hex
    shutil.copy2(origin, temporary)
    os.replace(temporary, destination)


def prepare(store, task):
    previous = record(store, task)
    if previous:
        if previous["status"] == "conflict":
            rebase(store, task)
            previous = record(store, task)
        if previous["status"] == "rebasing":
            finish_rebase(store, task, previous)
            previous = record(store, task)
        if previous["status"] == "creating":
            finish_prepare(store, task, previous)
            previous = record(store, task)
        require(Path(previous["root"]).is_dir(),
                "Workspace chuẩn bị bị gián đoạn; cần đối chiếu trước khi thực hiện lại.")
        return Path(previous["root"])
    root = store.project / ".product-cycle" / "workspaces" / (task["id"] + "-r" + str(task["revision"])) / "source"
    base = store.root / "workspace-bases" / (task["id"] + "-r" + str(task["revision"]))
    require(not root.exists() and not base.exists(), "Workspace path đã có dữ liệu chưa được đối chiếu.")
    require(not any(path.is_symlink() for path in (root.parent, root.parent.parent)), "Workspace cần thư mục riêng trong project.")
    baseline = inventory(store.project)
    root.parent.mkdir(parents=True, exist_ok=True)
    base.mkdir(parents=True)
    head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=store.project,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    kind = "git-worktree" if head.returncode == 0 else "isolated-snapshot"
    journal = {"type": "prepare", "head": head.stdout.decode().strip() if head.returncode == 0 else None,
               "initial": None}
    with store.db:
        store.db.execute("INSERT INTO workspaces(task_id,revision,root,base_path,baseline,kind,status,reviewed_fingerprint,journal,created_at) VALUES(?,?,?,?,?,?, 'creating',NULL,?,?)",
                         (task["id"], task["revision"], str(root), str(base), json.dumps(baseline), kind,
                          json.dumps(journal), now()))
    finish_prepare(store, task, record(store, task))
    return root


def finish_prepare(store, task, row):
    """Resume only recorded initial/baseline versions; retain unexpected edits."""
    root, base = Path(row["root"]), Path(row["base_path"])
    baseline = json.loads(row["baseline"])
    require(inventory(store.project) == baseline, "Source chuẩn đã thay đổi khi tạo workspace; giữ dữ liệu để đối chiếu.")
    journal = json.loads(row["journal"]) if row["journal"] else {"type": "prepare", "initial": {}}
    if not root.exists():
        if row["kind"] == "git-worktree":
            require(journal.get("head"), "Thiếu Git baseline cho workspace tạo dở; cần đối chiếu.")
            operation = subprocess.run(["git", "worktree", "add", "--detach", str(root), journal["head"]],
                cwd=store.project, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            require(operation.returncode == 0, "Chưa tạo được Git worktree; giữ bản ghi để đối chiếu.")
        else:
            root.mkdir()
    if row["kind"] == "isolated-snapshot" and not (root / ".git").exists():
        initialized = subprocess.run(["git", "init", str(root)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        require(initialized.returncode == 0, "Chưa chuẩn bị được repository riêng cho snapshot workspace.")
    if journal.get("initial") is None:
        if row["kind"] == "git-worktree":
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            status = subprocess.run(["git", "status", "--porcelain"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            require(head.returncode == status.returncode == 0 and head.stdout.decode().strip() == journal["head"]
                    and not status.stdout, "Git worktree tạo dở đã có thay đổi chưa ghi nhận; giữ dữ liệu để đối chiếu.")
        else:
            require(not inventory(root), "Snapshot tạo dở đã có thay đổi chưa ghi nhận; giữ dữ liệu để đối chiếu.")
        journal["initial"] = inventory(root)
        with store.db:
            store.db.execute("UPDATE workspaces SET journal=? WHERE task_id=? AND revision=?",
                             (json.dumps(journal), task["id"], task["revision"]))
    current, initial = inventory(root), journal["initial"]
    existing_base = inventory(base)
    require(all(current.get(path) in (initial.get(path), baseline.get(path))
                for path in set(current) | set(initial) | set(baseline))
            and all(path in baseline and value == baseline[path] for path, value in existing_base.items()),
            "Workspace tạo dở có source chưa được ghi nhận; giữ các phiên bản để đối chiếu.")
    for relative in set(current) - set(baseline):
        (root / relative).unlink()
    for relative in baseline:
        if current.get(relative) != baseline[relative]:
            _copy(store.project, root, relative)
        if existing_base.get(relative) != baseline[relative]:
            _copy(store.project, base, relative)
    require(inventory(root) == inventory(base) == inventory(store.project) == baseline,
            "Source thay đổi trong lúc chuẩn bị workspace; cần đối chiếu.")
    with store.db:
        store.db.execute("UPDATE workspaces SET status='ready' WHERE task_id=? AND revision=?", (task["id"], task["revision"]))
    store.event(task["id"], "workspace.prepared", {"revision": task["revision"], "root": str(root), "kind": row["kind"],
                                                   "source_fingerprint": fingerprint(root)})


def task_source(store, task):
    if isolated(store, task):
        row = record(store, task)
        if row:
            require(Path(row["root"]).is_dir() and not Path(row["root"]).is_symlink()
                    and Path(row["root"]).resolve() == Path(row["root"]), "Workspace source không còn tồn tại; cần đối chiếu.")
            return Path(row["root"])
    return store.project


def mark_reviewed(store, task):
    row = record(store, task)
    if row:
        with store.db:
            store.db.execute("UPDATE workspaces SET status='reviewed',reviewed_fingerprint=?,reviewed_inventory=? WHERE task_id=? AND revision=?",
                             (fingerprint(Path(row["root"])), json.dumps(inventory(Path(row["root"]))), task["id"], task["revision"]))
        integration = store.db.execute("SELECT id,status,reason FROM tasks WHERE id=?", ("integrate-" + task["id"],)).fetchone()
        if integration and integration["status"] == "blocked" and (integration["reason"] or "").startswith("Integration conflict"):
            store.update(integration["id"], status="rework", reason=None, review=None)


def rebase(store, task):
    """Prepare a repair against current source, preserving old bases and changes."""
    row = record(store, task)
    source, old_base = Path(row["root"]), Path(row["base_path"])
    baseline, proposed, current = json.loads(row["baseline"]), inventory(source), inventory(store.project)
    generation = store.root / "workspace-bases" / (task["id"] + "-repair-" + uuid.uuid4().hex)
    new_base, staged = generation / "base", generation / "source"
    new_base.mkdir(parents=True)
    staged.mkdir()
    for relative in current:
        _copy(store.project, new_base, relative)
        _copy(store.project, staged, relative)
    conflicts = []
    for relative in set(baseline) | set(proposed):
        before, desired, canonical = baseline.get(relative), proposed.get(relative), current.get(relative)
        if before == desired:
            continue
        target = staged / relative
        if canonical == before or canonical == desired:
            if desired is None:
                target.unlink(missing_ok=True)
            else:
                _copy(source, staged, relative)
        elif before and desired and canonical:
            merge = subprocess.run(["git", "merge-file", "-p", str(store.project / relative),
                                    str(old_base / relative), str(source / relative)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if merge.returncode in {0, 1}:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(merge.stdout)
                os.chmod(target, desired["mode"])
                if merge.returncode:
                    conflicts.append(relative)
            else:
                _copy(source, staged, relative)
                conflicts.append(relative)
        else:
            if desired:
                _copy(source, staged, relative)
            else:
                target.unlink(missing_ok=True)
            conflicts.append(relative)
    wanted = inventory(staged)
    journal = {"type": "rebase", "old_base": str(old_base), "new_base": str(new_base),
               "staged": str(staged), "baseline": current, "before": proposed, "after": wanted,
               "conflicts": conflicts}
    with store.db:
        store.db.execute("UPDATE workspaces SET status='rebasing',journal=? WHERE task_id=? AND revision=?",
                         (json.dumps(journal), task["id"], task["revision"]))
    finish_rebase(store, task, record(store, task))


def finish_rebase(store, task, row):
    journal = json.loads(row["journal"])
    root, staged = Path(row["root"]), Path(journal["staged"])
    current, before, after = inventory(root), journal["before"], journal["after"]
    require(all(current.get(path) in (before.get(path), after.get(path)) for path in set(current) | set(before) | set(after)),
            "Workspace thay đổi trong lúc rebase; giữ trạng thái để đối chiếu.")
    require(inventory(staged) == after and inventory(Path(journal["new_base"])) == journal["baseline"],
            "Bản chuẩn bị rebase thay đổi; cần đối chiếu.")
    for relative in set(current) - set(after):
        (root / relative).unlink()
    for relative in after:
        if current.get(relative) != after[relative]:
            _copy(staged, root, relative)
    with store.db:
        store.db.execute("UPDATE workspaces SET status='ready',base_path=?,baseline=?,reviewed_fingerprint=NULL,reviewed_inventory=NULL WHERE task_id=? AND revision=?",
                         (journal["new_base"], json.dumps(journal["baseline"]), task["id"], task["revision"]))
    store.event(task["id"], "workspace.rebased", {"conflicts": journal["conflicts"], "old_base": journal["old_base"],
                                                   "new_base": journal["new_base"]})


def pending_source_transition(store, task):
    return bool(store.db.execute("SELECT task_id FROM workspaces WHERE status='integrating' AND task_id!=? LIMIT 1",
                                (task["id"].removeprefix("integrate-"),)).fetchone())


def integrate(store, task):
    build = store.task(task["id"].removeprefix("integrate-"))
    row = record(store, build)
    if not row:
        return {"status": "shared_source", "source_fingerprint": fingerprint(store.project)}
    source, base = Path(row["root"]), Path(row["base_path"])
    require(build["status"] == "done" and row["status"] in {"reviewed", "integrating", "integrated", "conflict"},
            "Chỉ tích hợp workspace đã qua review độc lập.")
    require(fingerprint(source) == row["reviewed_fingerprint"], "Workspace thay đổi sau review; cần mở lại và review bản mới.")
    baseline, proposed = json.loads(row["baseline"]), inventory(source)
    require(row["reviewed_inventory"] is not None and proposed == json.loads(row["reviewed_inventory"]),
            "Workspace file hoặc quyền thực thi thay đổi sau review; cần review bản mới.")
    changes = {path: {"before": baseline.get(path), "after": proposed.get(path)}
               for path in set(baseline) | set(proposed) if baseline.get(path) != proposed.get(path)}
    current = inventory(store.project)
    # A partially applied journal permits only its exact old or new file versions.
    continuing = row["status"] in {"integrating", "integrated"} and row["journal"]
    conflicts = [path for path, change in changes.items() if current.get(path) != change["before"]
                 and not (continuing and current.get(path) == change["after"])]
    if conflicts:
        with store.db:
            store.db.execute("UPDATE workspaces SET status='conflict' WHERE task_id=? AND revision=?", (build["id"], build["revision"]))
        store.event(task["id"], "integration.conflict", {"files": sorted(conflicts), "build_revision": build["revision"]})
        store.update(build["id"], status="rework", review=None,
                     reason="Resolve integration conflict against current canonical source: " + ", ".join(sorted(conflicts)) +
                     ". The controller preserves old bases and rebases the isolated workspace; inspect both versions and resolve markers before fresh review.")
        raise WorkflowError("Integration conflict; giữ cả hai phiên bản, cần xử lý: " + ", ".join(sorted(conflicts)))
    journal = {"task_id": task["id"], "build_revision": build["revision"], "changes": changes,
               "workspace_fingerprint": row["reviewed_fingerprint"]}
    with store.db:
        store.db.execute("UPDATE workspaces SET status='integrating',journal=? WHERE task_id=? AND revision=?",
                         (json.dumps(journal), build["id"], build["revision"]))
    for relative, change in sorted(changes.items()):
        destination = store.project / relative
        require(destination.resolve().is_relative_to(store.project) and not destination.is_symlink(),
                "Không ghi integration ra ngoài project.")
        if current.get(relative) == change["after"]:
            continue
        if change["after"] is None:
            destination.unlink(missing_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + ".product-cycle-integrating")
            if temporary.exists():
                require(not temporary.is_symlink() and digest(temporary) == change["after"]["sha256"],
                        "Integration file chuyển tiếp chưa khớp; cần đối chiếu.")
            else:
                shutil.copy2(source / relative, temporary)
            os.replace(temporary, destination)
    journal["source_fingerprint"] = fingerprint(store.project)
    with store.db:
        store.db.execute("UPDATE workspaces SET status='integrated',journal=? WHERE task_id=? AND revision=?",
                         (json.dumps(journal), build["id"], build["revision"]))
    store.event(task["id"], "integration.applied", journal)
    return journal


def reconcile(store):
    """Resume deterministic file transitions only when no source writer is live."""
    if store.db.execute("SELECT id FROM team_runs WHERE source_writer=1 AND status IN ('preparing','dispatching','running','checking','unknown') LIMIT 1").fetchone():
        return []
    repaired = []
    for raw in store.db.execute("SELECT * FROM workspaces WHERE status IN ('creating','rebasing','integrating')").fetchall():
        row = dict(raw)
        task = store.task(row["task_id"])
        if task["revision"] != row["revision"]:
            continue
        if row["status"] == "creating":
            finish_prepare(store, task, row)
            repaired.append(task["id"])
        elif row["status"] == "rebasing":
            finish_rebase(store, task, row)
            repaired.append(task["id"])
        else:
            integrate(store, store.task("integrate-" + task["id"]))
            repaired.append("integrate-" + task["id"])
    return repaired
