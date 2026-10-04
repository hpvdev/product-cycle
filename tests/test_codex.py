import sys
import tempfile
import unittest
from pathlib import Path

from product_cycle.codex import CodexClient
from product_cycle.contracts import WorkflowError


class CodexProtocolTests(unittest.TestCase):
    def run_peer(self, mode="success", max_tokens=100, timeout=3, title=None):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            events = []
            command = [sys.executable, str(Path(__file__).with_name("fake_appserver.py")), mode]
            with CodexClient(directory, on_event=events.append, command=command) as client:
                result = client.run(directory, "Fixture", "test-model", "high", {"type": "object"},
                                    readonly=True, max_tokens=max_tokens, timeout=timeout, title=title)
            return result, events

    def test_handshake_and_actual_configuration(self):
        result, events = self.run_peer()
        self.assertEqual(result["result"]["effort"], "high")
        self.assertEqual(result["observed_model"], "test-model")
        self.assertEqual(result["observed_effort"], "high")
        self.assertEqual(result["tokens"], 30)
        self.assertTrue(any(event.get("method") == "client/threadReady" for event in events))

    def test_failed_turn_is_not_success(self):
        with self.assertRaises(WorkflowError):
            self.run_peer("failed")

    def test_worker_thread_has_a_readable_name(self):
        result, events = self.run_peer(title="Vocabulary game — Develop round")
        names = [event["params"] for event in events if event.get("method") == "thread/name/updated"]
        self.assertEqual(names, [{"threadId": result["thread_id"], "threadName": "Vocabulary game — Develop round"}])

    def test_token_budget_interrupts(self):
        with self.assertRaises(WorkflowError):
            self.run_peer(max_tokens=10)

    def test_usage_is_recorded_without_a_token_ceiling(self):
        result, events = self.run_peer(max_tokens=None)
        self.assertEqual(result["tokens"], 30)
        self.assertTrue(any(event.get("method") == "thread/tokenUsage/updated" for event in events))

    def test_timeout_interrupts(self):
        with self.assertRaises(WorkflowError):
            self.run_peer("timeout", timeout=.2)

    def test_user_input_request_is_not_answered_automatically(self):
        with self.assertRaises(WorkflowError):
            self.run_peer("request")


if __name__ == "__main__":
    unittest.main()
