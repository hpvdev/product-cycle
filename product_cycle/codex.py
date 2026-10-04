"""Codex App Server over stdio. No API key or global config changes required."""

import json
import os
import queue
import shutil
import signal
import subprocess
import threading
import time

from .contracts import WorkflowError, require
from . import __version__


class CodexClient:
    def __init__(self, directory, on_event=None, command=None):
        binary = os.environ.get("PRODUCT_CYCLE_CODEX") or shutil.which("codex")
        require(command is not None or binary, "Chưa tìm thấy Codex. Cài Codex hoặc đặt PRODUCT_CYCLE_CODEX.")
        self.on_event = on_event or (lambda event: None)
        self.messages = queue.Queue()
        self.counter = 0
        self.responses = {}
        self.notifications = []
        self.trace = (directory / "trace.jsonl").open("a", buffering=1)
        self.stderr = (directory / "stderr.log").open("a")
        self.process = subprocess.Popen(command or [binary, "app-server", "--stdio"],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.stderr, text=True, bufsize=1, start_new_session=True)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    self.messages.put(json.loads(line))
                except ValueError:
                    self.messages.put({"method": "client/invalidMessage", "params": {"line": line[:2000]}})
        finally:
            self.messages.put(None)

    def send(self, method, params, request=True):
        message = {"method": method, "params": params}
        if request:
            self.counter += 1
            message["id"] = self.counter
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        return message.get("id")

    def receive(self, deadline):
        remaining = deadline - time.monotonic()
        require(remaining > 0, "Phiên AI đã hết thời gian cho phép.")
        try:
            message = self.messages.get(timeout=remaining)
        except queue.Empty as exc:
            raise WorkflowError("Phiên AI đã hết thời gian cho phép.") from exc
        require(message is not None, "Kết nối Codex đã dừng; xem nhật ký phiên để xác định nguyên nhân.")
        self.trace.write(json.dumps(message, ensure_ascii=False) + "\n")
        if "id" in message and "method" in message:
            # Never silently approve a server request or invent a human answer.
            response = {"id": message["id"], "error": {"code": -32001, "message": "Product Cycle requires operator intervention for this request."}}
            self.process.stdin.write(json.dumps(response) + "\n")
            self.process.stdin.flush()
            self.on_event(message)
            raise WorkflowError("Codex cần tương tác: " + message["method"] + ". Yêu cầu đã được lưu trong nhật ký.")
        self.on_event(message)
        return message

    def request(self, method, params, deadline):
        rid = self.send(method, params)
        while rid not in self.responses:
            message = self.receive(deadline)
            if "id" in message:
                self.responses[message["id"]] = message
            else:
                self.notifications.append(message)
        response = self.responses.pop(rid)
        if "error" in response:
            raise WorkflowError("Codex từ chối " + method + ": " + str(response["error"].get("message", "Unknown error")))
        return response.get("result", {})

    def initialize(self, deadline):
        result = self.request("initialize", {"clientInfo": {"name": "product_cycle", "title": "Product Cycle", "version": __version__},
                                              "capabilities": {"experimentalApi": True}}, deadline)
        self.send("initialized", {}, request=False)
        return result

    def run(self, project, prompt, model, effort, schema, readonly=False, network=False,
            timeout=900, max_tokens=None, thread_id=None, title=None):
        deadline = time.monotonic() + timeout
        self.initialize(deadline)
        config = {"model_reasoning_effort": effort}
        params = {"cwd": str(project), "model": model, "approvalPolicy": "never",
                  "sandbox": "read-only" if readonly else "workspace-write", "config": config}
        if thread_id:
            params.update({"threadId": thread_id, "excludeTurns": True})
        started = self.request("thread/resume" if thread_id else "thread/start", params, deadline)
        thread = started["thread"]["id"]
        if title:
            self.request("thread/name/set", {"threadId": thread, "name": title}, deadline)
        observed = {"thread_id": thread, "observed_model": started.get("model"),
                    "observed_effort": started.get("reasoningEffort")}
        self.on_event({"method": "client/threadReady", "params": observed})
        policy = {"type": "readOnly"} if readonly else {"type": "workspaceWrite", "writableRoots": [str(project)], "networkAccess": network}
        turn = self.request("turn/start", {"threadId": thread, "input": [{"type": "text", "text": prompt}],
                                           "model": model, "effort": effort, "approvalPolicy": "never",
                                           "sandboxPolicy": policy, "outputSchema": schema}, deadline)
        turn_id = turn["turn"]["id"]
        self.on_event({"method": "client/turnReady", "params": {"turn_id": turn_id}})
        texts = {}
        tokens = None
        try:
            while True:
                message = self.notifications.pop(0) if self.notifications else self.receive(deadline)
                method = message.get("method")
                params = message.get("params", {})
                if params.get("threadId", thread) != thread or params.get("turnId", turn_id) != turn_id:
                    continue
                if method == "item/completed" and params.get("item", {}).get("type") == "agentMessage":
                    item = params["item"]
                    if item.get("phase") != "commentary":
                        texts[item.get("id", "final")] = item.get("text", "")
                if method == "thread/tokenUsage/updated":
                    tokens = params.get("tokenUsage", {}).get("total", {}).get("totalTokens")
                    if max_tokens is not None and tokens is not None and tokens > max_tokens:
                        raise WorkflowError("Phiên AI đã vượt ngân sách token.")
                if method == "turn/completed" and params.get("turn", {}).get("id") == turn_id:
                    status = params["turn"]["status"]
                    require(status == "completed", "Phiên Codex kết thúc với trạng thái " + status + ".")
                    raw = next(reversed(texts.values()), "")
                    try:
                        result = json.loads(raw)
                    except ValueError as exc:
                        raise WorkflowError("Codex chưa trả kết quả đúng cấu trúc JSON.") from exc
                    return {"result": result, "thread_id": thread, "turn_id": turn_id,
                            "tokens": tokens, **observed}
        except BaseException:
            try:
                self.send("turn/interrupt", {"threadId": thread, "turnId": turn_id})
            except (OSError, ValueError):
                pass
            raise

    def close(self):
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()
        self.stderr.close()
        self.trace.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
