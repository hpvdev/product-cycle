import sys
import tempfile
import unittest
from pathlib import Path

from product_cycle.codex import CodexClient, ModelCapacityError, provider_error
from product_cycle.contracts import WorkflowError


class CodexProtocolTests(unittest.TestCase):
    def test_dynamic_tool_round_trip_is_real_rpc_and_does_not_approve_requests(self):
        from product_cycle.team import tool_specs
        with tempfile.TemporaryDirectory() as folder:
            events, calls = [], []
            command = [sys.executable, str(Path(__file__).with_name("fake_appserver.py")), "dynamic"]
            def handler(params):
                calls.append(params)
                return {"advisory": True}
            with CodexClient(Path(folder), command=command, on_event=events.append) as client:
                result = client.run(Path(folder), "Synthetic dynamic tool test", "test-model", "high", {"type": "object"}, readonly=True,
                                    dynamic_tools=tool_specs(), tool_handler=handler, timeout=3)
            self.assertEqual(calls[0]["callId"], "fixture-call")
            self.assertTrue(result["result"]["tool_response"]["success"])
            self.assertTrue(any(event.get("method") == "client/toolResponse" for event in events))

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

    def test_capacity_is_retryable_but_quota_and_auth_are_not(self):
        for mode in ("capacity", "capacity-request"):
            with self.subTest(mode=mode), self.assertRaises(ModelCapacityError):
                self.run_peer(mode)
        for info in ("usageLimitExceeded", "unauthorized", "rateLimitExceeded"):
            self.assertNotIsInstance(provider_error({"message": "Unavailable", "codexErrorInfo": info}), ModelCapacityError)

    def test_read_thread_does_not_start_a_model_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            command = [sys.executable, str(Path(__file__).with_name("fake_appserver.py"))]
            with CodexClient(directory, command=command) as client:
                thread = client.read_thread("existing-thread")
            self.assertEqual(thread["id"], "existing-thread")
            self.assertEqual(thread["turns"][0]["status"], "completed")
            self.assertNotIn('"turn/start"', (directory / "trace.jsonl").read_text())

    def test_desktop_chat_ownership_is_explained_without_exposing_raw_error(self):
        error = provider_error({"message": "thread internal-id already has an active writer"})
        self.assertIsInstance(error, WorkflowError)
        self.assertNotIsInstance(error, ModelCapacityError)
        self.assertIn("Mở chat trong Codex", str(error))
        self.assertNotIn("internal-id", str(error))

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
