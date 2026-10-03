"""Explicitly synthetic fixtures for controller evaluation and dashboard demos."""

import json

from .contracts import FILES, work_steps
from .store import write_json, fingerprint


def complete_fixture(store, tid, approve=True, plan=None, review_decision="approve"):
    task = store.task(tid)
    aid, directory = store.begin(tid, "work")
    artifacts = []
    filenames = FILES.get(task["stage"], ["increment.md"])
    for filename in filenames:
        path = directory / filename
        if filename == "requirements.json":
            write_json(path, {"requirements": [{"id": "R1", "description": "Ghi và đọc lại một thông tin", "acceptance": ["Thông tin đã lưu có thể đọc lại"]}]})
        elif filename == "plan.json":
            write_json(path, plan or {"tasks": [{"id": "T1", "title": "Lưu thông tin", "instructions": "Tạo khả năng lưu và đọc", "depends_on": [], "requirements": ["R1"], "criteria": ["Đọc lại dữ liệu đã lưu"], "checks": []}], "verification_commands": [], "browser_required": False})
        elif filename == "retro.json":
            write_json(path, {"observations": [], "improvements": []})
        elif filename == "design-baseline.json":
            write_json(path, {"has_ui": False, "visual_reference": None,
                              "flows": ["Ghi và đọc lại thông tin minh họa"],
                              "states": ["Thành công", "Thông tin chưa có"],
                              "rules": {"interaction": "Hợp đồng minh họa, chưa có sản phẩm thật"},
                              "acceptance": ["Thông tin được đọc lại"]})
        else:
            path.write_text("# Dữ liệu minh họa\n\nĐây là đầu ra tổng hợp để kiểm tra bộ điều phối, không phải công việc của AI.\n")
        artifacts.append({"path": str(path.relative_to(store.project)), "purpose": "Đầu ra minh họa: " + filename,
                          "criteria": ["C" + str(i + 1) for i in range(len(task["criteria"]))], "requirements": task["requirements"]})
    result = {"summary": "Kết quả minh họa cho " + task["title"], "artifacts": artifacts,
              "steps": [{"id": step["id"], "summary": "Kết quả tổng hợp: " + step["title"],
                         "artifacts": [item["path"] for item in artifacts]} for step in work_steps(task["stage"])],
              "limitations": ["Dữ liệu tổng hợp, chưa có đánh giá AI."], "blocker": None}
    write_json(directory / "result.json", result)
    store.work_finished(tid, aid, result)
    from .runner import run_checks
    run_checks(store, store.task(tid), aid, directory)
    store.update(tid, fingerprint=fingerprint(store.project))
    review_id, review_dir = store.begin(tid, "review")
    records = store.current_evidence(tid)
    review = {"decision": review_decision, "summary": "Review tổng hợp để kiểm tra cơ chế chuyển trạng thái.",
              "criteria": [{"id": "C" + str(i + 1), "passed": True,
                            "evidence": [item["id"] for item in records if "C" + str(i + 1) in item["criteria"]],
                            "reason": "Tình huống tổng hợp có đầu ra."} for i in range(len(task["criteria"]))],
              "steps": [{"id": step["id"], "passed": review_decision == "approve",
                         "evidence": [item["id"] for item in records if item["source"] in step["artifacts"]],
                         "reason": "Tình huống tổng hợp có đầu ra."} for step in result["steps"]],
              "findings": [] if review_decision == "approve" else ["Cần bổ sung đầu ra theo tình huống minh họa."]}
    write_json(review_dir / "result.json", review)
    store.review_finished(tid, review_id, review)
    if approve and store.task(tid)["status"] == "awaiting_approval":
        store.decide(tid, "approve", "Fixture", "Quyết định tổng hợp, chỉ dành cho kiểm tra bộ điều phối.")
    return store.task(tid)


def prepare_plan(store, plan=None):
    for tid in ["analysis", "design", "architecture", "plan"]:
        complete_fixture(store, tid, plan=plan if tid == "plan" else None)
