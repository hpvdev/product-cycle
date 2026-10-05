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
from product_cycle.runner import context, execute, prompt_for, run_checks, run_cycle, run_phase, thread_title
from product_cycle.store import Store, fingerprint, digest, runner_lock, write_json
from product_cycle.bootstrap import prepare_project, repository_state, git
from product_cycle.installer import install_skills
from product_cycle.codex import ModelCapacityError
from product_cycle.runner import sync_task, continue_task


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

    def test_dashboard_keeps_attempt_step_contract_after_workflow_update(self):
        complete_fixture(self.store, "analysis")
        _, directory = self.store.begin("design", "work")
        prompt_for(self.store, self.store.task("design"), directory)
        packet = json.loads((directory / "context.json").read_text())
        packet["work_steps"][3].update(title="Historical state and asset design", description="Reviewed state and asset coverage, not per-action specifications.")
        write_json(directory / "context.json", packet)
        stage = next(stage for stage in self.store.snapshot()["stages"] if stage["id"] == "design")
        step = next(step for step in stage["steps"] if step["id"] == "S4")
        self.assertEqual(step["title"], "Historical state and asset design")
        self.assertEqual(step["description"], packet["work_steps"][3]["description"])

    def test_blocked_increment_keeps_its_reason_outputs_and_history(self):
        prepare_plan(self.store, self.plan())
        reason = "Cần dữ liệu cho đầu việc này trước khi hoàn tất."
        task = complete_fixture(self.store, "T1", blocker=reason)
        self.assertEqual(task["status"], "blocked")
        self.assertEqual(task["reason"], reason)
        self.assertEqual(task["result"]["blocker"], reason)
        self.assertTrue(self.store.current_evidence("T1"))
        self.assertEqual(self.store.snapshot()["execution"]["reason"], reason)
        with self.assertRaises(WorkflowError):
            self.store.validate_review("T1", {"decision": "approve", "summary": "Cannot accept blocker", "findings": []})

    def test_execution_uses_live_lock_and_attempt_activity_not_stored_running_status(self):
        self.assertEqual(self.store.snapshot()["execution"]["status"], "idle")
        aid, _ = self.store.begin("analysis", "work")
        self.store.attempt_update(aid, thread_id="worker-thread", turn_id="worker-turn", tokens=42)
        self.store.event("analysis", "runtime.activity", {"attempt_id": aid, "item_type": "fileChange"})
        with runner_lock(self.store):
            execution = self.store.snapshot()["execution"]
            self.assertTrue(execution["active"])
            self.assertEqual(execution["phase"], "work")
            self.assertEqual(execution["task_id"], "analysis")
            self.assertEqual(execution["attempt"]["thread_id"], "worker-thread")
            self.assertEqual(execution["attempt"]["tokens"], 42)
            self.assertLess(execution["seconds_since_activity"], 3)
            self.store.attempt_update(aid, status="completed")
            self.store.event("analysis", "check.started", {"attempt_id": aid})
            self.assertEqual(self.store.snapshot()["execution"]["phase"], "check")
            self.store.event("analysis", "check.completed", {"attempt_id": aid})
            self.assertEqual(self.store.snapshot()["execution"]["phase"], "controller")
            self.store.attempt_update(aid, status="running")
        execution = self.store.snapshot()["execution"]
        self.assertFalse(execution["active"])
        self.assertEqual(execution["status"], "interrupted")
        self.store.recover()
        self.assertEqual(self.store.snapshot()["execution"]["status"], "blocked")

    def test_browser_gate_belongs_to_product_verification_not_increment_flags(self):
        plan = self.plan(browser=True)
        validate_plan(plan, {"R1"})
        plan["tasks"][0]["browser_required"] = True
        with self.assertRaises(WorkflowError):
            validate_plan(plan, {"R1"})

    def test_execution_failure_supersedes_older_activity_but_not_new_chat_progress(self):
        aid, _ = self.store.begin("analysis", "work")
        self.store.attempt_update(aid, status="failed", ended_at="2026-10-04T04:54:29Z")
        self.store.update("analysis", status="blocked", reason="Connection unavailable")
        event = {"type": "thread.synced", "data": {"attempt_id": aid}, "created_at": "2026-10-04T04:23:53Z"}
        execution = self.store.execution_status(self.store.tasks(), [event])
        self.assertEqual(execution["last_activity_at"], "2026-10-04T04:54:29Z")
        self.assertIn("đã dừng", execution["activity"])
        self.assertFalse(execution["active"])
        event["created_at"] = "2026-10-04T05:00:00Z"
        execution = self.store.execution_status(self.store.tasks(), [event])
        self.assertEqual(execution["last_activity_at"], event["created_at"])
        self.assertEqual(execution["activity"], "Đã đồng bộ kết quả làm tiếp trong Codex")

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

    def test_full_restart_context_excludes_old_feedback_and_accepted_outputs(self):
        self.store.owner_input("analysis", "Owner", "Previous product direction")
        prepare_plan(self.store)
        old = self.store.current_evidence("analysis")[0]
        self.store.reopen("analysis", "Reconsider direction from scratch")
        self.store.owner_input("analysis", "Owner", "New product direction")
        _, directory = self.store.begin("analysis", "work")
        prompt_for(self.store, self.store.task("analysis"), directory)
        packet = json.loads((directory / "context.json").read_text())
        self.assertEqual(packet["accepted_inputs"], [])
        self.assertEqual([item["note"] for item in packet["owner_inputs"]], ["New product direction"])
        self.assertEqual(packet["feedback"], {"reason": "Reconsider direction from scratch",
                                              "review": None, "previous_outputs": []})
        self.assertTrue((self.store.root / old["object_path"]).is_file())
        events = self.store.db.execute("SELECT data FROM events WHERE type='owner.input'").fetchall()
        self.assertEqual([json.loads(row[0])["note"] for row in events],
                         ["Previous product direction", "New product direction"])

    def test_partial_restart_context_retains_only_accepted_upstream_outputs(self):
        prepare_plan(self.store)
        self.store.reopen("design", "Reconsider visual direction")
        packet = context(self.store, self.store.task("design"))
        self.assertEqual([item["task"] for item in packet["accepted_inputs"]], ["analysis"])
        self.assertIsNone(packet["task"]["result"])
        self.assertIsNone(packet["task"]["review"])

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

    def test_frontend_skill_routes_only_to_design_and_approved_ui_work(self):
        install_skills(self.store.project)
        prepare_plan(self.store, self.plan())
        _, directory = self.store.begin("T1", "work")
        baseline = self.base / "approved-baseline.json"
        inputs = [{"task": "design", "artifacts": [{"original_path": "design-baseline.json", "path": str(baseline)}]}]
        skill = self.store.project / ".agents/skills/frontend-app-builder/SKILL.md"
        for tid, has_ui, review, expected in [("design", False, False, True), ("T1", True, False, True),
                                              ("T1", False, False, False), ("T1", True, True, False)]:
            with self.subTest(tid=tid, has_ui=has_ui, review=review):
                write_json(baseline, {"has_ui": has_ui})
                with patch("product_cycle.runner.context", return_value={"accepted_inputs": inputs}):
                    prompt_for(self.store, self.store.task(tid), directory, review=review)
                packet = json.loads((directory / "context.json").read_text())
                self.assertEqual("frontend_skill" in packet, expected)
                if expected:
                    self.assertEqual(packet["frontend_skill"]["path"], str(skill))
                    self.assertTrue(skill.is_file())

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

    def test_optional_token_limits_use_the_remaining_cycle_budget(self):
        config = self.store.config
        self.assertIsNone(config["max_turn_tokens"])
        self.assertIsNone(config["max_cycle_tokens"])
        for turn_limit, cycle_limit, expected in [(None, None, None), (50, None, 50),
                                                   (None, 100, 70), (50, 100, 50),
                                                   (90, 100, 70), (None, 30, None)]:
            with self.subTest(turn=turn_limit, cycle=cycle_limit):
                config.update(max_turn_tokens=turn_limit, max_cycle_tokens=cycle_limit)
                write_json(self.store.root / "config.json", config)
                with patch("product_cycle.runner.prompt_for", return_value="Fixture"), \
                        patch.object(self.store, "snapshot", return_value={"tokens": 30}), \
                        patch("product_cycle.runner.CodexClient") as factory:
                    client = factory.return_value.__enter__.return_value
                    client.run.side_effect = WorkflowError("Controlled interruption")
                    with self.assertRaises(WorkflowError):
                        run_phase(self.store, self.store.task("analysis"), "fixture", self.base, False, factory)
                    if cycle_limit == 30:
                        factory.assert_not_called()
                    else:
                        self.assertEqual(client.run.call_args.kwargs["max_tokens"], expected)

    def test_new_worker_titles_identify_project_stage_and_work_without_prompt_text(self):
        config = {"name": "Vocab Blaster · Game bắn từ vựng"}
        task = {"stage": "build", "role": "project_setup", "title": "Thiết lập dự án"}
        self.assertEqual(thread_title(config, task),
                         "Dự án: Vocab Blaster · Bước lớn: Phát triển · Công việc: Thiết lập dự án · Thực hiện")
        task["title"] = "Ôn đúng tập từ sai và xem kết quả lượt ôn " * 10
        title = thread_title(config, task, review=True)
        self.assertIn("Công việc: Ôn đúng tập từ sai", title)
        self.assertIn("… · Review", title)
        self.assertLessEqual(len(title), 140)
        with patch("product_cycle.runner.prompt_for", return_value="Long operating contract"), \
                patch("product_cycle.runner.CodexClient") as factory:
            client = factory.return_value.__enter__.return_value
            client.run.side_effect = WorkflowError("Controlled interruption")
            for review in (False, True):
                with self.assertRaises(WorkflowError):
                    run_phase(self.store, self.store.task("analysis"), "fixture", self.base, review, factory)
                self.assertEqual(client.run.call_args.kwargs["title"],
                                 thread_title(self.store.config, self.store.task("analysis"), review))

    def test_exhausted_cycle_budget_does_not_start_an_attempt(self):
        config = self.store.config
        config.update(mode="live", max_cycle_tokens=30)
        write_json(self.store.root / "config.json", config)
        with patch.object(self.store, "snapshot", return_value={"tokens": 30}), \
                patch("product_cycle.runner.CodexClient") as factory:
            with self.assertRaises(WorkflowError):
                execute(self.store, "analysis", client_factory=factory)
        factory.assert_not_called()
        self.assertEqual(self.store.task("analysis")["attempts"], 0)

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

    def test_run_continues_unrelated_features_after_a_feature_blocker(self):
        plan = self.plan()
        plan["tasks"].append(dict(plan["tasks"][0], id="T2", title="Independent feature"))
        prepare_plan(self.store, plan)
        def fixture_execute(store, tid, factory):
            complete_fixture(store, tid, blocker="Need input" if tid == "T1" else None)
            if tid == "T1":
                raise WorkflowError("Need input")
        with patch("product_cycle.runner.execute", side_effect=fixture_execute):
            run_cycle(self.store, max_tasks=2)
        self.assertEqual(self.store.task("T1")["status"], "blocked")
        self.assertEqual(self.store.task("T2")["status"], "done")
        self.assertIsNone(self.store.next_task())

    def continuation_fixture(self, structured=False, active=False):
        prepare_plan(self.store)
        task = complete_fixture(self.store, "T1", blocker="Interrupted")
        aid = "T1:r1:a1:work"
        self.store.attempt_update(aid, thread_id="worker-thread", turn_id="original-turn")
        report = self.base / "project" / "follow-up.md"
        report.write_text("Observed some behavior; other criteria are still pending.")
        result = dict(task["result"], blocker=None)
        message = json.dumps(result) if structured else "Work continued. [Report](" + str(report) + ")"
        thread = {"id": "worker-thread", "cwd": str(self.store.project), "turns": [
            {"id": "original-turn", "status": "completed", "items": []},
            {"id": "follow-up-turn", "status": "inProgress" if active else "completed",
             "items": [{"type": "agentMessage", "phase": "final_answer", "text": message}]}]}
        from unittest.mock import MagicMock
        factory = MagicMock()
        factory.return_value.__enter__.return_value.read_thread.return_value = thread
        return factory, thread

    def test_plain_chat_completion_is_synced_once_without_claiming_acceptance(self):
        factory, _ = self.continuation_fixture()
        self.assertTrue(sync_task(self.store, "T1", factory)["updated"])
        self.assertFalse(sync_task(self.store, "T1", factory)["updated"])
        self.assertEqual(self.store.task("T1")["status"], "blocked")
        self.assertTrue(any(e["source"] == "follow-up.md" for e in self.store.current_evidence("T1")))
        self.assertFalse(any(e["kind"] == "browser" for e in self.store.current_evidence("T1")))
        factory.return_value.__enter__.return_value.run.assert_not_called()

    def test_sync_does_not_backfill_older_turns_as_new_progress(self):
        factory, thread = self.continuation_fixture()
        thread["turns"].insert(1, {"id": "older-turn", "status": "completed", "items": [
            {"type": "agentMessage", "text": "Outdated blocker"}]})
        self.assertTrue(sync_task(self.store, "T1", factory)["updated"])
        self.assertFalse(sync_task(self.store, "T1", factory)["updated"])
        execution = self.store.snapshot()["execution"]
        self.assertEqual(execution["continuation"]["turn_id"], "follow-up-turn")
        self.assertIn("Work continued", execution["continuation"]["message"])
        self.assertEqual(len(execution["continuation"]["reports"]), 1)
        self.assertFalse(execution["waiting_for_verification"])

    def test_latest_chat_report_uses_turn_order_not_ingestion_order(self):
        factory, _ = self.continuation_fixture()
        attempt = dict(self.store.db.execute("SELECT * FROM attempts ORDER BY rowid DESC LIMIT 1").fetchone())
        for turn_id, message in [("01a10503-0e79-7033-90ae-724e5dfb7d44", "Latest observations; touch still pending."),
                                 ("01a104fd-e758-7f42-8c85-094195241a1e", "Outdated: browser unavailable.")]:
            path = Path(attempt["directory"]) / ("continuation-" + turn_id + ".json")
            write_json(path, {"thread_id": attempt["thread_id"], "turn_id": turn_id, "phase": "work",
                              "messages": [message], "received_at": "2026-10-04T04:23:53Z"})
            self.store.record_file("T1", str(path.relative_to(self.store.project)), "Chat report", attempt_id=attempt["id"])
        continuation = self.store.snapshot()["execution"]["continuation"]
        self.assertEqual(continuation["turn_id"], "01a10503-0e79-7033-90ae-724e5dfb7d44")
        self.assertIn("touch still pending", continuation["message"])

    def test_acceptance_waiting_is_distinct_from_a_model_failure(self):
        prepare_plan(self.store)
        complete_fixture(self.store, "T1")
        complete_fixture(self.store, "verify", blocker="Còn thiếu bằng chứng nghiệm thu trình duyệt cho phiên bản hiện tại.")
        execution = self.store.snapshot()["execution"]
        self.assertTrue(execution["waiting_for_verification"])
        self.assertFalse(execution["active"])
        self.assertEqual(self.store.task("verify")["status"], "blocked")
        self.store.update("verify", reason="Model quá tải; chưa nhận được kết quả.")
        self.assertFalse(self.store.snapshot()["execution"]["waiting_for_verification"])

    def test_structured_chat_completion_becomes_reviewable_not_accepted(self):
        factory, _ = self.continuation_fixture(structured=True)
        self.assertTrue(sync_task(self.store, "T1", factory)["updated"])
        self.assertEqual(self.store.task("T1")["status"], "reviewing")
        self.assertIsNone(self.store.task("T1")["review"])
        self.assertIsNone(self.store.task("T1")["result"]["blocker"])

    def test_capacity_before_turn_start_can_resume_an_empty_existing_thread(self):
        factory, thread = self.continuation_fixture()
        self.store.attempt_update("T1:r1:a1:work", turn_id=None, status="failed")
        thread["turns"] = []
        task = self.store.task("T1")
        factory.return_value.__enter__.return_value.run.return_value = {
            "result": dict(task["result"], blocker=None), "thread_id": "worker-thread", "turn_id": "resumed-turn", "tokens": 20}
        with patch("product_cycle.runner.finish_work"):
            continue_task(self.store, "T1", factory)
        self.assertEqual(factory.return_value.__enter__.return_value.run.call_args.kwargs["thread_id"], "worker-thread")
        self.assertEqual(self.store.task("T1")["status"], "reviewing")

    def test_paused_cycle_does_not_restart_a_blocked_chat(self):
        factory, _ = self.continuation_fixture()
        self.store.pause(True)
        with self.assertRaises(WorkflowError):
            continue_task(self.store, "T1", factory)
        factory.assert_not_called()

    def test_active_or_wrong_project_chat_is_not_imported_or_restarted(self):
        factory, thread = self.continuation_fixture(active=True)
        self.assertTrue(continue_task(self.store, "T1", factory)["active"])
        execution = self.store.snapshot()["execution"]
        self.assertEqual(execution["status"], "running")
        self.assertEqual(execution["backend"], "codex-desktop")
        self.assertEqual(execution["task_id"], "T1")
        factory.return_value.__enter__.return_value.run.assert_not_called()
        thread["cwd"] = str(self.base / "other")
        with self.assertRaises(WorkflowError):
            sync_task(self.store, "T1", factory)

    def test_continue_repairs_in_existing_worker_chat_with_recorded_feedback(self):
        prepare_plan(self.store)
        task = complete_fixture(self.store, "T1", review_decision="blocked")
        work_id, review_id = "T1:r1:a1:work", "T1:r1:a1:review:1"
        self.store.attempt_update(work_id, thread_id="worker-thread", turn_id="worker-turn")
        self.store.attempt_update(review_id, thread_id="review-thread", turn_id="review-turn")
        from unittest.mock import MagicMock
        factory = MagicMock()
        client = factory.return_value.__enter__.return_value
        client.read_thread.return_value = {"id": "review-thread", "cwd": str(self.store.project),
                                          "turns": [{"id": "review-turn", "status": "completed", "items": []}]}
        client.run.return_value = {"result": task["result"], "thread_id": "worker-thread", "turn_id": "repair-turn", "tokens": 40}
        with patch("product_cycle.runner.finish_work") as finish:
            continue_task(self.store, "T1", factory)
        self.assertEqual(client.run.call_args.kwargs["thread_id"], "worker-thread")
        self.assertFalse(client.run.call_args.kwargs["readonly"])
        self.assertIsNone(client.run.call_args.kwargs["title"])
        self.assertEqual(self.store.task("T1")["attempts"], 1)
        finish.assert_called_once()
        context = json.loads((self.store.latest_directory("T1") / "context.json").read_text())
        self.assertEqual(context["feedback"]["review"]["findings"], task["review"]["findings"])

    def test_capacity_retries_same_model_without_consuming_work_attempts(self):
        config = self.store.config
        config["mode"] = "live"
        write_json(self.store.root / "config.json", config)
        with patch("product_cycle.runner.CodexClient") as factory, patch("product_cycle.runner.time.sleep") as sleep:
            client = factory.return_value.__enter__.return_value
            def unavailable(*args, **kwargs):
                factory.call_args.kwargs["on_event"]({"method": "client/threadReady", "params": {"thread_id": "capacity-thread"}})
                raise ModelCapacityError("Busy")
            client.run.side_effect = unavailable
            with self.assertRaises(ModelCapacityError):
                execute(self.store, "analysis", factory)
            self.assertEqual(client.run.call_count, 3)
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [15, 30])
            self.assertEqual({call.args[2] for call in client.run.call_args_list}, {config["models"]["analysis"]["model"]})
            self.assertEqual(client.run.call_args_list[-1].kwargs["thread_id"], "capacity-thread")
        self.assertEqual(self.store.task("analysis")["attempts"], 1)
        self.assertEqual(self.store.task("analysis")["status"], "blocked")
        retries = [e for e in self.store.snapshot()["events"] if e["type"] == "runtime.retry"]
        self.assertEqual(len(retries), 2)

    def test_continue_resumes_browser_verification_without_bypassing_acceptance(self):
        prepare_plan(self.store, self.plan(browser=True))
        complete_fixture(self.store, "T1")
        # The worker result exists but no genuine browser observation was recorded.
        aid, directory = self.store.begin("verify", "work")
        (directory / "acceptance.md").write_text("Browser evidence pending.")
        from product_cycle.contracts import work_steps
        path = str((directory / "acceptance.md").relative_to(self.store.project))
        criteria = ["C" + str(i + 1) for i in range(len(self.store.task("verify")["criteria"]))]
        result = {"summary": "Verification pending", "artifacts": [{"path": path, "purpose": "Acceptance report", "criteria": criteria, "requirements": ["R1"]}],
                  "limitations": ["No browser observations"], "blocker": None,
                  "steps": [{"id": s["id"], "summary": "Pending observation", "artifacts": [path]} for s in work_steps("verify")]}
        self.store.work_finished("verify", aid, result)
        self.store.update("verify", status="blocked")
        self.store.attempt_update(aid, thread_id="verify-thread", turn_id="verify-turn")
        from unittest.mock import MagicMock
        factory = MagicMock()
        factory.return_value.__enter__.return_value.read_thread.return_value = {
            "id": "verify-thread", "cwd": str(self.store.project), "turns": [{"id": "verify-turn", "status": "completed", "items": []}]}
        client = factory.return_value.__enter__.return_value
        client.run.return_value = {"result": result, "thread_id": "verify-thread", "turn_id": "continued-turn", "tokens": 20}
        with self.assertRaisesRegex(WorkflowError, "thiếu bằng chứng"):
            continue_task(self.store, "verify", factory)
        self.assertEqual(self.store.task("verify")["status"], "blocked")
        client.run.assert_called_once()
        self.assertEqual(client.run.call_args.kwargs["thread_id"], "verify-thread")
        self.assertIn('"browser_evidence_pending": true', client.run.call_args.args[1])
        self.assertIsNone(self.store.task("verify")["review"])
        self.assertEqual(self.store.task("handoff")["status"], "pending")

    def test_new_local_cycle_reaches_handoff_without_vps_or_remote_release(self):
        store = Store.create(self.base / "local-product", "Local product", "Local cycle")
        try:
            self.assertEqual(store.config["gates"], ["analysis", "design", "handoff"])
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

    def test_live_init_prepares_repository_without_committing_or_publishing(self):
        store = Store.create(self.base / "prepared", "Local product", "Prepared product")
        try:
            foundation = store.foundation()
            self.assertEqual(foundation["status"], "done")
            self.assertEqual(foundation["repository"]["branch"], "main")
            self.assertIsNone(foundation["repository"]["head"])
            self.assertEqual(git(store.project, "remote").stdout, "")
            self.assertEqual(len(list((store.project / ".agents/skills").glob("*/SKILL.md"))), 18)
            self.assertTrue((store.project / ".agents/skills/product-cycle-company-worker/SKILL.md").is_file())
            self.assertTrue((store.project / ".agents/skills/product-cycle-improve/SKILL.md").is_file())
            self.assertTrue((store.project / ".agents/skills/product-cycle-game-design/SKILL.md").is_file())
            for path in [".env", ".env.production", ".product-cycle/private.json"]:
                self.assertEqual(git(store.project, "check-ignore", "--no-index", path).returncode, 0)
            self.assertEqual(git(store.project, "check-ignore", "--no-index", ".env.example").returncode, 1)
            aid, directory = store.begin("analysis", "work")
            prompt = prompt_for(store, store.task("analysis"), directory)
            self.assertIn("Common development rules", prompt)
            events = store.snapshot()["events"]
            self.assertTrue(any(event["type"] == "repository.observed" and event["data"]["attempt_id"] == aid for event in events))
        finally:
            store.close()

    def test_preparation_preserves_existing_repository_and_rules(self):
        project = self.base / "existing"
        project.mkdir()
        git(project, "init", "--initial-branch=existing-branch")
        git(project, "remote", "add", "origin", "https://example.com/existing.git")
        git(project, "config", "user.name", "Existing owner")
        (project / "work.txt").write_text("Uncommitted user work")
        (project / "AGENTS.md").write_text("Existing instructions\n")
        (project / "PRODUCT_CYCLE_RULES.md").write_text("Custom common rules\n")
        frontend = project / ".agents/skills/frontend-app-builder/SKILL.md"
        frontend.parent.mkdir(parents=True)
        frontend.write_text("Custom frontend guidance\n")
        first = prepare_project(project)
        original = (project / "AGENTS.md").read_text()
        second = prepare_project(project)
        self.assertFalse(first["git_initialized"])
        self.assertEqual(repository_state(project)["branch"], "existing-branch")
        self.assertEqual(git(project, "remote", "get-url", "origin").stdout.strip(), "https://example.com/existing.git")
        self.assertEqual(git(project, "config", "user.name").stdout.strip(), "Existing owner")
        self.assertEqual((project / "work.txt").read_text(), "Uncommitted user work")
        self.assertTrue(original.startswith("Existing instructions\n"))
        self.assertEqual((project / "AGENTS.md").read_text(), original)
        self.assertEqual((project / "PRODUCT_CYCLE_RULES.md").read_text(), "Custom common rules\n")
        self.assertEqual(frontend.read_text(), "Custom frontend guidance\n")
        self.assertFalse(second["changes"])
        self.assertFalse(second["skills"]["installed"])

    def test_preparation_rejects_tracked_subproject_and_private_environment(self):
        project = self.base / "parent"
        child = project / "child"
        child.mkdir(parents=True)
        git(project, "init", "--initial-branch=main")
        (child / "source.py").write_text("print('fixture')")
        git(project, "add", "child/source.py")
        with self.assertRaises(WorkflowError):
            prepare_project(child)
        self.assertFalse((child / ".git").exists())
        (project / ".env").write_text("FIXTURE=synthetic\n")
        git(project, "add", ".env")
        with self.assertRaises(WorkflowError):
            prepare_project(project)
        self.assertEqual((project / ".env").read_text(), "FIXTURE=synthetic\n")

    def test_changed_common_rules_block_work_before_an_attempt_starts(self):
        store = Store.create(self.base / "protected", "Local product", "Protected product")
        try:
            rules = store.project / "PRODUCT_CYCLE_RULES.md"
            original = rules.read_text()
            rules.write_text("Changed rules without adoption")
            self.assertEqual(store.foundation()["status"], "blocked")
            with self.assertRaises(WorkflowError):
                store.begin("analysis", "work")
            self.assertEqual(store.task("analysis")["attempts"], 0)
            rules.write_text(original)
            self.assertEqual(store.foundation()["status"], "done")
        finally:
            store.close()

    def test_features_require_checked_project_setup_and_stable_coding_rules(self):
        store = Store.create(self.base / "foundation", "Local product", "Project foundation")
        try:
            prepare_plan(store)
            self.assertEqual(store.next_task()["id"], "project_setup")
            self.assertIn("project_setup", store.task("T1")["deps"])
            self.assertEqual(store.task("project_setup")["stage"], "build")
            self.assertEqual(store.task("project_setup")["role"], "project_setup")
            self.assertNotIn("project_setup", [stage["id"] for stage in store.snapshot()["stages"]])
            self.assertEqual(store.snapshot()["development"]["total"], 1)
            with self.assertRaises(WorkflowError):
                store.begin("T1", "work")
            complete_fixture(store, "project_setup")
            self.assertEqual(store.task("project_setup")["status"], "done")
            self.assertTrue(any(item["kind"] == "check" for item in store.current_evidence("project_setup")))
            self.assertEqual(store.next_task()["id"], "T1")
            (store.project / "CODING_RULES.md").write_text("Unreviewed convention change")
            with self.assertRaises(WorkflowError):
                store.begin("T1", "work")
        finally:
            store.close()

    def test_failed_project_setup_check_keeps_features_waiting(self):
        store = Store.create(self.base / "failed-foundation", "Local product", "Failed foundation")
        try:
            prepare_plan(store)
            with store.db:
                store.db.execute("UPDATE tasks SET checks=? WHERE id='project_setup'",
                                 (json.dumps([[sys.executable, "-c", "raise SystemExit(7)"]]),))
            with self.assertRaises(WorkflowError):
                complete_fixture(store, "project_setup")
            self.assertNotEqual(store.task("project_setup")["status"], "done")
            self.assertEqual(store.snapshot()["development"]["items"][0]["status"], "waiting")
            with self.assertRaises(WorkflowError):
                store.begin("T1", "work")
        finally:
            store.close()

    def test_missing_check_executable_is_recorded_as_failure(self):
        prepare_plan(self.store, self.plan([str(self.base / "missing-executable")]))
        with self.assertRaises(WorkflowError):
            complete_fixture(self.store, "T1")
        checks = [item for item in self.store.current_evidence("T1") if item["kind"] == "check"]
        self.assertEqual(len(checks), 1)
        report = json.loads((self.store.root / checks[0]["object_path"]).read_text())
        self.assertEqual(report["exit_code"], -1)
        self.assertNotEqual(self.store.task("T1")["status"], "done")

    def test_failed_accept_does_not_prematurely_mark_work_done(self):
        config = self.store.config
        config["gates"] = []
        write_json(self.store.root / "config.json", config)
        with patch.object(self.store, "accept", side_effect=WorkflowError("Changed output")):
            with self.assertRaises(WorkflowError):
                complete_fixture(self.store, "analysis")
        self.assertNotEqual(self.store.task("analysis")["status"], "done")

    def test_malformed_requirement_links_are_rejected_as_workflow_errors(self):
        plan = self.plan()
        plan["tasks"][0]["requirements"] = [{"id": "R1"}]
        with self.assertRaises(WorkflowError):
            validate_plan(plan, {"R1"})


if __name__ == "__main__":
    unittest.main()
