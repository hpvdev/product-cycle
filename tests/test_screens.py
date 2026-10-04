"""Synthetic screen contracts; these tests do not measure UI quality."""

import copy
import json
import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

from product_cycle.contracts import WorkflowError, work_steps
from product_cycle.fixtures import complete_fixture
from product_cycle.runner import prompt_for
from product_cycle.screens import validate_screen_design, validate_screen_plan
from product_cycle.store import Store, digest, fingerprint, write_json


def png(path, width=60, height=40, color=(20, 30, 40)):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    pixels = (b"\0" + bytes(color) * width) * height
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
                     chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


class ScreenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"PRODUCT_CYCLE_HOME": str(self.base / "state")})
        self.env.start()
        self.store = Store.create(self.base / "product", "Synthetic UI", "Screen contract", mode="demo")
        config = self.store.config
        config.update(screen_design_required=True, gates=[])
        write_json(self.store.root / "config.json", config)
        complete_fixture(self.store, "analysis")
        self.aid, self.directory = self.store.begin("design", "work")
        self.image = self.directory / "ready.png"
        png(self.image)
        self.reference = str(self.image.relative_to(self.store.project))
        self.target = {"screen_id": "play", "state": "ready", "viewport": {"width": 60, "height": 40}}
        self.baseline = {"has_ui": True, "visual_reference": self.reference, "version": "1",
            "flows": ["Play"], "states": ["Ready"], "rules": {"color": "Synthetic"}, "acceptance": ["Synthetic UI"],
            "screens": [{"id": "play", "name": "Màn chơi", "requirements": ["R1"],
                "states": [{"id": "ready", "name": "Sẵn sàng", "description": "Synthetic state"}],
                "references": [{"state": "ready", "image": self.reference, "viewport": self.target["viewport"]}],
                "transitions": [{"from_state": "ready", "action": "Start", "to_screen": "play", "to_state": "ready"}], "assets": []}]}
        (self.directory / "design.md").write_text("Synthetic design, not a real product")
        write_json(self.directory / "design-baseline.json", self.baseline)
        self.result = self.result_for("design", [self.directory / "design.md", self.directory / "design-baseline.json", self.image])

    def test_legacy_progress_does_not_claim_screen_image_bundle(self):
        config = self.store.config
        config["screen_design_required"] = False
        write_json(self.store.root / "config.json", config)
        design = next(task for task in self.store.snapshot()["tasks"] if task["id"] == "design")
        self.assertEqual(design["steps"][2]["title"], "Thử và đề xuất mốc thiết kế")

    def tearDown(self):
        self.store.close()
        self.env.stop()
        self.temp.cleanup()

    def result_for(self, tid, paths, blocker=None):
        task = self.store.task(tid)
        artifacts = [{"path": str(path.relative_to(self.store.project)), "purpose": "Synthetic contract evidence",
            "criteria": ["C" + str(i + 1) for i in range(len(task["criteria"]))], "requirements": ["R1"]} for path in paths]
        return {"summary": "Synthetic result", "artifacts": artifacts,
            "steps": [{"id": step["id"], "summary": "Synthetic output", "artifacts": [item["path"] for item in artifacts]}
                      for step in work_steps(task["role"])], "limitations": ["Not real UI quality"], "blocker": blocker}

    def review(self, tid):
        task = self.store.task(tid)
        refs = [item["id"] for item in self.store.current_evidence(tid)]
        return {"decision": "approve", "summary": "Synthetic review", "findings": [],
            "criteria": [{"id": "C" + str(i + 1), "passed": True, "evidence": refs, "reason": "Synthetic evidence"} for i in range(len(task["criteria"]))],
            "steps": [{"id": step["id"], "passed": True, "evidence": refs, "reason": "Synthetic step"} for step in task["result"]["steps"]]}

    def accept_design(self):
        self.store.work_finished("design", self.aid, self.result)
        aid, _ = self.store.begin("design", "review")
        self.store.review_finished("design", aid, self.review("design"))
        self.assertEqual(self.store.task("design")["status"], "awaiting_approval")
        self.store.decide("design", "approve", "Synthetic owner", "Accepted synthetic images")

    def plan(self):
        return {"tasks": [{"id": "T1", "title": "Play screen", "instructions": "Synthetic implementation",
            "depends_on": [], "requirements": ["R1"], "criteria": ["Synthetic match"], "checks": [], "screen_targets": [self.target]}],
            "browser_required": True, "verification_commands": []}

    def prepare_build(self):
        self.accept_design()
        complete_fixture(self.store, "architecture")
        complete_fixture(self.store, "plan", plan=self.plan())
        aid, directory = self.store.begin("T1", "work")
        rendered = directory / "render.png"
        png(rendered, color=(50, 60, 70))
        report = {"baseline_version": "1", "source_fingerprint": fingerprint(self.store.project),
            "comparisons": [dict(self.target, reference_sha256=digest(self.image), rendered_image=str(rendered.relative_to(self.store.project)),
                status="matched", observations=["Synthetic comparison, not aesthetic acceptance"])]}
        path = directory / "screen-comparisons.json"
        write_json(path, report)
        return aid, directory, report, self.result_for("T1", [path, rendered])

    def test_screen_bundle_requires_images_states_and_valid_transitions(self):
        artifacts = {item["path"]: self.store.safe_path(item["path"]) for item in self.result["artifacts"]}
        validate_screen_design(self.baseline, {"R1"}, artifacts)
        for mutation in ["image", "transition", "state", "viewport"]:
            with self.subTest(mutation=mutation):
                baseline = copy.deepcopy(self.baseline)
                screen = baseline["screens"][0]
                if mutation == "image": screen["references"][0]["image"] = "missing.png"
                if mutation == "transition": screen["transitions"][0]["to_screen"] = "missing"
                if mutation == "state": screen["states"].append({"id": "error", "name": "Lỗi", "description": "Missing image"})
                if mutation == "viewport": screen["references"][0]["viewport"]["width"] = 100
                with self.assertRaises(WorkflowError): validate_screen_design(baseline, {"R1"}, artifacts)

    def test_plan_cannot_skip_or_invent_screen_targets(self):
        plan = self.plan()
        validate_screen_plan(plan, self.baseline)
        for targets in [[], [dict(self.target, screen_id="unknown")]]:
            plan["tasks"][0]["screen_targets"] = targets
            with self.assertRaises(WorkflowError): validate_screen_plan(plan, self.baseline)

    def test_design_gate_and_dashboard_references_follow_actual_owner_decision(self):
        self.store.work_finished("design", self.aid, self.result)
        aid, _ = self.store.begin("design", "review")
        self.store.review_finished("design", aid, self.review("design"))
        snapshot = next(task for task in self.store.snapshot()["tasks"] if task["id"] == "design")
        self.assertEqual(snapshot["design_baseline"]["approval"], "pending")
        self.assertTrue(snapshot["design_baseline"]["screens"][0]["references"][0]["evidence_id"])
        self.assertEqual(snapshot["steps"][-1]["status"], "awaiting_approval")
        with self.assertRaises(WorkflowError): self.store.begin("architecture", "work")
        self.store.decide("design", "approve", "Owner", "Accept synthetic design")
        snapshot = next(task for task in self.store.snapshot()["tasks"] if task["id"] == "design")
        self.assertEqual(snapshot["design_baseline"]["approval"], "approved")

    def test_build_rejects_missing_stale_wrong_reference_and_unrepaired_comparisons(self):
        _, directory, report, result = self.prepare_build()
        self.store.validate_outputs("T1", result)
        for field, value in [("baseline_version", "2"), ("source_fingerprint", "stale"), ("comparisons", [])]:
            invalid = copy.deepcopy(report); invalid[field] = value
            write_json(directory / "screen-comparisons.json", invalid)
            with self.subTest(field=field), self.assertRaises(WorkflowError): self.store.validate_outputs("T1", result)
        for field, value in [("reference_sha256", "wrong"), ("status", "needs_changes"), ("rendered_image", self.reference)]:
            invalid = copy.deepcopy(report); invalid["comparisons"][0][field] = value
            write_json(directory / "screen-comparisons.json", invalid)
            with self.subTest(field=field), self.assertRaises(WorkflowError): self.store.validate_outputs("T1", result)
        missing = copy.deepcopy(result); missing["artifacts"] = [missing["artifacts"][1]]
        for step in missing["steps"]: step["artifacts"] = [missing["artifacts"][0]["path"]]
        with self.assertRaises(WorkflowError): self.store.validate_outputs("T1", missing)

    def test_comparison_claim_needs_independent_evidence_and_tracks_source_changes(self):
        aid, directory, _, result = self.prepare_build()
        self.store.work_finished("T1", aid, result)
        review = self.review("T1")
        incomplete = copy.deepcopy(review)
        for row in incomplete["criteria"]: row["evidence"] = row["evidence"][:1]
        with self.assertRaises(WorkflowError): self.store.validate_review("T1", incomplete)
        self.store.validate_review("T1", review)
        snapshot = next(task for task in self.store.snapshot()["tasks"] if task["id"] == "T1")
        self.assertTrue(snapshot["screen_comparisons"]["current_source"])
        self.assertTrue(snapshot["screen_comparisons"]["comparisons"][0]["evidence_id"])
        (self.store.project / "app.py").write_text("# Changed product")
        snapshot = next(task for task in self.store.snapshot()["tasks"] if task["id"] == "T1")
        self.assertFalse(snapshot["screen_comparisons"]["current_source"])

    def test_worker_receives_the_exact_assigned_screen(self):
        _, directory, _, _ = self.prepare_build()
        prompt_for(self.store, self.store.task("T1"), directory)
        packet = json.loads((directory / "context.json").read_text())
        self.assertEqual(packet["screen_targets"][0]["image"], self.reference)
        self.assertIn("screen-comparisons.json", packet["required_files"])

    def test_blocked_ui_work_keeps_outputs_without_claiming_a_visual_pass(self):
        aid, _, _, result = self.prepare_build()
        result["blocker"] = "Browser observation unavailable"
        result["artifacts"] = result["artifacts"][1:]
        for step in result["steps"]: step["artifacts"] = [result["artifacts"][0]["path"]]
        self.store.work_finished("T1", aid, result)
        self.assertEqual(self.store.task("T1")["status"], "blocked")
        with self.assertRaises(WorkflowError): self.store.validate_review("T1", self.review("T1"))
