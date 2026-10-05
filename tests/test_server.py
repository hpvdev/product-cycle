import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from product_cycle.fixtures import complete_fixture
from product_cycle.store import Store


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.env = dict(os.environ, PRODUCT_CYCLE_HOME=str(cls.base / "state"))
        with patch.dict(os.environ, cls.env):
            store = Store.create(cls.base / "project", "Non-sensitive fixture", "Dashboard test", mode="demo")
            complete_fixture(store, "analysis", approve=False)
            cls.evidence_id = store.current_evidence("analysis")[0]["id"]
            store.close()
        cls.process = subprocess.Popen([sys.executable, "-m", "product_cycle", "serve", "--project", str(cls.base / "project"), "--port", "0"],
                                       cwd=Path(__file__).parents[1], env=cls.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        line = cls.process.stdout.readline().strip()
        if not line.startswith("Product Cycle: "):
            raise RuntimeError("Dashboard did not start")
        cls.url = line.split(" ", 2)[-1].rstrip("/")
        with urlopen(cls.url + "/api/state", timeout=5) as response:
            cls.state = json.load(response)

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.communicate(timeout=5)
        cls.temp.cleanup()

    def test_dashboard_serves_and_declares_demo(self):
        with urlopen(self.url + "/", timeout=5) as response:
            self.assertIn("Product Cycle", response.read().decode())
        self.assertEqual(self.state["config"]["mode"], "demo")

    def test_only_registered_evidence_is_readable(self):
        with urlopen(self.url + "/evidence/" + self.evidence_id, timeout=5) as response:
            self.assertGreater(len(response.read()), 0)
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.url + "/evidence/not-registered", timeout=5)
        self.assertEqual(caught.exception.code, 400)

    def test_dashboard_assets_have_browser_content_types(self):
        for route, content_type in [("/dashboard.css", "text/css"), ("/office.css", "text/css"), ("/office-view.js", "text/javascript"), ("/evidence-reader.js", "text/javascript"), ("/workflow-canvas.js", "text/javascript"), ("/screens-view.js", "text/javascript")]:
            with self.subTest(route=route), urlopen(self.url + route, timeout=5) as response:
                self.assertEqual(response.headers.get_content_type(), content_type)
                self.assertGreater(len(response.read()), 0)
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.url + "/web/../store.py", timeout=5)
        self.assertEqual(caught.exception.code, 404)

    def test_additive_team_state_cursor_api_and_safe_assets(self):
        self.assertFalse(self.state["team"]["enabled"])
        for route in ("/api/team", "/api/team/events?after=0&limit=1", "/api/team/messages?after=0&limit=1", "/api/team/discussions?after=0&limit=1"):
            with urlopen(self.url + route, timeout=5) as response:
                data = json.load(response)
            self.assertIn("enabled" if route == "/api/team" else "cursor", data)
        for route in ("/api/team/events?after=-1", "/api/team/messages?limit=bad", "/api/team/discussions?after=-1", "/api/team/discussions?ids=not-a-topic", "/api/team/discussions?ids=0", "/assets/%2e%2e/store.py", "/assets/office/%2e%2e/%2e%2e/dashboard.html"):
            with self.subTest(route=route), self.assertRaises(HTTPError) as caught:
                urlopen(self.url + route, timeout=5)
            self.assertIn(caught.exception.code, (400, 404))
        with urlopen(self.url + "/assets/office/coordinator.png", timeout=5) as response:
            self.assertEqual(response.headers.get_content_type(), "image/png")

    def test_live_stream_delivers_changes_and_reconnects_with_full_state(self):
        def frame(response):
            event, data = None, None
            while True:
                line = response.readline().decode().rstrip('\r\n')
                if line.startswith('event: '):
                    event = line[7:]
                elif line.startswith('data: '):
                    data = json.loads(line[6:])
                elif not line and event:
                    if event == 'state':
                        return data
                    event, data = None, None
        with urlopen(self.url + '/api/live', timeout=6) as response:
            self.assertEqual(response.headers.get_content_type(), 'text/event-stream')
            self.assertEqual(frame(response)['project'], str((self.base / 'project').resolve()))
            with patch.dict(os.environ, self.env):
                store = Store(self.base / 'project')
                store.owner_input('analysis', 'Synthetic owner', 'Live-stream test: preserve this exact observation')
                store.close()
            for _ in range(10):
                current = frame(response)
                analysis = next(task for task in current['tasks'] if task['id'] == 'analysis')
                if any(note['note'] == 'Live-stream test: preserve this exact observation' for note in analysis['owner_inputs']):
                    break
            else:
                self.fail('Committed input did not reach the live connection')
        request = Request(self.url + '/api/live', headers={'Last-Event-ID': '999999999'})
        with urlopen(request, timeout=6) as response:
            reconnected = frame(response)
            self.assertIn('team', reconnected)
            self.assertIn('tasks', reconnected)
            self.assertEqual(reconnected['project'], str((self.base / 'project').resolve()))

    def test_post_requires_control_token(self):
        request = Request(self.url + "/api/pause", data=b"{}", headers={"Content-Type": "application/json"})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 403)

    def test_cross_origin_control_is_rejected(self):
        request = Request(self.url + "/api/pause", data=b"{}", headers={"Content-Type": "application/json", "X-Product-Cycle-Token": self.state["control_token"], "Origin": "https://other.example"})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 403)

    def test_read_only_dashboard_rejects_mutation_even_with_valid_token(self):
        from product_cycle.store import write_json
        with patch.dict(os.environ, self.env):
            store = Store(self.base / "project")
            config = store.config
            updated = dict(config, dashboard_read_only=True)
            write_json(store.root / "config.json", updated)
            try:
                request = Request(self.url + "/api/pause", data=b"{}", headers={
                    "Content-Type": "application/json", "X-Product-Cycle-Token": self.state["control_token"]})
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=5)
                self.assertEqual(caught.exception.code, 400)
                self.assertEqual(store.snapshot()["state"], "active")
            finally:
                write_json(store.root / "config.json", config)
                store.close()

    def test_real_gate_decision_through_dashboard(self):
        payload = {"task": "analysis", "action": "approve", "actor": "Test operator", "note": "Accepted fixture scope"}
        request = Request(self.url + "/api/decision", data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json", "X-Product-Cycle-Token": self.state["control_token"]})
        with urlopen(request, timeout=5) as response:
            self.assertTrue(json.load(response)["ok"])
        with urlopen(self.url + "/api/state", timeout=5) as response:
            updated = json.load(response)
        self.assertEqual(updated["tasks"][0]["status"], "done")
        self.assertEqual(updated["decisions"][-1]["actor"], "Test operator")
        self.assertEqual(updated["stages"][0]["percent"], 100)
        self.assertEqual(len(updated["stages"]), 8)
        self.assertTrue(all(stage["steps"] for stage in updated["stages"]))
        self.assertTrue(all(step["status"] == "done" for step in updated["tasks"][0]["steps"]))


if __name__ == "__main__":
    unittest.main()
