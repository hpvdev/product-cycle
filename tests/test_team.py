"""Synthetic controller/provider fixtures; these do not validate a real model."""
import json
import os
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from product_cycle.codex import ModelCapacityError
from product_cycle.contracts import WorkflowError, work_steps
from product_cycle.fixtures import complete_fixture
from product_cycle.store import Store, write_json, runner_lock
from product_cycle.team import (TeamStore, Supervisor, configure, supervisor_lock,
                                handle_tool, reconcile, run_mission, agent_for)


class SyntheticProvider:
    project = None
    threads = {}
    mode = "success"
    calls = []

    def __init__(self, directory, on_event=lambda event: None):
        self.directory, self.on_event = directory, on_event

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read_thread(self, tid):
        return self.threads[tid]

    def run(self, cwd, prompt, model, effort, schema, **options):
        tid, turn = "synthetic-" + uuid.uuid4().hex, "turn-" + uuid.uuid4().hex
        self.calls.append({"cwd": cwd, "prompt": prompt, "readonly": options["readonly"], "model": model})
        self.on_event({"method": "client/threadReady", "params": {"thread_id": tid, "observed_model": model}})
        self.on_event({"method": "client/turnStarting", "params": {"thread_id": tid}})
        self.on_event({"method": "client/turnReady", "params": {"turn_id": turn}})
        store = Store(self.project)
        run = dict(store.db.execute("SELECT * FROM team_runs WHERE directory=? AND status='running' ORDER BY rowid DESC LIMIT 1", (str(self.directory),)).fetchone())
        task = store.task(run["task_id"])
        if run["phase"] == "consult":
            result = {"summary": "Synthetic specialist advice", "findings": ["Inspect the stated acceptance criterion"], "limitations": ["Synthetic provider only"], "blocker": None}
        elif run["phase"] == "review":
            records = store.current_evidence(task["id"])
            result = {"decision": "approve", "summary": "Synthetic independent review", "findings": [],
                      "criteria": [{"id": "C" + str(i + 1), "passed": True, "evidence": [record["id"] for record in records if "C" + str(i + 1) in record["criteria"]], "reason": "Synthetic evidence checked"} for i in range(len(task["criteria"]))],
                      "steps": [{"id": step["id"], "passed": True, "evidence": [record["id"] for record in records if record["source"] in step["artifacts"]], "reason": "Synthetic step checked"} for step in task["result"]["steps"]]}
        else:
            files = ["analysis.md", "requirements.json"] if task["stage"] == "analysis" else ["increment.md"] if task["stage"] == "build" else ["design.md", "design-baseline.json"]
            if task["stage"] == "build":
                source = store.project / "synthetic_source.py"
                source.write_text("# Synthetic provider output, not model-generated product code\nvalue = 1\n")
            artifacts = []
            for filename in files:
                path = self.directory / filename
                if filename == "requirements.json":
                    write_json(path, {"requirements": [{"id": "R1", "description": "Read saved data", "acceptance": ["Read returns saved value"]}]})
                elif filename == "design-baseline.json":
                    write_json(path, {"has_ui": False, "visual_reference": None, "version": "1", "screens": [], "flows": ["Read data"], "states": ["Success"], "rules": {"interaction": "Synthetic only"}, "acceptance": ["Data read"]})
                else:
                    path.write_text("# Synthetic stage output\nThis checks the controller only.\n")
                artifacts.append({"path": str(path.relative_to(store.project)), "purpose": "Synthetic output", "criteria": ["C" + str(i + 1) for i in range(len(task["criteria"]))], "requirements": task["requirements"]})
            result = {"summary": "Synthetic work", "artifacts": artifacts, "steps": [{"id": step["id"], "summary": "Synthetic step output", "artifacts": [item["path"] for item in artifacts]} for step in work_steps(task["role"])], "limitations": ["No real model validation"], "blocker": None}
        store.close()
        self.threads[tid] = {"id": tid, "cwd": str(cwd), "usage_total": 11,
                             "turns": [{"id": turn, "status": "completed", "items": [{"type": "agentMessage", "text": json.dumps(result)}]}]}
        if self.mode == "lost":
            raise WorkflowError("Synthetic lost transport response")
        self.on_event({"method": "turn/completed", "params": {"threadId": tid, "turn": {"id": turn, "status": "failed" if self.mode == "capacity" else "completed"}}})
        if self.mode == "capacity":
            raise ModelCapacityError("Synthetic capacity rejection")
        self.on_event({"method": "thread/tokenUsage/updated", "params": {"threadId": tid, "turnId": turn, "tokenUsage": {"total": {"totalTokens": 11}}}})
        return {"thread_id": tid, "turn_id": turn, "tokens": 11, "result": result}


class TeamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"PRODUCT_CYCLE_HOME": str(base / "state")})
        self.env.start()
        self.store = Store.create(base / "project", "Synthetic team facts", "Team test", mode="demo", team=True)
        self.team = TeamStore(self.store)
        SyntheticProvider.project = self.store.project
        SyntheticProvider.mode, SyntheticProvider.threads, SyntheticProvider.calls = "success", {}, []

    def tearDown(self):
        self.store.close()
        self.env.stop()
        self.temp.cleanup()

    def live_fixture(self):
        write_json(self.store.root / "config.json", dict(self.store.config, mode="live"))

    def test_tick_defers_contended_runner_lock_without_cancelling_owned_turn(self):
        from concurrent.futures import Future
        self.live_fixture()
        supervisor = Supervisor(self.store, client_factory=SyntheticProvider)
        owned = Future()
        supervisor.futures['owned-running-turn'] = owned
        try:
            with runner_lock(self.store):
                self.assertTrue(supervisor.tick())
            self.assertFalse(supervisor.cancel.is_set())
            self.assertFalse(owned.cancelled())
            self.assertIs(supervisor.futures['owned-running-turn'], owned)
            self.assertEqual(SyntheticProvider.calls, [])
            self.assertEqual(self.store.task('analysis')['attempts'], 0)
        finally:
            supervisor.pool.shutdown(wait=True)

    def test_once_ignores_stale_consultation_but_drains_current_request(self):
        self.live_fixture()
        old = self.mission()
        stale = self.team.request(old, 'consult', 'analysis', 'old-question',
                                  'product_manager', 'Synthetic old revision advice')
        self.team.update(old['id'], status='completed')
        self.store.attempt_update(old['attempt_id'], status='completed')
        self.store.update('analysis', status='blocked')
        self.store.reopen('analysis', 'Synthetic revision change after terminal mission')
        current = self.mission()
        self.team.update(current['id'], status='completed')
        self.store.attempt_update(current['attempt_id'], status='completed')
        self.store.update('analysis', status='blocked')

        def run_once():
            supervisor = Supervisor(self.store, SyntheticProvider)
            original_tick = supervisor.tick
            calls = []

            def tick(allow_work=True):
                calls.append(allow_work)
                # The mission is already terminal at the first drain boundary.
                if len(calls) == 1:
                    return True
                if len(calls) > 30:
                    self.fail('once drain kept waiting for an undispatchable request')
                return original_tick(allow_work=allow_work)

            with patch.object(supervisor, 'tick', side_effect=tick):
                supervisor.run(once=True)
            return calls

        self.assertEqual(run_once(), [True])
        self.assertEqual(SyntheticProvider.calls, [])
        pending = self.team.request(current, 'consult', 'analysis', 'current-question',
                                    'product_manager', 'Synthetic current revision advice')
        calls = run_once()
        self.assertIn(False, calls)
        self.assertEqual(len(SyntheticProvider.calls), 1)
        self.assertTrue(SyntheticProvider.calls[0]['readonly'])
        self.assertEqual(self.store.db.execute('SELECT status FROM team_requests WHERE id=?',
                                              (pending['id'],)).fetchone()[0], 'completed')
        self.assertEqual(self.store.db.execute('SELECT status FROM team_requests WHERE id=?',
                                              (stale['id'],)).fetchone()[0], 'queued')

    def mission(self, agent="analysis", tid="analysis", phase="work", attempt=None):
        if attempt is None and phase != "consult":
            attempt, directory = self.store.begin(tid, phase)
        else:
            directory = None
        run = self.team.create_run(tid, phase, attempt, directory, agent)
        self.team.update(run["id"], status="running", thread_id="thread-" + run["id"], turn_id="turn-" + run["id"])
        return self.team.run(run["id"])

    def test_new_team_gates_and_existing_policy_are_distinct(self):
        self.assertEqual(self.store.config["gates"], ["analysis", "design", "handoff"])
        config = self.store.config
        config["gates"], config["task_gates"] = ["architecture"], ["checkpoint"]
        config["team"] = {"enabled": False}
        write_json(self.store.root / "config.json", config)
        configure(self.store)
        self.assertEqual(self.store.config["gates"], ["architecture"])
        self.assertTrue(self.store.owner_gate({"stage": "build", "id": "checkpoint"}))
        self.assertFalse(self.store.config["team"]["autonomous_checkpoint"])

    def test_context_keeps_authority_and_peer_ids_without_repeating_missions(self):
        self.store.owner_input("analysis", "Synthetic operator", "Current delegated scope, not human research")
        run = self.mission()
        packet = handle_tool(self.team, run["id"], {"tool": "team_context", "arguments": {},
                            "threadId": run["thread_id"], "turnId": run["turn_id"]})
        self.assertEqual(packet["context"]["task"]["criteria"], self.store.task("analysis")["criteria"])
        self.assertEqual(packet["context"]["owner_inputs"][0]["note"], "Current delegated scope, not human research")
        self.assertNotIn("instructions", packet["context"]["task"])
        self.assertNotIn("models", packet["context"]["policy"])
        self.assertEqual({a["id"] for a in packet["agents"]}, {a["id"] for a in self.team.roster()})
        self.assertTrue(all("mission" not in a and "stages" in a for a in packet["agents"]))
        self.assertEqual(Path(packet["mission_context_path"]), Path(run["directory"]) / "context.json")

    def test_message_transport_dedup_and_authenticated_ack(self):
        sender = self.mission()
        receiver = self.mission("ux_researcher", phase="consult", attempt=sender["attempt_id"])
        message = self.team.send_message(sender["id"], "ux_researcher", "Synthetic peer advice", "one")
        self.assertEqual(self.team.send_message(sender["id"], "ux_researcher", "Synthetic peer advice", "one")["id"], message["id"])
        with self.assertRaises(WorkflowError):
            self.team.send_message(sender["id"], "ux_researcher", "Different", "one")
        params = {"tool": "team_poll_messages", "arguments": {}, "threadId": receiver["thread_id"], "turnId": receiver["turn_id"], "callId": "poll-1"}
        self.assertEqual(handle_tool(self.team, receiver["id"], params)["messages"][0]["status"], "queued")
        self.assertEqual(self.team.page("team_messages")["items"][0]["status"], "delivering")
        self.team.delivered(receiver, "wrong-call")
        self.assertEqual(self.team.page("team_messages")["items"][0]["status"], "delivering")
        self.team.delivered(receiver, "poll-1")
        params.update(tool="team_ack_message", arguments={"message_id": message["id"]})
        self.assertTrue(handle_tool(self.team, receiver["id"], params)["acknowledged"])
        params["turnId"] = "forged"
        with self.assertRaises(WorkflowError):
            handle_tool(self.team, receiver["id"], params)
        with self.assertRaises(WorkflowError):
            self.team.send_message(sender["id"], "analysis_reviewer", "Bias review", "two")

    def test_one_writer_and_source_review_exclusion(self):
        self.store.add_task("source-a", "build", "Synthetic source", "Test", [], ["Criterion"], [], [])
        self.store.add_task("source-b", "build", "Synthetic source", "Test", [], ["Criterion"], [], [])
        writer = self.team.create_run("source-a", "work")
        self.assertEqual(Path(writer["cwd"]), self.store.project)
        with self.assertRaises(WorkflowError):
            self.team.create_run("source-b", "work")
        with self.assertRaises(WorkflowError):
            self.team.create_run("source-b", "review")
        consultant = self.team.create_run("source-a", "consult", agent_id="backend")
        self.assertEqual(Path(consultant["cwd"]), Path(consultant["directory"]))

    def test_usage_counts_consultations_once_and_missing_threads_remain_unknown(self):
        run = self.mission()
        peer = self.mission("product_manager", phase="consult", attempt=run["attempt_id"])
        self.team.usage(run, 20)
        self.team.usage(run, 19)
        self.team.usage(peer, 5)
        self.assertEqual(self.store.snapshot()["tokens"], 25)
        self.assertEqual(self.team.snapshot()["tokens"], 25)
        self.team.update(peer["id"], tokens=None, thread_id=None)
        self.assertFalse(self.team.snapshot()["token_tracking_complete"])

    def test_parallel_usage_keeps_attempt_and_journal_totals_consistent(self):
        run = self.mission()
        peer = self.mission("product_manager", phase="consult", attempt=run["attempt_id"])
        first_ready, second_ready, start = threading.Event(), threading.Event(), threading.Event()
        aggregate_pending, second_completed = threading.Event(), threading.Event()
        errors = []

        def record(mission, value, first):
            store = Store(self.store.project)
            try:
                if first:
                    def observe_sql(sql):
                        if sql.startswith("UPDATE attempts SET tokens="):
                            aggregate_pending.set()
                            # In the old split transactions the second observation
                            # completes here and the first overwrites it afterward.
                            second_completed.wait(.2)
                    store.db.set_trace_callback(observe_sql)
                (first_ready if first else second_ready).set()
                if not start.wait(3) or not first and not aggregate_pending.wait(3):
                    raise AssertionError("Synthetic accounting interleave did not start")
                TeamStore(store).usage(mission, value)
                if not first:
                    second_completed.set()
            except BaseException as exc:
                errors.append(exc)
            finally:
                store.close()

        threads = [threading.Thread(target=record, args=(run, 10, True)),
                   threading.Thread(target=record, args=(peer, 20, False))]
        for thread in threads:
            thread.start()
        self.assertTrue(first_ready.wait(3) and second_ready.wait(3))
        start.set()
        for thread in threads:
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertTrue(aggregate_pending.is_set() and second_completed.is_set())
        self.assertEqual(self.team.snapshot()["tokens"], 30)
        self.assertEqual(self.store.snapshot()["tokens"], 30)
        self.assertEqual(self.store.db.execute("SELECT tokens FROM attempts WHERE id=?", (run["attempt_id"],)).fetchone()[0], 30)

    def test_live_mission_remains_visible_beyond_bounded_history(self):
        run = self.mission()
        self.team.update(run["id"], status="unknown")
        for _ in range(100):
            history = self.team.create_run("analysis", "consult", agent_id="product_manager")
            self.team.update(history["id"], status="completed")
        snapshot = self.team.snapshot()
        agent = next(agent for agent in snapshot["agents"] if agent["id"] == "analysis")
        self.assertEqual(agent["status"], "unknown")
        self.assertEqual(agent["current_run_id"], run["id"])
        self.assertIn(run["id"], {item["id"] for item in snapshot["runs"]})

    def test_supervisor_lock_is_exclusive_and_liveness_is_not_a_stale_row(self):
        with supervisor_lock(self.store):
            with self.assertRaises(WorkflowError), supervisor_lock(self.store):
                pass
            self.assertTrue(self.team.snapshot()["supervisor"]["active"])
        self.assertFalse(self.team.snapshot()["supervisor"]["active"])

    def test_real_dispatch_fresh_review_and_owner_gate(self):
        self.live_fixture()
        Supervisor(self.store, SyntheticProvider).run(once=True)
        self.assertEqual(self.store.task("analysis")["status"], "reviewing")
        work_run = next(run for run in self.team.snapshot()["runs"] if run["phase"] == "work")
        self.assertEqual(next(call for call in SyntheticProvider.calls if not call["readonly"])["cwd"], Path(work_run["directory"]))
        Supervisor(self.store, SyntheticProvider).run(once=True)
        self.assertEqual(self.store.task("analysis")["status"], "awaiting_approval")
        runs = self.team.snapshot()["runs"]
        self.assertEqual(runs[0]["agent_id"], "analysis_reviewer")
        self.assertNotEqual(runs[0]["thread_id"], runs[1]["thread_id"])
        self.assertTrue(SyntheticProvider.calls[-1]["readonly"])

    def test_preflight_consultation_at_capacity_one_delivers_actual_result(self):
        complete_fixture(self.store, "analysis")
        config = self.store.config
        config["team"]["max_concurrent"] = 1
        config["mode"] = "live"
        write_json(self.store.root / "config.json", config)
        Supervisor(self.store, SyntheticProvider).run(once=True)
        self.assertEqual(self.store.task("design")["status"], "reviewing")
        self.assertEqual(len(SyntheticProvider.calls), 3)
        self.assertTrue(SyntheticProvider.calls[0]["readonly"])
        self.assertIn("Synthetic specialist advice", SyntheticProvider.calls[-1]["prompt"])
        self.assertEqual(self.team.page("team_messages")["items"][0]["status"], "delivered")

    def test_capacity_retry_preserves_product_attempt(self):
        self.live_fixture()
        SyntheticProvider.mode = "capacity"
        Supervisor(self.store, SyntheticProvider).run(once=True)
        run = self.team.snapshot()["runs"][0]
        self.assertEqual(run["status"], "backoff")
        self.assertEqual(self.store.task("analysis")["attempts"], 1)
        self.team.update(run["id"], retry_at=0)
        SyntheticProvider.mode = "success"
        Supervisor(self.store, SyntheticProvider).run(once=True)
        self.assertEqual(self.store.task("analysis")["attempts"], 1)
        self.assertEqual(self.store.task("analysis")["status"], "reviewing")

    def test_restart_imports_known_completion_once_without_new_turn(self):
        aid, directory = self.store.begin("analysis", "work")
        run = self.team.create_run("analysis", "work", aid, directory)
        SyntheticProvider.mode = "lost"
        run_mission(self.store.project, run["id"], SyntheticProvider, threading.Event())
        self.assertEqual(self.team.run(run["id"])["status"], "unknown")
        reconcile(self.team, SyntheticProvider)
        self.assertEqual(self.team.run(run["id"])["status"], "completed")
        count = len(self.store.current_evidence("analysis"))
        reconcile(self.team, SyntheticProvider)
        self.assertEqual(len(self.store.current_evidence("analysis")), count)
        self.assertEqual(len(SyntheticProvider.calls), 1)

    def test_periodic_reconcile_observes_later_completion_without_restart(self):
        self.live_fixture()
        aid, directory = self.store.begin("analysis", "work")
        run = self.team.create_run("analysis", "work", aid, directory)
        SyntheticProvider.mode = "lost"
        run_mission(self.store.project, run["id"], SyntheticProvider, threading.Event())
        tid = self.team.run(run["id"])["thread_id"]
        SyntheticProvider.threads[tid]["turns"][0]["status"] = "inProgress"
        supervisor = Supervisor(self.store, SyntheticProvider)
        try:
            supervisor.tick(allow_work=False)
            self.assertEqual(self.team.run(run["id"])["status"], "unknown")
            SyntheticProvider.threads[tid]["turns"][0]["status"] = "completed"
            supervisor.next_reconcile = 0
            supervisor.tick(allow_work=False)
            self.assertEqual(self.team.run(run["id"])["status"], "completed")
            self.assertEqual(len(SyntheticProvider.calls), 1)
        finally:
            supervisor.pool.shutdown()

    def test_unknown_without_thread_blocks_duplicate_but_not_independent_task(self):
        run = self.team.create_run("analysis", "work")
        reconcile(self.team, SyntheticProvider)
        self.assertEqual(self.team.run(run["id"])["status"], "unknown")
        self.store.add_task("independent", "verify", "Independent", "Test", [], ["Criterion"], [], [])
        self.live_fixture()
        supervisor = Supervisor(self.store, SyntheticProvider)
        try:
            self.assertEqual([task["id"] for task, _ in supervisor.eligible()], ["independent"])
        finally:
            supervisor.pool.shutdown()
        self.assertEqual(agent_for({"stage": "build", "role": "build"}, "review"), "build_reviewer")

    def test_assigned_engineer_really_dispatches_as_writer_and_reviewer_cannot(self):
        self.store.update("analysis", status="blocked", reason="Synthetic isolation")
        self.store.add_task("web-increment", "build", "Synthetic web increment", "Implement synthetic source", [], ["Output exists"], [], [])
        config = self.store.config
        config["team"].update(build_agent="frontend", task_agents={"web-increment": "build_reviewer"})
        write_json(self.store.root / "config.json", config)
        with self.assertRaises(WorkflowError):
            self.team.create_run("web-increment", "work")
        config["team"]["task_agents"]["web-increment"] = "frontend"
        config["mode"] = "live"
        write_json(self.store.root / "config.json", config)
        Supervisor(self.store, SyntheticProvider).run(once=True)
        run = next(run for run in self.team.snapshot()["runs"] if run["phase"] == "work")
        self.assertEqual(run["agent_id"], "frontend")
        self.assertTrue(run["source_writer"])
        self.assertEqual(Path(run["cwd"]), self.store.project)
        self.assertTrue((self.store.project / "synthetic_source.py").is_file())
        self.assertEqual(self.store.task("web-increment")["status"], "reviewing")
        self.assertFalse(SyntheticProvider.calls[-1]["readonly"])
        configure(self.store, active=False)
        configure(self.store, active=True)
        self.assertEqual(self.store.config["team"]["task_agents"], {"web-increment": "frontend"})


if __name__ == "__main__":
    unittest.main()
