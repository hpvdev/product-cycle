import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from product_cycle.contracts import WorkflowError, validate_plan
from product_cycle.evals import evaluate
from product_cycle.fixtures import complete_fixture, prepare_plan
from product_cycle.runner import execute, prompt_for, run_checks, run_cycle
from product_cycle.store import Store, fingerprint, digest, runner_lock, write_json


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {"PRODUCT_CYCLE_HOME": str(self.base / "state")})
        self.environment.start()
        self.store = Store.create(self.base / "project", "Synthetic product facts", "Test", mode="demo")

    def tearDown(self):
        self.store.close()
        self.environment.stop()
        self.temp.cleanup()

    def plan(self, command=None, browser=False):
        return {"tasks": [{"id": "T1", "title": "Increment", "instructions": "Implement outcome", "depends_on": [], "requirements": ["R1"], "criteria": ["Outcome observed"], "checks": [command] if command else []}], "verification_commands": [command] if command else [], "browser_required": browser}

    def test_scope_gate_blocks_downstream(self):
        complete_fixture(self.store, "analysis", approve=False)
        self.assertIsNone(self.store.next_task())
        with self.assertRaises(WorkflowError):
            self.store.begin("design", "work")
        self.store.decide("analysis", "approve", "Owner", "Agreed scope")
        self.assertEqual(self.store.next_task()["id"], "design")

    def test_real_check_is_executed_and_versioned(self):
        prepare_plan(self.store, self.plan([sys.executable, "-c", "print('observed pass')"]))
        complete_fixture(self.store, "T1")
        checks = [item for item in self.store.current_evidence("T1") if item["kind"] == "check"]
        self.assertEqual(len(checks), 1)
        report = json.loads((self.store.root / checks[0]["object_path"]).read_text())
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["source_fingerprint"], fingerprint(self.store.project))
        self.assertEqual(checks[0]["producer"], "controller")

    def test_failed_check_cannot_be_approved(self):
        prepare_plan(self.store, self.plan([sys.executable, "-c", "raise SystemExit(4)"]))
        with self.assertRaises(WorkflowError):
            complete_fixture(self.store, "T1")
        checks = [item for item in self.store.current_evidence("T1") if item["kind"] == "check"]
        self.assertEqual(json.loads((self.store.root / checks[0]["object_path"]).read_text())["exit_code"], 4)
        self.assertNotEqual(self.store.task("T1")["status"], "done")

    def test_fabricated_review_evidence_rejected(self):
        complete_fixture(self.store, "analysis", approve=False)
        review = self.store.task("analysis")["review"]
        review["criteria"][0]["evidence"] = ["E-invented"]
        with self.assertRaises(WorkflowError):
            self.store.validate_review("analysis", review)

    def test_changed_output_requires_new_review(self):
        complete_fixture(self.store, "analysis", approve=False)
        artifact = self.store.current_evidence("analysis")[0]
        (self.store.project / artifact["source"]).write_text("Different scope")
        with self.assertRaises(WorkflowError):
            self.store.decide("analysis", "approve", "Owner", "Approve old review")
        self.assertEqual(self.store.task("analysis")["status"], "awaiting_approval")

    def test_reopen_preserves_old_objects_and_attempts(self):
        prepare_plan(self.store)
        old = self.store.current_evidence("analysis")[0]
        old_path = self.store.root / old["object_path"]
        old_hash = digest(old_path)
        affected = self.store.reopen("analysis", "New product scope")
        self.assertIn("T1", affected)
        complete_fixture(self.store, "analysis")
        self.assertEqual(digest(old_path), old_hash)
        self.assertEqual(self.store.task("analysis")["revision"], 2)
        histories = self.store.snapshot()["tasks"][0]
        self.assertEqual(len(histories["attempt_history"]), 4)
        self.assertEqual(len(histories["evidence"]), 4)

    def test_replan_keeps_removed_task_history(self):
        prepare_plan(self.store)
        complete_fixture(self.store, "T1")
        self.store.reopen("plan", "Replace task")
        plan = self.plan()
        plan["tasks"][0]["id"] = "T2"
        complete_fixture(self.store, "plan", plan=plan)
        self.assertEqual(self.store.task("T1")["status"], "superseded")
        self.assertEqual(self.store.task("verify")["deps"], ["T2"])
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM attempts WHERE task_id='T1'").fetchone()[0], 2)

    def test_retry_budget_stops_rework(self):
        complete_fixture(self.store, "analysis", review_decision="rework")
        complete_fixture(self.store, "analysis", review_decision="rework")
        self.assertIsNone(self.store.next_task())
        self.assertEqual(self.store.task("analysis")["status"], "blocked")

    def test_browser_claim_is_not_browser_observation(self):
        prepare_plan(self.store, self.plan(browser=True))
        complete_fixture(self.store, "T1")
        with self.assertRaises(WorkflowError):
            complete_fixture(self.store, "verify")
        self.assertNotEqual(self.store.task("verify")["status"], "done")

    def test_changed_source_invalidates_verification(self):
        prepare_plan(self.store)
        complete_fixture(self.store, "T1")
        complete_fixture(self.store, "verify")
        (self.store.project / "new_source.py").write_text("changed = True\n")
        with self.assertRaises(WorkflowError):
            self.store.validate_review("verify", self.store.task("verify")["review"])

    def test_full_cycle_packages_evidence_manifest(self):
        while self.store.next_task():
            complete_fixture(self.store, self.store.next_task()["id"])
        destination = self.store.package(self.base / "delivery")
        manifest = json.loads((destination / "manifest.json").read_text())
        self.assertEqual(manifest["mode"], "demo")
        self.assertEqual(manifest["source_fingerprint"], fingerprint(self.store.project))
        self.assertTrue(all(task["status"] == "done" for task in manifest["snapshot"]["tasks"]))
        self.assertTrue(list((destination / "evidence").iterdir()))

    def test_lock_prevents_two_controllers(self):
        with runner_lock(self.store):
            with self.assertRaises(WorkflowError):
                with runner_lock(self.store):
                    pass

    def test_evidence_path_cannot_escape_project(self):
        outside = self.base / "secret.txt"
        outside.write_text("not evidence")
        with self.assertRaises(WorkflowError):
            self.store.safe_path("../secret.txt")
        link = self.store.project / "link.txt"
        link.symlink_to(outside)
        with self.assertRaises(WorkflowError):
            self.store.safe_path("link.txt")

    def test_controller_state_is_outside_worker_roots(self):
        self.assertFalse(self.store.root.is_relative_to(self.store.project))

    def test_delivery_copies_source_and_omits_environment_secrets(self):
        (self.store.project / "source.py").write_text("value = 1\n")
        (self.store.project / ".env").write_text("SECRET=fixture\n")
        (self.store.project / ".env.example").write_text("SECRET=\n")
        while self.store.next_task():
            complete_fixture(self.store, self.store.next_task()["id"])
        destination = self.store.package(self.base / "delivery")
        self.assertEqual((destination / "source" / "source.py").read_text(), "value = 1\n")
        self.assertFalse((destination / "source" / ".env").exists())
        self.assertTrue((destination / "source" / ".env.example").exists())
        manifest = json.loads((destination / "manifest.json").read_text())
        self.assertIn(".env", manifest["omitted_source_paths"])

    def test_delivery_preserves_full_event_history(self):
        for index in range(260):
            self.store.event(None, "fixture", {"index": index})
        self.assertEqual(len(self.store.snapshot()["events"]), 250)
        self.assertGreater(len(self.store.snapshot(full_history=True)["events"]), 260)

    def test_gate_rejects_criterion_without_mapped_evidence(self):
        complete_fixture(self.store, "analysis", approve=False)
        review = self.store.task("analysis")["review"]
        records = self.store.current_evidence("analysis")
        with self.store.db:
            self.store.db.execute("UPDATE evidence SET criteria='[]' WHERE task_id='analysis'")
        with self.assertRaises(WorkflowError):
            self.store.validate_review("analysis", review)

    def test_eval_suite(self):
        report = evaluate()
        self.assertTrue(report["passed"], json.dumps(report))

    def test_worker_progress_is_advisory_and_survives_event_window(self):
        aid, _ = self.store.begin("analysis", "work")
        self.store.step_progress(aid, [{"step": "S1 Identify users", "status": "completed"},
                                       {"step": "S2 Identify problem", "status": "in_progress"},
                                       {"step": "S99 Invented", "status": "completed"}])
        for index in range(260):
            self.store.event(None, "fixture", {"index": index})
        state = self.store.snapshot()
        steps = {step["id"]: step for step in state["tasks"][0]["steps"]}
        self.assertEqual(steps["S1"]["status"], "reported")
        self.assertEqual(steps["S2"]["status"], "running")
        self.assertNotIn("S99", steps)
        self.assertEqual(state["stages"][0]["completed"], 0)

    def test_result_and_review_require_small_step_coverage(self):
        complete_fixture(self.store, "analysis", approve=False)
        result = self.store.task("analysis")["result"]
        result["steps"].pop()
        with self.assertRaises(WorkflowError):
            self.store.validate_outputs("analysis", result)
        review = self.store.task("analysis")["review"]
        review["steps"].pop()
        with self.assertRaises(WorkflowError):
            self.store.validate_review("analysis", review)

    def test_review_step_must_reference_its_actual_output(self):
        complete_fixture(self.store, "analysis", approve=False)
        result = self.store.task("analysis")["result"]
        records = self.store.current_evidence("analysis")
        result["steps"][0]["artifacts"] = [records[0]["source"]]
        self.store.update("analysis", result=result)
        review = self.store.task("analysis")["review"]
        review["steps"][0]["evidence"] = [records[1]["id"]]
        with self.assertRaises(WorkflowError):
            self.store.validate_review("analysis", review)

    def test_owner_gate_is_part_of_progress_and_reopen_resets_steps(self):
        complete_fixture(self.store, "analysis", approve=False)
        stage = self.store.snapshot()["stages"][0]
        self.assertEqual(stage["completed"], stage["total"] - 1)
        self.assertEqual(stage["steps"][-1]["status"], "awaiting_approval")
        self.store.decide("analysis", "approve", "Owner", "Approved scope")
        self.assertEqual(self.store.snapshot()["stages"][0]["percent"], 100)
        self.store.reopen("analysis", "New scope")
        stage = self.store.snapshot()["stages"][0]
        self.assertEqual(stage["completed"], 0)
        self.assertTrue(all(not step["evidence"] for step in stage["steps"]))

    def test_historical_results_are_untracked_instead_of_invented(self):
        complete_fixture(self.store, "analysis")
        task = self.store.task("analysis")
        task["result"].pop("steps")
        task["review"].pop("steps")
        self.store.update("analysis", result=task["result"], review=task["review"])
        with self.store.db:
            self.store.db.execute("DELETE FROM events WHERE task_id='analysis' AND type='steps.started'")
        steps = self.store.snapshot()["tasks"][0]["steps"]
        self.assertTrue(all(step["status"] == "untracked" for step in steps if step["id"].startswith("S")))
        self.store.validate_review("analysis", task["review"])

    def test_ui_baseline_needs_a_registered_visual_reference(self):
        complete_fixture(self.store, "analysis")
        complete_fixture(self.store, "design", approve=False)
        path = self.store.latest_directory("design") / "design-baseline.json"
        value = json.loads(path.read_text())
        value.update(has_ui=True, visual_reference="missing-reference.png")
        write_json(path, value)
        with self.assertRaises(WorkflowError):
            self.store.validate_outputs("design", self.store.task("design")["result"])

    def test_retry_receives_review_and_owner_feedback(self):
        complete_fixture(self.store, "analysis", approve=False)
        self.store.decide("analysis", "reject", "Owner", "Narrow the first version")
        _, directory = self.store.begin("analysis", "work")
        prompt_for(self.store, self.store.task("analysis"), directory)
        feedback = json.loads((directory / "context.json").read_text())["feedback"]
        self.assertEqual(feedback["reason"], "Narrow the first version")
        self.assertIsNotNone(feedback["review"])
        self.assertTrue(feedback["previous_outputs"])

    def test_runtime_plan_notifications_are_scoped_to_the_current_turn(self):
        config = self.store.config
        config["mode"] = "live"
        write_json(self.store.root / "config.json", config)

        class Peer:
            def __init__(self, directory, on_event):
                self.notify = on_event

            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def run(self, *args, **kwargs):
                self.notify({"method": "client/threadReady", "params": {"thread_id": "current"}})
                self.notify({"method": "client/turnReady", "params": {"turn_id": "turn"}})
                self.notify({"method": "turn/plan/updated", "params": {"threadId": "other", "turnId": "turn", "plan": [{"step": "S3 Ignore", "status": "completed"}]}})
                self.notify({"method": "turn/plan/updated", "params": {"threadId": "current", "turnId": "turn", "plan": [{"step": "S1 Inputs", "status": "completed"}, {"step": "S2 Problem", "status": "in_progress"}]}})
                raise WorkflowError("Controlled interruption")

        with self.assertRaises(WorkflowError):
            execute(self.store, "analysis", client_factory=Peer)
        steps = {step["id"]: step for step in self.store.snapshot()["tasks"][0]["steps"]}
        self.assertEqual(steps["S1"]["status"], "reported")
        self.assertEqual(steps["S2"]["status"], "blocked")
        self.assertEqual(steps["S3"]["status"], "pending")

    def test_all_ten_proposed_items_are_visible_before_plan_approval(self):
        plan = self.plan()
        plan["tasks"] = [dict(plan["tasks"][0], id="T" + str(i), title="Increment " + str(i),
                              depends_on=["T" + str(i - 1)] if i > 1 else []) for i in range(1, 11)]
        for tid in ["analysis", "design", "architecture"]:
            complete_fixture(self.store, tid)
        complete_fixture(self.store, "plan", plan=plan, approve=False)
        progress = self.store.snapshot()["development"]
        self.assertEqual(progress["total"], 10)
        self.assertEqual(progress["counts"]["awaiting_plan"], 10)
        self.assertTrue(all(row["task_id"] is None for row in progress["items"]))
        self.assertFalse(any(task["stage"] == "build" for task in self.store.tasks()))
        write_json(self.store.latest_directory("plan") / "plan.json", self.plan())
        self.assertEqual(self.store.snapshot()["development"]["total"], 10)

    def test_task_counts_criteria_and_step_progress_follow_real_state(self):
        plan = self.plan()
        plan["tasks"].append(dict(plan["tasks"][0], id="T2", depends_on=["T1"]))
        prepare_plan(self.store, plan)
        progress = self.store.snapshot()["development"]
        self.assertEqual(progress["counts"]["ready"], 1)
        self.assertEqual(progress["counts"]["waiting"], 1)
        aid, _ = self.store.begin("T1", "work")
        self.store.step_progress(aid, [{"step": "S1 Inputs", "status": "completed"}, {"step": "S2 Implement", "status": "in_progress"}])
        item = self.store.snapshot()["development"]["items"][0]
        self.assertEqual(item["current_step"]["id"], "S2")
        self.assertEqual(item["criteria_passed"], 0)
        self.store.update("T1", status="blocked")
        self.store.reopen("T1", "Repeat interrupted fixture")
        complete_fixture(self.store, "T1")
        progress = self.store.snapshot()["development"]
        self.assertEqual(progress["completed"], 1)
        self.assertEqual(progress["items"][0]["criteria_passed"], 1)
        self.assertEqual(progress["items"][1]["status"], "stale")
        self.assertEqual(self.store.snapshot()["delivery"]["acceptance_status"], "stale")

    def test_replan_proposal_does_not_borrow_old_completion(self):
        prepare_plan(self.store)
        complete_fixture(self.store, "T1")
        self.store.reopen("plan", "Change increment scope")
        complete_fixture(self.store, "plan", plan=self.plan(), approve=False)
        item = self.store.snapshot()["development"]["items"][0]
        self.assertEqual(item["status"], "awaiting_plan")
        self.assertEqual(item["criteria_passed"], 0)
        self.assertIsNone(item["task_id"])
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM attempts WHERE task_id='T1'").fetchone()[0], 2)

    def local_services_plan(self, command=None):
        config = self.store.config
        config.update(service_setup_required=True, gates=["handoff"])
        write_json(self.store.root / "config.json", config)
        service = {"id": "email", "provider": "Email service", "purpose": "Reminder emails", "environment": "Fixture account",
                   "inputs": ["Secure credential reference"], "permissions": ["Project configuration"],
                   "configuration": "Configure the selected project after plan review", "verification": "Observed connection check",
                   "checks": [command or [sys.executable, "-c", "print('synthetic service check')"]],
                   "owner": "Owner", "cost": "No purchase in this fixture", "fallback": "Continue unrelated work"}
        plan = self.plan()
        plan["tasks"][0]["services"] = []
        plan["tasks"].append(dict(plan["tasks"][0], id="T2", title="Email increment", services=["email"]))
        plan.update(service_ids=["email"], delivery={"mode": "local", "access": "Local product", "instructions": "Open local product",
                                                   "run_commands": [], "deferred": ["VPS and external release"]})
        for tid in ["analysis", "design"]:
            complete_fixture(self.store, tid)
        complete_fixture(self.store, "architecture", services=[service])
        self.assertFalse(any(task["stage"] == "setup" for task in self.store.tasks()))
        complete_fixture(self.store, "plan", plan=plan)
        return plan

    def test_service_configuration_starts_after_design_plan_and_only_blocks_dependents(self):
        self.local_services_plan()
        self.assertEqual(self.store.task("setup-email")["deps"], ["plan"])
        self.assertEqual(self.store.task("T1")["deps"], ["plan"])
        self.assertEqual(self.store.task("T2")["deps"], ["plan", "setup-email"])
        complete_fixture(self.store, "setup-email", readiness={"services": [{"id": "email", "status": "needs_input",
                         "note": "Owner must supply the secure reference", "input_refs": ["Credential reference"]}]}, blocker="Missing configuration")
        state = self.store.snapshot()
        self.assertEqual(state["services"][0]["status"], "needs_input")
        self.assertEqual(state["development"]["counts"]["ready"], 1)
        self.assertEqual(state["development"]["counts"]["waiting"], 1)
        self.assertEqual(self.store.next_task()["id"], "T1")
        self.assertTrue(self.store.current_evidence("setup-email"))

    def test_worker_ready_claim_requires_actual_successful_service_check(self):
        self.local_services_plan([sys.executable, "-c", "raise SystemExit(4)"])
        with self.assertRaises(WorkflowError):
            complete_fixture(self.store, "setup-email")
        self.assertNotEqual(self.store.snapshot()["services"][0]["status"], "ready")
        self.assertNotEqual(self.store.task("setup-email")["status"], "done")
        self.assertEqual(self.store.snapshot()["development"]["items"][1]["service_status"], "pending")

    def test_service_readiness_is_reset_on_reopen_and_retains_evidence(self):
        self.local_services_plan()
        complete_fixture(self.store, "setup-email")
        state = self.store.snapshot()
        self.assertEqual(state["services"][0]["status"], "ready")
        self.assertTrue(state["services"][0]["evidence"])
        self.assertEqual(state["development"]["items"][1]["service_status"], "done")
        records = self.store.current_evidence("setup-email")
        self.store.reopen("setup-email", "Replace service configuration")
        state = self.store.snapshot()
        self.assertEqual(state["services"][0]["status"], "stale")
        self.assertFalse(state["services"][0]["evidence"])
        self.assertEqual(state["development"]["items"][1]["service_status"], "pending")
        self.store.intact(records)

    def test_run_continues_unrelated_work_after_service_input_blocker(self):
        self.local_services_plan()
        def fixture_execute(store, tid, factory):
            if tid == "setup-email":
                complete_fixture(store, tid, readiness={"services": [{"id": "email", "status": "needs_input", "note": "Need input", "input_refs": []}]}, blocker="Need input")
                raise WorkflowError("Need input")
            complete_fixture(store, tid)
        with patch("product_cycle.runner.execute", side_effect=fixture_execute) as executor:
            run_cycle(self.store, max_tasks=2)
        self.assertEqual([call.args[1] for call in executor.call_args_list], ["setup-email", "T1"])
        self.assertEqual(self.store.task("T1")["status"], "done")
        self.assertEqual(self.store.task("T2")["status"], "pending")

    def test_new_local_cycle_reaches_handoff_without_vps_or_remote_release(self):
        store = Store.create(self.base / "local-product", "Local product", "Local cycle")
        try:
            self.assertEqual(store.config["gates"], ["handoff"])
            self.assertEqual(store.config["delivery_mode"], "local")
            self.assertTrue(store.config["release_deferred"])
            while store.next_task():
                tid = store.next_task()["id"]
                complete_fixture(store, tid, approve=tid != "handoff")
            self.assertEqual(store.task("handoff")["status"], "awaiting_approval")
            self.assertEqual(store.task("verify")["status"], "done")
            self.assertFalse(any(task["stage"] == "setup" for task in store.tasks()))
            self.assertEqual(next(stage for stage in store.snapshot()["stages"] if stage["id"] == "setup")["status"], "not_required")
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
