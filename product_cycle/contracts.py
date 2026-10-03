"""Small, versioned contracts. Workflow policy is enforced by the controller."""

import json
from pathlib import Path

RESOURCES = Path(__file__).parent / "resources"
STAGES = ["analysis", "design", "architecture", "plan", "build", "verify", "handoff", "retro"]
STAGE_TITLES = {
    "analysis": "Phân tích sản phẩm", "design": "Thiết kế UX/UI",
    "architecture": "Thiết kế kỹ thuật", "plan": "Lập kế hoạch",
    "build": "Phát triển", "verify": "Nghiệm thu", "handoff": "Bàn giao",
    "retro": "Cải thiện quy trình",
}
FILES = {
    "analysis": ["analysis.md", "requirements.json"],
    "design": ["design.md"], "architecture": ["architecture.md"],
    "plan": ["plan.json"], "verify": ["acceptance.md"],
    "handoff": ["handoff.md"], "retro": ["retro.json"],
}
CRITERIA = {
    "analysis": ["Người dùng, vấn đề, kết quả mong muốn và phạm vi rõ ràng",
                 "Dữ kiện, giả định, điều chưa biết được phân biệt; yêu cầu có tiêu chí nghiệm thu"],
    "design": ["Luồng chính và các trạng thái trống, lỗi, tải được thiết kế",
               "Thiết kế truy vết tới yêu cầu và có đầu ra trực quan phù hợp với sản phẩm"],
    "architecture": ["Thiết kế dữ liệu, ranh giới code và quyết định kỹ thuật phù hợp phạm vi",
                     "Các rủi ro và cách kiểm chứng được xác định"],
    "plan": ["Công việc có phụ thuộc, yêu cầu liên quan và tiêu chí hoàn tất kiểm chứng được",
             "Kế hoạch nêu lệnh kiểm tra, kiểm chứng trải nghiệm và giới hạn thực thi"],
    "verify": ["Các tiêu chí nghiệm thu của yêu cầu có bằng chứng thực tế",
               "Sai lệch, hạn chế và trạng thái chưa kiểm chứng được ghi rõ"],
    "handoff": ["Có hướng dẫn chạy, kết quả kiểm chứng, giới hạn và phương án khôi phục",
                "Bản bàn giao liên kết đúng phiên bản sản phẩm và bằng chứng"],
    "retro": ["Nhận xét dựa trên lịch sử thực thi và phản hồi",
              "Đề xuất cải thiện có tình huống đánh giá và không tự thay đổi quy trình đang dùng"],
}


def defaults(model="gpt-6.1-sol", effort="high"):
    return {
        "version": 1, "workflow_version": "0.1.0", "mode": "live",
        "models": {stage: {"model": model, "effort": effort} for stage in STAGES + ["review"]},
        "gates": ["analysis", "plan", "handoff"],
        "max_attempts": 2, "turn_timeout_seconds": 900,
        "max_turn_tokens": 400000, "max_cycle_tokens": 2000000,
        "network_access": True, "verification_commands": [],
        "browser_required": False, "allowed_tools": [],
        "external_actions": "No publishing, deployment, messages, merges, account changes, or destructive operations unless separately authorized.",
    }


def object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


STRINGS = {"type": "array", "items": {"type": "string"}}
RESULT_SCHEMA = object_schema({
    "summary": {"type": "string"},
    "artifacts": {"type": "array", "items": object_schema({
        "path": {"type": "string"}, "purpose": {"type": "string"},
        "criteria": STRINGS, "requirements": STRINGS,
    })},
    "limitations": STRINGS,
    "blocker": {"type": ["string", "null"]},
})
REVIEW_SCHEMA = object_schema({
    "decision": {"type": "string", "enum": ["approve", "rework", "blocked"]},
    "summary": {"type": "string"},
    "criteria": {"type": "array", "items": object_schema({
        "id": {"type": "string"}, "passed": {"type": "boolean"},
        "evidence": STRINGS, "reason": {"type": "string"},
    })},
    "findings": STRINGS,
})


class WorkflowError(Exception):
    """An expected, actionable workflow failure."""


def require(condition, message):
    if not condition:
        raise WorkflowError(message)


def json_object(path):
    try:
        value = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise WorkflowError("Không đọc được tài liệu JSON: " + str(path)) from exc
    require(isinstance(value, dict), "Tài liệu phải là một đối tượng JSON.")
    return value


def validate_requirements(value):
    items = value.get("requirements")
    require(isinstance(items, list) and items, "Cần ít nhất một yêu cầu sản phẩm.")
    ids = set()
    for item in items:
        require(isinstance(item, dict), "Yêu cầu chưa đúng cấu trúc.")
        rid = item.get("id")
        require(isinstance(rid, str) and rid and rid not in ids, "Mã yêu cầu phải riêng biệt.")
        require(isinstance(item.get("description"), str) and item["description"].strip(), "Yêu cầu cần mô tả.")
        require(isinstance(item.get("acceptance"), list) and item["acceptance"] and
                all(isinstance(x, str) and x.strip() for x in item["acceptance"]), "Yêu cầu cần tiêu chí nghiệm thu.")
        ids.add(rid)
    return ids


def validate_commands(commands):
    require(isinstance(commands, list), "Danh sách lệnh kiểm tra chưa hợp lệ.")
    for command in commands:
        require(isinstance(command, list) and command and
                all(isinstance(x, str) and x and "\x00" not in x for x in command), "Lệnh kiểm tra phải là danh sách tham số, không phải chuỗi shell.")


def validate_plan(value, requirement_ids):
    tasks = value.get("tasks")
    require(isinstance(tasks, list) and tasks, "Kế hoạch cần có công việc phát triển.")
    ids = set()
    for task in tasks:
        require(isinstance(task, dict), "Công việc chưa đúng cấu trúc.")
        tid = task.get("id", "")
        require(isinstance(tid, str) and tid.startswith("T") and tid.replace("-", "").isalnum() and tid not in ids,
                "Mã công việc phải bắt đầu bằng T và không trùng.")
        ids.add(tid)
        for field in ["title", "instructions"]:
            require(isinstance(task.get(field), str) and task[field].strip(), "Công việc cần " + field)
        require(isinstance(task.get("criteria"), list) and task["criteria"] and
                all(isinstance(x, str) and x.strip() for x in task["criteria"]), "Công việc cần tiêu chí hoàn tất.")
        require(isinstance(task.get("requirements"), list) and task["requirements"] and
                set(task["requirements"]) <= requirement_ids, "Công việc tham chiếu yêu cầu không hợp lệ.")
        require(isinstance(task.get("depends_on"), list) and
                all(isinstance(x, str) for x in task["depends_on"]), "Phụ thuộc chưa hợp lệ.")
        validate_commands(task.get("checks", []))
    covered = {rid for task in tasks for rid in task["requirements"]}
    require(covered == requirement_ids, "Kế hoạch chưa bao phủ toàn bộ yêu cầu.")
    edges = {task["id"]: set(task["depends_on"]) for task in tasks}
    require(all(deps <= ids for deps in edges.values()), "Kế hoạch tham chiếu công việc không tồn tại.")
    remaining = set(ids)
    while remaining:
        ready = {tid for tid in remaining if not (edges[tid] & remaining)}
        require(ready, "Phụ thuộc công việc tạo thành vòng lặp.")
        remaining -= ready
    validate_commands(value.get("verification_commands", []))
    require(isinstance(value.get("browser_required", False), bool), "browser_required phải là boolean.")
    return tasks
