"""Authentic project discussions. Conclusions are advice, never task acceptance."""
import json
import uuid

from .contracts import require
from .store import now

BLOCKER_PREFIX = "Chờ trao đổi: "
ACTIVE = ('preparing', 'dispatching', 'running', 'checking', 'unknown', 'backoff')


def migrate(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS team_discussions(
          id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, revision INTEGER NOT NULL,
          owner_run_id TEXT NOT NULL REFERENCES team_runs(id), title TEXT NOT NULL,
          kind TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS team_discussion_posts(
          id INTEGER PRIMARY KEY, discussion_id INTEGER NOT NULL REFERENCES team_discussions(id),
          sender_run_id TEXT NOT NULL REFERENCES team_runs(id), sender_agent_id TEXT NOT NULL,
          kind TEXT NOT NULL, text TEXT NOT NULL, mentions TEXT NOT NULL, evidence TEXT NOT NULL,
          client_key TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(sender_run_id,client_key));
        CREATE TABLE IF NOT EXISTS team_discussion_requests(
          request_id TEXT PRIMARY KEY REFERENCES team_requests(id),
          discussion_id INTEGER NOT NULL REFERENCES team_discussions(id), purpose TEXT NOT NULL);
    """)


def pending(store, task_id):
    return store.db.execute("""SELECT d.* FROM team_discussions d JOIN tasks t ON t.id=d.task_id
        WHERE d.task_id=? AND d.revision=t.revision AND d.status IN ('open','needs_attention')
        ORDER BY d.id LIMIT 1""", (task_id,)).fetchone()


def _read(store, did):
    require(isinstance(did, int) and not isinstance(did, bool), "Chọn cuộc trao đổi đã được ghi nhận.")
    row = store.db.execute("SELECT * FROM team_discussions WHERE id=?", (did,)).fetchone()
    require(row is not None, "Không tìm thấy cuộc trao đổi.")
    result = dict(row)
    task = store.task(result['task_id'])
    result['task_title'] = task['title']
    if task['revision'] != result['revision']:
        result['status'] = 'stale'
    result['owner_agent_id'] = store.db.execute("SELECT agent_id FROM team_runs WHERE id=?", (row['owner_run_id'],)).fetchone()[0]
    result['posts'] = []
    for post in store.db.execute("SELECT * FROM team_discussion_posts WHERE discussion_id=? ORDER BY id", (did,)):
        post = dict(post)
        post['mentions'], post['evidence'] = json.loads(post['mentions']), json.loads(post['evidence'])
        result['posts'].append(post)
    result['requests'] = [dict(r) for r in store.db.execute("""SELECT q.id,q.agent_id,q.status,q.run_id,l.purpose
        FROM team_discussion_requests l JOIN team_requests q ON q.id=l.request_id
        WHERE l.discussion_id=? ORDER BY q.rowid""", (did,))]
    return result


def page(store, after=0, limit=50):
    require(isinstance(after, int) and after >= 0 and isinstance(limit, int) and 1 <= limit <= 100,
            "Mốc đọc trao đổi chưa hợp lệ.")
    ids = [r[0] for r in store.db.execute("SELECT id FROM team_discussions WHERE id>? ORDER BY id LIMIT ?", (after, limit + 1))]
    return {'items': [_read(store, did) for did in ids[:limit]],
            'cursor': ids[min(limit, len(ids)) - 1] if ids else after, 'has_more': len(ids) > limit}


def by_ids(store, ids):
    require(isinstance(ids, list) and 0 < len(ids) <= 100 and all(isinstance(did, int) and not isinstance(did, bool) and did > 0 for did in ids),
            "Chọn các cuộc trao đổi đã được ghi nhận.")
    return {'items': [_read(store, did) for did in dict.fromkeys(ids)]}


def recent(store, task_id=None):
    scope = " WHERE task_id=? AND revision=(SELECT revision FROM tasks WHERE id=?)" if task_id else ""
    args = (task_id, task_id) if task_id else ()
    sql = "SELECT id FROM team_discussions" + scope
    ids = [r[0] for r in store.db.execute(sql + " ORDER BY id DESC LIMIT 50", args)]
    active_sql = sql + (" AND" if task_id else " WHERE") + " status IN ('open','needs_attention') AND revision=(SELECT revision FROM tasks WHERE tasks.id=team_discussions.task_id)"
    ids = sorted(set(ids) | {r[0] for r in store.db.execute(active_sql, args)}, reverse=True)
    return [_read(store, did) for did in ids]


def _references(store, evidence):
    require(isinstance(evidence, list) and len(evidence) <= 20 and all(isinstance(eid, str) for eid in evidence),
            "Bằng chứng cần là danh sách đã được ghi nhận.")
    for eid in evidence:
        row = store.db.execute("SELECT * FROM evidence WHERE id=?", (eid,)).fetchone()
        require(row is not None, "Bằng chứng chưa được ghi nhận.")
        store.intact([dict(row)])


def _identity(team, rid):
    from .team import company_enabled
    run = team.validate_origin(rid)
    require(company_enabled(team.store) and run['phase'] not in {'review', 'improve_review'},
            "Trao đổi nhóm dành cho nhân viên thực hiện; review giữ phiên độc lập.")
    return run


def _queue(team, thread, sender, recipient, key, purpose, prompt):
    """Internal durable request; synthesis is a fresh consultation of the owner role."""
    rid = 'request-' + uuid.uuid4().hex
    team.db.execute("""INSERT INTO team_requests(id,sender_run_id,task_id,revision,agent_id,kind,prompt,status,client_key,created_at)
        VALUES(?,?,?,?,?,'consult',?,'queued',?,?)""",
        (rid, sender['id'], thread['task_id'], thread['revision'], recipient, prompt, key, now()))
    team.db.execute("INSERT INTO team_discussion_requests VALUES(?,?,?)", (rid, thread['id'], purpose))


def post(team, rid, title, text, kind, mentions, evidence, client_key, discussion_id=None):
    from .team import employee_role
    run = _identity(team, rid)
    require(kind in {'question', 'answer', 'update', 'handoff'}, "Chọn câu hỏi, trả lời, cập nhật hoặc bàn giao.")
    require(isinstance(text, str) and 0 < len(text.strip()) <= 8000 and isinstance(client_key, str) and 0 < len(client_key) <= 100,
            "Trao đổi cần nội dung và mã gửi riêng.")
    require(isinstance(mentions, list) and len(mentions) <= 10 and all(isinstance(m, str) for m in mentions)
            and len(set(mentions)) == len(mentions), "Chọn các đồng nghiệp cần trao đổi.")
    require(isinstance(title, str) and (discussion_id is not None or 0 < len(title.strip()) <= 200), "Cần tiêu đề ngắn cho cuộc trao đổi.")
    _references(team.store, evidence)
    with team.db:
        team.db.execute('BEGIN IMMEDIATE')
        old = team.db.execute("SELECT * FROM team_discussion_posts WHERE sender_run_id=? AND client_key=?", (rid, client_key)).fetchone()
        if old:
            thread = _read(team.store, old['discussion_id'])
            require((old['text'], old['kind'], json.loads(old['mentions']), json.loads(old['evidence'])) == (text, kind, mentions, evidence)
                    and (discussion_id == thread['id'] if discussion_id is not None else thread['title'] == title and old['kind'] != 'conclusion'),
                    "Mã gửi đã dùng cho một trao đổi khác.")
            return thread
        if discussion_id is None:
            require(kind in {'question', 'update', 'handoff'}, "Mở chủ đề bằng câu hỏi, cập nhật hoặc bàn giao.")
            # Consultations belong to the actual primary mission of this attempt.
            owner = team.db.execute("SELECT * FROM team_runs WHERE task_id=? AND revision=? AND attempt_id IS ? AND phase='work' ORDER BY rowid DESC LIMIT 1",
                                    (run['task_id'], run['revision'], run['attempt_id'])).fetchone()
            owner_id = owner['id'] if owner else rid
            cur = team.db.execute("INSERT INTO team_discussions(task_id,revision,owner_run_id,title,kind,status,created_at) VALUES(?,?,?,?,?,?,?)",
                    (run['task_id'], run['revision'], owner_id, title, kind, 'open' if kind == 'question' else 'informational', now()))
            discussion_id = cur.lastrowid
        thread = _read(team.store, discussion_id)
        require(thread['status'] in {'open', 'informational'} and thread['task_id'] == run['task_id'] and thread['revision'] == run['revision'],
                "Trao đổi đã chốt hoặc thuộc phạm vi khác; mở chủ đề cho công việc hiện tại.")
        if kind == 'question':
            require(team.store.task(run['task_id'])['status'] in {'running', 'blocked'},
                    "Phần việc đã chuyển sang kiểm chứng; không mở thêm câu hỏi cho bản đã nộp.")
            require(not team.db.execute("SELECT 1 FROM team_runs WHERE task_id=? AND revision=? AND phase='review' AND status IN ('dispatching','running','checking','unknown')",
                                        (run['task_id'], run['revision'])).fetchone(), "Review đang kiểm chứng bản đã nộp; giữ trao đổi độc lập.")
            require(not team.db.execute("SELECT 1 FROM team_discussion_requests WHERE request_id=? AND purpose='synthesize'", (run['request_id'],)).fetchone(),
                    "Phiên tổng hợp cần chốt chủ đề đã giao hoặc nêu vấn đề cần xử lý.")
            require(thread['status'] == 'open', "Câu hỏi cần một chủ đề chưa chốt.")
        for recipient in mentions:
            require(recipient in {a['id'] for a in team.roster()} and recipient != run['agent_id'], "Đồng nghiệp được gọi chưa hợp lệ.")
            role = employee_role(team.store, recipient)
            require(role['kind'] != 'reviewer' and team.store.task(thread['task_id'])['stage'] in role['stages'],
                    "Chọn chuyên gia phù hợp; reviewer không tham gia thảo luận của người làm.")
        cur = team.db.execute("INSERT INTO team_discussion_posts(discussion_id,sender_run_id,sender_agent_id,kind,text,mentions,evidence,client_key,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (discussion_id, rid, run['agent_id'], kind, text, json.dumps(mentions), json.dumps(evidence), client_key, now()))
        if kind == 'question':
            for recipient in mentions:
                _queue(team, thread, run, recipient, 'discussion:' + str(cur.lastrowid) + ':' + recipient, 'reply',
                       'Answer the specific question in project discussion ' + str(discussion_id) + '. Read it using team_read_discussions. '
                       'Use team_reply_discussion to publish your reasoning, concrete recommendation and limits; do not approve the task.\n' + text)
    team.event('discussion.posted', run, discussion_id=discussion_id, post_id=cur.lastrowid)
    return _read(team.store, discussion_id)


def resolve(team, rid, did, summary, evidence, client_key):
    run = _identity(team, rid)
    require(isinstance(summary, str) and 0 < len(summary.strip()) <= 8000 and isinstance(client_key, str) and 0 < len(client_key) <= 100,
            "Kết luận cần hành động cụ thể và mã gửi riêng.")
    _references(team.store, evidence)
    with team.db:
        team.db.execute('BEGIN IMMEDIATE')
        thread = _read(team.store, did)
        require(thread['task_id'] == run['task_id'] and thread['revision'] == run['revision'], "Không chốt trao đổi thuộc phạm vi cũ.")
        synthesis = team.db.execute("SELECT 1 FROM team_discussion_requests WHERE request_id=? AND discussion_id=? AND purpose='synthesize'", (run['request_id'], did)).fetchone()
        require(rid == thread['owner_run_id'] or synthesis, "Người phụ trách chủ đề hoặc phiên tổng hợp được giao mới được chốt.")
        old = team.db.execute("SELECT * FROM team_discussion_posts WHERE sender_run_id=? AND client_key=?", (rid, client_key)).fetchone()
        if old:
            require(old['discussion_id'] == did and old['kind'] == 'conclusion' and old['text'] == summary and json.loads(old['evidence']) == evidence,
                    "Mã kết luận đã dùng cho nội dung khác.")
            return thread
        require(thread['status'] == 'open', "Chủ đề này chưa thể chốt lại.")
        require(not any(q['status'] not in {'completed', 'blocked', 'cancelled'} and q['id'] != run['request_id'] for q in thread['requests']),
                "Chờ các chuyên gia trả lời hoặc xác định kết quả trước khi chốt.")
        team.db.execute("INSERT INTO team_discussion_posts(discussion_id,sender_run_id,sender_agent_id,kind,text,mentions,evidence,client_key,created_at) VALUES(?,?,?,'conclusion',?,'[]',?,?,?)",
                        (did, rid, run['agent_id'], summary, json.dumps(evidence), client_key, now()))
        team.db.execute("UPDATE team_discussions SET status='resolved' WHERE id=?", (did,))
    team.event('discussion.resolved', run, discussion_id=did)
    return _read(team.store, did)


def consultation_complete(team, run, result):
    link = team.db.execute("SELECT * FROM team_discussion_requests WHERE request_id=?", (run['request_id'],)).fetchone()
    if not link:
        return False
    thread = _read(team.store, link['discussion_id'])
    if thread['status'] == 'open':
        # A real returned consultation is shown even if it did not call the posting tool.
        exists = team.db.execute("SELECT 1 FROM team_discussion_posts WHERE discussion_id=? AND sender_run_id=? AND kind='answer'", (thread['id'], run['id'])).fetchone()
        if not exists:
            text = '\n'.join([result['summary'], *result['findings'], *result['limitations'], *([result['blocker']] if result['blocker'] else [])])[:8000]
            post(team, run['id'], '', text, 'answer', [], [], 'consult-result', thread['id'])
        if link['purpose'] == 'synthesize':
            # Never infer resolution from a free-form result; the authorized tool records it.
            with team.db:
                team.db.execute("UPDATE team_discussions SET status='needs_attention' WHERE id=? AND status='open'", (thread['id'],))
    return True


def maintain(team):
    """Schedule one bounded synthesis after actual replies, then resume only its dependency."""
    store = team.store
    with team.db:
        team.db.execute('BEGIN IMMEDIATE')
        for row in team.db.execute("SELECT d.* FROM team_discussions d JOIN tasks t ON t.id=d.task_id AND t.revision=d.revision WHERE d.status='open'").fetchall():
            thread = _read(store, row['id'])
            owner = team.run(thread['owner_run_id'])
            if owner['status'] in ACTIVE or any(q['status'] not in {'completed', 'blocked', 'cancelled'} for q in thread['requests']):
                continue
            if any(q['purpose'] == 'synthesize' for q in thread['requests']):
                team.db.execute("UPDATE team_discussions SET status='needs_attention' WHERE id=?", (thread['id'],))
                continue
            task = store.task(thread['task_id'])
            if owner['attempt_id']:
                a = team.db.execute("SELECT number FROM attempts WHERE id=?", (owner['attempt_id'],)).fetchone()
                if not a or a['number'] != task['attempts']:
                    team.db.execute("UPDATE team_discussions SET status='needs_attention' WHERE id=?", (thread['id'],))
                    continue
            _queue(team, thread, owner, owner['agent_id'], 'discussion-synthesis:' + str(thread['id']), 'synthesize',
                   'You are responsible for concluding project discussion ' + str(thread['id']) + '. '
                   'Read the genuine posts and accepted inputs. Resolve within accepted scope using team_resolve_discussion '
                   'with the chosen action, rationale, affected artifacts and remaining limits. No task approval. '
                   'If you cannot safely resolve, ask the owner only for a material missing decision, or report the precise blocker. '
                   'Do not open another discussion to avoid concluding this one.')
        for task in store.tasks():
            if task['status'] != 'blocked' or not (task['reason'] or '').startswith(BLOCKER_PREFIX) or pending(store, task['id']):
                continue
            if team.db.execute("SELECT 1 FROM team_runs WHERE task_id=? AND revision=? AND status IN ('preparing','dispatching','running','checking','unknown','backoff')", (task['id'], task['revision'])).fetchone():
                continue
            question = team.db.execute("""SELECT q.question FROM company_questions q JOIN team_runs r ON r.id=q.source_run_id
                LEFT JOIN attempts a ON a.id=r.attempt_id WHERE q.task_id=? AND q.revision=?
                AND (q.status='open' OR q.status='answered' AND q.consumed_at IS NULL
                     AND (r.attempt_id IS NULL OR a.number=? AND a.revision=?)) LIMIT 1""",
                (task['id'], task['revision'], task['attempts'], task['revision'])).fetchone()
            native = team.db.execute("SELECT prompt FROM capability_jobs WHERE task_id=? AND revision=? AND status IN ('queued','claimed','bound','unknown') LIMIT 1", (task['id'], task['revision'])).fetchone()
            if question or native:
                reason = 'Cần bạn trả lời: ' + question[0] if question else 'Chờ công cụ: ' + native[0][:240]
                team.db.execute('UPDATE tasks SET reason=? WHERE id=?', (reason, task['id']))
            else:
                team.db.execute("UPDATE tasks SET status='rework',reason=NULL WHERE id=?", (task['id'],))
                team.db.execute("INSERT INTO events(task_id,type,data,created_at) VALUES(?,'company.discussions.resumed',?,?)", (task['id'], json.dumps({'revision': task['revision']}), now()))
