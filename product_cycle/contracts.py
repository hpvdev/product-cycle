"""Small, versioned contracts. Workflow policy is enforced by the controller."""

import json
from pathlib import Path

RESOURCES = Path(__file__).parent / "resources"
STAGES = ["analysis", "design", "architecture", "plan", "setup", "build", "verify", "handoff", "retro"]
STAGE_TITLES = {
    "setup": "Cấu hình dịch vụ",
    "analysis": "Phân tích sản phẩm", "design": "Thiết kế UX/UI",
    "architecture": "Thiết kế kỹ thuật", "plan": "Lập kế hoạch",
    "build": "Phát triển", "verify": "Nghiệm thu", "handoff": "Bàn giao",
    "retro": "Cải thiện quy trình",
}
FILES = {
    "setup": ["readiness.json", "setup.md"],
    "analysis": ["analysis.md", "requirements.json"],
    "design": ["design.md", "design-baseline.json"], "architecture": ["architecture.md"],
    "plan": ["plan.json"], "verify": ["acceptance.md"],
    "handoff": ["handoff.md"], "retro": ["retro.json"],
}

# Local task IDs remain stable across retries; progress is scoped to each attempt.
WORK_STEPS = {
    "setup": [
        ("Đọc nhu cầu tích hợp", "Xác định dịch vụ, mục đích và tính năng phụ thuộc theo thiết kế."),
        ("Kiểm tra tài khoản và quyền", "Xác định tài khoản được phép dùng và những thông tin cần bạn cấp."),
        ("Cấu hình các dịch vụ cần thiết", "Thiết lập trong phạm vi đã được cấp phép; ghi rõ phần còn thiếu."),
        ("Kiểm tra kết nối thực tế", "Chạy kiểm tra phù hợp để xác nhận quyền và kết nối tới dịch vụ."),
        ("Ghi nhận cấu hình sẵn sàng", "Lưu kết quả kiểm tra, giới hạn và cách xử lý khi thiếu cấu hình; không lưu bí mật."),
    ],
    "analysis": [
        ("Xác định người dùng và mục tiêu", "Nêu ai sử dụng sản phẩm và kết quả họ cần đạt."),
        ("Làm rõ vấn đề", "Mô tả tình huống sử dụng, khó khăn và nhu cầu chính."),
        ("Đối chiếu dữ kiện và giả định", "Ghi nguồn, giả định và câu hỏi còn ảnh hưởng tới quyết định."),
        ("Chốt phạm vi", "Xác định phiên bản đầu tiên, giới hạn và những phần để sau."),
        ("Viết yêu cầu và tiêu chí", "Mỗi yêu cầu có hành vi quan sát được để nghiệm thu."),
    ],
    "design": [
        ("Vẽ luồng thao tác", "Liên kết hành trình chính với yêu cầu đã chốt."),
        ("Khảo sát hướng thiết kế", "Dùng thiết kế hiện có hoặc tạo phương án bằng Product Design và Image Gen khi công cụ sẵn có."),
        ("Đề xuất mốc thiết kế", "Lưu hình tham khảo hoặc prototype cụ thể để chủ sản phẩm duyệt."),
        ("Bổ sung trạng thái màn hình", "Mô tả dữ liệu, trống, tải, lỗi và hoàn thành theo tính năng."),
        ("Chốt quy tắc và cách nghiệm thu", "Ghi màu, font, khoảng cách, bố cục thích ứng và tiêu chí so sánh."),
    ],
    "architecture": [
        ("Đọc cấu trúc hiện có", "Xác định phần code và quy tắc liên quan; dùng lại thành phần phù hợp."),
        ("Thiết kế dữ liệu và giao tiếp", "Mô tả dữ liệu, ranh giới thành phần và hợp đồng giao tiếp."),
        ("Chọn dịch vụ và cách tích hợp", "Nêu dịch vụ cần dùng, lý do, quyền, cấu hình cần bạn cấp và cách kiểm tra."),
        ("Xử lý điểm chưa chắc", "Kiểm chứng phần kỹ thuật có rủi ro hoặc ghi rõ điều còn bị chặn."),
        ("Xác định cách kiểm tra và khôi phục", "Nêu cách chứng minh tính đúng và khôi phục khi cần."),
    ],
    "plan": [
        ("Chia lát chức năng", "Mỗi công việc tạo ra một kết quả có thể nhận và kiểm tra."),
        ("Sắp xếp phụ thuộc", "Xác định thứ tự thực hiện, tránh vòng lặp phụ thuộc."),
        ("Viết hợp đồng công việc", "Ghi đầu vào, phạm vi, yêu cầu liên quan và tiêu chí hoàn tất."),
        ("Chọn cách kiểm chứng", "Dùng kiểm tra phù hợp và kiểm chứng trình duyệt khi trải nghiệm yêu cầu."),
        ("Chốt cách chạy local và giới hạn", "Ghi cách dùng bản local, giới hạn thực thi và phần phát hành để giai đoạn sau."),
    ],
    "build": [
        ("Đọc đầu vào và tái hiện", "Đọc yêu cầu, mốc thiết kế và code liên quan; tái hiện lỗi nếu đang sửa bug."),
        ("Triển khai trong phạm vi", "Dùng mẫu hiện có và chỉ sửa phần phục vụ công việc."),
        ("Hoàn thiện hành vi và trạng thái", "Đáp ứng luồng chính cùng các trường hợp cần thiết."),
        ("Đối chiếu thay đổi", "Xem lại phần code đã sửa, đầu ra và hạn chế trước khi gửi kiểm chứng."),
    ],
    "verify": [
        ("Lập đối chiếu yêu cầu", "Liên kết từng tiêu chí nghiệm thu với cách kiểm chứng."),
        ("Kiểm tra kết quả đã ghi", "Đọc kết quả thực tế và xác định đúng phiên bản sản phẩm."),
        ("Đánh giá trải nghiệm", "So sánh giao diện với mốc thiết kế và thử hành trình; ghi thiếu bằng chứng khi chưa thể quan sát."),
        ("Ghi sai lệch và hạn chế", "Phân biệt lỗi, giới hạn được chấp nhận và phần chưa kiểm chứng."),
        ("Kết luận nghiệm thu", "Kết luận dựa trên bằng chứng, giữ nguyên tiêu chí đã chốt."),
    ],
    "handoff": [
        ("Xác định phiên bản bàn giao", "Liên kết bản bàn giao với đúng phiên bản đã nghiệm thu."),
        ("Giao bản local để dùng thử", "Ghi cách mở web hoặc chạy app ở môi trường hiện tại cùng tài khoản thử nếu cần."),
        ("Tập hợp đầu ra và bằng chứng", "Liên kết tài liệu, source và kết quả kiểm chứng."),
        ("Ghi cách khôi phục", "Nêu phương án khôi phục phù hợp với cách bàn giao."),
        ("Chốt hạn chế và việc tiếp theo", "Ghi rõ những phần chưa thực hiện hoặc chưa kiểm chứng."),
    ],
    "retro": [
        ("Đọc lịch sử và phản hồi", "Dùng bằng chứng của lần chạy để xác định điều thực sự xảy ra."),
        ("Tìm nguyên nhân phải làm lại", "Xác định thiếu đầu vào, lỗi quy trình và can thiệp cần thiết."),
        ("Chọn cải tiến có tác động", "Ưu tiên thay đổi nhỏ giải quyết vấn đề đã quan sát."),
        ("Thiết kế tình huống đánh giá", "Nêu đầu vào và kết quả mong đợi để kiểm chứng cải tiến."),
        ("Đề xuất cho vòng sau", "Đưa đề xuất có bằng chứng; chưa tự thay đổi quy trình đang chạy."),
    ],
}


