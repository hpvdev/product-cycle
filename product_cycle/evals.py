"""Deterministic workflow evaluations, distinct from model-quality evaluations."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from .contracts import WorkflowError, validate_plan
from .fixtures import complete_fixture, prepare_plan
from .store import Store, digest


def must_reject(action):
    try:
        action()
    except WorkflowError:
        return
    raise AssertionError("Một thao tác không hợp lệ đã được chấp nhận.")


def evaluate():
    results = []
    cases = ["dependency_gate", "scope_gate", "missing_artifact", "evidence_tampering", "reopen_invalidates_dependents", "recovery_preserves_history", "cycle_in_plan", "delivery_requires_completion"]
    for name in cases:
        try:
            with tempfile.TemporaryDirectory(prefix="product-cycle-eval-") as temp:
                base = Path(temp)
                with patch.dict(os.environ, {"PRODUCT_CYCLE_HOME": str(base / "state")}):
                    store = Store.create(base / "project", "Một dữ kiện mẫu không nhạy cảm.", "Controller evaluation", mode="demo")
                    try:
                        if name == "dependency_gate":
                            must_reject(lambda: store.begin("design", "work"))
                        elif name == "scope_gate":
                            complete_fixture(store, "analysis", approve=False)
                            assert store.task("analysis")["status"] == "awaiting_approval"
                            assert store.next_task() is None
                        elif name == "missing_artifact":
                            aid, _ = store.begin("analysis", "work")
                            must_reject(lambda: store.work_finished("analysis", aid, {"summary": "Claimed complete", "artifacts": [], "limitations": [], "blocker": None}))
                        elif name == "evidence_tampering":
                            complete_fixture(store, "analysis", approve=False)
                            evidence = store.current_evidence("analysis")[0]
                            (store.root / evidence["object_path"]).write_text("Changed evidence")
                            must_reject(lambda: store.decide("analysis", "approve", "Operator", "Accept"))
                        elif name == "reopen_invalidates_dependents":
                            prepare_plan(store)
                            old = store.current_evidence("analysis")[0]
                            old_hash = digest(store.root / old["object_path"])
                            affected = store.reopen("analysis", "Thay đổi yêu cầu")
                            assert "T1" in affected and "retro" in affected
                            assert store.task("plan")["status"] == "stale"
                            complete_fixture(store, "analysis")
                            assert digest(store.root / old["object_path"]) == old_hash
                            assert store.task("analysis")["revision"] == 2
                        elif name == "recovery_preserves_history":
                            store.begin("analysis", "work")
                            assert store.recover() == ["analysis"]
                            assert store.task("analysis")["attempts"] == 1
                            assert store.snapshot()["tasks"][0]["attempt_history"][0]["status"] == "interrupted"
                        elif name == "cycle_in_plan":
                            plan = {"tasks": [{"id": "T1", "title": "Task", "instructions": "Scope", "requirements": ["R1"], "criteria": ["Done"], "depends_on": ["T1"], "checks": []}]}
                            must_reject(lambda: validate_plan(plan, {"R1"}))
                        elif name == "delivery_requires_completion":
                            must_reject(lambda: store.package(base / "delivery"))
                    finally:
                        store.close()
            results.append({"case": name, "passed": True})
        except Exception as exc:
            results.append({"case": name, "passed": False, "reason": str(exc)})
    return {"kind": "controller_evaluation", "model_calls": 0, "passed": all(row["passed"] for row in results), "cases": results,
            "scope": "Kiểm chứng cơ chế và bất biến của bộ điều phối; không đo chất lượng phân tích, thiết kế hoặc code của model."}
