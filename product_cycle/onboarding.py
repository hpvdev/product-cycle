"""Office-first onboarding; preparation is distinct from starting AI work."""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from .contracts import require
from .store import write_json, now


def connected(project, url):
    if not isinstance(url, str) or not re.fullmatch(r'http://127\.0\.0\.1:[0-9]+/?', url):
        return False
    try:
        with urlopen(url.rstrip('/') + '/api/state', timeout=1) as response:
            state = json.load(response)
        return Path(state.get('project', '')).resolve() == project.resolve()
    except (OSError, ValueError):
        return False


def open_dashboard(store, port=0):
    require(isinstance(port, int) and 0 <= port <= 65535, "Chọn cổng hợp lệ để mở văn phòng.")
    registry = store.root / 'onboarding-runtime.json'
    runtime = json.loads(registry.read_text()) if registry.is_file() else {}
    if connected(store.project, runtime.get('dashboard_url')):
        return runtime['dashboard_url']
    path = store.root / 'dashboard.log'
    with path.open('ab') as logfile:
        offset = logfile.tell()
        process = subprocess.Popen([sys.executable, '-m', 'product_cycle', 'serve', '--project', str(store.project), '--port', str(port)],
            cwd=Path(__file__).resolve().parent.parent, stdout=logfile, stderr=logfile, start_new_session=True)
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        with path.open('rb') as logfile:
            logfile.seek(offset)
            text = logfile.read().decode('utf-8', errors='replace')
        match = re.search(r'Product Cycle: (http://127\.0\.0\.1:[0-9]+/)', text)
        if match and connected(store.project, match[1]):
            runtime.update(dashboard_url=match[1], dashboard_pid=process.pid, updated_at=now())
            write_json(registry, runtime)
            return match[1]
        time.sleep(.1)
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
    require(False, "Chưa mở được văn phòng. Kiểm tra cổng đang dùng và thử lại; dự án được giữ nguyên.")


def submit_request(store, brief):
    require(store.config.get('awaiting_request') is True, "Dự án đã nhận yêu cầu. Trao đổi bổ sung trong chat dự án thay vì khởi tạo lại.")
    require(isinstance(brief, str) and brief.strip(), "Hãy mô tả sản phẩm bạn muốn công ty thực hiện.")
    require(not store.db.execute('SELECT id FROM attempts LIMIT 1').fetchone(), "Dự án đã có phiên thực hiện; giữ lịch sử và dùng luồng cập nhật yêu cầu.")
    (store.root / 'brief.md').write_text(brief.rstrip() + '\n')
    write_json(store.root / 'config.json', dict(store.config, awaiting_request=False))
    with store.db:
        store.db.execute("UPDATE meta SET value='0' WHERE key='onboarding.awaiting_request'")
        store.db.execute("UPDATE meta SET value='active' WHERE key='state'")
    store.event('analysis', 'onboarding.request_received', {'source': 'owner', 'summary': brief[:500]})


def bind_owner_chat(store, thread_id, client_factory=None):
    from .codex import CodexClient
    require(isinstance(thread_id, str) and thread_id.strip() and len(thread_id) <= 150,
            "Cần danh tính thật của chat chủ sản phẩm.")
    require(not store.db.execute('SELECT id FROM team_runs WHERE thread_id=?', (thread_id,)).fetchone(),
            "Chọn chat chủ sản phẩm thay vì phiên worker chạy nền.")
    directory = store.root / 'owner-chat-check'
    directory.mkdir(exist_ok=True)
    with (client_factory or CodexClient)(directory) as client:
        deadline = time.monotonic() + 10
        client.initialize(deadline)
        thread = client.request('thread/read', {'threadId': thread_id, 'includeTurns': False}, deadline)['thread']
    require(thread.get('id') == thread_id and Path(thread.get('cwd', '')).resolve() == store.project,
            "Chat chưa thuộc dự án này. Mở chat Codex trong đúng thư mục dự án để liên kết.")
    write_json(store.root / 'config.json', dict(store.config, owner_chat={'thread_id': thread_id, 'verified_at': now()}))
    store.event(None, 'onboarding.owner_chat_bound', {'thread_id': thread_id})


