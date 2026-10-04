"""Local dashboard; same-origin controls; only registered evidence is exposed."""

import json
import mimetypes
import secrets
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .contracts import WorkflowError, require
from .store import Store, runner_lock
from . import desktop
from .codex import CodexClient


def serve(project, port=8787):
    token = secrets.token_urlsafe(32)
    project = str(Path(project).resolve())
    stopped = threading.Event()

    def sync_chats():
        from .runner import sync_task, continue_task, run_cycle
        failures = {}
        while not stopped.wait(15):
            advance = False
            store = Store(project)
            try:
                if store.config["mode"] != "live" or store.snapshot()["state"] != "active":
                    continue
                with runner_lock(store):
                    if desktop.enabled(store):
                        desktop.sync_usage(store)
                    for task in store.tasks():
                        if task["status"] not in {"blocked", "running", "reviewing"} or not task["attempts"]:
                            continue
                        if desktop.enabled(store) and not desktop.latest(store, task["id"])["thread_id"]:
                            continue
                        try:
                            outcome = sync_task(store, task["id"])
                            if outcome["updated"] and store.task(task["id"])["status"] in {"reviewing", "done"}:
                                advance = not desktop.enabled(store)
                                if store.task(task["id"])["status"] == "reviewing":
                                    if desktop.enabled(store):
                                        from .runner import finish_work
                                        attempt = desktop.latest(store, task["id"])
                                        finish_work(store, task["id"], attempt["id"], Path(attempt["directory"]), CodexClient)
                                    else:
                                        continue_task(store, task["id"])
                            failures.pop(task["id"], None)
                        except (WorkflowError, OSError) as exc:
                            if failures.get(task["id"]) != str(exc):
                                store.event(task["id"], "continuation.waiting", {"reason": str(exc)})
                                failures[task["id"]] = str(exc)
                if advance:
                    run_cycle(store)
            except (WorkflowError, OSError):
                # Another controller may own the lock; never race its state or execution.
                pass
            finally:
                store.close()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, value, content_type="application/json; charset=utf-8"):
            body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get("Host") in {"127.0.0.1:" + str(self.server.server_port), "localhost:" + str(self.server.server_port)}

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, {"error": "Không thể truy cập bảng điều khiển từ địa chỉ này."})
            route = urlparse(self.path).path
            if route == "/":
                return self.reply(200, (Path(__file__).parent / "web" / "dashboard.html").read_bytes(), "text/html; charset=utf-8")
            if route == "/dashboard.css":
                return self.reply(200, (Path(__file__).parent / "web" / "dashboard.css").read_bytes(), "text/css; charset=utf-8")
            if route == "/evidence-reader.js":
                return self.reply(200, (Path(__file__).parent / "web" / "evidence-reader.js").read_bytes(), "text/javascript; charset=utf-8")
            if route in {"/workflow-canvas.js", "/screens-view.js"}:
                return self.reply(200, (Path(__file__).parent / "web" / route[1:]).read_bytes(), "text/javascript; charset=utf-8")
            store = Store(project)
            try:
                if route == "/api/state":
                    state = store.snapshot()
                    state["control_token"] = token
                    return self.reply(200, state)
                if route.startswith("/evidence/"):
                    eid = route.rsplit("/", 1)[-1]
                    row = store.db.execute("SELECT * FROM evidence WHERE id=?", (eid,)).fetchone()
                    require(row is not None, "Không tìm thấy bằng chứng.")
                    store.intact([dict(row)])
                    mime = mimetypes.guess_type(row["source"])[0]
                    safe_mime = mime if mime in {"image/png", "image/jpeg", "image/webp", "application/pdf"} else "text/plain; charset=utf-8"
                    return self.reply(200, (store.root / row["object_path"]).read_bytes(), safe_mime)
                self.reply(404, {"error": "Không tìm thấy nội dung."})
            except WorkflowError as exc:
                self.reply(400, {"error": str(exc)})
            finally:
                store.close()

        def do_POST(self):
            origin = self.headers.get("Origin")
            if not self.valid_host() or self.headers.get("X-Product-Cycle-Token") != token or origin not in {None, "http://" + self.headers.get("Host", "")}:
                return self.reply(403, {"error": "Phiên điều khiển chưa hợp lệ. Hãy tải lại trang."})
            route = urlparse(self.path).path
            store = Store(project)
            try:
                require(not store.config.get("dashboard_read_only", False), "Thực hiện trao đổi và quyết định trong Codex. Dashboard chỉ hiển thị kết quả.")
                length = int(self.headers.get("Content-Length", "0"))
                require(0 < length <= 16384, "Thông tin gửi lên chưa hợp lệ.")
                data = json.loads(self.rfile.read(length))
                require(isinstance(data, dict), "Thông tin gửi lên chưa hợp lệ.")
                if route in {"/api/pause", "/api/resume"}:
                    store.pause(route.endswith("pause"))
                elif route == "/api/decision":
                    with runner_lock(store):
                        store.decide(data["task"], data["action"], data["actor"], data["note"])
                elif route == "/api/reopen":
                    with runner_lock(store):
                        store.reopen(data["task"], data["note"])
                elif route in {"/api/run", "/api/continue", "/api/sync"}:
                    with runner_lock(store):
                        require(store.config["mode"] == "live", "Dữ liệu minh họa chỉ dùng để xem quy trình.")
                        if route != "/api/sync":
                            require(store.snapshot()["state"] == "active", "Bỏ tạm dừng trước khi tiếp tục quy trình.")
                        if route != "/api/run":
                            store.task(data["task"])
                    command = [sys.executable, "-m", "product_cycle"]
                    command += ["run", "--project", project, "--continue-blocked"] if route == "/api/run" else [
                        "continue" if route == "/api/continue" else "sync", "--project", project, "--task", data["task"]]
                    logfile = (store.root / "controller.log").open("ab")
                    try:
                        subprocess.Popen(command,
                                         cwd=Path(__file__).parent.parent, stdout=logfile, stderr=subprocess.STDOUT, start_new_session=True)
                    finally:
                        logfile.close()
                else:
                    return self.reply(404, {"error": "Không tìm thấy thao tác."})
                self.reply(200, {"ok": True})
            except WorkflowError as exc:
                self.reply(400, {"error": str(exc)})
            except (ValueError, KeyError, TypeError):
                self.reply(400, {"error": "Chưa thực hiện được thao tác. Kiểm tra trạng thái và thông tin quyết định."})
            finally:
                store.close()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=sync_chats, daemon=True, name="product-cycle-chat-sync").start()
    print("Product Cycle: http://127.0.0.1:" + str(server.server_port) + "/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stopped.set()
        server.server_close()
