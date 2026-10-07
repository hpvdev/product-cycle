"""Feature and runtime contracts; structural validity is not behavioral proof."""

from pathlib import Path
import copy

from .contracts import require, validate_commands


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value, nonempty=False):
    return isinstance(value, list) and (not nonempty or bool(value)) and all(text(item) for item in value)


def validate_verification(value):
    require(value.get("version") == 1, "Verification contract cần version=1.")
    require(value.get("surface") in {"web", "desktop", "mobile", "game", "cli", "api", "library"},
            "Cần xác định bề mặt thực tế để kiểm chứng sản phẩm.")
    environment = value.get("environment")
    require(isinstance(environment, dict) and text(environment.get("runtime"))
            and strings(environment.get("requirements"))
            and environment.get("instance_policy") in {"exclusive", "isolated"},
            "Cần môi trường, đầu vào và quy tắc cách ly instance để kiểm chứng.")
    for key in ("launch", "doctor", "cleanup"):
        section = value.get(key)
        require(isinstance(section, dict) and text(section.get("instructions")), "Verification contract cần " + key)
        validate_commands(section.get("commands"))
    require(text(value["launch"].get("ready")), "Cần dấu hiệu xác nhận sản phẩm sẵn sàng.")
    require(value["doctor"].get("read_only") is True, "Doctor phải là kiểm tra chỉ đọc.")
    require(value["cleanup"].get("preserve_evidence") is True, "Cleanup phải giữ bằng chứng.")
    procedures = value.get("procedures")
    require(isinstance(procedures, list) and procedures, "Cần thủ tục kiểm chứng hành vi thực tế.")
    ids = set()
    for procedure in procedures:
        require(isinstance(procedure, dict) and text(procedure.get("id")) and procedure["id"] not in ids,
                "Thủ tục kiểm chứng cần mã riêng.")
        ids.add(procedure["id"])
        require(strings(procedure.get("actions"), True) and strings(procedure.get("expected"), True)
                and strings(procedure.get("evidence"), True),
                "Thủ tục cần thao tác, kết quả quan sát mong đợi và loại bằng chứng.")
        validate_commands(procedure.get("commands", []))
    return value


def validate_feature_map(value, requirements, baseline, verification):
    require(value.get("version") == 1, "Feature map cần version=1.")
    features = value.get("features")
    require(isinstance(features, list) and features, "Cần danh sách tính năng trong phạm vi đã chốt.")
    ids, covered = set(), set()
    screens = {screen["id"]: {state["id"] for state in screen["states"]} for screen in baseline.get("screens", [])}
    procedures = {procedure["id"] for procedure in verification["procedures"]}
    for feature in features:
        require(isinstance(feature, dict) and text(feature.get("id")) and feature["id"] not in ids,
                "Tính năng cần mã riêng.")
        ids.add(feature["id"])
        require(text(feature.get("name")) and text(feature.get("purpose")), "Tính năng cần tên và mục đích.")
        links = feature.get("requirements")
        require(strings(links, True) and set(links) <= requirements, "Tính năng cần liên kết yêu cầu đã chốt.")
        covered.update(links)
        require(strings(feature.get("depends_on")) and strings(feature.get("verification"), True)
                and set(feature["verification"]) <= procedures, "Tính năng cần phụ thuộc và thủ tục kiểm chứng hợp lệ.")
        require(feature.get("implementation_status") == "planned", "Feature map trước build phải ghi implementation_status=planned.")
        require(strings(feature.get("code_entry_points")), "Cần ghi entry points dự kiến, có thể rỗng trước build.")
        targets = feature.get("screen_states")
        require(isinstance(targets, list) and all(isinstance(target, dict)
                and target.get("screen_id") in screens and target.get("state") in screens[target["screen_id"]]
                for target in targets), "Tính năng tham chiếu màn hình hoặc trạng thái không có trong thiết kế.")
    require(covered == requirements, "Feature map chưa bao phủ yêu cầu đã chốt.")
    edges = {feature["id"]: set(feature["depends_on"]) for feature in features}
    require(all(deps <= ids for deps in edges.values()), "Tính năng phụ thuộc mã không có trong feature map.")
    remaining = set(ids)
    while remaining:
        ready = {fid for fid in remaining if not edges[fid] & remaining}
        require(ready, "Phụ thuộc tính năng tạo thành vòng lặp.")
        remaining -= ready
    return features


