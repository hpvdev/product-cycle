"""A protocol peer, not a model-quality evaluator."""

import json
import sys

mode = sys.argv[1] if len(sys.argv) > 1 else "success"


def emit(value):
    print(json.dumps(value), flush=True)


for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    params = message.get("params", {})
    mid = message.get("id")
    if method == "initialize":
        emit({"id": mid, "result": {"userAgent": "fixture"}})
    elif method in {"thread/start", "thread/resume"}:
        emit({"id": mid, "result": {"thread": {"id": "fixture-thread"}, "model": params["model"], "reasoningEffort": params["config"]["model_reasoning_effort"]}})
    elif method == "thread/name/set":
        emit({"id": mid, "result": {}})
        emit({"method": "thread/name/updated", "params": {"threadId": params["threadId"], "threadName": params["name"]}})
    elif method == "turn/start":
        if mode == "request":
            emit({"id": 99, "method": "item/tool/requestUserInput", "params": {"threadId": "fixture-thread", "questions": []}})
            continue
        emit({"id": mid, "result": {"turn": {"id": "fixture-turn", "status": "inProgress"}}})
        if mode == "timeout":
            continue
        emit({"method": "thread/tokenUsage/updated", "params": {"threadId": "fixture-thread", "turnId": "fixture-turn", "tokenUsage": {"total": {"totalTokens": 30}}}})
        if mode != "failed":
            emit({"method": "item/completed", "params": {"threadId": "fixture-thread", "turnId": "fixture-turn", "item": {"type": "agentMessage", "id": "answer", "phase": "final_answer", "text": json.dumps({"ok": True, "effort": params["effort"]})}}})
        emit({"method": "turn/completed", "params": {"threadId": "fixture-thread", "turn": {"id": "fixture-turn", "status": "failed" if mode == "failed" else "completed"}}})
