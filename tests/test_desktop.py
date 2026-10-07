"""Synthetic native handoffs: these tests do not run Codex or prove product quality."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from product_cycle import desktop
from product_cycle.codex import local_thread_usage
from product_cycle.contracts import WorkflowError, work_steps, validate_experience_checkpoint
from product_cycle.runner import run_cycle
from product_cycle.store import Store, write_json


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.env = patch.dict(os.environ, PRODUCT_CYCLE_HOME=str(self.base / 'state'))
        self.env.start()
        self.store = Store.create(self.base / 'project', 'Synthetic brief', 'Test', mode='demo')
        config = self.store.config
        config.update(mode='live', executor='codex-desktop', dashboard_read_only=True)
        write_json(self.store.root / 'config.json', config)

    def tearDown(self):
        self.store.close()
        self.env.stop()
        self.temp.cleanup()

    def peer(self, thread_id='worker', total=10, cwd=None):
        factory = MagicMock()
        factory.return_value.__enter__.return_value.read_thread.return_value = {
            'id': thread_id, 'cwd': str(cwd or self.store.project), 'turns': [], 'usage_total': total}
        return factory

    def work_result(self, request):
        directory = Path(request['result_path']).parent
        (directory / 'analysis.md').write_text('# Synthetic scope\nNo actual product research.')
        write_json(directory / 'requirements.json', {'requirements': [
            {'id': 'R1', 'description': 'Synthetic outcome', 'acceptance': ['Observed synthetic behavior']}]})
        artifacts = [{'path': str(path.relative_to(self.store.project)), 'purpose': 'Synthetic artifact',
                      'criteria': ['C1', 'C2'], 'requirements': []}
                     for path in [directory / 'analysis.md', directory / 'requirements.json']]
        result = {'summary': 'Synthetic analysis', 'artifacts': artifacts,
                  'steps': [{'id': step['id'], 'summary': 'Synthetic observation',
                             'artifacts': [item['path'] for item in artifacts]} for step in work_steps('analysis')],
                  'limitations': ['Not real product quality evidence'], 'blocker': None}
        write_json(directory / 'result.json', result)
        return result

    def test_native_work_review_gate_and_next_handoff_never_start_separate_writer(self):
        with patch('product_cycle.codex.CodexClient.run', side_effect=AssertionError('Separate writer')):
            request = run_cycle(self.store)
            repeated = run_cycle(self.store)
            self.assertEqual(request['attempt'], repeated['attempt'])
            self.assertEqual(self.store.snapshot()['execution']['status'], 'queued')
            self.assertFalse(self.store.snapshot()['execution']['active'])
            desktop.bind(self.store, 'analysis', request['attempt'], 'worker', self.peer())
            result = self.work_result(request)
            desktop.submit(self.store, 'analysis', request['attempt'], request['result_path'])
            review = run_cycle(self.store)
            self.assertEqual(review['phase'], 'review')
            with self.assertRaisesRegex(WorkflowError, 'độc lập'):
                desktop.bind(self.store, 'analysis', review['attempt'], 'worker', self.peer())
            desktop.bind(self.store, 'analysis', review['attempt'], 'reviewer', self.peer('reviewer'))
            records = self.store.current_evidence('analysis')
            evidence = [item['id'] for item in records]
            write_json(review['result_path'], {'decision': 'approve', 'summary': 'Synthetic review',
                'criteria': [{'id': cid, 'passed': True, 'evidence': evidence, 'reason': 'Inspected synthetic files'} for cid in ['C1', 'C2']],
                'steps': [{'id': step['id'], 'passed': True, 'evidence': evidence, 'reason': 'Inspected synthetic outputs'} for step in result['steps']],
                'findings': []})
            desktop.submit(self.store, 'analysis', review['attempt'], review['result_path'])
            self.assertEqual(self.store.task('analysis')['status'], 'awaiting_approval')
            self.assertEqual(run_cycle(self.store)['status'], 'waiting')
            self.store.decide('analysis', 'approve', 'Synthetic owner', 'Explicit synthetic decision')
            self.assertEqual(run_cycle(self.store)['task'], 'design')
            with self.assertRaises(WorkflowError):
                desktop.submit(self.store, 'analysis', review['attempt'], review['result_path'])

    def test_binding_rejects_wrong_project_and_preserves_pending_request(self):
        request = run_cycle(self.store)
        with self.assertRaisesRegex(WorkflowError, 'không thuộc'):
            desktop.bind(self.store, 'analysis', request['attempt'], 'worker', self.peer(cwd=self.base))
        self.assertIsNone(desktop.latest(self.store, 'analysis')['thread_id'])
        self.assertEqual(run_cycle(self.store)['attempt'], request['attempt'])

    def test_usage_delta_is_idempotent_and_missing_counter_stays_unknown(self):
        request = run_cycle(self.store)
        desktop.bind(self.store, 'analysis', request['attempt'], 'worker', self.peer(total=100))
        attempt = desktop.latest(self.store, 'analysis')
        self.assertIsNone(attempt['tokens'])
        desktop.update_usage(self.store, attempt, {'usage_total': 140})
        desktop.update_usage(self.store, attempt, {'usage_total': 140})
        desktop.update_usage(self.store, attempt, {})
        self.assertEqual(desktop.latest(self.store, 'analysis')['tokens'], 40)
        self.assertEqual(self.store.snapshot()['tokens'], 40)

    def test_usage_sync_reads_bound_task_without_losing_native_reconciliation(self):
        request = run_cycle(self.store)
        desktop.bind(self.store, 'analysis', request['attempt'], 'worker', self.peer(total=100))
        desktop.sync_usage(self.store, self.peer(total=140))
        self.assertEqual(desktop.latest(self.store, 'analysis')['tokens'], 40)

    def test_owner_feedback_is_revision_scoped_and_does_not_approve(self):
        self.store.owner_input('analysis', 'Owner', 'Do not simplify the desired experience')
        self.assertEqual(self.store.task('analysis')['status'], 'pending')
        request = run_cycle(self.store)
        context = json.loads((Path(request['result_path']).parent / 'context.json').read_text())
        self.assertEqual(context['owner_inputs'][0]['note'], 'Do not simplify the desired experience')
        self.assertIn('output_schema', context)
        self.store.recover()
        self.store.reopen('analysis', 'New direction')
        self.assertEqual(self.store.owner_inputs('analysis'), [])

    def test_core_experience_blocks_expansion_and_preserves_prerequisites(self):
        plan = {'tasks': [{'id': 'T1', 'depends_on': []}, {'id': 'T2', 'depends_on': ['T1']},
                          {'id': 'T3', 'depends_on': ['T2']}],
                'experience_checkpoint': {'task_id': 'T2', 'goal': 'Usable core', 'evaluation': ['Try the complete journey']}}
        validate_experience_checkpoint(plan)
        plan['tasks'].append({'id': 'T4', 'depends_on': ['T1']})
        with self.assertRaisesRegex(WorkflowError, 'phụ thuộc mốc'):
            validate_experience_checkpoint(plan)

    def test_native_recovery_does_not_import_an_unchanged_old_result(self):
        from product_cycle.runner import sync_task, continue_task
        request = run_cycle(self.store)
        desktop.bind(self.store, 'analysis', request['attempt'], 'worker', self.peer())
        self.work_result(request)
        self.store.attempt_update(request['attempt'], status='completed')
        self.store.update('analysis', status='blocked', reason='Need owner discussion')
        resumed = desktop.prepare(self.store, 'analysis', resume=True)
        desktop.bind(self.store, 'analysis', resumed['attempt'], 'worker', self.peer())
        peer = self.peer()
        peer.return_value.__enter__.return_value.read_thread.return_value['turns'] = [
            {'id': 'new-turn', 'status': 'completed', 'items': [{'type': 'agentMessage', 'text': 'A question for the owner'}]}]
        outcome = sync_task(self.store, 'analysis', peer)
        self.assertTrue(outcome['updated'])
        self.assertEqual(self.store.task('analysis')['status'], 'blocked')
        self.assertIsNone(self.store.task('analysis')['result'])
        self.assertEqual(desktop.latest(self.store, 'analysis')['status'], 'completed')
        continued = continue_task(self.store, 'analysis', peer)
        self.assertEqual(continued['status'], 'native_handoff')
        self.assertEqual(desktop.latest(self.store, 'analysis')['status'], 'queued')

    def test_core_gate_requires_a_real_owner_decision_before_expansion(self):
        from product_cycle.fixtures import complete_fixture
        for tid in ['analysis', 'design', 'architecture']:
            complete_fixture(self.store, tid)
        config = self.store.config
        config['experience_checkpoint_required'] = True
        write_json(self.store.root / 'config.json', config)
        plan = {'tasks': [
            {'id': 'T1', 'title': 'Core', 'instructions': 'Usable journey', 'depends_on': [], 'requirements': ['R1'], 'criteria': ['Usable'], 'checks': []},
            {'id': 'T2', 'title': 'Expansion', 'instructions': 'Extend core', 'depends_on': ['T1'], 'requirements': ['R1'], 'criteria': ['Extended'], 'checks': []}],
            'experience_checkpoint': {'task_id': 'T1', 'goal': 'Try core', 'evaluation': ['Observe the complete journey']},
            'verification_commands': [], 'browser_required': False}
        complete_fixture(self.store, 'plan', plan=plan)
        complete_fixture(self.store, 'T1', approve=False)
        self.assertEqual(self.store.task('T1')['status'], 'awaiting_approval')
        with self.assertRaises(WorkflowError):
            self.store.begin('T2', 'work')
        self.store.decide('T1', 'approve', 'Synthetic owner', 'Core approved in test')
        self.assertEqual(self.store.next_task()['id'], 'T2')

    def test_native_submit_preserves_the_product_browser_gate(self):
        from product_cycle.fixtures import prepare_plan, complete_fixture
        prepare_plan(self.store, {'tasks': [
            {'id': 'T1', 'title': 'Core', 'instructions': 'Usable journey', 'depends_on': [], 'requirements': ['R1'], 'criteria': ['Usable'], 'checks': []}],
            'verification_commands': [], 'browser_required': True})
        complete_fixture(self.store, 'T1')
        request = run_cycle(self.store)
        desktop.bind(self.store, 'verify', request['attempt'], 'worker', self.peer())
        path = Path(request['result_path']).parent / 'acceptance.md'
        path.write_text('# Synthetic worker claims; no operator observation')
        relative = str(path.relative_to(self.store.project))
        write_json(request['result_path'], {'summary': 'Unobserved UI', 'artifacts': [
            {'path': relative, 'purpose': 'Synthetic worker report', 'criteria': ['C1', 'C2'], 'requirements': ['R1']}],
            'steps': [{'id': step['id'], 'summary': 'Synthetic claim', 'artifacts': [relative]} for step in work_steps('verify')],
            'limitations': ['No operator observation'], 'blocker': None})
        with self.assertRaisesRegex(WorkflowError, 'thiếu bằng chứng'):
            desktop.submit(self.store, 'verify', request['attempt'], request['result_path'])
        self.assertEqual(self.store.task('verify')['status'], 'blocked')
        self.assertEqual(self.store.task('handoff')['status'], 'pending')

    def test_local_usage_reader_checks_identity_and_location(self):
        home = self.base / 'codex'
        sessions = home / 'sessions'
        sessions.mkdir(parents=True)
        path = sessions / 'synthetic.jsonl'
        records = [{'type': 'session_meta', 'payload': {'id': 'worker', 'cwd': str(self.store.project)}},
                   {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': {'total_tokens': 123}}}}]
        path.write_text('\n'.join(json.dumps(row) for row in records))
        thread = {'id': 'worker', 'cwd': str(self.store.project), 'path': str(path)}
        with patch.dict(os.environ, CODEX_HOME=str(home)):
            self.assertEqual(local_thread_usage(thread), 123)
            self.assertIsNone(local_thread_usage(dict(thread, id='other')))
            self.assertIsNone(local_thread_usage(dict(thread, path=str(self.base / 'elsewhere.jsonl'))))