def task_features(store, task):
    if not store.config.get("agent_workflow_version") or task["stage"] not in {"build", "integration", "verify", "handoff"} or task["role"] == "project_setup":
        return []
    feature_map = current_feature_map(store)
    if task["stage"] in {"verify", "handoff"}:
        return feature_map["features"]
    tid = task["id"].removeprefix("integrate-")
    item = next(item for item in store.approved_plan()["tasks"] if item["id"] == tid)
    selected = [feature for feature in feature_map["features"] if feature["id"] in item["features"]]
    for feature in selected:
        feature["verification"] = item.get("feature_verification", {}).get(feature["id"], feature["verification"])
    return selected


def current_feature_map(store):
    """Compose independently accepted observations without rewriting the baseline."""
    value = copy.deepcopy(store.sealed_document("feature_map", "feature-map.json"))
    by_id = {feature["id"]: feature for feature in value["features"]}
    current = store.task_fingerprint("verify")
    accepted = [task for task in store.tasks() if task["stage"] == "integration" and task["status"] == "done"]
    accepted.sort(key=lambda task: (task["accepted_at"] or "", task["id"]))
    for task in accepted:
        records = store.current_evidence(task["id"])
        proof = next((record for record in records if Path(record["source"]).name == "feature-map-update.json"), None)
        require(proof is not None, "Tích hợp đã chốt thiếu feature map quan sát.")
        store.intact([proof])
        update = store.sealed_document(task["id"], "feature-map-update.json")
        for observation in update["features"]:
            feature = by_id[observation["id"]]
            if "observations" not in feature:
                feature["planned_code_entry_points"] = feature["code_entry_points"]
                feature["code_entry_points"] = []
                feature["observations"] = []
            feature["implementation_status"] = "observed"
            feature["code_entry_points"] = sorted(set(feature["code_entry_points"]) | set(observation["code_entry_points"]))
            feature["observations"].append({"task_id": task["id"], "revision": task["revision"],
                "evidence_id": proof["id"], "path": str(store.root / proof["object_path"]), "sha256": proof["sha256"],
                "source_fingerprint": task["fingerprint"], "is_source_current": task["fingerprint"] == current,
                "code_entry_points": observation["code_entry_points"]})
    return value


def validate_feature_plan(plan, feature_map):
    features = {feature["id"]: feature for feature in feature_map["features"]}
    covered, procedures = set(), {fid: set() for fid in features}
    for task in plan["tasks"]:
        from .dispatch import validate_execution
        validate_execution(task.get("execution", {}))
        selected = task.get("features")
        require(strings(selected, True) and len(selected) == len(set(selected)) and set(selected) <= set(features),
                "Mỗi đầu việc cần mã tính năng hợp lệ.")
        covered.update(selected)
        assigned = task.get("feature_verification", {})
        require(isinstance(assigned, dict) and set(assigned) <= set(selected), "Task verification cần đúng các feature được giao.")
        for fid in selected:
            checks = assigned.get(fid, features[fid]["verification"])
            require(strings(checks, True) and len(checks) == len(set(checks)) and set(checks) <= set(features[fid]["verification"]),
                    "Task verification cần thủ tục hợp lệ trong feature map.")
            procedures[fid].update(checks)
        require(set(task["requirements"]) <= {rid for fid in selected for rid in features[fid]["requirements"]},
                "Đầu việc cần feature map bao phủ các yêu cầu được giao.")
    require(covered == set(features), "Plan chưa bao phủ các tính năng.")
    require(all(procedures[fid] == set(feature["verification"]) for fid, feature in features.items()),
            "Plan chưa giao đủ thủ tục kiểm chứng của các tính năng.")
    # Feature prerequisites must have landed before a dependent worker starts.
    # Providers sharing one task are implemented together; other providers must
    # be ancestors in the task DAG (the controller replaces edges by integration).
    tasks = {task["id"]: task for task in plan["tasks"] if "id" in task}
    providers = {fid: {tid for tid, item in tasks.items() if fid in item["features"]} for fid in features}
    for tid, task in tasks.items():
        ancestors, pending = set(), list(task.get("depends_on", []))
        while pending:
            dependency = pending.pop()
            require(dependency in tasks and dependency != tid, "Phụ thuộc đầu việc chưa hợp lệ.")
            if dependency not in ancestors:
                ancestors.add(dependency)
                pending.extend(tasks[dependency].get("depends_on", []))
        for fid in task["features"]:
            for prerequisite in features[fid]["depends_on"]:
                require(providers[prerequisite] <= ancestors | {tid},
                        "Plan phải chờ các đầu việc của tính năng phụ thuộc tích hợp trước: " + fid + " -> " + prerequisite)


