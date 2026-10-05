"""Synthetic company-chat routing tests, not a product or real-model evaluation."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from product_cycle.contracts import WorkflowError
from product_cycle.store import Store, write_json
from product_cycle.team import TeamStore, Supervisor, handle_tool, apply_output, tool_specs, run_mission
from product_cycle import team_discussions as chat
from product_cycle import company_questions as questions
from product_cycle.company import management_jobs
from test_team import SyntheticProvider


class DiscussionProvider(SyntheticProvider):
    def run(self, *args, **options):
        result = super().run(*args, **options)
        store = Store(self.project)
        row = store.db.execute("""SELECT d.id FROM team_discussion_requests l JOIN team_discussions d ON d.id=l.discussion_id
            JOIN team_requests q ON q.id=l.request_id JOIN team_runs r ON r.request_id=q.id
            WHERE r.directory=? AND r.status='running' AND l.purpose='synthesize'""", (str(self.directory),)).fetchone()
        store.close()
        if row:
            options['tool_handler']({'tool': 'team_resolve_discussion', 'threadId': result['thread_id'],
                'turnId': result['turn_id'], 'arguments': {'discussion_id': row['id'],
                'summary': 'Use the accepted objective; update analysis with the specialist recommendation.',
                'evidence': '[]', 'client_key': 'synthesis'}})
        return result


class WorkerQuestionProvider(SyntheticProvider):
    def run(self, *args, **options):
        result = super().run(*args, **options)
        options['tool_handler']({'tool': 'team_open_discussion', 'threadId': result['thread_id'],
            'turnId': result['turn_id'], 'arguments': {'title': 'Objective for this increment',
            'text': 'Need advice before finalizing the increment.', 'kind': 'question',
            'mentions': '["product_manager"]', 'evidence': '[]', 'client_key': 'blocking-question'}})
        return result


class WorkerBlockedProvider(WorkerQuestionProvider):
    def run(self, *args, **options):
        result = super().run(*args, **options)
        result['result']['blocker'] = 'Missing authorized API access'
        return result


class DiscussionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.env = patch.dict(os.environ, PRODUCT_CYCLE_HOME=str(base / 'state'))
        self.env.start()
        self.store = Store.create(base / 'project', 'Synthetic company', 'Company', mode='demo', team=True)
        self.team = TeamStore(self.store)
        self.owner = self.mission()
        SyntheticProvider.project = self.store.project
        SyntheticProvider.threads, SyntheticProvider.calls, SyntheticProvider.mode = {}, [], 'success'

    def tearDown(self):
        self.store.close()
        self.env.stop()
        self.temp.cleanup()

    def mission(self, phase='work', agent=None, request=None):
        if phase == 'work':
            aid, directory = self.store.begin('analysis', phase)
        else:
            aid, directory = self.owner['attempt_id'], None
        run = self.team.create_run('analysis', phase, aid, directory, agent, request_id=request)
        self.team.update(run['id'], status='running', thread_id='thread-' + run['id'], turn_id='turn-1')
        return self.team.run(run['id'])

    def open(self, **kwargs):
        params = dict(title='Learning objective', text='Which accepted objective should guide this screen?',
                      kind='question', mentions=['product_manager'], evidence=[], client_key='question-1')
        params.update(kwargs)
        return chat.post(self.team, self.owner['id'], **params)

    def finish_owner(self, topic):
        self.team.update(self.owner['id'], status='completed')
        self.store.attempt_update(self.owner['attempt_id'], status='completed')
        self.store.update('analysis', status='blocked', reason=chat.BLOCKER_PREFIX + topic['title'])

    def test_mentions_queue_actual_consultation_and_deduplicate(self):
        topic = self.open()
        self.assertEqual(self.open()['id'], topic['id'])
        self.assertEqual(len(topic['posts']), 1)  # No invented answer.
        self.assertEqual(len(topic['requests']), 1)
        self.assertEqual(topic['requests'][0]['status'], 'queued')
        self.assertEqual(topic['requests'][0]['agent_id'], 'product_manager')
        with self.assertRaises(WorkflowError):
            self.open(text='Another question')
        with self.assertRaises(WorkflowError):
            self.open(mentions=['ba_reviewer'], client_key='bias-review')
        self.assertEqual(len(chat.page(self.store)['items']), 1)  # Invalid mention rolls back root.
        update = self.open(kind='update', mentions=['ux_researcher'], client_key='update')
        self.assertEqual(update['requests'], [])
        self.assertEqual(update['status'], 'informational')

    def test_independent_reviewer_and_forged_tool_cannot_participate(self):
        run = self.mission('review')
        names = {s['name'] for s in tool_specs(True)}
        self.assertNotIn('team_read_discussions', names)
        with self.assertRaises(WorkflowError):
            chat.post(self.team, run['id'], 'Bias', 'Claim success', 'update', [], [], 'bias')
        with self.assertRaises(WorkflowError):
            handle_tool(self.team, self.owner['id'], {'tool': 'team_read_discussions', 'arguments': {},
                        'threadId': self.owner['thread_id'], 'turnId': 'forged'})
        packet = handle_tool(self.team, run['id'], {'tool': 'team_context', 'arguments': {},
                             'threadId': run['thread_id'], 'turnId': run['turn_id']})
        self.assertNotIn('discussions', packet['context'])

    def test_terminal_reply_is_real_and_owner_synthesis_resumes_without_approval(self):
        topic = self.open()
        self.finish_owner(topic)
        self.assertEqual(list(management_jobs(self.store)), [])
        config = self.store.config
        config['mode'] = 'live'
        config['team']['max_concurrent'] = 1
        write_json(self.store.root / 'config.json', config)
        Supervisor(self.store, DiscussionProvider).run(once=True)
        topic = chat.page(self.store)['items'][0]
        self.assertEqual(topic['status'], 'resolved')
        self.assertEqual([p['kind'] for p in topic['posts']], ['question', 'answer', 'conclusion'])
        self.assertEqual([q['purpose'] for q in topic['requests']], ['reply', 'synthesize'])
        self.assertTrue(all(q['status'] == 'completed' for q in topic['requests']))
        self.assertTrue(all(c['readonly'] for c in SyntheticProvider.calls))
        self.assertEqual(len(SyntheticProvider.calls), 2)
        self.assertEqual(self.store.task('analysis')['status'], 'rework')
        self.assertIsNone(self.store.task('analysis')['accepted_at'])
        chat.maintain(self.team)
        self.assertEqual(self.store.task('analysis')['attempts'], 1)
        self.assertEqual(len(chat.page(self.store)['items'][0]['requests']), 2)

    def test_unknown_consultation_cannot_resolve_or_start_synthesis(self):
        topic = self.open()
        with self.assertRaises(WorkflowError):
            chat.resolve(self.team, self.owner['id'], topic['id'], 'Premature', [], 'resolve')
        self.finish_owner(topic)
        request = topic['requests'][0]
        run = self.mission('consult', 'product_manager', request['id'])
        self.team.update(run['id'], status='unknown')
        with self.store.db:
            self.store.db.execute("UPDATE team_requests SET status='running',run_id=? WHERE id=?", (run['id'], request['id']))
        chat.maintain(self.team)
        self.assertEqual(len(chat.page(self.store)['items'][0]['requests']), 1)
        self.assertEqual(self.store.task('analysis')['status'], 'blocked')

    def test_no_conclusion_becomes_attention_instead_of_infinite_chatter(self):
        topic = self.open(mentions=[])
        self.finish_owner(topic)
        config = self.store.config
        config['mode'] = 'live'
        write_json(self.store.root / 'config.json', config)
        Supervisor(self.store, SyntheticProvider).run(once=True)
        topic = chat.page(self.store)['items'][0]
        self.assertEqual(topic['status'], 'needs_attention')
        chat.maintain(self.team)
        self.assertEqual(len(chat.page(self.store)['items'][0]['requests']), 1)
        self.assertEqual(self.store.task('analysis')['status'], 'blocked')
        self.assertEqual(len(list(management_jobs(self.store))), 1)

    def test_answered_owner_question_still_waits_for_unresolved_group_dependency(self):
        topic = self.open(mentions=[])
        question = questions.ask(self.store, self.owner, 'Choose learning focus', ['Recall', 'Recognition'],
                                 'Recall', 'Missing goal', 'goal')
        self.finish_owner(topic)
        self.store.update('analysis', reason=questions.BLOCKER_PREFIX + question['question'])
        questions.answer(self.store, question['id'], 'Synthetic owner', 'Recall')
        questions.resume_answered(self.store)
        task = self.store.task('analysis')
        self.assertEqual(task['status'], 'blocked')
        self.assertTrue(task['reason'].startswith(chat.BLOCKER_PREFIX))
        self.assertEqual(task['attempts'], 1)

    def test_successful_work_cannot_enter_review_with_an_open_question(self):
        run_mission(self.store.project, self.owner['id'], WorkerQuestionProvider, threading.Event())
        task = self.store.task('analysis')
        self.assertEqual(self.team.run(self.owner['id'])['status'], 'completed')
        self.assertEqual(task['status'], 'blocked')
        self.assertTrue(task['reason'].startswith(chat.BLOCKER_PREFIX))
        self.assertTrue(self.store.current_evidence('analysis'))
        write_json(self.store.root / 'config.json', dict(self.store.config, mode='live'))
        supervisor = Supervisor(self.store, SyntheticProvider)
        try:
            self.assertEqual(list(supervisor.eligible()), [])
        finally:
            supervisor.pool.shutdown()

    def test_resolving_an_unrelated_discussion_preserves_access_blocker(self):
        run_mission(self.store.project, self.owner['id'], WorkerBlockedProvider, threading.Event())
        self.assertEqual(self.store.task('analysis')['reason'], 'Missing authorized API access')
        write_json(self.store.root / 'config.json', dict(self.store.config, mode='live'))
        Supervisor(self.store, DiscussionProvider).run(once=True)
        self.assertEqual(chat.page(self.store)['items'][0]['status'], 'resolved')
        self.assertEqual(self.store.task('analysis')['status'], 'blocked')
        self.assertEqual(self.store.task('analysis')['reason'], 'Missing authorized API access')

    def test_late_question_cannot_change_submitted_or_accepted_work(self):
        self.store.update('analysis', status='reviewing')
        with self.assertRaises(WorkflowError):
            self.open()
        self.assertEqual(chat.page(self.store)['items'], [])

    def test_stale_threads_remain_history_and_never_resume_a_new_scope(self):
        topic = self.open(mentions=[])
        self.finish_owner(topic)
        self.store.reopen('analysis', 'New authorized scope')
        new_owner = self.mission()
        with self.assertRaises(WorkflowError):
            chat.post(self.team, new_owner['id'], '', 'Old context', 'answer', [], [], 'old', topic['id'])
        self.assertEqual(chat.page(self.store)['items'][0]['status'], 'stale')
        self.assertEqual(chat.recent(self.store, 'analysis'), [])
        chat.maintain(self.team)
        self.assertIsNone(chat.pending(self.store, 'analysis'))
        self.assertEqual(self.store.task('analysis')['status'], 'running')

    def test_open_topics_remain_visible_beyond_recent_history(self):
        topic = self.open(mentions=[])
        for i in range(51):
            self.open(kind='update', mentions=[], client_key='update-' + str(i), title='Update ' + str(i))
        self.assertIn(topic['id'], {t['id'] for t in chat.recent(self.store)})
        page = chat.page(self.store, limit=10)
        self.assertTrue(page['has_more'])
        self.assertEqual(page['cursor'], 10)
        self.assertEqual(len(chat.page(self.store, after=page['cursor'], limit=10)['items']), 10)
        chat.resolve(self.team, self.owner['id'], topic['id'], 'Use the accepted learning objective.', [], 'close')
        self.assertNotIn(topic['id'], {t['id'] for t in chat.recent(self.store)})
        updated = chat.by_ids(self.store, [topic['id']])['items'][0]
        self.assertEqual(updated['status'], 'resolved')
        self.assertEqual(updated['posts'][-1]['kind'], 'conclusion')


if __name__ == '__main__':
    unittest.main()
