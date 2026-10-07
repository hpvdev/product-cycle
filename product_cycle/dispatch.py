"""Explicit runtime/model routing; configured capability is not an observation."""

import shutil

from .contracts import WorkflowError, require


EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
EXECUTORS = {"codex-desktop", "codex-app-server"}
COMPLEXITIES = {"routine", "standard", "complex"}


def validate_profiles(value):
    profiles = value.get("profiles")
    require(isinstance(profiles, list) and profiles, "Routing cần profiles đã cấu hình.")
    ids = set()
    for profile in profiles:
        require(isinstance(profile, dict) and isinstance(profile.get("id"), str) and profile["id"]
                and profile["id"] not in ids and profile.get("executor") in EXECUTORS,
                "Runtime profile cần mã riêng và executor được hỗ trợ.")
        ids.add(profile["id"])
        require(isinstance(profile.get("domains", []), list) and all(isinstance(item, str) and item for item in profile.get("domains", [])),
                "Runtime domains cần danh sách rõ ràng.")
        require(isinstance(profile.get("complexities", []), list) and set(profile.get("complexities", [])) <= COMPLEXITIES,
                "Runtime complexities chưa hợp lệ.")
        require(isinstance(profile.get("capabilities"), list) and all(isinstance(item, str) and item for item in profile["capabilities"]),
                "Profile cần capabilities được cấu hình rõ.")
        models = profile.get("models", {})
        require(isinstance(models, dict), "Profile models cần là object.")
        for choice in models.values():
            require(isinstance(choice, dict) and isinstance(choice.get("model"), str) and choice["model"]
                    and choice.get("effort") in EFFORTS, "Profile model/effort chưa hợp lệ.")
    return value


def execution_metadata(store, task):
    if task["stage"] not in {"build", "integration"} or task["role"] == "project_setup":
        return {}
    tid = task["id"].removeprefix("integrate-")
    return next(item.get("execution", {}) for item in store.approved_plan()["tasks"] if item["id"] == tid)


def validate_execution(value):
    require(isinstance(value, dict), "Task execution cần là object.")
    require(value.get("complexity", "standard") in COMPLEXITIES, "Complexity cần routine, standard hoặc complex.")
    for key in ("capabilities", "consultants"):
        require(isinstance(value.get(key, []), list) and all(isinstance(item, str) and item for item in value.get(key, [])),
                "Execution cần danh sách " + key)
    from .team import ROLE_DETAILS
    require(all(role in ROLE_DETAILS and ROLE_DETAILS[role]["kind"] != "reviewer"
                and "build" in ROLE_DETAILS[role]["stages"] for role in value.get("consultants", [])),
            "Consultants cần vai trò phù hợp với build; review độc lập do controller giao.")
    require(value.get("runtime") is None or isinstance(value["runtime"], str) and value["runtime"], "Runtime cần mã profile.")
    return value


def route(store, task, phase="work", role_override=None):
    config = store.config
    role = "review" if phase in {"review", "improve_review"} else task["role"]
    if role_override is not None:
        role = role_override
    elif phase == "work" and role == "build" and config.get("team", {}).get("enabled"):
        from .team import agent_for, employee_role
        employee = employee_role(store, agent_for(task, phase, store))
        role = employee["model_role"] if employee["base_role"] in {"frontend", "backend", "mobile", "game_engineer"} else role
    metadata = validate_execution(execution_metadata(store, task)) if config.get("agent_workflow_version") else {}
    if phase != "work":
        metadata = {}
    routing = config.get("routing")
    observed = [name for name in ("git", "python3") if shutil.which(name)]
    if not routing:
        profile = {"id": "local", "executor": config["executor"], "capabilities": ["shell", "git"], "models": {}}
    else:
        profiles = validate_profiles(routing)["profiles"]
        requested = metadata.get("runtime")
        needed = set(metadata.get("capabilities", []))
        domain, complexity = metadata.get("domain", task["role"]), metadata.get("complexity", "standard")
        eligible = [profile for profile in profiles if (not requested or profile["id"] == requested)
                    and needed <= set(profile["capabilities"])
                    and (not profile.get("domains") or domain in profile["domains"])
                    and (not profile.get("complexities") or complexity in profile["complexities"])
                    and profile["executor"] == config["executor"]]
        require(eligible, "Chờ runtime/capability: không có profile phù hợp với executor và công cụ được yêu cầu.")
        profile = eligible[0]
    required = set(metadata.get("capabilities", []))
    require(required <= set(profile["capabilities"]), "Chờ capability: runtime chưa được cấu hình cho công cụ cần thiết.")
    require("git" not in required or "git" in observed, "Chờ capability: chưa tìm thấy Git trong runtime local.")
    choice = profile.get("models", {}).get(role + ":" + metadata.get("complexity", "standard"),
              profile.get("models", {}).get(role, config["models"][role]))
    return {"version": 1, "runtime": profile["id"], "executor": profile["executor"],
            "device": profile.get("device", "local"), "domain": metadata.get("domain", task["role"]),
            "complexity": metadata.get("complexity", "standard"), "model": choice["model"], "effort": choice["effort"],
            "skill": "product-cycle-" + task["role"], "required_capabilities": sorted(required),
            "configured_capabilities": profile["capabilities"], "observed_local_executables": observed,
            "provider_capabilities": "unconfirmed_until_session", "reason": "explicit_profile" if routing else "configured_role_default"}
