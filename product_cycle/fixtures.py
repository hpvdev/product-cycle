"""Explicitly synthetic fixtures for controller evaluation and dashboard demos."""

import json
import copy
import sys

from .contracts import FILES, work_steps
from .store import write_json, fingerprint


def complete_fixture(store, tid, approve=True, plan=None, review_decision="approve", services=None, readiness=None, blocker=None, project_setup=None):
    task = store.task(tid)
    aid, directory = store.begin(tid, "work")
    artifacts = []
    filenames = list(FILES.get(task["role"], ["increment.md"]))
    if task["stage"] == "analysis" and store.config.get("collaborative_product"):
        filenames += ["product-direction.json"]
    if task["stage"] == "architecture" and store.config.get("service_setup_required"):
        filenames = filenames + ["services.json"]
    if task["stage"] == "architecture" and store.config.get("project_setup_required"):
        filenames = filenames + ["project-setup.json"]
    enhanced = store.config.get("agent_workflow_version")
    if enhanced and task["stage"] == "architecture":
        filenames += ["verification.json"]
    if enhanced and task["role"] in {"build", "integration", "verify"} and not blocker:
        filenames += ["fixture-observation.json", "runtime-observations.json"]
        if task["role"] == "build":
            source = store.task_source(task) / "synthetic.py"
            source.write_text("print('synthetic controller fixture; not a real product')\n")
            artifacts.append({"path": str(source.relative_to(store.project)), "purpose": "Synthetic source for controller mechanics",
                              "criteria": ["C1"], "requirements": task["requirements"]})
    if enhanced and task["stage"] == "integration" and not blocker:
        filenames += ["feature-map-update.json"]
    for filename in filenames:
        path = directory / filename
        if filename == "requirements.json":
            write_json(path, {"requirements": [{"id": "R1", "description": "Ghi và đọc lại một thông tin", "acceptance": ["Thông tin đã lưu có thể đọc lại"]}]})
        elif filename == "product-direction.json":
            write_json(path, {"users": "Người dùng tổng hợp", "problem": "Tình huống kiểm tra controller",
                "desired_experience": "Ghi và đọc thông tin", "differentiation": "Chỉ minh họa, chưa đánh giá thị trường",
                "options": [{"name": "Phương án minh họa", "description": "Không phải hướng sản phẩm thật", "tradeoffs": "Chưa kiểm chứng trải nghiệm"}],
                "recommendation": "Phương án minh họa", "quality_targets": [{"description": "Đọc lại thông tin",
                    "verification": "Quan sát tổng hợp", "requirement": "R1"}], "open_questions": []})
        elif filename == "plan.json":
            value = copy.deepcopy(plan) if plan else {"tasks": [{"id": "T1", "title": "Lưu thông tin", "instructions": "Tạo khả năng lưu và đọc", "depends_on": [], "requirements": ["R1"], "criteria": ["Đọc lại dữ liệu đã lưu"], "checks": []}], "verification_commands": [], "browser_required": False}
            if enhanced:
                for item in value["tasks"]:
                    item.setdefault("features", ["synthetic"])
            if store.config.get("service_setup_required") and plan is None:
                value.update(service_ids=[service["id"] for service in store.services()],
                             delivery={"mode": "local", "access": "Bản local minh họa", "instructions": "Hợp đồng minh họa, chưa có sản phẩm thật.", "run_commands": [], "deferred": ["VPS và phát hành ra ngoài"]})
                value["tasks"][0]["services"] = value["service_ids"]
            if store.config.get("experience_checkpoint_required") and plan is None:
                value["experience_checkpoint"] = {"task_id": "T1", "goal": "Trải nghiệm minh họa", "evaluation": ["Chỉ kiểm tra controller, chưa có sản phẩm thật"]}
            if store.config.get("screen_design_required") and plan is None:
                value["tasks"][0]["screen_targets"] = []
            write_json(path, value)
        elif filename == "verification.json":
            write_json(path, {"version": 1, "surface": "cli",
                "environment": {"runtime": "synthetic", "requirements": [], "instance_policy": "isolated"},
                "launch": {"commands": [], "instructions": "Synthetic fixture only", "ready": "No product is claimed"},
                "doctor": {"commands": [], "instructions": "Synthetic contract", "read_only": True},
                "cleanup": {"commands": [], "instructions": "Preserve fixture evidence", "preserve_evidence": True},
                "procedures": [{"id": "synthetic-record", "actions": ["Synthetic record"], "expected": ["Synthetic result"], "evidence": ["Synthetic fixture record"], "commands": []}]})
        elif filename == "feature-map.json":
            write_json(path, {"version": 1, "features": [{"id": "synthetic", "name": "Synthetic feature", "purpose": "Controller test only",
                "requirements": ["R1"], "depends_on": [], "screen_states": [], "code_entry_points": [],
                "implementation_status": "planned", "verification": ["synthetic-record"]}]})
        elif filename == "fixture-observation.json":
            write_json(path, {"synthetic": True, "scope": "Controller mechanics only; no real product/provider observation"})
        elif filename == "runtime-observations.json":
            from .features import task_features
            proof = str((directory / "fixture-observation.json").relative_to(store.project))
            value = {"version": 1, "source_fingerprint": store.task_fingerprint(task),
                "environment": {"runtime": "synthetic", "instance": "fixture", "surface": "cli"},
                "features": [{"id": feature["id"], "status": "pass", "observations": [{"procedure": procedure,
                    "action": "Synthetic action", "expected": "Synthetic result", "actual": "Synthetic controller fixture",
                    "evidence": [proof]} for procedure in feature["verification"]]} for feature in task_features(store, task)]}
            if task["stage"] == "verify":
                value["whole_product"] = {category: {"status": "pass", "reason": "Synthetic controller case only", "evidence": [proof]}
                    for category in ("main_journey", "cross_feature", "ux_consistency", "visual_consistency", "performance", "error_recovery")}
            write_json(path, value)
        elif filename == "feature-map-update.json":
            from .features import task_features
            write_json(path, {"version": 1, "features": [{"id": feature["id"], "implementation_status": "observed",
                "code_entry_points": ["synthetic.py"]} for feature in task_features(store, task)]})
        elif filename == "services.json":
            write_json(path, {"services": services or []})
        elif filename == "project-setup.json":
            write_json(path, project_setup or {
                "stack": {"language": "Python", "runtime": "Python 3.9+", "framework": "Thư viện chuẩn", "package_manager": "Không cần dependency cho fixture"},
                "structure": ["src/ cho code minh họa"], "coding_rules": ["Quy tắc tổng hợp, chưa phải app thật"],
                "common_components": [], "environment_names": [],
                "tooling": {"format": "Không áp dụng trong fixture", "lint": "Không áp dụng trong fixture", "typecheck": "Không áp dụng trong fixture", "test": "Lệnh tổng hợp kiểm tra cơ chế"},
                "instructions": "Thiết lập nền minh họa; không tuyên bố có sản phẩm thật.",
                "checks": [[sys.executable, "-c", "print('synthetic project setup check; not a real product')"]]})
        elif filename == "readiness.json":
            service = next(service for service in store.services() if "setup-" + service["id"] == tid)
            write_json(path, readiness or {"services": [{"id": service["id"], "status": "ready",
                                                        "note": "Kết quả tổng hợp, chưa kết nối dịch vụ thật.", "input_refs": service["inputs"]}]})
        elif filename == "retro.json":
            write_json(path, {"observations": [], "improvements": []})
        elif filename == "design-baseline.json":
            write_json(path, {"has_ui": False, "visual_reference": None, "version": "1", "screens": [],
                              "flows": ["Ghi và đọc lại thông tin minh họa"],
                              "states": ["Thành công", "Thông tin chưa có"],
                              "rules": {"interaction": "Hợp đồng minh họa, chưa có sản phẩm thật"},
                              "acceptance": ["Thông tin được đọc lại"]})
        else:
            path.write_text("# Dữ liệu minh họa\n\nĐây là đầu ra tổng hợp để kiểm tra bộ điều phối, không phải công việc của AI.\n")
        artifacts.append({"path": str(path.relative_to(store.project)), "purpose": "Đầu ra minh họa: " + filename,
                          "criteria": ["C" + str(i + 1) for i in range(len(task["criteria"]))], "requirements": task["requirements"]})
    if task["role"] == "project_setup":
        setup = store.project_setup_contract()
        path = store.project / "CODING_RULES.md"
        path.write_text("# Quy tắc minh họa\n\n" + "\n".join(setup["coding_rules"]) + "\n")
        artifacts.append({"path": "CODING_RULES.md", "purpose": "Quy tắc tổng hợp", "criteria": ["C1", "C2"], "requirements": []})
        if setup["environment_names"]:
            path = store.project / ".env.example"
            path.write_text("".join(name + "=\n" for name in setup["environment_names"]))
            artifacts.append({"path": ".env.example", "purpose": "Mẫu môi trường tổng hợp", "criteria": ["C1", "C2"], "requirements": []})
    result = {"summary": "Kết quả minh họa cho " + task["title"], "artifacts": artifacts,
              "steps": [{"id": step["id"], "summary": "Kết quả tổng hợp: " + step["title"],
                         "artifacts": [item["path"] for item in artifacts]} for step in work_steps(task["role"])],
              "limitations": ["Dữ liệu tổng hợp, chưa có đánh giá AI."], "blocker": blocker}
    write_json(directory / "result.json", result)
    store.work_finished(tid, aid, result)
    if blocker:
        return store.task(tid)
    from .runner import run_checks
    run_checks(store, store.task(tid), aid, directory)
    store.update(tid, fingerprint=store.task_fingerprint(task))
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
    stages = ["analysis", "design", "architecture"] + (["feature_map"] if store.config.get("agent_workflow_version") else []) + ["plan"]
    for tid in stages:
        complete_fixture(store, tid, plan=plan if tid == "plan" else None)
