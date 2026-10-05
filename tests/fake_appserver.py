"""A protocol peer, not a model-quality evaluator."""

import json
import os
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
    elif method == "thread/read":
        emit({"id": mid, "result": {"thread": {"id": params["threadId"], "cwd": os.getcwd(),
              "turns": [{"id": "fixture-turn", "status": "completed", "items": []}]}}})
    elif method in {"thread/start", "thread/resume"}:
        emit({"id": mid, "result": {"thread": {"id": "fixture-thread"}, "model": params["model"], "reasoningEffort": params["config"]["model_reasoning_effort"]}})
    elif method == "thread/name/set":
        emit({"id": mid, "result": {}})
        emit({"method": "thread/name/updated", "params": {"threadId": params["threadId"], "threadName": params["name"]}})
    elif method == "turn/start":
        if mode == "capacity-request":
            emit({"id": mid, "error": {"code": -32000, "message": "Selected model is at capacity. Please try a different model."}})
            continue
        if mode == "request":
            emit({"id": 99, "method": "item/tool/requestUserInput", "params": {"threadId": "fixture-thread", "questions": []}})
            continue
        emit({"id": mid, "result": {"turn": {"id": "fixture-turn", "status": "inProgress"}}})
        if mode == "dynamic":
            emit({"id": 99, "method": "item/tool/call", "params": {"threadId": "fixture-thread", "turnId": "fixture-turn", "callId": "fixture-call", "tool": "team_context", "arguments": {}}})
            continue
        if mode == "timeout":
            continue
        emit({"method": "thread/tokenUsage/updated", "params": {"threadId": "fixture-thread", "turnId": "fixture-turn", "tokenUsage": {"total": {"totalTokens": 30}}}})
        if mode not in {"failed", "capacity"}:
            emit({"method": "item/completed", "params": {"threadId": "fixture-thread", "turnId": "fixture-turn", "item": {"type": "agentMessage", "id": "answer", "phase": "final_answer", "text": json.dumps({"ok": True, "effort": params["effort"]})}}})
        turn = {"id": "fixture-turn", "status": "failed" if mode in {"failed", "capacity"} else "completed"}
        if mode == "capacity":
            turn["error"] = {"message": "Selected model is at capacity", "codexErrorInfo": "serverOverloaded"}
        emit({"method": "turn/completed", "params": {"threadId": "fixture-thread", "turn": turn}})
    elif mode == "dynamic" and mid == 99 and "result" in message:
        emit({"method": "item/completed", "params": {"threadId": "fixture-thread", "turnId": "fixture-turn", "item": {"type": "agentMessage", "id": "answer", "text": json.dumps({"tool_response": message["result"]})}}})
        emit({"method": "turn/completed", "params": {"threadId": "fixture-thread", "turn": {"id": "fixture-turn", "status": "completed"}}})
