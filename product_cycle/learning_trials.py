"""Bounded behavioral trials and opaque judge packets owned by the controller."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from .contracts import WorkflowError, require, object_schema, STRINGS
from .store import digest, now, write_json


TRIAL_SCHEMA = object_schema({"summary": {"type": "string"}, "artifacts": STRINGS,
                             "limitations": STRINGS, "blocker": {"type": ["string", "null"]}})
SCORE_SCHEMA = object_schema({"label": {"type": "string"}, "score": {"type": "integer", "minimum": 0, "maximum": 100},
                             "reason": {"type": "string"}, "evidence": STRINGS})
BLIND_SCHEMA = object_schema({"evaluation": {"anyOf": [object_schema({
    "packet_hash": {"type": "string"}, "decision": {"type": "string", "enum": ["pass", "fail"]},
    "permissions_preserved": {"type": "boolean"}, "goals_preserved": {"type": "boolean"},
    "acceptance_preserved": {"type": "boolean"}, "cases": {"type": "array", "items": object_schema({
        "id": {"type": "string"}, "scores": {"type": "array", "items": SCORE_SCHEMA},
        "reason": {"type": "string"}})}}), {"type": "null"}]}, "reason": {"type": "string"}})


def migrate(db):
    db.executescript("""CREATE TABLE IF NOT EXISTS improvement_trials(
        id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL, evaluator_run_id TEXT NOT NULL,
        case_id TEXT NOT NULL, case_label TEXT NOT NULL, variant TEXT NOT NULL, label TEXT NOT NULL,
        root TEXT NOT NULL, status TEXT NOT NULL, input_sha256 TEXT NOT NULL,
        thread_id TEXT, turn_id TEXT, tokens INTEGER, result_path TEXT, trajectory_path TEXT,
        evidence TEXT, created_at TEXT NOT NULL, UNIQUE(candidate_id,case_id,variant));
        CREATE TABLE IF NOT EXISTS improvement_blind_packets(
        candidate_id TEXT PRIMARY KEY, packet TEXT NOT NULL, sha256 TEXT NOT NULL);""")


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode()


def _case(source):
    value = json.loads(Path(source["object_path"]).read_text())
    require(isinstance(value, dict) and isinstance(value.get("prompt"), str) and value["prompt"].strip()
            and isinstance(value.get("expectations"), list) and value["expectations"]
            and all(isinstance(item, str) and item.strip() for item in value["expectations"]),
            "Raw learning case cần prompt nguyên gốc và expectations dành riêng cho judge.")
    files = value.get("files", {})
    require(isinstance(files, dict) and len(files) <= 100 and all(isinstance(contents, str) for contents in files.values()),
            "Raw case files phải là fixture văn bản có giới hạn.")
    for relative in files:
        path = Path(relative)
        require(not path.is_absolute() and path.parts and not any(part in {"..", ".git", ".agents"} for part in path.parts)
                and not path.name.startswith(".env"), "Raw case fixture không được thay quyền, skill hoặc chứa credentials.")
    require(sum(len(contents.encode()) for contents in files.values()) <= 2 * 1024 * 1024, "Raw case fixture quá lớn.")
    return value


def select_holdouts(improvements, excluded, limit=2):
    chosen = []
    seen = set(excluded)
    seen_hashes = {digest(improvements.store.safe_path(path)) for path in excluded}
    for record in improvements.db.execute("SELECT * FROM evidence WHERE kind='artifact' ORDER BY rowid DESC"):
        if record["source"] in seen or record["sha256"] in seen_hashes or not record["source"].startswith(".product-cycle/"):
            continue
        path = improvements.store.root / record["object_path"]
        source = {"path": record["source"], "object_path": str(path), "sha256": record["sha256"]}
        try:
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
            _case(source)
        except (WorkflowError, OSError, ValueError, UnicodeError):
            continue
        require(digest(path) == source["sha256"], "Held-out input cần bằng chứng nguyên vẹn.")
        chosen.append(source)
        seen.add(source["path"])
        seen_hashes.add(source["sha256"])
        if len(chosen) == limit:
            break
    return chosen


def trial_tokens(db, run_id):
    return db.execute("SELECT COALESCE(SUM(tokens),0) FROM improvement_trials WHERE evaluator_run_id=?", (run_id,)).fetchone()[0]


def run_trials(improvements, cid, run, client_factory, control=None):
    store, db = improvements.store, improvements.db
    migrate(db)
    existing = db.execute("SELECT packet FROM improvement_blind_packets WHERE candidate_id=?", (cid,)).fetchone()
    if existing:
        return json.loads(existing[0])
    context = improvements.evaluation_context(cid)
    sources = context["raw_case_sources"]
    budget = {"max_cases": 4, "max_trials": 8, "timeout_seconds": 150, "max_trial_tokens": 8000}
    budget.update(store.config.get("learning_budget", {}))
    require(all(type(value) is int and value > 0 for value in budget.values()), "Learning budget cần giới hạn số nguyên dương.")
    require(len(sources) <= budget["max_cases"] and len(sources) * 2 <= budget["max_trials"], "Learning cases vượt ngân sách đã cấu hình.")
    for source in sources:
        _case(source)
    for source in sources:
        case = _case(source)
        label = "case-" + uuid.uuid4().hex[:10]
        previous_case = db.execute("SELECT case_label FROM improvement_trials WHERE candidate_id=? AND case_id=? LIMIT 1", (cid, source["path"])).fetchone()
        if previous_case:
            label = previous_case[0]
        for variant in ("before", "after"):
            prior = db.execute("SELECT * FROM improvement_trials WHERE candidate_id=? AND case_id=? AND variant=?", (cid, source["path"], variant)).fetchone()
            if prior:
                require(prior["status"] == "completed", "Learning trial có kết quả chưa rõ; đối chiếu đúng phiên trước khi chạy lại.")
                continue
            if control:
                control()
            cap = store.config.get("max_cycle_tokens")
            consumed = (store.snapshot()["tokens"] or 0)
            require(cap is None or consumed < cap, "Learning đã đạt ngân sách token của cycle.")
            token_limit = min(budget["max_trial_tokens"], cap - consumed) if cap else budget["max_trial_tokens"]
            identifier, variant_label = uuid.uuid4().hex, "variant-" + uuid.uuid4().hex[:10]
            root = store.project / ".product-cycle" / "observations" / ("product-" + identifier)
            root.mkdir(parents=True)
            for relative, contents in case.get("files", {}).items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents)
            snapshots = improvements.root / cid / variant
            for folder in snapshots.iterdir():
                if folder.is_dir():
                    shutil.copytree(folder, root / ".agents" / "skills" / folder.name)
            with db:
                db.execute("INSERT INTO improvement_trials(id,candidate_id,evaluator_run_id,case_id,case_label,variant,label,root,status,input_sha256,created_at) VALUES(?,?,?,?,?,?,?,?, 'running',?,?)",
                           (identifier, cid, run["id"], source["path"], label, variant, variant_label, str(root), source["sha256"], now()))
            trajectory, terminal = [], False

            def observe(message):
                nonlocal terminal
                method, params = message.get("method", ""), message.get("params", {})
                if method == "client/threadReady":
                    with db:
                        db.execute("UPDATE improvement_trials SET thread_id=? WHERE id=?", (params["thread_id"], identifier))
                elif method == "client/turnReady":
                    with db:
                        db.execute("UPDATE improvement_trials SET turn_id=? WHERE id=?", (params["turn_id"], identifier))
                elif method == "thread/tokenUsage/updated":
                    tokens = params.get("tokenUsage", {}).get("total", {}).get("totalTokens")
                    if type(tokens) is int and tokens >= 0:
                        with db:
                            db.execute("UPDATE improvement_trials SET tokens=MAX(COALESCE(tokens,0),?) WHERE id=?", (tokens, identifier))
                if method == "turn/completed":
                    terminal = True
                if method in {"item/started", "item/completed", "turn/completed"}:
                    item = params.get("item", {})
                    trajectory.append({"method": method, "item_type": item.get("type"),
                        "status": params.get("turn", {}).get("status"),
                        "observation": {key: item[key] for key in ("command", "cwd", "exitCode", "aggregatedOutput", "changes", "status", "tool", "arguments", "result", "text") if key in item}})
            try:
                model = store.config["models"]["build"]
                prompt = ("Work only in this assigned fixture workspace. Read applicable skills from .agents/skills. "
                          "Do not access other projects, accounts, services or controller state. Network and external actions "
                          "are unavailable. Preserve outputs in this workspace and return concrete relative artifact paths.\n\n" + case["prompt"])
                with client_factory(root, on_event=observe) as client:
                    output = client.run(root, prompt, model["model"], model["effort"], TRIAL_SCHEMA,
                                        readonly=False, network=False, timeout=budget["timeout_seconds"], max_tokens=token_limit,
                                        title="Project task", writable_roots=[root], control=control)
                row = db.execute("SELECT * FROM improvement_trials WHERE id=?", (identifier,)).fetchone()
                require(terminal and output.get("thread_id") == row["thread_id"] and output.get("turn_id") == row["turn_id"],
                        "Learning output chưa khớp phiên thực tế đã hoàn tất.")
                seal_trial(improvements, dict(row), output["result"], trajectory, output.get("tokens"))
            except BaseException:
                with db:
                    db.execute("UPDATE improvement_trials SET status=? WHERE id=?", ("failed" if terminal else "unknown", identifier))
                raise
    cases = []
    for source in sources:
        rows = db.execute("SELECT * FROM improvement_trials WHERE candidate_id=? AND case_id=? ORDER BY label", (cid, source["path"])).fetchall()
        cases.append({"id": rows[0]["case_label"], "expectations": _case(source)["expectations"],
                      "variants": [{"label": row["label"], "artifacts": json.loads(row["evidence"])} for row in rows]})
    holdouts = improvements._row(cid)["bundle"].get("held_out_sources", [])
    packet = {"version": 1, "cases": cases, "held_out_count": len(holdouts),
              "limitations": [] if holdouts else ["No additional registered raw cases were available for held-out evaluation."]}
    sha = hashlib.sha256(_encoded(packet)).hexdigest()
    packet["packet_hash"] = sha
    with db:
        db.execute("INSERT INTO improvement_blind_packets VALUES(?,?,?)", (cid, json.dumps(packet), sha))
    return packet


def seal_trial(improvements, row, result, trajectory, tokens=None):
    store, db, root = improvements.store, improvements.db, Path(row["root"])
    require(isinstance(result, dict) and result.get("blocker") is None and isinstance(result.get("artifacts"), list),
            "Learning trial chưa hoàn tất hành vi cần đánh giá.")
    from .installer import skill_hashes
    snapshots = improvements.root / row["candidate_id"] / row["variant"]
    require(all(skill_hashes(root / ".agents" / "skills" / folder.name) == skill_hashes(folder)
                for folder in snapshots.iterdir() if folder.is_dir()),
            "Learning trial đã thay skill snapshot; không dùng làm bằng chứng cải tiến.")
    proof = []
    for relative in result["artifacts"]:
        require(isinstance(relative, str), "Learning output path cần là chuỗi.")
        path = (root / relative).resolve()
        require(path.is_relative_to(root) and path.is_file() and not path.name.startswith(".env"),
                "Learning output phải nằm trong fixture được giao.")
        proof.append({"path": str(path.relative_to(store.project)), "sha256": digest(path)})
    result_path, trace_path = root / "result.json", root / "trajectory.json"
    write_json(result_path, result)
    write_json(trace_path, {"events": trajectory, "provider_outcome": "completed"})
    proof += [{"path": str(path.relative_to(store.project)), "sha256": digest(path)} for path in (result_path, trace_path)]
    with db:
        if type(tokens) is int and tokens >= 0:
            db.execute("UPDATE improvement_trials SET tokens=MAX(COALESCE(tokens,0),?) WHERE id=?", (tokens, row["id"]))
        db.execute("UPDATE improvement_trials SET status='completed',result_path=?,trajectory_path=?,evidence=? WHERE id=?",
                   (str(result_path.relative_to(store.project)), str(trace_path.relative_to(store.project)), json.dumps(proof), row["id"]))


def reconcile_trials(improvements, client_factory):
    """Observe the exact orphaned trial; never launch or restart candidate turns."""
    store, db = improvements.store, improvements.db
    migrate(db)
    outcomes = []
    for raw in db.execute("SELECT * FROM improvement_trials WHERE status IN ('running','unknown')").fetchall():
        row = dict(raw)
        if not row["thread_id"] or not row["turn_id"]:
            outcomes.append({"id": row["id"], "status": "unknown", "reason": "Exact thread/turn identity is missing"})
            continue
        try:
            with client_factory(Path(row["root"])) as client:
                thread = client.read_thread(row["thread_id"])
            require(thread.get("id") == row["thread_id"] and Path(thread.get("cwd", "")).resolve() == Path(row["root"]).resolve(),
                    "Learning chat không khớp fixture được giao.")
            turn = next((turn for turn in thread.get("turns", []) if turn.get("id") == row["turn_id"]), None)
            require(turn is not None, "Chưa đọc được đúng learning turn đã ghi.")
            if turn.get("status") == "completed":
                texts = [item["text"] for item in turn.get("items", []) if item.get("type") == "agentMessage" and item.get("phase") != "commentary"]
                require(texts, "Learning turn thiếu kết quả có cấu trúc.")
                trace = [{"method": "reconciled/item", "item_type": item.get("type"), "observation": item} for item in turn.get("items", [])]
                seal_trial(improvements, row, json.loads(texts[-1]), trace, thread.get("usage_total"))
                status = "completed"
            elif turn.get("status") in {"failed", "interrupted"}:
                status = "failed"
                with db:
                    db.execute("UPDATE improvement_trials SET status=? WHERE id=?", (status, row["id"]))
            else:
                status = "unknown"
            outcomes.append({"id": row["id"], "status": status})
        except (WorkflowError, OSError, ValueError, KeyError) as exc:
            outcomes.append({"id": row["id"], "status": "unknown", "reason": str(exc)})
    # Only an evaluator that never launched its judging turn may be queued again.
    # Completed candidates are reused; uncertain judge sessions stay reserved.
    with db:
        for entry in db.execute("""SELECT l.* FROM company_learning l JOIN team_runs r ON r.id=l.run_id
            WHERE l.phase='improve_evaluate' AND l.status IN ('running','attention')
            AND r.status IN ('blocked','interrupted') AND r.thread_id IS NULL AND r.turn_id IS NULL""").fetchall():
            trials = db.execute("SELECT status FROM improvement_trials WHERE candidate_id=?", (entry["candidate_id"],)).fetchall()
            candidate = improvements._row(entry["candidate_id"])
            if trials and all(trial[0] == "completed" for trial in trials) and candidate["status"] == "evaluating":
                db.execute("UPDATE company_learning SET status='queued',run_id=NULL,reason=NULL WHERE id=?", (entry["id"],))
                store.event(entry["task_id"], "learning.trials_reconciled", {"candidate_id": entry["candidate_id"]})
    return outcomes


def record_judgment(improvements, cid, report, run_id):
    db, store = improvements.db, improvements.store
    raw = db.execute("SELECT * FROM improvement_blind_packets WHERE candidate_id=?", (cid,)).fetchone()
    require(raw is not None and report.get("packet_hash") == raw["sha256"], "Blind judgment cần đúng packet đã ghi nhận.")
    packet = json.loads(raw["packet"])
    require(isinstance(report.get("cases"), list) and len(report["cases"]) == len(packet["cases"])
            and {case.get("id") for case in report["cases"]} == {case["id"] for case in packet["cases"]}, "Judge cần đánh giá đủ raw cases.")
    context = improvements.evaluation_context(cid)
    forward = {key: report[key] for key in ("decision", "permissions_preserved", "goals_preserved", "acceptance_preserved")}
    forward.update(candidate_hash=context["candidate_hash"], context_hash=context["context_hash"], cases=[])
    for case in report["cases"]:
        trials = db.execute("SELECT * FROM improvement_trials WHERE candidate_id=? AND case_label=?", (cid, case["id"])).fetchall()
        require(len(trials) == 2 and all(row["status"] == "completed" for row in trials), "Judge cần hai trial đã hoàn tất.")
        labels = {row["label"] for row in trials}
        require(isinstance(case.get("scores"), list) and len(case["scores"]) == 2
                and {item.get("label") for item in case["scores"]} == labels, "Judge cần đánh giá đúng opaque labels.")
        scores = {item["label"]: item for item in case["scores"]}
        by_variant = {row["variant"]: row for row in trials}
        for row in trials:
            proof = json.loads(row["evidence"])
            require(all(digest(store.safe_path(item["path"])) == item["sha256"] for item in proof), "Trial outputs thay đổi sau khi tạo judge packet.")
            score = scores[row["label"]]
            require(type(score.get("score")) is int and 0 <= score["score"] <= 100
                    and isinstance(score.get("reason"), str) and score["reason"].strip()
                    and isinstance(score.get("evidence"), list) and score["evidence"]
                    and set(score["evidence"]) <= {item["path"] for item in proof}, "Judge cần score và dẫn bằng chứng trial thực tế.")
        before, after = by_variant["before"], by_variant["after"]
        before_score, after_score = scores[before["label"]]["score"], scores[after["label"]]["score"]
        source = next(item for item in context["raw_case_sources"] if item["path"] == before["case_id"])
        inputs = store.project / ".product-cycle" / "learning-inputs" / cid
        require(not inputs.is_symlink() and inputs.resolve().is_relative_to(store.project), "Raw input copy cần thư mục controller riêng.")
        inputs.mkdir(parents=True, exist_ok=True)
        copy = inputs / (source["sha256"] + ".json")
        if copy.exists():
            require(not copy.is_symlink() and digest(copy) == source["sha256"], "Raw input copy đã thay đổi; giữ bằng chứng để đối chiếu.")
        else:
            shutil.copyfile(source["object_path"], copy)
        forward["cases"].append({"case_id": source["path"], "input_artifact": str(copy.relative_to(store.project)),
            "input_sha256": source["sha256"], "before_artifacts": [item["path"] for item in json.loads(before["evidence"])],
            "after_artifacts": [item["path"] for item in json.loads(after["evidence"])], "improved": after_score > before_score,
            "regressed": after_score < before_score, "reason": case["reason"]})
    result = improvements.record_evaluation(cid, forward, run_id)
    improvements._update(cid, result["status"], "evaluation.blind_judgment", {"packet_hash": raw["sha256"], "judge_run_id": run_id})
    return improvements._row(cid)
