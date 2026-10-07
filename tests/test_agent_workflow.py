"""Controller mechanics only; synthetic cases do not prove product quality."""

import copy
import json
import os
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from product_cycle.authority import policy_packet, upgrade
from product_cycle.contracts import WorkflowError
from product_cycle.features import validate_feature_map, validate_verification, validate_feature_plan, task_features
from product_cycle.store import Store, write_json
from product_cycle.context_packs import build_pack, validate_pack
from product_cycle.dispatch import route
from product_cycle.workspaces import prepare, integrate, mark_reviewed, reconcile, inventory, record
from product_cycle.fixtures import complete_fixture, prepare_plan


def verification_contract():
    return {
        "version": 1, "surface": "cli",
        "environment": {"runtime": "local-python", "requirements": [], "instance_policy": "isolated"},
        "launch": {"commands": [], "instructions": "Run the CLI for each scenario.", "ready": "Process starts."},
        "doctor": {"commands": [], "instructions": "Inspect executable and source version.", "read_only": True},
        "cleanup": {"commands": [], "instructions": "CLI exits; retain logs.", "preserve_evidence": True},
        "procedures": [{"id": "calculate", "actions": ["Enter 2+3"], "expected": ["Result is 5"],
                        "evidence": ["CLI transcript"], "commands": []}],
    }


def feature_map():
    return {"version": 1, "features": [{"id": "calculator", "name": "Calculate", "purpose": "Calculate a sum",
            "requirements": ["R1"], "depends_on": [], "screen_states": [], "code_entry_points": [],
            "implementation_status": "planned", "verification": ["calculate"]}]}


class AgentWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"PRODUCT_CYCLE_HOME": str(self.base / "state")})
        self.env.start()
        self.store = Store.create(self.base / "product", "Synthetic brief", "Synthetic", mode="demo")

    def tearDown(self):
        self.store.close()
        self.env.stop()
        self.temp.cleanup()

    def test_authority_packet_preserves_mode_gates_scope_and_budgets(self):
        task = self.store.task("analysis")
        self.assertEqual(policy_packet(self.store, task)["gate"]["authority"], "owner")
        config = self.store.config
        config.update(gates=[], max_attempts=3, team={"enabled": True, "policy": "autonomous", "autonomous_checkpoint": True})
        write_json(self.store.root / "config.json", config)
        packet = policy_packet(self.store, task)
        self.assertEqual(packet["mode"], "autonomous")
        self.assertFalse(packet["gate"]["required"])
        self.assertEqual(packet["scope"]["criteria"], task["criteria"])
        self.assertEqual(packet["budgets"]["max_attempts"], 3)
        self.assertTrue(packet["independent_review_required"])

    def test_upgrade_is_explicit_and_preserves_history_and_policy(self):
        original = self.store.config
        history = self.store.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        self.assertFalse(upgrade(self.store)["applied"])
        self.assertEqual(self.store.config, original)
        report = upgrade(self.store, True)
        self.assertTrue(report["applied"])
        self.assertEqual(self.store.task("feature_map")["deps"], ["architecture"])
        self.assertEqual(self.store.task("plan")["deps"], ["feature_map"])
        self.assertEqual(self.store.config["gates"], original["gates"])
        self.assertEqual(self.store.config["models"]["build"], original["models"]["build"])
        self.assertGreater(self.store.db.execute("SELECT COUNT(*) FROM events").fetchone()[0], history)
        self.assertFalse(upgrade(self.store, True)["applied"])

    def test_interrupted_upgrade_replays_config_without_incrementing_revisions_twice(self):
        with patch("product_cycle.store.write_json", side_effect=OSError("Synthetic config interruption")):
            with self.assertRaises(OSError):
                upgrade(self.store, True)
        revision = self.store.task("architecture")["revision"]
        self.assertTrue(upgrade(self.store)["recovery_required"])
        with self.assertRaises(WorkflowError):
            self.store.begin("analysis", "work")
        self.assertTrue(upgrade(self.store, True)["applied"])
        self.assertEqual(self.store.task("architecture")["revision"], revision)
        self.assertEqual(self.store.config["agent_workflow_version"], 1)

    def test_legacy_progress_does_not_add_unrun_agent_workflow_stages(self):
        self.assertNotIn("feature_map", {stage["id"] for stage in self.store.snapshot()["stages"]})
        self.assertNotIn("integration", {stage["id"] for stage in self.store.snapshot()["stages"]})
        upgrade(self.store, True)
        self.assertIn("feature_map", {stage["id"] for stage in self.store.snapshot()["stages"]})

    def test_upgrade_refuses_active_attempt(self):
        self.store.begin("analysis", "work")
        with self.assertRaises(WorkflowError):
            upgrade(self.store, True)
        self.assertEqual(self.store.config["agent_workflow_version"], 0)

    def test_feature_map_and_verification_are_observable_and_linked(self):
        verification = validate_verification(verification_contract())
        value = feature_map()
        validate_feature_map(value, {"R1"}, {"screens": []}, verification)
        for field, invalid in (("verification", ["missing"]), ("requirements", ["R2"]),
                               ("implementation_status", "observed"), ("depends_on", ["calculator"])):
            changed = copy.deepcopy(value)
            changed["features"][0][field] = invalid
            with self.subTest(field=field), self.assertRaises(WorkflowError):
                validate_feature_map(changed, {"R1"}, {"screens": []}, verification)
        contract = verification_contract()
        contract["cleanup"]["preserve_evidence"] = False
        with self.assertRaises(WorkflowError):
            validate_verification(contract)

    def test_feature_plan_cannot_skip_or_invent_features(self):
        plan = {"tasks": [{"features": ["calculator"], "requirements": ["R1"]}]}
        validate_feature_plan(plan, feature_map())
        for features in ([], ["unknown"], ["calculator", "calculator"]):
            plan["tasks"][0]["features"] = features
            with self.assertRaises(WorkflowError):
                validate_feature_plan(plan, feature_map())

    def test_context_pins_authority_and_retains_original_evidence(self):
        complete_fixture(self.store, "analysis")
        task = self.store.task("design")
        directory = self.store.project / ".product-cycle" / "context"
        directory.mkdir()
        pack = build_pack(self.store, task, "builder", directory)
        self.assertEqual(pack["authority"]["scope"]["criteria"], task["criteria"])
        self.assertTrue(pack["accepted_inputs"])
        self.assertTrue(all(Path(item["path"]).is_file() and item["sha256"] for item in pack["accepted_inputs"]))
        self.assertTrue((directory / ("context-pack-" + pack["sha256"] + ".json")).is_file())
        changed = dict(task, revision=task["revision"] + 1)
        self.assertNotEqual(build_pack(self.store, changed, "builder", directory)["sha256"], pack["sha256"])

    def test_feature_dependencies_require_transitive_task_providers(self):
        value = feature_map()
        prerequisite = copy.deepcopy(value["features"][0])
        prerequisite["id"] = "input"
        value["features"][0]["depends_on"] = ["input"]
        value["features"].append(prerequisite)
        plan = {"tasks": [{"id": "A", "features": ["calculator"], "requirements": ["R1"], "depends_on": []},
                          {"id": "B", "features": ["input"], "requirements": ["R1"], "depends_on": []}]}
        with self.assertRaises(WorkflowError):
            validate_feature_plan(plan, value)
        plan["tasks"][0]["depends_on"] = ["B"]
        validate_feature_plan(plan, value)
        plan["tasks"].append({"id": "C", "features": ["input"], "requirements": ["R1"], "depends_on": ["B"]})
        with self.assertRaises(WorkflowError):
            validate_feature_plan(plan, value)
        plan["tasks"][0]["depends_on"] = ["C"]
        validate_feature_plan(plan, value)
        validate_feature_plan({"tasks": [{"id": "combined", "features": ["input", "calculator"],
                                         "requirements": ["R1"], "depends_on": []}]}, value)

    def test_context_requires_current_owner_decisions_and_accepted_inputs(self):
        directory = self.store.project / ".product-cycle" / "context"
        directory.mkdir()
        build_pack(self.store, self.store.task("analysis"), "builder", directory)
        self.store.owner_input("analysis", "Owner", "New scope within the same revision")
        with self.assertRaises(WorkflowError):
            validate_pack(self.store, self.store.task("analysis"), directory)
        build_pack(self.store, self.store.task("analysis"), "builder", directory)
        validate_pack(self.store, self.store.task("analysis"), directory)
        complete_fixture(self.store, "analysis")
        build_pack(self.store, self.store.task("design"), "builder", directory)
        self.store.update("analysis", revision=2, status="stale")
        with self.assertRaises(WorkflowError):
            validate_pack(self.store, self.store.task("design"), directory)

    def test_context_hash_pins_assigned_feature_procedures(self):
        upgrade(self.store, True)
        prepare_plan(self.store)
        _, directory = self.store.begin("T1", "work")
        pack = build_pack(self.store, self.store.task("T1"), "builder", directory)
        self.assertEqual(pack["feature_scope"][0]["id"], "synthetic")
        self.assertEqual(pack["feature_scope"][0]["verification"], self.store.sealed_document("feature_map", "feature-map.json")["features"][0]["verification"])
        plan = self.store.approved_plan()
        plan["tasks"][0]["feature_verification"] = {"synthetic": ["changed-procedure"]}
        with patch.object(self.store, "approved_plan", return_value=plan), self.assertRaises(WorkflowError):
            validate_pack(self.store, self.store.task("T1"), directory)

    def test_context_includes_bounded_source_graph_and_test_navigation(self):
        root = self.store.project
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src/model.py").write_text("class Record:\n    pass\n")
        (root / "src/calc.py").write_text("from .model import Record\ndef calculate():\n    return Record()\n")
        (root / "tests/test_calc.py").write_text("from src.calc import calculate\ndef test_calculate():\n    assert calculate() is not None\n")
        (root / "src/model.ts").write_text("export const value = 1;\n")
        (root / "src/view.ts").write_text("import {value} from './model';\n")
        private = root / ".agents/skills/private"
        private.mkdir(parents=True)
        (private / "tool.py").write_text("private = True\n")
        directory = root / ".product-cycle/context"
        directory.mkdir()
        pack = build_pack(self.store, self.store.task("analysis"), "builder", directory)
        index = pack["source_context"]
        edges = {(edge["from"], edge["to"]): edge["basis"] for edge in index["dependency_graph"]}
        self.assertEqual(edges[("src/calc.py", "src/model.py")], "python_ast")
        self.assertEqual(edges[("src/view.ts", "src/model.ts")], "import_regex_hint")
        self.assertEqual(index["tests"][0]["path"], "tests/test_calc.py")
        self.assertNotIn(".agents/skills/private/tool.py", {node["path"] for node in index["selected_files"]})
        self.assertTrue(all(Path(node["original_path"]).is_file() for node in index["selected_files"]))
        self.assertIn("bounded", index["limitations"][-1])

    def test_repair_pack_pins_feedback_after_begin_clears_task(self):
        self.store.update("analysis", status="rework", reason="Failed observed behavior", review={"findings": ["Repair scope"]})
        _, directory = self.store.begin("analysis", "work")
        task = self.store.task("analysis")
        self.assertIsNone(task["reason"])
        pack = build_pack(self.store, task, "fix", directory)
        self.assertEqual(pack["repair"]["reason"], "Failed observed behavior")
        self.assertEqual(pack["repair"]["review"]["findings"], ["Repair scope"])

    def test_interrupted_preparation_resumes_proven_baseline_and_preserves_unknown_edits(self):
        self._workspace_tasks()
        from product_cycle.workspaces import _copy
        count = 0
        def interrupted(*args):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("Synthetic copy interruption")
            _copy(*args)
        with patch("product_cycle.workspaces._copy", side_effect=interrupted):
            with self.assertRaises(OSError):
                prepare(self.store, self.store.task("T1"))
        self.assertEqual(record(self.store, self.store.task("T1"))["status"], "creating")
        self.assertIn("T1", reconcile(self.store))
        root = prepare(self.store, self.store.task("T1"))
        self.assertEqual(inventory(root), inventory(self.store.project))
        with patch("product_cycle.workspaces._copy", side_effect=OSError("Synthetic interruption")):
            with self.assertRaises(OSError):
                prepare(self.store, self.store.task("T2"))
        second = Path(record(self.store, self.store.task("T2"))["root"])
        (second / "unrecorded.txt").write_text("Preserve this change")
        with self.assertRaises(WorkflowError):
            prepare(self.store, self.store.task("T2"))
        self.assertEqual((second / "unrecorded.txt").read_text(), "Preserve this change")

    def test_detached_git_preparation_preserves_dirty_baseline_after_interruption(self):
        self._workspace_tasks()
        def git(*args):
            return subprocess.run(["git", *args], cwd=self.store.project, check=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        git("init")
        git("add", "a.txt", "b.txt")
        git("-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid", "commit", "-m", "Synthetic fixture")
        (self.store.project / "a.txt").write_text("Uncommitted canonical version")
        (self.store.project / "b.txt").unlink()
        (self.store.project / "untracked.txt").write_text("Untracked canonical version")
        with patch("product_cycle.workspaces._copy", side_effect=OSError("Synthetic interruption")):
            with self.assertRaises(OSError):
                prepare(self.store, self.store.task("T1"))
        self.assertIn("T1", reconcile(self.store))
        row = record(self.store, self.store.task("T1"))
        self.assertEqual(row["kind"], "git-worktree")
        root = Path(row["root"])
        self.assertEqual(inventory(root), inventory(self.store.project))
        self.assertEqual((root / "a.txt").read_text(), "Uncommitted canonical version")
        self.assertFalse((root / "b.txt").exists())
        self.assertNotEqual(subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=root).returncode, 0)

    def test_authenticated_context_refresh_delivers_new_decisions_without_approval(self):
        complete_fixture(self.store, "analysis")
        config = self.store.config
        config["agent_workflow_version"] = 1
        write_json(self.store.root / "config.json", config)
        from product_cycle.team import TeamStore, handle_tool
        team = TeamStore(self.store)
        aid, directory = self.store.begin("design", "work")
        build_pack(self.store, self.store.task("design"), "builder", directory)
        run = team.create_run("design", "work", aid, directory)
        team.update(run["id"], status="running", thread_id="synthetic-thread", turn_id="synthetic-turn")
        self.store.owner_input("design", "Owner", "Keep the office background")
        with self.assertRaises(WorkflowError):
            validate_pack(self.store, self.store.task("design"), directory)
        packet = handle_tool(team, run["id"], {"tool": "team_context", "arguments": {},
                    "threadId": "synthetic-thread", "turnId": "synthetic-turn"})
        self.assertEqual(packet["context"]["context_pack"]["authority"]["decisions"][-1]["note"], "Keep the office background")
        validate_pack(self.store, self.store.task("design"), directory)
        self.assertEqual(self.store.task("design")["status"], "running")
        self.assertTrue(self.store.owner_gate(self.store.task("design")))

    def test_feature_verification_can_be_split_without_omitting_final_coverage(self):
        value = feature_map()
        value["features"][0]["verification"] = ["input", "calculate"]
        plan = {"tasks": [{"id": "T1", "features": ["calculator"], "requirements": ["R1"], "depends_on": [],
                           "feature_verification": {"calculator": ["input"]}},
                          {"id": "T2", "features": ["calculator"], "requirements": ["R1"], "depends_on": ["T1"],
                           "feature_verification": {"calculator": ["calculate"]}}]}
        validate_feature_plan(plan, value)
        plan["tasks"][1]["feature_verification"]["calculator"] = ["input"]
        with self.assertRaises(WorkflowError):
            validate_feature_plan(plan, value)

    def test_confirmed_feature_map_flows_into_later_context_with_provenance(self):
        upgrade(self.store, True)
        prepare_plan(self.store)
        complete_fixture(self.store, "T1")
        complete_fixture(self.store, "integrate-T1")
        feature = task_features(self.store, self.store.task("verify"))[0]
        self.assertEqual(feature["implementation_status"], "observed")
        self.assertIn("synthetic.py", feature["code_entry_points"])
        self.assertTrue(feature["observations"][0]["is_source_current"])
        self.assertTrue(Path(feature["observations"][0]["path"]).is_file())
        self.assertEqual(self.store.sealed_document("feature_map", "feature-map.json")["features"][0]["implementation_status"], "planned")
        (self.store.project / "synthetic.py").write_text("# Later changed version")
        self.assertFalse(task_features(self.store, self.store.task("verify"))[0]["observations"][0]["is_source_current"])

    def test_runtime_instance_reservation_survives_unknown_and_releases_on_terminal(self):
        upgrade(self.store, True)
        config = self.store.config
        config["workspace_mode"] = "isolated"
        write_json(self.store.root / "config.json", config)
        prepare_plan(self.store)
        from product_cycle.team import TeamStore
        team = TeamStore(self.store)
        contract = self.store.sealed_document("architecture", "verification.json")
        contract["environment"]["instance_policy"] = "exclusive"
        # Supply a synthetic sealed contract for admission; no product is launched.
        original = self.store.sealed_document
        def sealed(tid, name):
            return contract if name == "verification.json" else original(tid, name)
        with patch.object(self.store, "sealed_document", side_effect=sealed):
            first = team.create_run("T1", "work")
            self.assertIsNotNone(first["resource_key"])
            team.update(first["id"], status="unknown")
            with self.assertRaises(WorkflowError):
                team.create_run("T1", "review")
            team.update(first["id"], status="completed")
            reviewer = team.create_run("T1", "review")
            self.assertEqual(reviewer["resource_key"], first["resource_key"])

    def test_scheduler_contains_missing_exclusive_capability_and_dispatches_independent_workspace(self):
        upgrade(self.store, True)
        config = self.store.config
        config.update(workspace_mode="isolated")
        config["team"] = {"enabled": True, "policy": "autonomous", "max_concurrent": 3, "autonomous_checkpoint": True}
        write_json(self.store.root / "config.json", config)
        tasks = [{"id": tid, "title": tid, "instructions": "Synthetic change", "requirements": ["R1"],
                  "criteria": ["Observed"], "depends_on": [], "features": ["synthetic"],
                  "execution": {"complexity": "routine"}} for tid in ("T1", "T2")]
        prepare_plan(self.store, {"tasks": tasks, "verification_commands": [], "browser_required": False})
        plan = self.store.approved_plan()
        plan["tasks"][0]["execution"]["capabilities"] = ["unavailable-device"]
        contract = self.store.sealed_document("architecture", "verification.json")
        contract["environment"]["instance_policy"] = "exclusive"
        original = self.store.sealed_document
        def sealed(tid, name):
            return contract if name == "verification.json" else original(tid, name)
        config = self.store.config
        config["mode"] = "live"  # Synthetic scheduling fixture; provider calls are forbidden below.
        write_json(self.store.root / "config.json", config)
        from product_cycle.team import Supervisor
        from concurrent.futures import Future
        supervisor = Supervisor(self.store, client_factory=lambda *_: self.fail("No provider is authorized"))
        scheduled = []
        def submit(function, project, rid, *args):
            scheduled.append(supervisor.team.run(rid))
            return Future()
        try:
            with patch.object(self.store, "approved_plan", return_value=plan), patch.object(self.store, "sealed_document", side_effect=sealed), patch.object(supervisor.pool, "submit", side_effect=submit):
                supervisor.tick()
            self.assertEqual(self.store.task("T1")["status"], "blocked")
            self.assertEqual(self.store.task("T1")["attempts"], 0)
            self.assertEqual([run["task_id"] for run in scheduled], ["T2"])
            self.assertEqual(scheduled[0]["source_writer"], 0)
            self.assertEqual(scheduled[0]["cwd"], str(self.store.task_source("T2")))
        finally:
            supervisor.pool.shutdown()

    def test_scheduler_admits_two_isolated_workers_without_canonical_writer(self):
        upgrade(self.store, True)
        config = self.store.config
        config.update(workspace_mode="isolated")
        config["team"] = {"enabled": True, "policy": "autonomous", "max_concurrent": 3, "autonomous_checkpoint": True}
        write_json(self.store.root / "config.json", config)
        tasks = [{"id": tid, "title": tid, "instructions": "Synthetic change", "requirements": ["R1"],
                  "criteria": ["Observed"], "depends_on": [], "features": ["synthetic"],
                  "execution": {"complexity": "routine"}} for tid in ("T1", "T2")]
        prepare_plan(self.store, {"tasks": tasks, "verification_commands": [], "browser_required": False})
        config = self.store.config
        config["mode"] = "live"  # Synthetic scheduling fixture; provider calls are forbidden below.
        write_json(self.store.root / "config.json", config)
        from product_cycle.team import Supervisor
        from concurrent.futures import Future
        supervisor = Supervisor(self.store, client_factory=lambda *_: self.fail("No provider is authorized"))
        scheduled = []
        def submit(function, project, rid, *args):
            scheduled.append(supervisor.team.run(rid))
            return Future()
        try:
            with patch.object(supervisor.pool, "submit", side_effect=submit):
                supervisor.tick()
            self.assertEqual({run["task_id"] for run in scheduled}, {"T1", "T2"})
            self.assertEqual(len({run["cwd"] for run in scheduled}), 2)
            self.assertTrue(all(run["source_writer"] == run["source_barrier"] == 0 for run in scheduled))
            self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM team_runs WHERE source_writer=1").fetchone()[0], 0)
        finally:
            supervisor.pool.shutdown()

    def test_complex_integration_preflight_is_admitted_and_failure_releases_writer(self):
        upgrade(self.store, True)
        config = self.store.config
        config["team"] = {"enabled": True, "policy": "autonomous", "max_concurrent": 3, "autonomous_checkpoint": True}
        write_json(self.store.root / "config.json", config)
        prepare_plan(self.store)
        complete_fixture(self.store, "T1")
        plan = self.store.approved_plan()
        plan["tasks"][0]["execution"] = {"complexity": "complex"}
        config = self.store.config
        config["mode"] = "live"  # Synthetic scheduling only; no provider may launch.
        write_json(self.store.root / "config.json", config)
        from product_cycle.team import Supervisor
        supervisor = Supervisor(self.store, client_factory=lambda *_: self.fail("No provider is authorized"))
        try:
            with patch.object(self.store, "approved_plan", return_value=plan):
                supervisor.tick()
            requests = self.store.db.execute("SELECT * FROM team_requests WHERE task_id='integrate-T1'").fetchall()
            self.assertTrue(requests)
            self.assertEqual({request["agent_id"] for request in requests}, {"test_automation", "performance", "security"})
            run = supervisor.team.run(requests[0]["sender_run_id"])
            self.assertEqual((run["status"], run["source_writer"]), ("preparing", 1))
            with self.store.db:
                self.store.db.execute("UPDATE team_requests SET status='completed' WHERE sender_run_id=?", (run["id"],))
            self.assertEqual([item["id"] for item in supervisor.prepared()], [run["id"]])
            # Exercise a preflight request failure in a fresh revision, retaining prior history.
            supervisor.team.update(run["id"], status="blocked")
            self.store.attempt_update(run["attempt_id"], status="failed")
            self.store.update("integrate-T1", status="rework")
            with patch.object(self.store, "approved_plan", return_value=plan), patch.object(supervisor.team, "request", side_effect=WorkflowError("Synthetic consultation failure")):
                supervisor.tick()
            latest = self.store.db.execute("SELECT status FROM team_runs WHERE task_id='integrate-T1' ORDER BY rowid DESC LIMIT 1").fetchone()
            self.assertEqual(latest[0], "blocked")
            self.assertFalse(self.store.db.execute("SELECT id FROM team_runs WHERE source_writer=1 AND status IN ('preparing','dispatching','running','unknown')").fetchone())
        finally:
            supervisor.pool.shutdown()

    def test_exhausted_repair_budget_preserves_scope_without_reopening_again(self):
        config = self.store.config
        config.update(agent_workflow_version=1, max_repairs=2)
        config["team"] = {"enabled": True, "policy": "autonomous", "max_concurrent": 3}
        write_json(self.store.root / "config.json", config)
        self.store.update("analysis", status="blocked", reason="Synthetic repeated failure")
        from product_cycle.team import TeamStore
        from product_cycle.company import apply_repairs, reserve_management
        team = TeamStore(self.store)
        for index in range(3):
            run = team.create_run("analysis", "manage")
            team.update(run["id"], status="completed")
            reserve_management(self.store, run, "synthetic-signature-" + str(index))
            with self.store.db:
                self.store.db.execute("UPDATE company_decisions SET action='repair',reason='Synthetic correction',status=? WHERE run_id=?",
                                      ("applied" if index < 2 else "pending", run["id"]))
        revision = self.store.task("analysis")["revision"]
        apply_repairs(self.store)
        self.assertEqual(self.store.task("analysis")["revision"], revision)
        self.assertEqual(self.store.task("analysis")["status"], "blocked")
        self.assertIn("giới hạn sửa", self.store.task("analysis")["reason"])
        self.assertEqual(self.store.db.execute("SELECT status FROM company_decisions WHERE run_id=?", (run["id"],)).fetchone()[0], "waiting")
        self.assertEqual(policy_packet(self.store, self.store.task("analysis"))["budgets"]["max_repairs"], 2)

    def test_runtime_contract_rejects_missing_proof_wrong_surface_and_stale_version(self):
        from product_cycle.features import validate_runtime_report
        feature = feature_map()["features"][0]
        report = {"version": 1, "source_fingerprint": "current",
                  "environment": {"runtime": "local", "instance": "owned-instance", "surface": "cli"},
                  "features": [{"id": "calculator", "status": "pass", "observations": [{"procedure": "calculate",
                      "action": "Enter 2+3", "expected": "5", "actual": "5", "evidence": ["proof.txt"]}]}]}
        task = dict(self.store.task("analysis"), stage="build", role="build")
        with patch("product_cycle.features.task_features", return_value=[feature]), patch.object(self.store, "sealed_document", return_value=verification_contract()):
            validate_runtime_report(self.store, task, report, {"proof.txt"}, "current")
            for change in ("stale", "surface", "missing", "self_report"):
                invalid = copy.deepcopy(report)
                if change == "stale": invalid["source_fingerprint"] = "old"
                if change == "surface": invalid["environment"]["surface"] = "api"
                if change == "missing": invalid["features"][0]["observations"] = []
                if change == "self_report": invalid["features"][0]["observations"][0]["evidence"] = ["runtime-observations.json"]
                with self.subTest(change=change), self.assertRaises(WorkflowError):
                    validate_runtime_report(self.store, task, invalid, {"proof.txt", "runtime-observations.json"}, "current")
            for status in ("fail", "blocked"):
                limited = copy.deepcopy(report)
                limited["features"][0].update(status=status, observations=[])
                self.assertEqual(validate_runtime_report(self.store, task, limited, set(), "current")[0]["status"], status)

    def test_declared_consultants_and_complexity_control_preflight(self):
        from product_cycle.team import preflight_roles
        from product_cycle.dispatch import validate_execution
        upgrade(self.store, True)
        prepare_plan(self.store)
        plan = self.store.approved_plan()
        plan["tasks"][0]["execution"] = {"complexity": "routine", "consultants": ["security"]}
        with patch.object(self.store, "approved_plan", return_value=plan):
            self.assertEqual(preflight_roles(self.store, self.store.task("T1")), ["security"])
            plan["tasks"][0]["execution"] = {"complexity": "routine"}
            self.assertEqual(preflight_roles(self.store, self.store.task("T1")), [])
            plan["tasks"][0]["execution"] = {"complexity": "complex"}
            self.assertIn("test_automation", preflight_roles(self.store, self.store.task("T1")))
        with self.assertRaises(WorkflowError):
            validate_execution({"consultants": ["build_reviewer"]})

    def test_dispatch_preserves_defaults_and_blocks_missing_capability_before_attempt(self):
        task = self.store.task("analysis")
        selected = route(self.store, task)
        self.assertEqual(selected["model"], self.store.config["models"]["analysis"]["model"])
        config = self.store.config
        config.update(agent_workflow_version=1, routing={"profiles": [{"id": "local", "executor": config["executor"],
            "capabilities": ["shell"], "models": {"analysis": {"model": "chosen-model", "effort": "high"}}}]})
        write_json(self.store.root / "config.json", config)
        self.assertEqual(route(self.store, task)["model"], "chosen-model")
        config["routing"]["profiles"][0]["executor"] = "codex-desktop"
        write_json(self.store.root / "config.json", config)
        with self.assertRaises(WorkflowError):
            self.store.begin("analysis", "work")
        self.assertEqual(self.store.task("analysis")["status"], "pending")
        self.assertEqual(self.store.task("analysis")["attempts"], 0)

    def _workspace_tasks(self):
        config = self.store.config
        config.update(agent_workflow_version=1, workspace_mode="isolated")
        write_json(self.store.root / "config.json", config)
        for tid in ("T1", "T2"):
            self.store.add_task(tid, "build", tid, "Synthetic change", [], ["Change observed"], ["R1"], [])
            self.store.add_task("integrate-" + tid, "integration", "Integrate " + tid, "Synthetic integration", [tid], ["Integrated"], ["R1"], [])
        (self.store.project / "a.txt").write_text("a0")
        (self.store.project / "b.txt").write_text("b0")

    def test_isolated_workers_integrate_independent_changes_without_lost_updates(self):
        self._workspace_tasks()
        first = prepare(self.store, self.store.task("T1"))
        second = prepare(self.store, self.store.task("T2"))
        (first / "a.txt").write_text("a1")
        (second / "b.txt").write_text("b2")
        self.assertEqual((self.store.project / "a.txt").read_text(), "a0")
        for tid in ("T1", "T2"):
            self.store.update(tid, status="done")
            mark_reviewed(self.store, self.store.task(tid))
            integrate(self.store, self.store.task("integrate-" + tid))
        self.assertEqual((self.store.project / "a.txt").read_text(), "a1")
        self.assertEqual((self.store.project / "b.txt").read_text(), "b2")
        self.assertEqual(integrate(self.store, self.store.task("integrate-T1"))["source_fingerprint"],
                         self.store.task_fingerprint("integrate-T1"))

    def test_integration_rejects_executable_mode_change_after_review(self):
        self._workspace_tasks()
        root = prepare(self.store, self.store.task("T1"))
        (root / "a.txt").write_text("Reviewed code")
        self.store.update("T1", status="done")
        mark_reviewed(self.store, self.store.task("T1"))
        (root / "a.txt").chmod(0o755)
        with self.assertRaises(WorkflowError):
            integrate(self.store, self.store.task("integrate-T1"))
        self.assertEqual((self.store.project / "a.txt").read_text(), "a0")

    def test_conflicting_integration_preserves_both_versions_and_applies_nothing(self):
        self._workspace_tasks()
        root = prepare(self.store, self.store.task("T1"))
        (root / "a.txt").write_text("worker")
        (root / "b.txt").write_text("worker-b")
        self.store.update("T1", status="done")
        mark_reviewed(self.store, self.store.task("T1"))
        (self.store.project / "a.txt").write_text("concurrent")
        with self.assertRaises(WorkflowError):
            integrate(self.store, self.store.task("integrate-T1"))
        self.assertEqual((self.store.project / "a.txt").read_text(), "concurrent")
        self.assertEqual((self.store.project / "b.txt").read_text(), "b0")
        self.assertEqual((root / "a.txt").read_text(), "worker")

    def test_interrupted_integration_reconciles_exact_files_without_restarting_worker(self):
        self._workspace_tasks()
        root = prepare(self.store, self.store.task("T1"))
        (root / "a.txt").write_text("worker")
        self.store.update("T1", status="done")
        mark_reviewed(self.store, self.store.task("T1"))
        with patch("product_cycle.workspaces.os.replace", side_effect=OSError("Synthetic interruption")):
            with self.assertRaises(OSError):
                integrate(self.store, self.store.task("integrate-T1"))
        self.assertEqual((self.store.project / "a.txt").read_text(), "a0")
        self.assertIn("integrate-T1", reconcile(self.store))
        self.assertEqual((self.store.project / "a.txt").read_text(), "worker")
        self.assertEqual(self.store.task("T1")["attempts"], 0)

    def test_conflict_rebases_worker_for_fresh_review_without_overwriting_canonical(self):
        self._workspace_tasks()
        root = prepare(self.store, self.store.task("T1"))
        (root / "a.txt").write_text("worker\n")
        self.store.update("T1", status="done")
        mark_reviewed(self.store, self.store.task("T1"))
        (self.store.project / "a.txt").write_text("canonical\n")
        with self.assertRaises(WorkflowError):
            integrate(self.store, self.store.task("integrate-T1"))
        self.assertEqual(self.store.task("T1")["status"], "rework")
        self.assertEqual(prepare(self.store, self.store.task("T1")), root)
        self.assertIn("<<<<<<<", (root / "a.txt").read_text())
        self.assertEqual((self.store.project / "a.txt").read_text(), "canonical\n")
        (root / "a.txt").write_text("resolved\n")
        self.store.update("T1", status="done")
        mark_reviewed(self.store, self.store.task("T1"))
        integrate(self.store, self.store.task("integrate-T1"))
        self.assertEqual((self.store.project / "a.txt").read_text(), "resolved\n")

    def test_versioned_flow_requires_integration_and_whole_product_verification(self):
        upgrade(self.store, True)
        config = self.store.config
        config["workspace_mode"] = "isolated"
        write_json(self.store.root / "config.json", config)
        prepare_plan(self.store)
        self.assertEqual(self.store.task("verify")["deps"], ["integrate-T1"])
        complete_fixture(self.store, "T1")
        self.assertFalse((self.store.project / "synthetic.py").exists())
        with self.assertRaises(WorkflowError):
            self.store.begin("verify", "work")
        complete_fixture(self.store, "integrate-T1")
        self.assertTrue((self.store.project / "synthetic.py").exists())
        complete_fixture(self.store, "verify")
        self.assertTrue(self.store.snapshot()["coordinator"]["whole_product_verified"])
        (self.store.project / "synthetic.py").write_text("# Changed after verification\n")
        self.assertFalse(self.store.snapshot()["coordinator"]["whole_product_verified"])
