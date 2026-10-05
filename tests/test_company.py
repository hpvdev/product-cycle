"""Synthetic company controller checks; not real product-quality evaluation."""
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from product_cycle.store import Store, write_json, runner_lock
from product_cycle.team import TeamStore, Supervisor, configure, at_capacity, agent_for, apply_output
from product_cycle.company import management_jobs, reserve_management, complete_management, apply_repairs
from product_cycle.company_learning import jobs, reserve, complete, pending, refresh
from product_cycle.contracts import WorkflowError, work_steps
from product_cycle.cli import parser
from product_cycle.server import company_document
from product_cycle.fixtures import complete_fixture


class CompanyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"PRODUCT_CYCLE_HOME": str(Path(self.temp.name) / "state")})
        self.env.start()
        self.store = Store.create(Path(self.temp.name) / "project", "Synthetic company", "Company", mode="demo", team=True)
        self.team = TeamStore(self.store)

    def tearDown(self):
        self.store.close()
        self.env.stop()
        self.temp.cleanup()

    def run_for(self, task="analysis", phase="work", **kwargs):
        with runner_lock(self.store):
            if phase in {"work", "review"}:
                attempt, directory = self.store.begin(task, phase)
                kwargs.update(attempt_id=attempt, directory=directory)
            run = self.team.create_run(task, phase, **kwargs)
        self.team.update(run["id"], status="running", thread_id="synthetic-" + uuid.uuid4().hex, turn_id="turn-1")
        return self.team.run(run["id"])

    def test_new_policy_and_explicit_legacy_migration(self):
        self.assertEqual(self.store.config["gates"], [])
        self.assertFalse(self.store.owner_gate(self.store.task("analysis")))
        self.assertFalse(self.store.owner_gate(self.store.task("design")))
        self.assertTrue(self.store.config["team"]["self_improve"])
        config = self.store.config
        config["team"].pop("policy")
        config["team"].pop("self_improve")
        config["gates"] = ["analysis", "design", "handoff"]
        write_json(self.store.root / "config.json", config)
        configure(self.store)
        self.assertEqual(self.store.config["team"]["policy"], "supervised")
        self.assertEqual(self.store.config["gates"], ["analysis", "design", "handoff"])

    def test_capacity_is_runtime_limit_with_consultation_lane(self):
        runs = [{"phase": "work"}] * 20
        self.assertFalse(at_capacity(self.store, runs, "work"))
        configure(self.store, max_concurrent=8)
        self.assertTrue(at_capacity(self.store, runs, "work"))
        self.assertFalse(at_capacity(self.store, runs, "consult"))
        self.assertFalse(at_capacity(self.store, [{"phase": "consult"}] * 20, "work"))

    def test_explicit_autonomous_policy_replaces_legacy_analysis_gate(self):
        config = self.store.config
        config["gates"] = ["analysis"]
        config["collaborative_product"] = True
        write_json(self.store.root / "config.json", config)
        configure(self.store, max_concurrent=4)
        self.assertTrue(self.store.owner_gate(self.store.task("analysis")))
        configure(self.store, policy="autonomous")
        complete_fixture(self.store, "analysis", approve=False)
        self.assertEqual(self.store.task("analysis")["status"], "done")
        self.assertEqual(self.store.task("analysis")["review"]["decision"], "approve")
        self.assertFalse(list(self.store.db.execute("SELECT id FROM decisions")))
        self.assertEqual(self.store.next_task()["id"], "design")

    def test_supervised_policy_restores_owner_analysis_gate(self):
        configure(self.store, policy="supervised")
        complete_fixture(self.store, "analysis", approve=False)
        self.assertEqual(self.store.task("analysis")["status"], "awaiting_approval")

    def test_hired_employee_is_independent_and_specialized(self):
        role = self.team.hire("product_manager")
        origin = self.run_for()
        consultant = self.run_for(phase="consult", agent_id=role["id"])
        self.assertNotEqual(origin["agent_id"], consultant["agent_id"])
        self.assertEqual(consultant["source_writer"], 0)
        self.assertEqual(len({a["id"] for a in self.team.roster()}), len(self.team.roster()))
        with self.assertRaises(WorkflowError):
            self.run_for(phase="consult", agent_id="ba_reviewer")

    def test_inactive_peer_gets_durable_consultation_not_fake_reply(self):
        run = self.run_for()
        message = self.team.send_message(run["id"], "product_manager", "Which accepted objective applies?", "ask-1")
        request = dict(self.store.db.execute("SELECT * FROM team_requests WHERE client_key=?", ("inbox:" + str(message["id"]),)).fetchone())
        self.assertEqual(request["status"], "queued")
        self.assertEqual(request["prompt"], message["text"])
        self.assertEqual(len(self.team.mailbox(run, "poll")), 0)
        self.assertEqual(self.team.send_message(run["id"], "product_manager", message["text"], "ask-1")["id"], message["id"])

    def test_director_repair_preserves_failed_history_and_does_not_approve(self):
        run = self.run_for()
        self.team.update(run["id"], status="blocked")
        with self.store.db:
            self.store.db.execute("UPDATE attempts SET status='failed' WHERE id=?", (run["attempt_id"],))
        self.store.update("analysis", status="blocked", reason="Synthetic missing artifact")
        task, signature = next(management_jobs(self.store))
        manager = self.run_for(phase="manage")
        reserve_management(self.store, manager, signature)
        complete_management(self.team, manager, {"summary": "Repair missing output", "action": "repair", "reason": "Write the required artifact from accepted inputs", "question": None, "options": [], "recommendation": ""})
        self.team.update(manager["id"], status="completed")
        apply_repairs(self.store)
        self.assertEqual(self.store.task("analysis")["revision"], task["revision"] + 1)
        self.assertEqual(self.store.db.execute("SELECT status FROM attempts WHERE id=?", (run["attempt_id"],)).fetchone()[0], "failed")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)

    def test_improvement_null_is_bounded_no_change_not_pass(self):
        for task in self.store.tasks():
            self.store.update(task["id"], status="done")
        task, phase, prior = next(jobs(self.store))
        run = self.run_for(task["id"], phase)
        reserve(self.store, run, prior)
        result = {"candidate": None, "reason": "No reproducible raw case exists in this synthetic cycle"}
        complete(self.team, run, result)
        complete(self.team, run, result)
        self.team.update(run["id"], status="completed")
        self.assertFalse(pending(self.store))
        self.assertEqual(list(jobs(self.store)), [])
        self.assertEqual(self.team.snapshot()["company"]["improvements"], [])
        self.assertEqual(self.store.db.execute("SELECT status FROM company_learning").fetchone()[0], "no_change")

    def test_failed_improvement_does_not_look_active_or_modify_product(self):
        for task in self.store.tasks():
            self.store.update(task["id"], status="done")
        task, phase, prior = next(jobs(self.store))
        run = self.run_for(task["id"], phase)
        reserve(self.store, run, prior)
        self.team.update(run["id"], status="blocked", reason="Synthetic provider failure")
        refresh(self.store)
        self.assertEqual(self.store.db.execute("SELECT status FROM company_learning").fetchone()[0], "attention")
        self.assertEqual(self.store.task("retro")["status"], "done")

    def test_learning_waits_for_unknown_but_not_stale_queue(self):
        for task in self.store.tasks():
            self.store.update(task["id"], status="done")
        task, phase, prior = next(jobs(self.store))
        run = self.run_for(task["id"], phase)
        reserve(self.store, run, prior)
        self.team.update(run["id"], status="unknown")
        refresh(self.store)
        self.assertTrue(pending(self.store))
        self.team.update(run["id"], status="blocked")
        with self.store.db:
            self.store.db.execute("UPDATE company_learning SET status='queued'")
            self.store.db.execute("UPDATE tasks SET revision=revision+1 WHERE id='retro'")
        self.assertFalse(pending(self.store))

    def test_questions_from_primary_or_consultant_and_fast_answers_are_not_lost(self):
        for consultant, fast_answer in [(False, True), (True, False), (True, True)]:
            with self.subTest(consultant=consultant, fast_answer=fast_answer):
                if self.store.task("analysis")["status"] != "pending":
                    self.store.reopen("analysis", "New synthetic independent question case")
                self.question_during_source(consultant, fast_answer)

    def question_during_source(self, consultant=False, fast_answer=True):
        from product_cycle.company_questions import ask, answer, resume_answered
        run = self.run_for()
        source = self.run_for(phase="consult", agent_id="product_manager", attempt_id=run["attempt_id"]) if consultant else run
        question = ask(self.store, source, "Choose audience", ["Adults", "Children"], "Adults", "Cannot infer audience", "audience")
        if fast_answer:
            answer(self.store, question["id"], "Product owner", "Adults")
        if consultant:
            self.team.update(source["id"], status="completed")
        task = self.store.task("analysis")
        directory = Path(run["directory"])
        (directory / "analysis.md").write_text("Synthetic analysis only")
        write_json(directory / "requirements.json", {"requirements": [{"id": "R1", "description": "Save value", "acceptance": ["Saved value can be read"]}]})
        artifacts = [{"path": str((directory / name).relative_to(self.store.project)), "purpose": "Synthetic output",
                      "criteria": ["C" + str(i + 1) for i in range(len(task["criteria"]))], "requirements": []}
                     for name in ["analysis.md", "requirements.json"]]
        result = {"summary": "Need audience", "artifacts": artifacts,
                  "steps": [{"id": step["id"], "summary": "Synthetic output", "artifacts": [a["path"] for a in artifacts]} for step in work_steps("analysis")],
                  "limitations": [], "blocker": None if consultant else "Choose audience"}
        apply_output(self.team, run, {"result": result})
        self.assertTrue(self.store.task("analysis")["reason"].startswith("Cần bạn trả lời: "))
        if not fast_answer:
            self.assertEqual(resume_answered(self.store), [])
            answer(self.store, question["id"], "Product owner", "Adults")
        self.assertEqual(len(resume_answered(self.store)), 1)
        self.assertEqual(self.store.task("analysis")["status"], "rework")
        self.assertEqual(self.store.task("analysis")["revision"], run["revision"])

    def test_ancestor_repair_cannot_stale_unknown_native_outcome(self):
        from product_cycle.capability_jobs import request, claim, source_in_use
        self.store.update("analysis", status="done")
        run = self.run_for("design")
        native = request(self.store, run, "image_generation", "Real tool output still uncertain", "image")
        self.team.update(run["id"], status="completed")
        with self.store.db:
            self.store.db.execute("UPDATE attempts SET status='completed' WHERE id=?", (run["attempt_id"],))
        self.store.update("design", status="blocked", reason="Chờ công cụ: Image")
        claim(self.store, native["id"], "Native worker", self.store.project)
        with self.store.db:
            self.store.db.execute("UPDATE capability_jobs SET status='unknown' WHERE id=?", (native["id"],))
        self.store.update("analysis", status="blocked", reason="Synthetic ancestor correction")
        task, signature = next(item for item in management_jobs(self.store) if item[0]["id"] == "analysis")
        manager = self.run_for(phase="manage")
        reserve_management(self.store, manager, signature)
        complete_management(self.team, manager, {"summary": "Repair", "action": "repair", "reason": "Concrete correction", "question": None, "options": [], "recommendation": ""})
        self.team.update(manager["id"], status="completed")
        apply_repairs(self.store)
        self.assertEqual(self.store.task("analysis")["revision"], task["revision"])
        self.assertTrue(source_in_use(self.store))

    def test_attachment_failure_does_not_leave_orphan_attempt(self):
        for task in self.store.tasks():
            self.store.update(task["id"], status="pending" if task["id"] == "verify" else "done")
        write_json(self.store.root / "config.json", dict(self.store.config, mode="live"))
        supervisor = Supervisor(self.store)
        supervisor.next_reconcile = float("inf")
        with patch("product_cycle.capability_jobs.completed_context", return_value=[{"id": "native", "is_source_current": True, "manifest": {"browser": {"screenshot": "capture.png"}}}]), \
             patch("product_cycle.capability_jobs.register_browser_evidence", side_effect=WorkflowError("Synthetic damaged capture")), \
             patch.object(Path, "write_text", side_effect=OSError("Synthetic unavailable diagnostic directory")):
            supervisor.tick()
        self.assertEqual(self.store.task("verify")["status"], "blocked")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM attempts WHERE status IN ('running','queued')").fetchone()[0], 0)
        self.assertEqual(len(supervisor.futures), 0)

    def test_specialized_plan_dispatch_and_cli_bridge(self):
        config = self.store.config
        config["team"]["task_agents"] = {"T1": "mobile"}
        write_json(self.store.root / "config.json", config)
        self.assertEqual(agent_for({"id": "T1", "role": "build"}, "work", self.store), "mobile")
        args = parser().parse_args(["company-submit", "--project", str(self.store.project), "--job", "native-1", "--actor", "Tool worker", "--thread", "chat-1", "--file", "manifest.json"])
        self.assertEqual(args.thread, "chat-1")
        self.assertIn("&lt;script&gt;", company_document(json.dumps({"summary": "<script>bad()</script>"}).encode()).decode())


if __name__ == "__main__":
    unittest.main()
