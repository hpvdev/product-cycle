"""Synthetic capability handoff checks; no model, ImageGen or browser execution."""

import hashlib
import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from product_cycle import capability_jobs as jobs
from product_cycle import company_questions as questions
from product_cycle.contracts import WorkflowError
from product_cycle.store import Store, write_json
from product_cycle.team import TeamStore
from product_cycle.runner import browser_ready
from product_cycle.company import management_jobs


class NativeThreadReader:
    thread = {}

    def __init__(self, directory):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read_thread(self, thread_id):
        return self.thread


class CapabilityJobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"PRODUCT_CYCLE_HOME": str(base / "state")})
        self.env.start()
        self.store = Store.create(base / "project", "Synthetic capability gap", "Tools", mode="demo", team=True)
        jobs.migrate(self.store.db)
        self.team = TeamStore(self.store)
        attempt, directory = self.store.begin("analysis", "work")
        run = self.team.create_run("analysis", "work", attempt, directory)
        self.team.update(run["id"], status="running", thread_id="source-thread", turn_id="source-turn")
        self.run = self.team.run(run["id"])
        NativeThreadReader.thread = {"id": "native-thread", "cwd": str(self.store.project)}

    def tearDown(self):
        self.store.close()
        self.env.stop()
        self.temp.cleanup()

    def request(self, key="visual", capability="image_generation"):
        return jobs.request(self.store, self.run, capability, "Generate the authorized product reference", key)

    def block(self):
        self.team.update(self.run["id"], status="completed")
        self.store.attempt_update(self.run["attempt_id"], status="completed")
        self.store.update("analysis", status="blocked", reason=jobs.BLOCKER_PREFIX + "Tạo hình ảnh")

    def bind(self, job):
        jobs.claim(self.store, job["id"], "Native worker", self.store.project)
        return jobs.bind(self.store, job["id"], "Native worker", "native-thread", NativeThreadReader)

    def manifest(self, job):
        directory = self.store.project / ".product-cycle" / "capabilities" / job["id"]
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "synthetic-output.txt"
        path.write_text("Synthetic tool evidence. Does not prove genuine tool execution.")
        return {"source_fingerprint": job["source_fingerprint"], "observations": ["Synthetic result inspected"],
                "tool": {"name": jobs.TOOLS[job["capability"]], "prompt": "Synthetic call"},
                "artifacts": [{"path": str(path.relative_to(self.store.project)),
                               "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "purpose": "Synthetic evidence"}]}

    def submit(self, job, manifest=None):
        return jobs.fulfill(self.store, job["id"], "Native worker", "native-thread", manifest or self.manifest(job))

    def test_authenticated_current_request_is_idempotent_without_dispatch(self):
        jobs.migrate(self.store.db)
        job = self.request()
        self.assertEqual(self.request()["id"], job["id"])
        with self.assertRaises(WorkflowError):
            jobs.request(self.store, self.run, "computer_use", "Different work", "visual")
        with self.assertRaises(WorkflowError):
            jobs.request(self.store, dict(self.run, agent_id="dev"), "image_generation", "Work", "forged")
        with self.assertRaises(WorkflowError):
            self.request("unsupported", "email")
        self.assertEqual(self.store.task("analysis")["status"], "running")
        self.assertEqual(jobs.snapshot(self.store)["pending"][0]["capability_name"], "Tạo hình ảnh")
        self.block()
        with self.assertRaises(WorkflowError):
            self.request("late")

    def test_native_shared_instance_reservation_survives_unknown_outcome(self):
        with self.store.db:
            self.store.db.execute("UPDATE team_runs SET resource_key='synthetic-shared-runtime' WHERE id=?", (self.run["id"],))
        first, second = self.request("first"), self.request("second")
        self.block()
        self.bind(first)
        self.assertTrue(jobs.resource_in_use(self.store, first["resource_key"]))
        with self.assertRaises(WorkflowError):
            jobs.claim(self.store, second["id"], "Native worker", self.store.project)
        jobs.stop(self.store, first["id"], "Native worker", "Synthetic lost native outcome")
        with self.assertRaises(WorkflowError):
            jobs.claim(self.store, second["id"], "Native worker", self.store.project)
        self.submit(first)
        self.assertFalse(jobs.resource_in_use(self.store, first["resource_key"]))
        self.assertEqual(jobs.claim(self.store, second["id"], "Native worker", self.store.project)["status"], "claimed")

    def test_isolated_job_pins_workspace_through_native_submission_and_resume(self):
        self.block()
        config = self.store.config
        config.update(agent_workflow_version=1, workspace_mode="isolated")
        write_json(self.store.root / "config.json", config)
        self.store.add_task("T1", "build", "Synthetic feature", "Synthetic change", [], ["Observed"], [], [])
        from product_cycle.workspaces import prepare
        root = prepare(self.store, self.store.task("T1"))
        (root / "feature.txt").write_text("Workspace feature")
        self.store.update("T1", status="running", attempts=1)
        with self.store.db:
            self.store.db.execute("UPDATE team_runs SET task_id='T1',attempt_id=NULL,status='running',source_writer=0 WHERE id=?",
                                  (self.run["id"],))
        run = self.team.run(self.run["id"])
        job = jobs.request(self.store, run, "computer_use", "Observe isolated feature", "workspace")
        self.assertEqual(job["source_root"], str(root))
        self.assertEqual(job["source_fingerprint"], self.store.task_fingerprint("T1"))
        self.team.update(run["id"], status="completed")
        self.store.update("T1", status="blocked", reason=jobs.BLOCKER_PREFIX + "Native observation")
        (self.store.project / "canonical.txt").write_text("Independent canonical change")
        self.assertEqual(jobs.expire(self.store), [])
        jobs.claim(self.store, job["id"], "Native worker", self.store.project)
        NativeThreadReader.thread = {"id": "native-thread", "cwd": str(root)}
        jobs.bind(self.store, job["id"], "Native worker", "native-thread", NativeThreadReader)
        manifest = self.manifest(job)
        with self.assertRaises(WorkflowError):
            self.submit(job, manifest)
        manifest["source_root"] = str(root)
        self.assertEqual(self.submit(job, manifest)["status"], "completed")
        self.assertTrue(jobs.completed_context(self.store, "T1")[0]["is_source_current"])
        self.assertEqual(jobs.resume_completed(self.store)[0]["task_id"], "T1")
        self.assertEqual(self.store.task("T1")["status"], "rework")
        (root / "feature.txt").write_text("Changed after native observation")
        self.assertFalse(jobs.completed_context(self.store, "T1")[0]["is_source_current"])

    def test_claim_waits_for_source_boundary_and_checks_project_and_owner(self):
        job = self.request()
        with self.assertRaises(WorkflowError):
            jobs.claim(self.store, job["id"], "Native worker", self.store.project)
        self.block()
        with self.assertRaises(WorkflowError):
            jobs.claim(self.store, job["id"], "Native worker", Path(self.temp.name))
        claimed = jobs.claim(self.store, job["id"], "Native worker", self.store.project)
        self.assertEqual(jobs.claim(self.store, job["id"], "Native worker", self.store.project), claimed)
        with self.assertRaises(WorkflowError):
            jobs.claim(self.store, job["id"], "Other worker", self.store.project)
        NativeThreadReader.thread["cwd"] = self.temp.name
        with self.assertRaises(WorkflowError):
            jobs.bind(self.store, job["id"], "Native worker", "native-thread", NativeThreadReader)
        self.assertEqual(jobs.snapshot(self.store)["history"][0]["status"], "claimed")

    def test_current_claim_freezes_source_but_stale_claim_does_not(self):
        job = self.request()
        self.block()
        self.assertFalse(jobs.source_in_use(self.store))
        # An unrelated active writer must be excluded inside the claim transaction.
        with self.store.db:
            self.store.db.execute("""INSERT INTO team_runs(id,agent_id,task_id,revision,phase,status,
                source_writer,model,effort,directory,created_at) VALUES('other-writer','dev','design',1,
                'work','running',1,'synthetic','low',?,'synthetic')""", (self.temp.name,))
        with self.assertRaises(WorkflowError):
            jobs.claim(self.store, job["id"], "Native worker", self.store.project)
        self.team.update("other-writer", status="completed")
        self.bind(job)
        self.assertTrue(jobs.source_in_use(self.store))
        jobs.stop(self.store, job["id"], "Native worker", "Interrupted native action")
        self.assertTrue(jobs.source_in_use(self.store))
        self.store.reopen("analysis", "New scope after recovery decision")
        self.assertFalse(jobs.source_in_use(self.store))

    def test_fulfill_validates_hash_and_assigned_paths_then_seals_evidence(self):
        job = self.request()
        self.block()
        self.bind(job)
        manifest = self.manifest(job)
        wrong = dict(manifest, artifacts=[dict(manifest["artifacts"][0], sha256="bad")])
        with self.assertRaises(WorkflowError):
            self.submit(job, wrong)
        external = Path(self.temp.name) / "outside.txt"
        external.write_text("outside")
        wrong = dict(manifest, artifacts=[dict(manifest["artifacts"][0], path=str(external))])
        with self.assertRaises(WorkflowError):
            self.submit(job, wrong)
        sibling = self.store.project / ".product-cycle" / "another-output.txt"
        sibling.write_text("different job")
        wrong = dict(manifest, artifacts=[dict(manifest["artifacts"][0], path=str(sibling))])
        with self.assertRaises(WorkflowError):
            self.submit(job, wrong)
        with self.assertRaises(WorkflowError):
            jobs.fulfill(self.store, job["id"], "Other worker", "native-thread", manifest)
        completed = self.submit(job, manifest)
        self.assertEqual(self.submit(job, manifest), completed)
        artifact = completed["manifest"]["artifacts"][0]
        sealed = self.store.root / artifact["object_path"]
        (self.store.project / artifact["path"]).write_text("Changed after submission")
        self.assertEqual(hashlib.sha256(sealed.read_bytes()).hexdigest(), artifact["sha256"])
        self.assertEqual(self.store.task("analysis")["status"], "blocked")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)

    def test_expired_or_stopped_claim_is_unknown_never_reclaimed_and_can_reconcile(self):
        job = self.request()
        self.block()
        self.bind(job)
        manifest = self.manifest(job)
        with self.store.db:
            self.store.db.execute("UPDATE capability_jobs SET expires_at=0 WHERE id=?", (job["id"],))
        self.assertEqual(jobs.expire(self.store), [job["id"]])
        with self.assertRaises(WorkflowError):
            jobs.claim(self.store, job["id"], "Native worker", self.store.project)
        self.assertEqual(jobs.resume_completed(self.store), [])
        self.assertEqual(self.submit(job, manifest)["status"], "completed")
        self.assertEqual(jobs.stop(self.store, job["id"], "Native worker", "Stop requested")["status"], "completed")

    def test_stop_preserves_bound_identity_and_does_not_queue_again(self):
        job = self.request()
        self.block()
        self.bind(job)
        stopped = jobs.stop(self.store, job["id"], "Native worker", "Owner stopped the session")
        self.assertEqual((stopped["status"], stopped["thread_id"]), ("unknown", "native-thread"))
        with self.assertRaises(WorkflowError):
            jobs.claim(self.store, job["id"], "Native worker", self.store.project)
        self.assertEqual(jobs.resume_completed(self.store), [])

    def test_obsolete_queued_job_waits_for_writer_then_allows_director_repair(self):
        job = self.request()
        self.block()
        with self.store.db:
            self.store.db.execute("""INSERT INTO team_runs(id,agent_id,task_id,revision,phase,status,
                source_writer,model,effort,directory,created_at) VALUES('other-writer','dev','design',1,
                'work','running',1,'synthetic','low',?,'synthetic')""", (self.temp.name,))
        (self.store.project / "independent-source.txt").write_text("Synthetic independent source change")
        self.assertEqual(jobs.expire(self.store), [])
        self.assertEqual(jobs.snapshot(self.store)["pending"][0]["status"], "queued")
        self.team.update("other-writer", status="completed")
        self.assertEqual(jobs.expire(self.store), [job["id"]])
        snapshot = jobs.snapshot(self.store)
        self.assertEqual(snapshot["pending"], [])
        self.assertEqual(snapshot["history"][0]["status"], "cancelled")
        self.assertEqual(snapshot["history"][0]["reason"], jobs.SOURCE_CHANGED_REASON)
        self.assertEqual(self.store.task("analysis")["status"], "blocked")
        self.assertEqual(jobs.resume_completed(self.store), [])
        self.assertEqual([task["id"] for task, _ in management_jobs(self.store)], ["analysis"])

    def test_source_change_cancels_only_queued_and_preserves_claimed_bound_unknown(self):
        queued = self.request("queued")
        claimed = self.request("claimed")
        bound = self.request("bound")
        unknown = self.request("unknown")
        self.block()
        jobs.claim(self.store, claimed["id"], "Native worker", self.store.project)
        self.bind(bound)
        jobs.claim(self.store, unknown["id"], "Native worker", self.store.project)
        jobs.stop(self.store, unknown["id"], "Native worker", "Interrupted existing action")
        (self.store.project / "source-changed.txt").write_text("Synthetic manual source change")
        self.assertEqual(jobs.expire(self.store), [queued["id"]])
        statuses = {row["id"]: row["status"] for row in jobs.snapshot(self.store)["history"]}
        self.assertEqual(statuses, {queued["id"]: "cancelled", claimed["id"]: "claimed",
                                    bound["id"]: "bound", unknown["id"]: "unknown"})
        self.assertTrue(jobs.source_in_use(self.store))
        self.assertEqual(list(management_jobs(self.store)), [])

    def test_obsolete_queued_job_keeps_owner_question_and_requires_director_after_answer(self):
        question = questions.ask(self.store, self.run, "Choose audience", [], None,
                                 "Owner must choose", "audience")
        job = self.request()
        self.block()
        self.store.update("analysis", reason=questions.BLOCKER_PREFIX + "Choose audience")
        (self.store.project / "changed-source.txt").write_text("Synthetic independent source change")
        self.assertEqual(jobs.expire(self.store), [job["id"]])
        self.assertEqual(len(questions.snapshot(self.store)["open"]), 1)
        self.assertEqual(list(management_jobs(self.store)), [])
        questions.answer(self.store, question["id"], "Owner", "Learners")
        self.assertEqual(questions.resume_answered(self.store), [])
        self.assertEqual(self.store.task("analysis")["status"], "blocked")
        self.assertEqual(self.store.owner_inputs("analysis")[0]["answer"], "Learners")
        self.assertEqual([task["id"] for task, _ in management_jobs(self.store)], ["analysis"])

    def test_current_version_and_revision_are_required(self):
        job = self.request()
        self.block()
        self.bind(job)
        manifest = self.manifest(job)
        (self.store.project / "changed-source.txt").write_text("Source changed during native work")
        with self.assertRaises(WorkflowError):
            self.submit(job, manifest)
        self.store.reopen("analysis", "Changed product scope")
        with self.assertRaises(WorkflowError):
            self.submit(job, manifest)
        snapshot = jobs.snapshot(self.store)
        self.assertEqual(snapshot["pending"], [])
        self.assertEqual(snapshot["history"][0]["status"], "stale")
        self.assertEqual(snapshot["history"][0]["thread_id"], "native-thread")

    def test_old_attempt_job_cannot_be_claimed_for_a_later_attempt(self):
        job = self.request()
        self.block()
        self.store.update("analysis", status="rework")
        attempt, _ = self.store.begin("analysis", "work")
        self.store.attempt_update(attempt, status="completed")
        self.store.update("analysis", status="blocked", reason=jobs.BLOCKER_PREFIX + "Tạo hình ảnh")
        with self.assertRaises(WorkflowError):
            jobs.claim(self.store, job["id"], "Native worker", self.store.project)

    def test_completed_native_job_waits_for_owner_answer_without_new_attempt(self):
        question = questions.ask(self.store, self.run, "Choose the audience", [], None,
                                 "Owner must choose the audience", "owner")
        job = self.request()
        self.block()
        self.bind(job)
        self.submit(job)
        before = self.store.task("analysis")
        result = jobs.resume_completed(self.store)
        self.assertEqual(result[0]["status"], "blocked")
        after = self.store.task("analysis")
        self.assertEqual(after["status"], "blocked")
        self.assertTrue(after["reason"].startswith(questions.BLOCKER_PREFIX))
        self.assertEqual(after["attempts"], before["attempts"])
        questions.answer(self.store, question["id"], "Owner", "Learners")
        self.assertEqual(len(questions.resume_answered(self.store)), 1)
        self.assertEqual(self.store.task("analysis")["status"], "rework")
        self.assertEqual(jobs.resume_completed(self.store), [])

    def test_resume_waits_for_all_jobs_and_preserves_gates_and_unrelated_blockers(self):
        one = self.request("one")
        two = self.request("two", "computer_use")
        self.block()
        self.bind(one)
        self.submit(one)
        self.assertEqual(jobs.resume_completed(self.store), [])
        self.bind(two)
        self.submit(two)
        self.store.update("analysis", reason="An unrelated required service is unavailable")
        self.assertEqual(jobs.resume_completed(self.store), [])
        before = self.store.task("analysis")
        self.store.update("analysis", reason=jobs.BLOCKER_PREFIX + "Tạo hình ảnh")
        resumed = jobs.resume_completed(self.store)
        self.assertEqual(set(resumed[0]["job_ids"]), {one["id"], two["id"]})
        after = self.store.task("analysis")
        self.assertEqual(after["status"], "rework")
        self.assertEqual((after["revision"], after["attempts"]), (before["revision"], before["attempts"]))
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)
        self.store.update("analysis", status="blocked", reason=jobs.BLOCKER_PREFIX + "Tạo hình ảnh")
        self.assertEqual(jobs.resume_completed(self.store), [])

    def browser_manifest(self, job, requirements):
        manifest = self.manifest(job)
        path = self.store.project / Path(manifest["artifacts"][0]["path"]).with_suffix(".png")
        path.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1l8AAAAASUVORK5CYII="))
        manifest["artifacts"] = [{"path": str(path.relative_to(self.store.project)),
                                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "purpose": "Synthetic browser fixture"}]
        manifest["browser"] = {"url": "http://localhost:3000/play", "requirements": requirements,
                               "screenshot": manifest["artifacts"][0]["path"],
                               "observation": manifest["observations"][0]}
        return manifest

    def test_browser_registration_rejects_unknown_requirement_nonimage_and_unobserved_claim(self):
        with self.store.db:
            self.store.db.execute("UPDATE tasks SET stage='verify' WHERE id='analysis'")
        job = self.request(capability="computer_use")
        self.block()
        self.bind(job)
        with patch.object(self.store, "requirement_ids", return_value={"R1", "R2"}):
            manifest = self.browser_manifest(job, ["invented"])
            with self.assertRaises(WorkflowError):
                self.submit(job, manifest)
            manifest = self.browser_manifest(job, ["R1"])
            manifest["browser"]["observation"] = "An outcome not present in the real observations"
            with self.assertRaises(WorkflowError):
                self.submit(job, manifest)
            manifest = self.browser_manifest(job, ["R1"])
            path = self.store.project / manifest["artifacts"][0]["path"]
            path.write_text("Plain text with a PNG extension")
            manifest["artifacts"][0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(WorkflowError):
                self.submit(job, manifest)
        self.assertEqual(self.store.current_evidence("analysis"), [])
        self.assertEqual(jobs.snapshot(self.store)["history"][0]["status"], "bound")

    def test_browser_registration_covers_exact_requirements_and_reuses_same_version_in_next_attempt(self):
        with self.store.db:
            self.store.db.execute("UPDATE tasks SET stage='verify' WHERE id='analysis'")
        job = self.request(capability="computer_use")
        self.block()
        self.bind(job)
        with patch.object(self.store, "requirement_ids", return_value={"R1", "R2"}), \
                patch.object(self.store, "approved_plan", return_value={"browser_required": True}):
            self.assertFalse(browser_ready(self.store, self.store.task("analysis")))
            manifest = self.browser_manifest(job, ["R1", "R2"])
            completed = self.submit(job, manifest)
            self.assertTrue(browser_ready(self.store, self.store.task("analysis")))
            self.assertEqual(self.submit(job, manifest), completed)
            self.assertEqual(len(self.store.current_evidence("analysis")), 2)
            result = jobs.register_browser_evidence(self.store, job["id"])
            self.assertEqual(result, completed["manifest"]["browser_evidence"])
            self.assertEqual(len(self.store.current_evidence("analysis")), 2)
            jobs.resume_completed(self.store)
            attempt, _ = self.store.begin("analysis", "work")
            self.assertFalse(browser_ready(self.store, self.store.task("analysis")))
            evidence = jobs.register_browser_evidence(self.store, job["id"])
            self.assertEqual(evidence["attempt_id"], attempt)
            self.assertTrue(browser_ready(self.store, self.store.task("analysis")))
            context = jobs.completed_context(self.store, "analysis")
            self.assertTrue(context[0]["is_source_current"])
            report_record = next(row for row in self.store.current_evidence("analysis") if row["kind"] == "browser")
            import json
            report = json.loads((self.store.root / report_record["object_path"]).read_text())
            self.assertEqual((report["actor"], report["thread_id"]), ("Native worker", "native-thread"))
            self.assertNotIn("passed", report)
            self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)
            self.assertEqual(self.store.task("analysis")["status"], "running")
            (self.store.project / "source-changed.txt").write_text("Changed after browser observation")
            with self.assertRaises(WorkflowError):
                jobs.register_browser_evidence(self.store, job["id"])


if __name__ == "__main__":
    unittest.main()
