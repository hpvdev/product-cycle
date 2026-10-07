"""Deterministic task context with pinned authority and sealed provenance."""

import hashlib
import json
from pathlib import Path

from .authority import policy_packet
from .store import fingerprint, write_json


def build_pack(store, task, phase, directory):
    requirements = set(task["requirements"])
    ancestors = set(task["deps"])
    tasks = {item["id"]: item for item in store.tasks()}
    pending = list(ancestors)
    while pending:
        current = tasks[pending.pop()]
        for dependency in current["deps"]:
            if dependency not in ancestors:
                ancestors.add(dependency)
                pending.append(dependency)
    pinned = {"analysis", "design", "architecture", "feature_map", "plan", "project_setup"}
    inputs, supplementary = [], []
    for other in tasks.values():
        if other["status"] != "done" or other["id"] == task["id"]:
            continue
        records = store.current_evidence(other["id"])
        store.intact(records)
        for record in records:
            if record["kind"] != "artifact":
                continue
            item = {"task_id": other["id"], "revision": other["revision"], "evidence_id": record["id"],
                    "path": str(store.root / record["object_path"]), "original_path": record["source"],
                    "sha256": record["sha256"], "requirements": record["requirements"],
                    "authority": "accepted_artifact", "summary": record["description"]}
            score = 3 if other["id"] in ancestors else 2 if other["id"] in pinned else 1 if requirements & set(record["requirements"]) else 0
            item["relevance"] = score
            (inputs if score else supplementary).append(item)
    inputs.sort(key=lambda item: (-item["relevance"], item["task_id"], item["original_path"]))
    source = store.task_source(task) if hasattr(store, "task_source") else store.project
    packet = {"version": 1, "phase": phase, "task_id": task["id"], "revision": task["revision"],
              "attempt": task["attempts"], "project": str(store.project), "source_root": str(source),
              "source_fingerprint": fingerprint(source), "authority": policy_packet(store, task),
              "accepted_inputs": inputs, "supplementary_index": supplementary,
              "pinned_fields": ["authority", "revision", "source_fingerprint"],
              "claims": [], "observed_evidence": [], "repair": None}
    from .features import task_features
    features = task_features(store, task)
    from .source_context import source_packet
    packet["source_context"] = source_packet(store, task, features)
    packet["feature_scope"] = [{key: feature[key] for key in ("id", "requirements", "screen_states", "verification")}
                               for feature in features]
    from .knowledge import project_packet
    packet["project_knowledge"] = project_packet(store)
    from .workspaces import record
    workspace = record(store, task)
    packet["workspace"] = {key: workspace[key] for key in ("root", "base_path", "status", "kind", "reviewed_fingerprint")} if workspace else None
    if phase == "reviewer":
        records = store.current_evidence(task["id"])
        store.intact(records)
        packet["claims"] = [task["result"]] if task["result"] else []
        packet["observed_evidence"] = [{"id": item["id"], "kind": item["kind"], "producer": item["producer"],
                "path": str(store.root / item["object_path"]), "sha256": item["sha256"],
                "requirements": item["requirements"], "criteria": item["criteria"]} for item in records]
    if phase == "fix":
        starts = store.db.execute("SELECT data FROM events WHERE task_id=? AND type IN ('attempt.started','attempt.continued') ORDER BY id DESC", (task["id"],))
        aid = task["id"] + ":r" + str(task["revision"]) + ":a" + str(task["attempts"]) + ":work"
        feedback = next((value.get("feedback") for row in starts for value in [json.loads(row[0])]
                         if value.get("id") == aid), None)
        packet["repair"] = feedback or {"reason": task["reason"], "review": task["review"], "previous_outputs": [
            {"id": item["id"], "path": str(store.root / item["object_path"]), "sha256": item["sha256"]}
            for item in store.current_evidence(task["id"])]}
    payload = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    packet["sha256"] = hashlib.sha256(payload).hexdigest()
    path = Path(directory) / ("context-pack-" + packet["sha256"] + ".json")
    write_json(path, packet)
    store.event(task["id"], "context.prepared", {"phase": phase, "revision": task["revision"],
                "sha256": packet["sha256"], "path": str(path.relative_to(store.project)),
                "source_fingerprint": packet["source_fingerprint"]})
    return packet


def validate_pack(store, task, directory):
    from .contracts import require
    rows = store.db.execute("SELECT data FROM events WHERE task_id=? AND type='context.prepared' ORDER BY id DESC", (task["id"],)).fetchall()
    event = next((json.loads(row[0]) for row in rows if json.loads(row[0])["revision"] == task["revision"]
                  and Path(json.loads(row[0])["path"]).parent == Path(directory).relative_to(store.project)), None)
    if not event:
        return
    packet = json.loads((store.project / event["path"]).read_text())
    sha = packet.pop("sha256", None)
    actual = hashlib.sha256(json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(sha == actual == event["sha256"] and packet["task_id"] == task["id"] and packet["revision"] == task["revision"]
            and packet["authority"]["scope"]["criteria"] == task["criteria"], "Context pack hoặc tiêu chí đã thay đổi sau khi giao việc.")
    require(packet["authority"] == policy_packet(store, task),
            "Quyền hoặc phản hồi đã thay đổi; đọc context hiện tại trước khi gửi kết quả.")
    for item in packet["accepted_inputs"]:
        accepted = store.task(item["task_id"])
        require(accepted["status"] == "done" and accepted["revision"] == item["revision"],
                "Đầu vào đã chốt thay đổi; cần context và kiểm chứng mới.")
        record = next((record for record in store.current_evidence(accepted["id"])
                       if record["id"] == item["evidence_id"] and record["sha256"] == item["sha256"]), None)
        require(record is not None, "Đầu vào context không còn thuộc phiên bản đã chốt.")
        store.intact([record])
    from .features import task_features
    scope = [{key: feature[key] for key in ("id", "requirements", "screen_states", "verification")}
             for feature in task_features(store, task)]
    require(packet["feature_scope"] == scope, "Phạm vi feature/procedure đã thay đổi; cần context hiện tại.")
