"""Local dashboard; same-origin controls; only registered evidence is exposed."""

import json
import mimetypes
import secrets
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .contracts import WorkflowError, require
from .store import Store, runner_lock


def serve(project, port=8787):
    token = secrets.token_urlsafe(32)
    project = str(Path(project).resolve())

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
                elif route == "/api/run":
                    with runner_lock(store):
                        require(store.config["mode"] == "live", "Dữ liệu minh họa chỉ dùng để xem quy trình.")
                    logfile = (store.root / "controller.log").open("ab")
                    try:
                        subprocess.Popen([sys.executable, "-m", "product_cycle", "run", "--project", project],
                                         cwd=Path(__file__).parent.parent, stdout=logfile, stderr=subprocess.STDOUT, start_new_session=True)
                    finally:
                        logfile.close()
                else:
                    return self.reply(404, {"error": "Không tìm thấy thao tác."})
                self.reply(200, {"ok": True})
            except (WorkflowError, ValueError, KeyError, TypeError):
                self.reply(400, {"error": "Chưa thực hiện được thao tác. Kiểm tra trạng thái và thông tin quyết định."})
            finally:
                store.close()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("Product Cycle: http://127.0.0.1:" + str(server.server_port) + "/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
