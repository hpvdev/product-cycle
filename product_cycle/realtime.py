"""One read-only state watcher shared by dashboard event-stream subscribers."""
import json
import threading
import time

from .store import Store


class StateFeed:
    def __init__(self, project, token, stopped, interval=.5):
        self.project, self.token, self.stopped, self.interval = project, token, stopped, interval
        self.condition = threading.Condition()
        self.subscribers = 0
        self.version = 0
        self.event = None
        self.payload = None
        self.last_read = 0
        self.thread = threading.Thread(target=self.watch, daemon=True, name='product-cycle-state-feed')
        self.thread.start()

    def subscribe(self):
        with self.condition:
            if time.monotonic() - self.last_read > 1:
                self.payload = None
            self.subscribers += 1
            self.condition.notify_all()

    def unsubscribe(self):
        with self.condition:
            self.subscribers -= 1

    def read(self, version, timeout=5):
        with self.condition:
            self.condition.wait_for(lambda: self.payload is not None and self.version != version or self.stopped.is_set(), timeout)
            return self.version, self.event, self.payload

    def watch(self):
        while not self.stopped.is_set():
            with self.condition:
                self.condition.wait_for(lambda: self.subscribers or self.stopped.is_set(), .5)
                if not self.subscribers:
                    continue
            store = None
            try:
                store = Store(self.project)
                state = store.snapshot()
                state['control_token'] = self.token
                event, payload = 'state', json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            except Exception:
                # Keep failures visible, without exposing internal errors or claiming fresh data.
                event, payload = 'unavailable', json.dumps({'message': 'Chưa nhận được trạng thái mới. Đang kết nối lại.'}, ensure_ascii=False)
            finally:
                if store:
                    store.close()
            with self.condition:
                self.last_read = time.monotonic()
                if (event, payload) != (self.event, self.payload):
                    self.version += 1
                    self.event, self.payload = event, payload
                    self.condition.notify_all()
            self.stopped.wait(self.interval)
        with self.condition:
            self.condition.notify_all()