def work_steps(stage):
    return [{"id": "S" + str(i + 1), "title": title, "description": description}
            for i, (title, description) in enumerate(WORK_STEPS[stage])]
CRITERIA = {
    "setup": ["Dịch vụ, tài khoản và phạm vi được phép cấu hình đã rõ",
              "Cấu hình có kiểm tra kết nối thực tế thành công"],
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


def defaults(model=None, effort=None):
    return {
        "version": 1, "workflow_version": "0.2.0", "mode": "live",
        "service_setup_required": True, "delivery_mode": "local", "release_deferred": True,
        "models": {stage: {
            "model": model or ("gpt-6-astra" if stage in {"analysis", "design", "architecture"} else "gpt-6.1-sol"),
            "effort": effort or ("high" if stage == "review" else "medium"),
        } for stage in STAGES + ["review"]},
        "gates": ["handoff"],
        "max_attempts": 2, "turn_timeout_seconds": 900,
        "max_turn_tokens": 400000, "max_cycle_tokens": 2000000,
        "network_access": True, "verification_commands": [],
        "browser_required": False, "allowed_tools": [],
        "external_actions": "Configure only the third-party services required by the design within the user's authorized accounts and project. Do not infer authorization from a logged-in account. Develop and verify locally. VPS provisioning, deployment and external publication are deferred. No messages, paid purchases, unrelated account changes or destructive operations unless explicitly authorized.",
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
    "steps": {"type": "array", "items": object_schema({
        "id": {"type": "string"}, "summary": {"type": "string"}, "artifacts": STRINGS,
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
    "steps": {"type": "array", "items": object_schema({
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


def validate_services(value):
    services = value.get("services")
    require(isinstance(services, list), "Thiết kế cần danh sách dịch vụ, kể cả khi không dùng bên thứ ba.")
    ids = set()
    for service in services:
        require(isinstance(service, dict), "Thông tin dịch vụ chưa hợp lệ.")
        for key in ["id", "provider", "purpose", "environment", "configuration", "verification", "owner", "cost", "fallback"]:
            require(isinstance(service.get(key), str) and service[key].strip(), "Dịch vụ cần mô tả " + key)
        require(service["id"].replace("-", "").isalnum() and service["id"] not in ids, "Dịch vụ cần mã riêng biệt, gồm chữ, số hoặc dấu gạch ngang.")
        ids.add(service["id"])
        for key in ["inputs", "permissions"]:
            require(isinstance(service.get(key), list) and all(isinstance(x, str) and x.strip() for x in service[key]),
                    "Dịch vụ cần danh sách " + key)
        validate_commands(service.get("checks", []))
        require(service.get("checks"), "Dịch vụ cần lệnh kiểm tra kết nối hoặc quyền thực tế.")
    return services


def validate_local_plan(plan, services):
    """Configuration dependencies are scoped to the increments that need them."""
    known = {service["id"] for service in services}
    service_ids = plan.get("service_ids")
    require(isinstance(service_ids, list) and all(isinstance(sid, str) for sid in service_ids) and
            len(service_ids) == len(known) and set(service_ids) == known,
            "Plan cần bao phủ các dịch vụ của thiết kế kỹ thuật.")
    used = set()
    for task in plan["tasks"]:
        needed = task.get("services")
        require(isinstance(needed, list) and all(isinstance(sid, str) and sid in known for sid in needed),
                "Mỗi đầu việc cần ghi các dịch vụ phụ thuộc; dùng danh sách rỗng nếu không cần dịch vụ.")
        used.update(needed)
    require(used == known, "Mỗi dịch vụ trong thiết kế cần liên kết tới công việc sử dụng nó.")
    delivery = plan.get("delivery")
    require(isinstance(delivery, dict) and delivery.get("mode") == "local", "Plan cần bàn giao bản local; VPS và phát hành để giai đoạn sau.")
    for key in ["access", "instructions"]:
        require(isinstance(delivery.get(key), str) and delivery[key].strip(), "Bản local cần " + key)
    validate_commands(delivery.get("run_commands", []))
    require(isinstance(delivery.get("deferred"), list) and all(isinstance(item, str) and item.strip() for item in delivery["deferred"]),
            "Plan cần ghi rõ những việc phát hành để giai đoạn sau.")
    return delivery
