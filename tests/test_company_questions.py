"""Synthetic owner-input controller checks; no provider or product acceptance."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from product_cycle import company_questions as questions
from product_cycle import capability_jobs as capabilities
from product_cycle.contracts import WorkflowError
from product_cycle.store import Store
from product_cycle.team import TeamStore


class CompanyQuestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"PRODUCT_CYCLE_HOME": str(base / "state")})
        self.env.start()
        self.store = Store.create(base / "project", "Synthetic owner questions", "Questions", mode="demo", team=True)
        self.team = TeamStore(self.store)

    def tearDown(self):
        self.store.close()
        self.env.stop()
        self.temp.cleanup()

    def mission(self):
        attempt, directory = self.store.begin("analysis", "work")
        run = self.team.create_run("analysis", "work", attempt, directory)
        self.team.update(run["id"], status="running", thread_id="synthetic-thread", turn_id="synthetic-turn")
        return self.team.run(run["id"])

    def ask(self, run, key="audience"):
        return questions.ask(self.store, run, "Who is this for?", ["Learners", "Teachers"],
                             "Learners because practice is the primary goal.",
                             "The owner has not chosen the intended audience.", key)

    def finish(self, run):
        self.team.update(run["id"], status="completed")
        if run["attempt_id"]:
            self.store.attempt_update(run["attempt_id"], status="completed")
        self.store.update(run["task_id"], status="blocked", reason=questions.BLOCKER_PREFIX + "Who is this for?")

    def test_idempotent_question_and_authenticated_current_origin(self):
        questions.migrate(self.store.db)
        questions.migrate(self.store.db)
        run = self.mission()
        first = self.ask(run)
        self.assertEqual(self.ask(run)["id"], first["id"])
        self.assertEqual(first["source_thread_id"], run["thread_id"])
        with self.assertRaises(WorkflowError):
            questions.ask(self.store, run, "Different question", [], None, "Need owner choice", "audience")
        with self.assertRaises(WorkflowError):
            self.ask(dict(run, agent_id="product_manager"), "forged")
        self.finish(run)
        with self.assertRaises(WorkflowError):
            self.ask(run, "late")
        self.assertEqual(len(questions.snapshot(self.store)["history"]), 1)

    def test_answer_is_input_not_approval_or_reopen_and_retry_is_idempotent(self):
        run = self.mission()
        question = self.ask(run)
        self.finish(run)
        before = self.store.task("analysis")
        answered = questions.answer(self.store, question["id"], "Product owner", "Learners")
        self.assertEqual(questions.answer(self.store, question["id"], "Product owner", "Learners"), answered)
        with self.assertRaises(WorkflowError):
            questions.answer(self.store, question["id"], "Product owner", "Teachers")
        self.assertEqual(self.store.task("analysis"), before)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)
        inputs = self.store.owner_inputs("analysis")
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0]["actor"], "Product owner")
        self.assertEqual(inputs[0]["answer"], "Learners")
        self.assertEqual(inputs[0]["question_id"], question["id"])
        self.assertEqual(answered["options"], question["options"])
        self.assertEqual(answered["source_run_id"], run["id"])

    def test_reopen_preserves_stale_history_and_rejects_old_response(self):
        run = self.mission()
        answered = self.ask(run, "answered")
        unanswered = self.ask(run, "unanswered")
        questions.answer(self.store, answered["id"], "Owner", "Learners")
        self.finish(run)
        self.store.reopen("analysis", "Owner changed product scope")
        with self.assertRaises(WorkflowError):
            questions.answer(self.store, unanswered["id"], "Owner", "Teachers")
        with self.assertRaises(WorkflowError):
            questions.answer(self.store, answered["id"], "Owner", "Learners")
        snapshot = questions.snapshot(self.store)
        self.assertEqual(snapshot["open"], [])
        self.assertEqual({row["status"] for row in snapshot["history"]}, {"stale"})
        self.assertEqual(snapshot["answered"][0]["answer"], "Learners")
        self.assertEqual(self.store.owner_inputs("analysis"), [])
        self.assertEqual(questions.resume_answered(self.store), [])

    def test_resume_waits_for_all_answers_and_live_work_then_consumes_once(self):
        run = self.mission()
        first, second = self.ask(run, "one"), self.ask(run, "two")
        questions.answer(self.store, first["id"], "Owner", "Learners")
        self.store.update("analysis", status="blocked", reason=questions.BLOCKER_PREFIX + "Who is this for?")
        self.assertEqual(questions.resume_answered(self.store), [])
        questions.answer(self.store, second["id"], "Owner", "Learners")
        self.assertEqual(questions.resume_answered(self.store), [])
        self.finish(run)
        before = self.store.task("analysis")
        resumed = questions.resume_answered(self.store, "analysis")
        self.assertEqual(len(resumed), 1)
        self.assertEqual(set(resumed[0]["question_ids"]), {first["id"], second["id"]})
        after = self.store.task("analysis")
        self.assertEqual(after["status"], "rework")
        self.assertEqual((after["revision"], after["attempts"]), (before["revision"], before["attempts"]))
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)
        self.store.update("analysis", status="blocked", reason="Later unrelated failure")
        self.assertEqual(questions.resume_answered(self.store), [])
        self.assertTrue(all(row["consumed_at"] for row in questions.snapshot(self.store)["answered"]))

    def test_old_attempt_answer_does_not_resume_later_attempt(self):
        run = self.mission()
        question = self.ask(run)
        questions.answer(self.store, question["id"], "Owner", "Learners")
        self.finish(run)
        self.store.update("analysis", status="rework")
        later = self.mission()
        self.finish(later)
        self.assertEqual(questions.resume_answered(self.store), [])

    def test_unconsumed_answer_does_not_resume_an_unrelated_failure(self):
        run = self.mission()
        question = self.ask(run)
        questions.answer(self.store, question["id"], "Owner", "Learners")
        self.finish(run)
        self.store.update("analysis", status="blocked", reason="A required service is unavailable")
        self.assertEqual(questions.resume_answered(self.store), [])
        self.assertEqual(self.store.task("analysis")["status"], "blocked")
        self.assertIsNone(questions.snapshot(self.store)["answered"][0]["consumed_at"])

    def test_answer_waits_for_pending_native_job_without_invalidating_source_attempt(self):
        run = self.mission()
        question = self.ask(run)
        job = capabilities.request(self.store, run, "image_generation", "Generate the selected reference", "image")
        self.finish(run)
        questions.answer(self.store, question["id"], "Owner", "Learners")
        before = self.store.task("analysis")
        result = questions.resume_answered(self.store)
        self.assertEqual(result[0]["status"], "blocked")
        after = self.store.task("analysis")
        self.assertEqual(after["status"], "blocked")
        self.assertTrue(after["reason"].startswith(capabilities.BLOCKER_PREFIX))
        self.assertEqual((after["revision"], after["attempts"]), (before["revision"], before["attempts"]))
        self.assertEqual(capabilities.claim(self.store, job["id"], "Native", self.store.project)["status"], "claimed")
        self.assertEqual(questions.resume_answered(self.store), [])

    def test_management_question_without_attempt_and_owner_input_at_any_stage(self):
        # Use a persisted synthetic management origin without starting a provider.
        run = self.mission()
        with self.store.db:
            self.store.db.execute("UPDATE team_runs SET phase='manage',agent_id='product_manager',attempt_id=NULL WHERE id=?",
                                  (run["id"],))
            self.store.db.execute("UPDATE tasks SET stage='build' WHERE id='analysis'")
        run = self.team.run(run["id"])
        question = self.ask(run)
        questions.answer(self.store, question["id"], "Owner", "Learners")
        self.assertEqual(self.store.owner_inputs("analysis")[0]["answer"], "Learners")
        self.finish(run)
        # A still-running legacy attempt prevents a management response racing work.
        self.assertEqual(questions.resume_answered(self.store), [])
        self.store.attempt_update(self.store.db.execute("SELECT id FROM attempts").fetchone()[0], status="completed")
        self.assertEqual(len(questions.resume_answered(self.store)), 1)


if __name__ == "__main__":
    unittest.main()