def validate_runtime_report(store, task, report, artifacts, source_fingerprint):
    require(report.get("version") == 1 and report.get("source_fingerprint") == source_fingerprint,
            "Runtime evidence cần đúng phiên bản source đang kiểm chứng.")
    environment = report.get("environment")
    require(isinstance(environment, dict) and all(text(environment.get(key)) for key in ("runtime", "instance", "surface")),
            "Runtime evidence cần môi trường và instance thực tế.")
    verification = store.sealed_document("architecture", "verification.json")
    require(environment["surface"] == verification["surface"], "Runtime surface phải đúng hợp đồng đã chốt.")
    features = {feature["id"]: feature for feature in task_features(store, task)}
    expected = set(features)
    rows = report.get("features")
    require(isinstance(rows, list) and len(rows) == len(expected)
            and all(isinstance(row, dict) and text(row.get("id")) for row in rows)
            and {row["id"] for row in rows} == expected, "Runtime evidence chưa bao phủ tính năng được giao.")
    for row in rows:
        require(row.get("status") in {"pass", "fail", "blocked"}, "Runtime outcome cần pass, fail hoặc blocked.")
        observations = row.get("observations")
        require(isinstance(observations, list), "Cần các quan sát thực tế.")
        require(row["status"] != "pass" or observations, "PASS cần bằng chứng quan sát thực tế.")
        for observation in observations:
            require(isinstance(observation, dict) and observation.get("procedure") in features[row["id"]]["verification"]
                    and all(text(observation.get(key)) for key in ("action", "expected", "actual"))
                    and strings(observation.get("evidence"), True), "Quan sát cần thao tác, mong đợi, kết quả thật và bằng chứng.")
            require(all(path in artifacts and Path(path).name != "runtime-observations.json" for path in observation["evidence"]),
                    "Quan sát cần bằng chứng đã đăng ký, ngoài chính báo cáo.")
        require(row["status"] != "pass" or {observation["procedure"] for observation in observations}
                == set(features[row["id"]]["verification"]), "PASS cần bao phủ các thủ tục đã chốt của tính năng.")
    if task["stage"] == "verify":
        whole = report.get("whole_product")
        categories = {"main_journey", "cross_feature", "ux_consistency", "visual_consistency", "performance", "error_recovery"}
        require(isinstance(whole, dict) and set(whole) == categories, "Whole-product verify cần hành trình, tương tác và chất lượng toàn sản phẩm.")
        for category, result in whole.items():
            require(isinstance(result, dict) and result.get("status") in {"pass", "fail", "blocked", "not_applicable"}
                    and text(result.get("reason")), "Whole-product outcome cần trạng thái và lý do cụ thể.")
            require(category != "main_journey" or result["status"] != "not_applicable", "Hành trình chính luôn cần kiểm chứng.")
            if result["status"] == "not_applicable":
                continue
            require(strings(result.get("evidence"), result["status"] == "pass")
                    and all(path in artifacts and Path(path).name != "runtime-observations.json" for path in result["evidence"]),
                    "Whole-product outcome cần bằng chứng đã đăng ký.")
    return rows


def validate_feature_update(store, task, value, source):
    expected = {feature["id"] for feature in task_features(store, task)}
    rows = value.get("features")
    require(value.get("version") == 1 and isinstance(rows, list) and len(rows) == len(expected)
            and all(isinstance(row, dict) and text(row.get("id")) for row in rows)
            and {row["id"] for row in rows} == expected, "Feature update cần đúng tính năng đã triển khai.")
    for row in rows:
        require(row.get("implementation_status") == "observed" and strings(row.get("code_entry_points"), True),
                "Feature update cần entry points được xác nhận trong code thực tế.")
        for relative in row["code_entry_points"]:
            path = (source / relative).resolve()
            require(path.is_relative_to(source) and path.is_file(), "Entry point cần nằm trong source đã kiểm chứng.")
