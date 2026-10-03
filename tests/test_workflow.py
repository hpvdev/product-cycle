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
from product_cycle.runner import run_checks
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


if __name__ == "__main__":
    unittest.main()
