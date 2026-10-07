"""One controller-owned authority packet for work, review and repair."""

import json

from .contracts import require


CONTRACT_VERSION = 1


def policy_packet(store, task):
    config = store.config
    team = config.get("team", {})
    autonomous = bool(team.get("enabled") and team.get("policy") == "autonomous")
    gated = store.owner_gate(task)
    return {
        "version": CONTRACT_VERSION,
        "mode": "autonomous" if autonomous else "supervised",
        "task_id": task["id"], "revision": task["revision"],
        "gate": {"required": gated, "authority": "owner" if gated else "delegated_company" if autonomous else "independent_review"},
        "scope": {"requirements": task["requirements"], "criteria": task["criteria"],
                  "instructions": task["instructions"]},
        "decisions": store.owner_inputs(task["id"]),
        "external_actions": config["external_actions"],
        "delivery_mode": config.get("delivery_mode", "local"),
        "budgets": {key: config.get(key) for key in
                    ("max_attempts", "max_repairs", "turn_timeout_seconds", "max_turn_tokens", "max_cycle_tokens")},
        "controller_owns_state": True,
        "independent_review_required": True,
    }


def pending_upgrade(store):
    row = store.db.execute("SELECT type,data FROM events WHERE type IN ('workflow.upgrade_prepared','workflow.upgraded') ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(row["data"]) if row and row["type"] == "workflow.upgrade_prepared" else None


def upgrade(store, apply=False):
    """Explicit idle contract upgrade; previous evidence and policy stay intact."""
    pending = pending_upgrade(store)
    if pending:
        report = dict(pending["report"], recovery_required=True)
        if not apply:
            return report
        from .store import write_json
        require(not store.db.execute("SELECT id FROM attempts WHERE status IN ('running','queued')").fetchone()
                and not store.db.execute("SELECT id FROM team_runs WHERE status IN ('preparing','dispatching','running','checking','unknown','backoff')").fetchone(),
                "Kết thúc hoặc đối chiếu phiên đang chạy trước khi hoàn tất nâng cấp workflow.")
        require(store.config in (pending["previous_config"], pending["target_config"]),
                "Cấu hình đã thay đổi trong lúc nâng cấp; giữ journal để đối chiếu trước khi tiếp tục.")
        write_json(store.root / "config.json", pending["target_config"])
        report.update(applied=True, recovery_required=False)
        store.event(None, "workflow.upgraded", report)
        return report
    current = store.config.get("agent_workflow_version", 0)
    affected = [task["id"] for task in store.tasks()
                if task["stage"] in {"architecture", "plan", "build", "setup", "integration", "verify", "handoff", "retro"}
                and task["status"] != "superseded"] if not current else []
    report = {"current_version": current, "target_version": CONTRACT_VERSION,
              "affected_tasks": affected, "applied": False}
    if not apply or current == CONTRACT_VERSION:
        return report
    require(current == 0, "Phiên bản workflow chưa được hỗ trợ để nâng cấp.")
    require(not store.db.execute("SELECT id FROM attempts WHERE status IN ('running','queued')").fetchone()
            and not store.db.execute("SELECT id FROM team_runs WHERE status IN ('preparing','dispatching','running','checking','unknown','backoff')").fetchone()
            and not any(task["status"] in {"running", "reviewing", "awaiting_approval"} for task in store.tasks()),
            "Kết thúc hoặc đối chiếu các phiên và quyết định đang chờ trước khi nâng cấp workflow.")
    from .contracts import CRITERIA, STAGE_TITLES
    from .store import write_json, now
    config = store.config
    previous_config = dict(config)
    config = json.loads(json.dumps(config))
    config["agent_workflow_version"] = CONTRACT_VERSION
    config["workflow_version"] = "0.4.0"
    for role in ("feature_map", "integration"):
        config["models"].setdefault(role, dict(config["models"]["architecture" if role == "feature_map" else "build"]))
    with store.db:
        store.db.execute("""INSERT OR IGNORE INTO tasks(id,stage,title,instructions,deps,criteria,requirements,checks,status,created_at)
            VALUES('feature_map','feature_map',?,?, '["architecture"]',?,'[]','[]','pending',?)""",
            (STAGE_TITLES["feature_map"], "Map accepted features and their verification procedures.",
             json.dumps(CRITERIA["feature_map"]), now()))
        store.db.execute("UPDATE tasks SET deps='[\"feature_map\"]' WHERE id='plan'")
        for tid in affected:
            store.db.execute("UPDATE tasks SET status='stale',revision=revision+1,attempts=0,result=NULL,review=NULL,accepted_at=NULL,reason=? WHERE id=?",
                             ("Áp dụng hợp đồng agent workflow mới theo yêu cầu nâng cấp.", tid))
        store.db.execute("INSERT INTO events(type,data,created_at) VALUES('workflow.upgrade_prepared',?,?)",
            (json.dumps({"report": report, "previous_config": previous_config, "target_config": config}),
             now()))
    write_json(store.root / "config.json", config)
    report["applied"] = True
    store.event(None, "workflow.upgraded", report)
    return report
