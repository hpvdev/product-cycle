"""Office-first setup tests. No real model or product cycle is dispatched."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from product_cycle.contracts import WorkflowError
from product_cycle.store import Store, write_json, runner_lock
from product_cycle.onboarding import submit_request, start_team, summary, connected, open_dashboard, bind_owner_chat


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.env = patch.dict(os.environ, PRODUCT_CYCLE_HOME=str(base / 'state'))
        self.env.start()
        self.store = Store.create(base / 'product', '', 'New company', team=True, awaiting_request=True)

    def tearDown(self):
        self.store.close()
        self.env.stop()
        self.temp.cleanup()

    def test_office_has_real_foundation_and_no_invented_product_or_workers(self):
        packet = summary(self.store)
        self.assertEqual(packet['status'], 'awaiting_request')
        self.assertIsNone(packet['dashboard_url'])
        self.assertEqual(packet['chats'], [])
        self.assertFalse(packet['execution_active'])
        self.assertEqual((self.store.root / 'brief.md').read_text().strip(), '')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0], 0)
        self.assertTrue((self.store.project / '.git').is_dir())
        self.assertTrue((self.store.project / '.agents/skills/product-cycle-onboard/SKILL.md').is_file())
        with self.assertRaises(WorkflowError):
            self.store.pause(False)
        with self.assertRaises(WorkflowError):
            self.store.begin('analysis', 'work')
        with patch('product_cycle.onboarding.subprocess.Popen') as spawn, self.assertRaises(WorkflowError):
            start_team(self.store)
        spawn.assert_not_called()

    def test_request_activates_analysis_without_approving_or_changing_policy(self):
        models, team = self.store.config['models'], self.store.config['team']
        original_gate = self.store.owner_gate(self.store.task('analysis'))
        with runner_lock(self.store):
            submit_request(self.store, 'Build a game to practise recalling familiar words.')
        self.assertFalse(self.store.config['awaiting_request'])
        self.assertEqual(self.store.db.execute("SELECT value FROM meta WHERE key='state'").fetchone()[0], 'active')
        self.assertEqual(self.store.config['models'], models)
        self.assertEqual(self.store.config['team'], team)
        self.assertEqual(self.store.owner_gate(self.store.task('analysis')), original_gate)
        self.assertFalse(original_gate)  # New explicitly autonomous company policy.
        self.assertEqual(self.store.task('analysis')['status'], 'pending')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM decisions').fetchone()[0], 0)
        with self.assertRaises(WorkflowError):
            submit_request(self.store, 'Overwrite accepted request')

    def test_config_cannot_bypass_the_unsubmitted_request(self):
        write_json(self.store.root / 'config.json', dict(self.store.config, awaiting_request=False))
        self.assertTrue(self.store.config['awaiting_request'])
        with self.assertRaises(WorkflowError):
            self.store.pause(False)
        submit_request(self.store, 'Actual owner request')
        self.assertFalse(self.store.config['awaiting_request'])

    def test_failed_brief_save_keeps_company_waiting(self):
        original = Path.write_text
        def fail_brief(path, *args, **kwargs):
            if path == self.store.root / 'brief.md':
                raise OSError('synthetic disk failure')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'write_text', fail_brief), self.assertRaises(OSError):
            submit_request(self.store, 'Actual requirement')
        self.assertTrue(self.store.config['awaiting_request'])
        self.assertEqual(self.store.db.execute("SELECT value FROM meta WHERE key='state'").fetchone()[0], 'paused')

    def test_existing_paused_project_is_not_silently_started(self):
        submit_request(self.store, 'Actual request')
        self.store.pause(True)
        with patch('product_cycle.onboarding.subprocess.Popen') as spawn, self.assertRaises(WorkflowError):
            start_team(self.store)
        spawn.assert_not_called()

    def test_startup_releases_runner_lock_and_observes_the_child_heartbeat(self):
        submit_request(self.store, 'Actual request')
        real_popen = subprocess.Popen
        processes = []
        # A local fixture reproduces the supervisor lock order without invoking any model.
        script = """import os,time,sys
from product_cycle.store import Store,runner_lock,now
from product_cycle.team import supervisor_lock
s=Store(sys.argv[1])
with supervisor_lock(s):
 with runner_lock(s):
  with s.db:
   s.db.execute("INSERT INTO team_supervisor(id,status,pid,last_heartbeat) VALUES(1,'running',?,?)",(os.getpid(),now()))
 time.sleep(5)
s.close()
"""
        def launch(command, **kwargs):
            process = real_popen([sys.executable, '-c', script, str(self.store.project)], **kwargs)
            processes.append(process)
            return process
        try:
            with patch('product_cycle.onboarding.subprocess.Popen', side_effect=launch):
                start_team(self.store)
            row = self.store.db.execute('SELECT * FROM team_supervisor WHERE id=1').fetchone()
            self.assertEqual(row['pid'], processes[0].pid)
            self.assertIsNotNone(row['last_heartbeat'])
            self.assertIsNone(processes[0].poll())
        finally:
            for process in processes:
                process.terminate()
                process.wait(timeout=3)

    def test_owner_reply_link_is_verified_in_the_right_project_without_reading_turns(self):
        with patch('product_cycle.codex.CodexClient') as client:
            connection = client.return_value.__enter__.return_value
            connection.request.return_value = {'thread': {'id': 'real-owner-chat', 'cwd': str(self.store.project)}}
            bind_owner_chat(self.store, 'real-owner-chat')
            self.assertEqual(connection.request.call_args.args[1], {'threadId': 'real-owner-chat', 'includeTurns': False})
            self.assertEqual(summary(self.store)['owner_chat_url'], 'codex://threads/real-owner-chat')
            connection.request.return_value = {'thread': {'id': 'wrong-chat', 'cwd': '/another-project'}}
            with self.assertRaises(WorkflowError):
                bind_owner_chat(self.store, 'wrong-chat')
            self.assertEqual(self.store.config['owner_chat']['thread_id'], 'real-owner-chat')

    def test_dashboard_url_must_be_loopback_and_match_the_project(self):
        self.assertFalse(connected(self.store.project, 'https://other.example'))
        with patch('product_cycle.onboarding.urlopen') as get:
            get.return_value.__enter__.return_value.read.return_value = json.dumps({'project': str(self.store.project)}).encode()
            self.assertTrue(connected(self.store.project, 'http://127.0.0.1:8787/'))
            get.return_value.__enter__.return_value.read.return_value = json.dumps({'project': '/another-project'}).encode()
            self.assertFalse(connected(self.store.project, 'http://127.0.0.1:8787/'))

    def test_already_connected_office_is_reused_without_another_process(self):
        write_json(self.store.root / 'onboarding-runtime.json', {'dashboard_url': 'http://127.0.0.1:8787/'})
        with patch('product_cycle.onboarding.connected', return_value=True), patch('product_cycle.onboarding.subprocess.Popen') as spawn:
            self.assertEqual(open_dashboard(self.store), 'http://127.0.0.1:8787/')
        spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
