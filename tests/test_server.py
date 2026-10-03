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


if __name__ == "__main__":
    unittest.main()