def start_team(store):
    from .team import supervisor_active, enabled
    require(not store.config.get('awaiting_request'), "Văn phòng đang chờ yêu cầu của bạn; chưa giao việc cho nhân viên.")
    require(store.config['mode'] == 'live' and enabled(store), "Dự án cần chế độ đội ngũ thực tế để khởi động công ty.")
    require(store.db.execute("SELECT value FROM meta WHERE key='state'").fetchone()[0] == 'active', "Dự án đang tạm dừng. Tiếp tục dự án trước khi giao việc.")
    if supervisor_active(store):
        return
    require(not store.db.execute("SELECT a.id FROM attempts a WHERE a.status IN ('running','queued') AND NOT EXISTS(SELECT 1 FROM team_runs r WHERE r.attempt_id=a.id)").fetchone(),
            "Có chat đang thực hiện công việc này. Kết thúc hoặc đối chiếu chat đó trước khi bật đội ngũ.")
    # The supervisor owns its process lock. Never hold runner.lock across process launch.
    if supervisor_active(store):
        return
    with (store.root / 'supervisor.log').open('ab') as logfile:
        process = subprocess.Popen([sys.executable, '-m', 'product_cycle', 'supervise', '--project', str(store.project)],
            cwd=Path(__file__).resolve().parent.parent, stdout=logfile, stderr=logfile, start_new_session=True)
    # The child needs the runner lock to initialize. Observe it after releasing our lock.
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        row = store.db.execute("SELECT pid,status,last_heartbeat FROM team_supervisor WHERE id=1").fetchone()
        if process.poll() is not None:
            break
        if supervisor_active(store) and row and row['pid'] == process.pid and row['last_heartbeat'] and row['status'] in {'running', 'waiting'}:
            return
        time.sleep(.1)
    require(False, 'Chưa xác nhận điều phối đã khởi động. Kiểm tra nhật ký và trạng thái trước khi chạy lại.')


def summary(store, dashboard_url=None):
    snapshot = store.snapshot()
    waiting = store.config.get('awaiting_request', False)
    registry = store.root / 'onboarding-runtime.json'
    if not dashboard_url and registry.is_file():
        dashboard_url = json.loads(registry.read_text()).get('dashboard_url')
    linked = bool(dashboard_url and connected(store.project, dashboard_url))
    team = snapshot['team']
    chats = {}
    for task in snapshot['tasks']:
        for attempt in task['attempt_history']:
            if attempt.get('thread_id'):
                chats[attempt['thread_id']] = {'name': task['title'], 'url': 'codex://threads/' + attempt['thread_id']}
    for agent in team['agents']:
        if agent.get('thread_id'):
            chats[agent['thread_id']] = {'name': agent['name'], 'url': 'codex://threads/' + agent['thread_id']}
    return {'name': store.config['name'], 'project': str(store.project),
        'status': 'awaiting_request' if waiting else 'running' if team['supervisor']['active'] else 'ready_to_start',
        'dashboard_url': dashboard_url if linked else None, 'dashboard_connected': linked,
        'execution_active': team['supervisor']['active'], 'chats': list(chats.values()),
        'owner_chat_url': 'codex://threads/' + store.config['owner_chat']['thread_id'] if store.config.get('owner_chat') else None,
        'foundation': snapshot['foundation'], 'models': store.config['models'],
        'next_action': 'Mở văn phòng và giao yêu cầu trong chat Codex. Nhân viên đang chờ nhận việc.' if waiting else
            'Theo dõi nhân viên trong văn phòng và trao đổi với đội phân tích trong Codex.' if team['supervisor']['active'] else
            'Yêu cầu đã được ghi nhận. Khởi động đội ngũ để bắt đầu phân tích; xem trạng thái kết nối trên dashboard.',
        'note': 'Văn phòng mở được không chứng minh nhân viên đang chạy. Ảnh và trình duyệt cần công cụ thật trong chat được giao.'}
