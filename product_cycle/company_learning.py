"""Durable, finite improvement experiments after a completed product cycle."""

import hashlib
import json
from pathlib import Path

from .contracts import require
from .store import now, write_json
from .improvements import (ImprovementStore, GUIDANCE, PROPOSE_SCHEMA, EVALUATE_SCHEMA,
                           IMPROVEMENT_REVIEW_SCHEMA)


def migrate(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS company_learning(
          id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, revision INTEGER NOT NULL,
          phase TEXT NOT NULL, candidate_id TEXT, run_id TEXT, status TEXT NOT NULL,
          reason TEXT, created_at TEXT NOT NULL, UNIQUE(task_id,revision,phase));
    """)


def enabled(store):
    from .team import company_enabled
    return company_enabled(store) and store.config.get("team", {}).get("self_improve") is True


def jobs(store):
    if not enabled(store) or not all(t["status"] in {"done", "superseded"} for t in store.tasks()):
        return
    refresh(store)
    retro = next((t for t in store.tasks() if t["stage"] == "retro" and t["status"] == "done"), None)
    if not retro:
        return
    with store.db:
        store.db.execute("INSERT OR IGNORE INTO company_learning(task_id,revision,phase,status,created_at) VALUES(?,?,'improve_propose','queued',?)",
                         (retro["id"], retro["revision"], now()))
    # A known failed/unknown session remains visible for deliberate recovery.
    # It is never silently replaced with a fictitious successful experiment.
    for row in store.db.execute("SELECT * FROM company_learning WHERE task_id=? AND revision=? AND status='queued' ORDER BY id", (retro["id"], retro["revision"])).fetchall():
        yield retro, row["phase"], dict(row)


def reserve(store, run, prior):
    if prior.get("retry_at") is not None:
        with store.db:
            store.db.execute("UPDATE company_learning SET run_id=? WHERE run_id=?", (run["id"], prior["id"]))
    else:
        with store.db:
            store.db.execute("UPDATE company_learning SET run_id=?,status='running' WHERE id=? AND status='queued'",
                             (run["id"], prior["id"]))


def mission(store, run, client_factory=None, control=None):
    from .runner import context
    row = store.db.execute("SELECT * FROM company_learning WHERE run_id=?", (run["id"],)).fetchone()
    require(row, "Nhiệm vụ cải tiến chưa được phân công.")
    improvements = ImprovementStore(store)
    if run["phase"] == "improve_propose":
        targets = []
        for name, spec in improvements.targets.items():
            folder = store.project / spec["path"]
            path = folder / GUIDANCE
            targets.append({"target_id": name, "path": str(folder),
                            "before_sha256": hashlib.sha256(path.read_bytes() if path.exists() else b"").hexdigest()})
        packet = {"accepted_context": context(store, store.task(run["task_id"])), "targets": targets}
        instruction = ("Read actual retrospective and failed/successful artifacts. Propose one small, testable improvement to "
                       "installed learned guidance only, with real evidence and raw reproducible case IDs. Do not change goals, "
                       "permissions, gates, cost or acceptance. Candidate is not applied by this mission. If no substantiated "
                       "improvement is testable, return candidate=null with an honest reason. Never invent failure cases.")
        if store.config.get("agent_workflow_version"):
            instruction += (" Raw cases must be sealed JSON artifacts with the genuine prompt, expectations reserved for "
                            "the judge, and optional files mapping relative fixture paths to text. Do not include credentials "
                            "or unrelated chats. The controller selects additional held-out cases and runs opaque before/after trials.")
        schema = PROPOSE_SCHEMA
    elif run["phase"] == "improve_evaluate":
        if store.config.get("agent_workflow_version"):
            from .learning_trials import run_trials, BLIND_SCHEMA
            require(client_factory is not None, "Cần runtime được giao để chạy learning trials.")
            packet = run_trials(improvements, row["candidate_id"], run, client_factory, control)
            instruction = ("You are an independent blinded evaluator. Inspect both opaque variants against each case's "
                           "expectations and actual artifacts, including execution trajectory and source. Cite observed proof "
                           "for each score. Do not infer variant identity or consult author rationale, current installed "
                           "guidance or other chats. Score both on the same scale. Missing behavior proof is a limitation, "
                           "not a pass. Return evaluation=null if evidence cannot establish a comparison. The controller "
                           "resolves variant identity and regressions; scores alone cannot authorize adoption.")
            write_json(Path(run["directory"]) / "context.json", packet)
            return instruction + "\n" + json.dumps(packet, ensure_ascii=False), BLIND_SCHEMA
        packet = improvements.evaluation_context(row["candidate_id"])
        instruction = ("Independently forward-test identical raw cases with before and after guidance. Keep original inputs, "
                       "outputs and assessment in your artifact directory, separately for both variants. Do not run real product "
                       "cycles, third-party writes or publication for this experiment. Structural tests alone do not establish "
                       "benefit. Return evaluation=null if you cannot produce genuine before/after evidence. Any regression fails.")
        instruction += (" Use the exact raw_case_sources sealed input bytes, copy each input to your artifacts, and record its "
                        "input_artifact and input_sha256. Both variants must use that unchanged input, never a rewritten case.")
        schema = EVALUATE_SCHEMA
    else:
        packet = improvements.review_context(row["candidate_id"])
        instruction = ("Fresh independent read-only reviewer: inspect actual raw before/after cases and guidance. Verify genuine "
                       "benefit and no regression or authority change. Do not approve based on evaluator claims. Your returned "
                       "result is persisted by the controller as result.json; use that path for your review report artifact. "
                       "Return review=null if evidence is insufficient; never fabricate a review report file.")
        schema = IMPROVEMENT_REVIEW_SCHEMA
    packet["result_path"] = str((Path(run["directory"]) / "result.json").relative_to(store.project))
    write_json(Path(run["directory"]) / "context.json", packet)
    return instruction + "\n" + json.dumps(packet, ensure_ascii=False), schema


def complete(team, run, result):
    require(isinstance(result, dict) and isinstance(result.get("reason"), str) and result["reason"].strip(),
            "Cải tiến cần có kết luận và lý do rõ ràng.")
    store = team.store
    row = store.db.execute("SELECT * FROM company_learning WHERE run_id=?", (run["id"],)).fetchone()
    require(row, "Kết quả chưa gắn với nhiệm vụ cải tiến.")
    if row["status"] in {"completed", "no_change"}:
        return
    improvements = ImprovementStore(store)
    key = {"improve_propose": "candidate", "improve_evaluate": "evaluation", "improve_review": "review"}[run["phase"]]
    require(key in result, "Kết quả cải tiến chưa đúng cấu trúc.")
    if result[key] is None:
        if row["candidate_id"]:
            improvements._update(row["candidate_id"], "rejected", "experiment.insufficient", {"reason": result["reason"]})
        with store.db:
            store.db.execute("UPDATE company_learning SET status='no_change',reason=? WHERE id=?", (result["reason"], row["id"]))
        team.event("improvement.no_change", run, reason=result["reason"])
        return
    next_phase = None
    if run["phase"] == "improve_propose":
        candidate = improvements.propose(result[key], run["id"])
        # Trusted checks run once before opening a separate evaluator session.
        if candidate["status"] == "proposed" or candidate["status"] == "evaluating" and candidate["evaluation"] is None:
            candidate = improvements.evaluate(candidate["id"])
        if candidate["status"] == "evaluating":
            next_phase = "improve_evaluate"
    elif run["phase"] == "improve_evaluate":
        if store.config.get("agent_workflow_version"):
            from .learning_trials import record_judgment
            candidate = record_judgment(improvements, row["candidate_id"], result[key], run["id"])
        else:
            candidate = improvements.record_evaluation(row["candidate_id"], result[key], run["id"])
        if candidate["status"] == "evaluated":
            next_phase = "improve_review"
    else:
        candidate = improvements.record_review(row["candidate_id"], result[key], run["id"])
    with store.db:
        store.db.execute("UPDATE company_learning SET candidate_id=?,status='completed',reason=? WHERE id=?", (candidate["id"], result["reason"], row["id"]))
        if next_phase:
            store.db.execute("INSERT OR IGNORE INTO company_learning(task_id,revision,phase,candidate_id,status,created_at) VALUES(?,?,?,?,'queued',?)",
                             (row["task_id"], row["revision"], next_phase, candidate["id"], now()))
    team.event("improvement.phase_completed", run, candidate_id=candidate["id"], status=candidate["status"])


def pending(store):
    if not enabled(store):
        return False
    ImprovementStore(store)
    return bool(store.db.execute("""SELECT l.id FROM company_learning l JOIN tasks t ON t.id=l.task_id
                  LEFT JOIN team_runs r ON r.id=l.run_id WHERE l.revision=t.revision AND
                  (l.status='queued' OR r.status IN ('preparing','dispatching','running','checking','unknown','backoff'))""").fetchone() or
                store.db.execute("""SELECT c.id FROM improvement_candidates c JOIN team_runs r ON r.id=c.author_run_id
                  JOIN tasks t ON t.id=r.task_id WHERE c.status='reviewed' AND r.revision=t.revision""").fetchone())


def refresh(store):
    with store.db:
        store.db.execute("""UPDATE company_learning SET status='attention',
          reason=(SELECT reason FROM team_runs WHERE id=company_learning.run_id)
          WHERE status='running' AND run_id IN
          (SELECT id FROM team_runs WHERE status IN ('blocked','interrupted','unknown'))""")


def settle(store):
    """Called outside the dispatcher lock; applying skills acquires its own lock."""
    if not enabled(store):
        return
    if not all(t["status"] in {"done", "superseded"} for t in store.tasks()) or store.db.execute(
            "SELECT id FROM team_runs WHERE status IN ('preparing','dispatching','running','checking','unknown','backoff')").fetchone():
        return
    from .capability_jobs import source_in_use
    if source_in_use(store):
        return
    improvements = ImprovementStore(store)
    for candidate in improvements.snapshot()["candidates"]:
        if candidate["status"] == "reviewed":
            author = store.db.execute("SELECT r.revision,t.revision AS current_revision FROM team_runs r JOIN tasks t ON t.id=r.task_id WHERE r.id=?", (candidate["author_run_id"],)).fetchone()
            if author["revision"] != author["current_revision"]:
                improvements._update(candidate["id"], "rejected", "experiment.superseded", {"reason": "Phạm vi đã thay đổi; giữ hướng dẫn hiện hành."})
                continue
            improvements.apply(candidate["id"])
            improvements.monitor(candidate["id"])
