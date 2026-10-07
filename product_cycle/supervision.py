"""Compact coordinator view of recorded outcomes and actionable waits."""

from .store import fingerprint


def summary(store):
    tasks = store.tasks()
    by_id = {task["id"]: task for task in tasks}
    current = fingerprint(store.project)
    final = by_id["verify"]
    whole_verified = final["status"] == "done" and final["fingerprint"] == current
    outcomes, waits = [], []
    for task in tasks:
        if task["stage"] == "build" and task["role"] != "project_setup" and task["status"] != "superseded":
            integration = by_id.get("integrate-" + task["id"])
            outcomes.append({"task_id": task["id"], "workspace_verified": task["status"] == "done",
                             "integrated": bool(integration and integration["status"] == "done"),
                             "product_verified": whole_verified and bool(integration and integration["status"] == "done"),
                             "current_source": bool(integration and integration["fingerprint"] == current)})
        if task["status"] == "awaiting_approval":
            waits.append({"task_id": task["id"], "kind": "decision", "owner": "product_owner",
                          "condition": "configured_gate", "clear_action": "record approve or reject for the reviewed version"})
        elif task["status"] == "blocked":
            reason = task["reason"] or "Unspecified blocker"
            kind, owner, action = "failure", "coordinator", "inspect evidence and propose a bounded correction"
            if reason.startswith("Cần bạn trả lời:"):
                kind, owner, action = "input", "product_owner", "answer the recorded question"
            elif reason.startswith(("Chờ công cụ:", "Chờ capability:", "Chờ runtime/capability:")):
                kind, owner, action = "capability", "runtime_operator", "supply the missing authorized runtime or tool"
            elif reason.startswith("Integration conflict"):
                kind, owner, action = "integration", "feature_builder", "repair the rebased workspace and obtain fresh review"
            waits.append({"task_id": task["id"], "kind": kind, "owner": owner, "condition": reason, "clear_action": action})
    unknown = [dict(row) for row in store.db.execute("SELECT id,task_id,thread_id,turn_id FROM team_runs WHERE status='unknown'")]
    for run in unknown:
        waits.append({"task_id": run["task_id"], "kind": "unknown_execution", "owner": "supervisor",
                      "condition": "provider outcome is unconfirmed", "clear_action": "read the exact recorded thread/turn before retrying",
                      "run_id": run["id"]})
    return {"version": 1, "evidence_scope": "synthetic_controller" if store.config.get("mode") == "demo" else "recorded_product_evidence", "whole_product_verified": whole_verified, "whole_product_accepted": whole_verified and by_id["handoff"]["status"] == "done" and by_id["handoff"]["fingerprint"] == current, "source_fingerprint": current,
            "outcomes": outcomes, "waits": waits,
            "running": [{"id": row["id"], "task_id": row["task_id"], "recorded_status": row["status"]}
                        for row in store.db.execute("SELECT id,task_id,status FROM team_runs WHERE status IN ('preparing','dispatching','running','checking')")],
            "pending": [task["id"] for task in tasks if task["status"] in {"pending", "rework", "stale"}]}
