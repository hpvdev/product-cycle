"""Synthetic trial transport validates mechanics, not behavioral improvement."""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from product_cycle.contracts import WorkflowError
from product_cycle.improvements import ImprovementStore, GUIDANCE
from product_cycle.installer import install_skills
from product_cycle.learning_trials import run_trials, record_judgment, reconcile_trials
from product_cycle.store import Store, write_json
from product_cycle.team import TeamStore


class TrialClient:
    calls = []

    def __init__(self, root, on_event=None):
        self.root, self.observe = root, on_event

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def run(self, root, prompt, model, effort, schema, **options):
        self.calls.append({"root": str(root), "prompt": prompt, "options": options})
        thread, turn = "thread-" + root.name, "turn-" + root.name
        self.observe({"method": "client/threadReady", "params": {"thread_id": thread}})
        self.observe({"method": "client/turnReady", "params": {"turn_id": turn}})
        tip = root / ".agents" / "skills" / "product-cycle-design" / GUIDANCE
        output = root / "observed.json"
        write_json(output, {"synthetic": True, "reads": 2 if tip.exists() else 8})
        self.observe({"method": "turn/completed", "params": {"turn": {"status": "completed"}}})
        return {"thread_id": thread, "turn_id": turn, "tokens": 11,
                "result": {"summary": "Synthetic transport output", "artifacts": ["observed.json"], "limitations": ["Synthetic"], "blocker": None}}


class LearningTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"PRODUCT_CYCLE_HOME": str(Path(self.temp.name) / "state")})
        self.env.start()
        self.store = Store.create(Path(self.temp.name) / "project", "Synthetic case", "Synthetic", mode="demo", team=True)
        install_skills(self.store.project)
        self.team = TeamStore(self.store)
        self.improvements = ImprovementStore(self.store, checks={"skill_frontmatter": {
            "argv": [sys.executable, "-c", "print('synthetic')"]}, "targeted_controller": {"argv": [sys.executable, "-c", "print('synthetic')"]}})
        TrialClient.calls = []

    def tearDown(self):
        self.store.close()
        self.env.stop()
        self.temp.cleanup()

    def mission(self, agent, phase):
        run = self.team.create_run("analysis", "consult", agent_id="coordinator")
        with self.store.db:
            self.store.db.execute("UPDATE team_runs SET agent_id=?,phase=? WHERE id=?", (agent, phase, run["id"]))
        self.team.update(run["id"], status="completed", thread_id="recorded-" + run["id"], turn_id="turn-" + run["id"])
        return self.team.run(run["id"])

    def candidate(self, held_out=False):
        raw = self.store.project / ".product-cycle" / "request.json"
        write_json(raw, {"prompt": "Read request.md and describe the next action.", "files": {"request.md": "A manifest is pending."},
                         "expectations": ["Use bounded waits instead of repeated full reads"]})
        self.store.record_file("analysis", str(raw.relative_to(self.store.project)), "Synthetic raw case")
        if held_out:
            extra = raw.with_name("another-request.json")
            write_json(extra, {"prompt": "Read status.md and describe the next action.", "files": {"status.md": "A result is pending."},
                               "expectations": ["Read only the changed result"]})
            self.store.record_file("analysis", str(extra.relative_to(self.store.project)), "Synthetic held-out raw case")
        config = self.store.config
        config["agent_workflow_version"] = 1
        write_json(self.store.root / "config.json", config)
        author = self.mission("skill_engineer", "improve_propose")
        bundle = {"schema_version": 1, "title": "Synthetic waits", "rationale": "Synthetic redundant reads",
                  "hypothesis": "Fewer reads preserve the result", "case_ids": [str(raw.relative_to(self.store.project))],
                  "changes": [{"target_id": "product-cycle-design", "before_sha256": hashlib.sha256(b"").hexdigest(),
                               "guidance": "Wait in bounded intervals and read only the changed manifest."}],
                  "evidence": [str(raw.relative_to(self.store.project))]}
        row = self.improvements.propose(bundle, author["id"])
        self.improvements.evaluate(row["id"])
        return row["id"], self.mission("evaluation_engineer", "improve_evaluate")

    def judgment(self, packet):
        report = {"packet_hash": packet["packet_hash"], "decision": "pass", "permissions_preserved": True,
                  "goals_preserved": True, "acceptance_preserved": True, "cases": []}
        for case in packet["cases"]:
            scores = []
            for variant in case["variants"]:
                proof = next(item for item in variant["artifacts"] if item["path"].endswith("observed.json"))
                reads = json.loads(self.store.safe_path(proof["path"]).read_text())["reads"]
                scores.append({"label": variant["label"], "score": 90 if reads == 2 else 50,
                               "reason": "Synthetic output inspected", "evidence": [proof["path"]]})
            report["cases"].append({"id": case["id"], "scores": scores, "reason": "Synthetic case comparison"})
        return report

    def test_actual_trials_are_opaque_to_judge_and_include_held_out_cases(self):
        cid, run = self.candidate(held_out=True)
        packet = run_trials(self.improvements, cid, run, TrialClient)
        self.assertEqual(len(TrialClient.calls), 4)
        self.assertEqual(packet["held_out_count"], 1)
        encoded = json.dumps(packet)
        for leaked in ("before_directory", "after_directory", "rationale", "hypothesis", "another-request.json"):
            self.assertNotIn(leaked, encoded)
        for call in TrialClient.calls:
            self.assertFalse(call["options"]["network"])
            self.assertNotIn("expectations", call["prompt"])
            self.assertEqual(call["options"]["writable_roots"], [Path(call["root"])])
        self.assertEqual(self.store.snapshot()["tokens"], 44)
        result = record_judgment(self.improvements, cid, self.judgment(packet), run["id"])
        self.assertEqual(result["status"], "evaluated")
        self.assertIsNone(result["review"])

    def test_raw_input_copy_never_overwrites_judged_trial_output(self):
        cid, run = self.candidate()
        class InputOutput(TrialClient):
            def run(inner, root, *args, **kwargs):
                output = super(InputOutput, inner).run(root, *args, **kwargs)
                path = root / "input.json"
                path.write_text("A legitimate trial output named input.json")
                output["result"]["artifacts"].append("input.json")
                return output
        packet = run_trials(self.improvements, cid, run, InputOutput)
        artifacts = [proof for variant in packet["cases"][0]["variants"] for proof in variant["artifacts"] if proof["path"].endswith("input.json")]
        before = {proof["path"]: self.store.safe_path(proof["path"]).read_bytes() for proof in artifacts}
        result = record_judgment(self.improvements, cid, self.judgment(packet), run["id"])
        self.assertEqual(result["status"], "evaluated")
        self.assertEqual(before, {path: self.store.safe_path(path).read_bytes() for path in before})
        for case in result["evaluation"]["forward_test"]["cases"]:
            self.assertIn("learning-inputs", case["input_artifact"])

    def test_duplicate_case_bytes_do_not_count_as_held_out(self):
        cid, run = self.candidate()
        row = self.improvements._row(cid)
        source = self.store.safe_path(row["bundle"]["case_ids"][0])
        duplicate = source.with_name("duplicate-request.json")
        duplicate.write_bytes(source.read_bytes())
        self.store.record_file("analysis", str(duplicate.relative_to(self.store.project)), "Synthetic duplicated input")
        from product_cycle.learning_trials import select_holdouts
        self.assertEqual(select_holdouts(self.improvements, row["bundle"]["case_ids"]), [])

    def test_changed_trial_artifacts_cannot_be_judged(self):
        cid, run = self.candidate()
        packet = run_trials(self.improvements, cid, run, TrialClient)
        report = self.judgment(packet)
        proof = packet["cases"][0]["variants"][0]["artifacts"][0]["path"]
        self.store.safe_path(proof).write_text("changed")
        with self.assertRaises(WorkflowError):
            record_judgment(self.improvements, cid, report, run["id"])

    def test_lost_trial_is_reconciled_by_exact_identity_and_only_remaining_variant_runs(self):
        cid, run = self.candidate()
        threads = {}
        class LostResponse(TrialClient):
            def run(inner, root, *args, **kwargs):
                original = inner.observe
                inner.observe = lambda message: original(message) if message.get("method") != "turn/completed" else None
                output = super(LostResponse, inner).run(root, *args, **kwargs)
                threads[output["thread_id"]] = {"id": output["thread_id"], "cwd": str(root), "usage_total": output["tokens"],
                    "turns": [{"id": output["turn_id"], "status": "completed", "items": [
                        {"type": "agentMessage", "text": json.dumps(output["result"])}]}]}
                raise RuntimeError("Synthetic lost transport response")
            def read_thread(inner, thread_id):
                return threads[thread_id]
        with self.assertRaises(RuntimeError):
            run_trials(self.improvements, cid, run, LostResponse)
        first = self.store.db.execute("SELECT * FROM improvement_trials WHERE candidate_id=?", (cid,)).fetchone()
        self.assertEqual(first["status"], "unknown")
        # A snapshot with the wrong exact turn cannot release the reservation.
        actual_turn = threads[first["thread_id"]]["turns"][0]["id"]
        threads[first["thread_id"]]["turns"][0]["id"] = "unrelated-turn"
        self.assertEqual(reconcile_trials(self.improvements, LostResponse)[0]["status"], "unknown")
        threads[first["thread_id"]]["turns"][0]["id"] = actual_turn
        self.assertEqual(reconcile_trials(self.improvements, LostResponse)[0]["status"], "completed")
        packet = run_trials(self.improvements, cid, run, TrialClient)
        self.assertEqual(len(TrialClient.calls), 2)
        self.assertNotEqual(TrialClient.calls[0]["root"], TrialClient.calls[1]["root"])
        self.assertEqual(len(packet["cases"][0]["variants"]), 2)

    def test_trial_cannot_change_immutable_guidance_snapshot(self):
        cid, run = self.candidate()
        class ChangedSkill(TrialClient):
            def run(inner, root, *args, **kwargs):
                output = super(ChangedSkill, inner).run(root, *args, **kwargs)
                skill = root / ".agents/skills/product-cycle-design/SKILL.md"
                skill.write_text(skill.read_text() + "\nChanged during trial\n")
                return output
        with self.assertRaises(WorkflowError):
            run_trials(self.improvements, cid, run, ChangedSkill)
        self.assertEqual(self.store.db.execute("SELECT status FROM improvement_trials WHERE candidate_id=?", (cid,)).fetchone()[0], "failed")

    def test_budget_exhaustion_prevents_trials(self):
        cid, run = self.candidate()
        config = self.store.config
        config["learning_budget"] = {"max_trials": 1}
        write_json(self.store.root / "config.json", config)
        with self.assertRaises(WorkflowError):
            run_trials(self.improvements, cid, run, TrialClient)
        self.assertFalse(TrialClient.calls)

    def test_unknown_trial_is_not_restarted(self):
        cid, run = self.candidate()
        with patch.object(TrialClient, "run", side_effect=RuntimeError("Synthetic lost response")) as calls:
            with self.assertRaises(RuntimeError):
                run_trials(self.improvements, cid, run, TrialClient)
            with self.assertRaises(WorkflowError):
                run_trials(self.improvements, cid, run, TrialClient)
            self.assertEqual(calls.call_count, 1)
