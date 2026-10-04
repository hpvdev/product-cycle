"""SQLite journal, immutable evidence, dependency gates, and recovery."""

import contextlib
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

from .contracts import (CRITERIA, FILES, STAGE_TITLES, WorkflowError, defaults,
                        json_object, require, validate_plan, validate_requirements, work_steps,
                        validate_services, validate_local_plan, validate_project_setup)
from .bootstrap import prepare_project, foundation_status, repository_state


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, path)


def state_root(project):
    home = Path(os.environ.get("PRODUCT_CYCLE_HOME", str(Path.home() / ".local" / "share" / "product-cycle"))).expanduser().resolve()
    # State and sealed evidence are outside the agent's writable project roots.
    return home / hashlib.sha256(str(Path(project).resolve()).encode()).hexdigest()[:24]


def source_files(project):
    """Source projection shared by fingerprinting and delivery packaging."""
    project = Path(project).resolve()
    excluded = {".git", ".product-cycle", "node_modules", ".venv", "__pycache__", "dist", "build", ".runtime"}
    found = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=project,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if found.returncode == 0:
        paths = [project / os.fsdecode(p) for p in found.stdout.split(b"\0") if p]
    else:
        paths = []
        for root, dirs, names in os.walk(project):
            dirs[:] = [name for name in dirs if name not in excluded]
            paths.extend(Path(root) / name for name in names)
    for path in sorted(set(paths)):
        relative = path.relative_to(project)
        if any(part in excluded for part in relative.parts) or not path.is_file():
            continue
        yield path


def fingerprint(project):
    """Hash source files, excluding controller data and dependency trees."""
    project = Path(project).resolve()
    h = hashlib.sha256()
    for path in source_files(project):
        relative = path.relative_to(project)
        if path.is_symlink():
            h.update(str(relative).encode() + b"\0" + os.readlink(path).encode())
            continue
        h.update(str(relative).encode() + b"\0" + path.read_bytes() + b"\0")
    return h.hexdigest()


class Store:
    def __init__(self, project):
        self.project = Path(project).expanduser().resolve()
        self.root = state_root(self.project)
        require(not self.root.is_relative_to(self.project), "Kho trạng thái phải nằm ngoài thư mục dự án mà AI được ghi.")
        require((self.root / "state.sqlite3").is_file(), "Dự án chưa được khởi tạo bằng Product Cycle.")
        self.db = sqlite3.connect(str(self.root / "state.sqlite3"), timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")

    @classmethod
    def create(cls, project, brief, name, model=None, effort=None, mode="live"):
        project = Path(project).expanduser().resolve()
        project.mkdir(parents=True, exist_ok=True)
        root = state_root(project)
        require(not root.is_relative_to(project), "PRODUCT_CYCLE_HOME phải nằm ngoài dự án.")
        require(not root.exists(), "Dự án đã có một quy trình; dùng status để kiểm tra.")
        require(brief.strip(), "Cần mô tả mục tiêu sản phẩm.")
        preparation = prepare_project(project) if mode == "live" else None
        root.mkdir(mode=0o700, parents=True)
        (root / "objects").mkdir()
        (project / ".product-cycle").mkdir(exist_ok=True)
        (root / "brief.md").write_text(brief.rstrip() + "\n")
        config = defaults(model, effort)
        config.update({"name": name, "mode": mode, "created_at": now()})
        if mode == "demo":
            config.update(service_setup_required=False, project_setup_required=False, bootstrap_required=False,
                          gates=["analysis", "design", "plan", "handoff"],
                          executor="codex-app-server", dashboard_read_only=False,
                          collaborative_product=False, experience_checkpoint_required=False)
        write_json(root / "config.json", config)
        if preparation:
            preparation["prepared_at"] = now()
            write_json(root / "bootstrap.json", preparation)
        with sqlite3.connect(str(root / "state.sqlite3")) as db:
            db.executescript("""
                CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO meta VALUES('state','active');
                CREATE TABLE tasks(
                    id TEXT PRIMARY KEY, stage TEXT NOT NULL, title TEXT NOT NULL,
                    instructions TEXT NOT NULL, deps TEXT NOT NULL, criteria TEXT NOT NULL,
                    requirements TEXT NOT NULL, checks TEXT NOT NULL, status TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 1, attempts INTEGER NOT NULL DEFAULT 0,
                    result TEXT, review TEXT, reason TEXT, fingerprint TEXT,
                    accepted_at TEXT, created_at TEXT NOT NULL
                );
                CREATE TABLE attempts(
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
                    revision INTEGER NOT NULL, number INTEGER NOT NULL, phase TEXT NOT NULL,
                    thread_id TEXT, turn_id TEXT, requested_model TEXT NOT NULL,
                    requested_effort TEXT NOT NULL, observed_model TEXT, observed_effort TEXT,
                    tokens INTEGER, status TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT,
                    directory TEXT NOT NULL
                );
                CREATE TABLE evidence(
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
                    revision INTEGER NOT NULL, attempt_id TEXT, kind TEXT NOT NULL,
                    producer TEXT NOT NULL, source TEXT NOT NULL, object_path TEXT NOT NULL,
                    sha256 TEXT NOT NULL, criteria TEXT NOT NULL, requirements TEXT NOT NULL,
                    description TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE decisions(
                    id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, revision INTEGER NOT NULL,
                    action TEXT NOT NULL, actor TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE events(
                    id INTEGER PRIMARY KEY, task_id TEXT, type TEXT NOT NULL,
                    data TEXT NOT NULL, created_at TEXT NOT NULL
                );
            """)
        store = cls(project)
        previous = []
        stages = ["analysis", "design", "architecture", "plan"]
        if config["project_setup_required"]:
            stages += ["project_setup"]
        stages += ["verify", "handoff", "retro"]
        for stage in stages:
            store.add_task(stage, "build" if stage == "project_setup" else stage, STAGE_TITLES[stage], "Complete the " + stage + " contract.",
                           previous, CRITERIA[stage], [], [])
            previous = [stage]
        store.event(None, "cycle.created", {"name": name, "mode": mode, "workflow_version": config["workflow_version"]})
        if preparation:
            store.event(None, "project.prepared", preparation)
        return store

    def close(self):
        self.db.close()

    @property
    def config(self):
        return json_object(self.root / "config.json")

    def foundation(self):
        path = self.root / "bootstrap.json"
        return foundation_status(self.project, json_object(path) if path.is_file() else None)

    def validate_foundation(self):
        if self.config.get("bootstrap_required"):
            require(self.foundation()["status"] == "done",
                    "Chuẩn bị dự án chưa đạt. Kiểm tra Git, quy tắc và skill bằng doctor --project rồi ghi nhận lại bằng bootstrap.")
        if self.config.get("project_setup_required") and self.task("project_setup")["status"] == "done":
            record = next((item for item in self.current_evidence("project_setup") if item["source"] == "CODING_RULES.md"), None)
            require(record is not None and digest(self.safe_path("CODING_RULES.md")) == record["sha256"],
                    "Coding rules đã thay đổi sau khi thiết lập dự án; mở lại bước thiết lập để review thay đổi.")

    def bootstrap(self):
        require(not any(task["status"] in {"running", "reviewing"} for task in self.tasks()),
                "Dừng phiên đang chạy trước khi bổ sung nền tảng dự án.")
        before = fingerprint(self.project)
        report = prepare_project(self.project)
        report["prepared_at"] = now()
        write_json(self.root / "bootstrap.json", report)
        config = self.config
        config["bootstrap_required"] = True
        write_json(self.root / "config.json", config)
        if before != fingerprint(self.project) and self.task("verify")["attempts"]:
            self.reopen("verify", "Nền tảng dự án đã thay đổi; cần kiểm chứng lại bản local.")
        self.event(None, "project.prepared", report)
        return report

    def event(self, task_id, kind, data):
        with self.db:
            self.db.execute("INSERT INTO events(task_id,type,data,created_at) VALUES(?,?,?,?)",
                            (task_id, kind, json.dumps(data, ensure_ascii=False), now()))

    def add_task(self, tid, stage, title, instructions, deps, criteria, requirements, checks):
        with self.db:
            self.db.execute("INSERT INTO tasks(id,stage,title,instructions,deps,criteria,requirements,checks,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (tid, stage, title, instructions, json.dumps(deps), json.dumps(criteria),
                             json.dumps(requirements), json.dumps(checks), "pending", now()))

    @staticmethod
    def decode(row):
        item = dict(row)
        item["role"] = "project_setup" if item["id"] == "project_setup" else item["stage"]
        for field in ["deps", "criteria", "requirements", "checks", "result", "review"]:
            if item.get(field) is not None:
                item[field] = json.loads(item[field])
        return item

    def task(self, tid):
        row = self.db.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        require(row is not None, "Không tìm thấy công việc: " + tid)
        return self.decode(row)

    def tasks(self):
        return [self.decode(row) for row in self.db.execute("SELECT * FROM tasks ORDER BY rowid")]

    def evidence(self, tid, revision=None):
        revision = revision or self.task(tid)["revision"]
        records = []
        for row in self.db.execute("SELECT * FROM evidence WHERE task_id=? AND revision=? ORDER BY created_at,id", (tid, revision)):
            record = dict(row)
            record["criteria"] = json.loads(record["criteria"])
            record["requirements"] = json.loads(record["requirements"])
            records.append(record)
        return records

    def current_evidence(self, tid):
        task = self.task(tid)
        prefix = tid + ":r" + str(task["revision"]) + ":a" + str(task["attempts"]) + ":"
        return [item for item in self.evidence(tid) if item["attempt_id"] and item["attempt_id"].startswith(prefix)]

    def update(self, tid, **fields):
        allowed = {"status", "attempts", "result", "review", "reason", "fingerprint", "accepted_at", "revision", "deps"}
        require(set(fields) <= allowed, "Trường trạng thái không hợp lệ.")
        converted = [json.dumps(value, ensure_ascii=False) if key in {"result", "review", "deps"} and value is not None else value for key, value in fields.items()]
        with self.db:
            self.db.execute("UPDATE tasks SET " + ",".join(key + "=?" for key in fields) + " WHERE id=?", converted + [tid])

    def safe_path(self, relative):
        require(isinstance(relative, str) and relative, "Đường dẫn bằng chứng chưa hợp lệ.")
        path = (self.project / relative).resolve()
        require(path.is_relative_to(self.project), "Bằng chứng phải nằm trong thư mục dự án.")
        rel = path.relative_to(self.project)
        require(not (path.name.startswith(".env") and path.name != ".env.example"), "Không dùng file cấu hình môi trường chứa thông tin bí mật làm bằng chứng.")
        require(".git" not in rel.parts and path not in [self.root / "state.sqlite3", self.root / "config.json"], "Không sử dụng dữ liệu nội bộ làm bằng chứng.")
        require(path.is_file() and 0 < path.stat().st_size <= 20 * 1024 * 1024, "Bằng chứng phải là file có nội dung, tối đa 20 MB.")
        return path

    def record_file(self, tid, relative, description, criteria=None, requirements=None,
                    kind="artifact", producer="worker", attempt_id=None):
        task = self.task(tid)
        path = self.safe_path(relative)
        sha = digest(path)
        target = self.root / "objects" / sha
        if not target.exists():
            shutil.copyfile(path, target)
        eid = "E-" + uuid.uuid4().hex[:12]
        if attempt_id is None and task["attempts"]:
            attempt_id = tid + ":r" + str(task["revision"]) + ":a" + str(task["attempts"]) + ":work"
        require(kind in {"artifact", "check", "browser", "manual"}, "Loại bằng chứng chưa hợp lệ.")
        criteria = criteria or []
        requirements = requirements or []
        require(set(criteria) <= {"C" + str(i + 1) for i in range(len(task["criteria"]))}, "Bằng chứng tham chiếu tiêu chí không tồn tại.")
        with self.db:
            self.db.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (eid, tid, task["revision"], attempt_id, kind, producer,
                             str(path.relative_to(self.project)), str(target.relative_to(self.root)), sha,
                             json.dumps(criteria), json.dumps(requirements), description, now()))
        self.event(tid, "evidence.recorded", {"id": eid, "kind": kind, "producer": producer, "sha256": sha})
        return eid

    def intact(self, records):
        for evidence in records:
            path = self.root / evidence["object_path"]
            require(path.is_file() and digest(path) == evidence["sha256"], "Bằng chứng đã thay đổi hoặc không còn: " + evidence["id"])

    def next_task(self):
        require(self.db.execute("SELECT value FROM meta WHERE key='state'").fetchone()[0] == "active", "Quy trình đang tạm dừng.")
        tasks = self.tasks()
        done = {task["id"] for task in tasks if task["status"] == "done"}
        for task in tasks:
            if task["status"] in {"pending", "rework", "stale"} and set(task["deps"]) <= done:
                if task["attempts"] >= self.config["max_attempts"]:
                    self.update(task["id"], status="blocked", reason="Đã đạt giới hạn thực hiện; cần xác định nguyên nhân rồi mở revision mới.")
                    self.event(task["id"], "task.blocked", {"reason": "attempt_budget"})
                    continue
                return task
        return None

    def begin(self, tid, phase):
        self.validate_foundation()
        task = self.task(tid)
        feedback = None
        require(phase in {"work", "review"}, "Giai đoạn thực thi không hợp lệ.")
        if phase == "work":
            require(task["status"] in {"pending", "rework", "stale", "blocked"}, "Công việc chưa sẵn sàng thực thi.")
            require(all(self.task(dep)["status"] == "done" for dep in task["deps"]), "Phụ thuộc chưa hoàn tất.")
            require(task["attempts"] < self.config["max_attempts"], "Đã đạt giới hạn số lần thực hiện; cần xác định nguyên nhân trước khi tiếp tục.")
            if task["reason"] or task["review"]:
                feedback = {"reason": task["reason"], "review": task["review"],
                            "previous_outputs": [{"id": item["id"], "path": str(self.root / item["object_path"]),
                                                   "original_path": item["source"]}
                                                  for item in self.current_evidence(tid) if item["kind"] == "artifact"]}
            number = task["attempts"] + 1
            self.update(tid, status="running", attempts=number, reason=None, result=None, review=None)
        else:
            require(task["status"] == "reviewing", "Công việc chưa sẵn sàng review.")
            number = task["attempts"]
        directory = self.project / ".product-cycle" / "artifacts" / tid / ("r" + str(task["revision"])) / ("a" + str(number)) / phase
        if phase == "review":
            reviews = self.db.execute("SELECT COUNT(*) FROM attempts WHERE task_id=? AND revision=? AND number=? AND phase='review'", (tid, task["revision"], number)).fetchone()[0]
            directory = directory.with_name("review-" + str(reviews + 1))
        directory.mkdir(parents=True, exist_ok=False)
        aid = tid + ":r" + str(task["revision"]) + ":a" + str(number) + ":" + phase
        if phase == "review":
            aid += ":" + str(reviews + 1)
        model = self.config["models"]["review" if phase == "review" else task["role"]]
        with self.db:
            self.db.execute("INSERT INTO attempts(id,task_id,revision,number,phase,requested_model,requested_effort,status,started_at,directory) VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (aid, tid, task["revision"], number, phase, model["model"], model["effort"], "running", now(), str(directory)))
        self.event(tid, "attempt.started", {"id": aid, "phase": phase, "feedback": feedback, **model})
        if self.config.get("bootstrap_required"):
            self.event(tid, "repository.observed", {"attempt_id": aid, **repository_state(self.project)})
        if phase == "work":
            self.event(tid, "steps.started", {"attempt_id": aid})
        return aid, directory

    def step_progress(self, aid, plan):
        """Transport reports are advisory; only review can confirm a work step."""
        attempt = self.db.execute("SELECT * FROM attempts WHERE id=?", (aid,)).fetchone()
        if not attempt or attempt["phase"] != "work" or attempt["status"] != "running" or not isinstance(plan, list):
            return
        task = self.task(attempt["task_id"])
        if (attempt["revision"], attempt["number"]) != (task["revision"], task["attempts"]):
            return
        known = {step["id"] for step in work_steps(task["role"])}
        for row in plan:
            if not isinstance(row, dict) or not isinstance(row.get("step"), str):
                continue
            sid = row["step"].split(" ", 1)[0].rstrip(".:·")
            status = {"pending": "pending", "in_progress": "running", "completed": "reported"}.get(row.get("status"))
            if sid in known and status:
                self.event(task["id"], "step.progress", {"attempt_id": aid, "step": sid, "status": status})

    def attempt_update(self, aid, **fields):
        allowed = {"thread_id", "turn_id", "observed_model", "observed_effort", "tokens", "status", "ended_at"}
        require(set(fields) <= allowed, "Trường phiên thực thi chưa hợp lệ.")
        with self.db:
            self.db.execute("UPDATE attempts SET " + ",".join(key + "=?" for key in fields) + " WHERE id=?", list(fields.values()) + [aid])

    def latest_directory(self, tid, phase="work"):
        task = self.task(tid)
        row = self.db.execute("SELECT directory FROM attempts WHERE task_id=? AND revision=? AND phase=? ORDER BY rowid DESC LIMIT 1", (tid, task["revision"], phase)).fetchone()
        require(row is not None, "Chưa có phiên thực thi.")
        return Path(row[0])

    def validate_outputs(self, tid, result):
        self.validate_foundation()
        task = self.task(tid)
        require(isinstance(result, dict) and isinstance(result.get("summary"), str) and result["summary"].strip(), "Kết quả cần có tóm tắt.")
        require(isinstance(result.get("artifacts"), list) and result["artifacts"], "Kết quả cần có đầu ra thực tế.")
        require(result.get("blocker") is None or isinstance(result.get("blocker"), str) and result["blocker"].strip(),
                "Cần mô tả cụ thể vấn đề đang chặn và phần cần xử lý.")
        require(isinstance(result.get("limitations"), list), "Kết quả cần khai báo giới hạn.")
        directory = self.latest_directory(tid)
        paths = []
        for item in result["artifacts"]:
            require(isinstance(item, dict) and isinstance(item.get("purpose"), str) and item["purpose"].strip(), "Đầu ra cần có mục đích.")
            require(isinstance(item.get("criteria"), list) and isinstance(item.get("requirements"), list), "Đầu ra cần liên kết tiêu chí và yêu cầu.")
            paths.append(self.safe_path(item.get("path")))
        tracked = self.db.execute("SELECT data FROM events WHERE task_id=? AND type='steps.started'", (tid,)).fetchall()
        current_aid = tid + ":r" + str(task["revision"]) + ":a" + str(task["attempts"]) + ":work"
        tracking = any(json.loads(row[0]).get("attempt_id") == current_aid for row in tracked)
        steps = result.get("steps")
        if tracking or steps is not None:
            expected = {step["id"] for step in work_steps(task["role"])}
            require(isinstance(steps, list) and len(steps) == len(expected) and
                    all(isinstance(step, dict) and isinstance(step.get("id"), str) for step in steps) and {step.get("id") for step in steps} == expected,
                    "Kết quả chưa bao phủ đầy đủ các bước nhỏ.")
            declared = {item["path"] for item in result["artifacts"]}
            for step in steps:
                require(isinstance(step.get("summary"), str) and step["summary"].strip() and
                        isinstance(step.get("artifacts"), list) and step["artifacts"] and
                        all(isinstance(path, str) and path in declared for path in step["artifacts"]),
                        "Mỗi bước nhỏ cần kết quả và đầu ra có thể kiểm chứng.")
        # Existing sealed results keep their original contract until reopened.
        filenames = list(FILES.get(task["role"], []))
        if task["stage"] == "analysis" and self.config.get("collaborative_product"):
            filenames += ["product-direction.json"]
        if self.config.get("service_setup_required") and task["stage"] == "architecture":
            filenames = filenames + ["services.json"]
        if self.config.get("project_setup_required") and task["stage"] == "architecture":
            filenames = filenames + ["project-setup.json"]
        if task["stage"] == "design" and not tracking and steps is None:
            filenames = ["design.md"]
        for filename in filenames:
            require(directory / filename in paths, "Thiếu đầu ra bắt buộc: " + filename)
        if task["stage"] == "design" and "design-baseline.json" in filenames:
            baseline = json_object(directory / "design-baseline.json")
            require(isinstance(baseline.get("has_ui"), bool), "Mốc thiết kế cần xác định sản phẩm có giao diện hay không.")
            for field in ["flows", "states", "acceptance"]:
                require(isinstance(baseline.get(field), list) and baseline[field] and
                        all(isinstance(value, str) and value.strip() for value in baseline[field]), "Mốc thiết kế cần luồng, trạng thái và tiêu chí nghiệm thu.")
            require(isinstance(baseline.get("rules"), dict) and baseline["rules"], "Mốc thiết kế cần các quy tắc giao diện hoặc hợp đồng tương tác.")
            if baseline["has_ui"]:
                reference = baseline.get("visual_reference")
                require(isinstance(reference, str) and reference in {item["path"] for item in result["artifacts"]}, "Cần đầu ra trực quan đã đăng ký để duyệt thiết kế.")
                require(self.safe_path(reference).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".html", ".pdf", ".svg"}, "Mốc thiết kế cần ảnh, prototype hoặc tài liệu trực quan.")
        if task["stage"] == "analysis":
            requirements = validate_requirements(json_object(directory / "requirements.json"))
            if self.config.get("collaborative_product"):
                from .contracts import validate_product_direction
                validate_product_direction(json_object(directory / "product-direction.json"), requirements)
        if task["stage"] == "plan":
            plan = json_object(directory / "plan.json")
            validate_plan(plan, self.requirement_ids())
            if self.config.get("experience_checkpoint_required"):
                from .contracts import validate_experience_checkpoint
                validate_experience_checkpoint(plan)
            if self.config.get("service_setup_required"):
                validate_local_plan(plan, self.services())
        if task["stage"] == "architecture" and self.config.get("service_setup_required"):
            validate_services(json_object(directory / "services.json"))
        if task["stage"] == "architecture" and self.config.get("project_setup_required"):
            validate_project_setup(json_object(directory / "project-setup.json"))
        if task["role"] == "project_setup":
            require(self.project / "CODING_RULES.md" in paths, "Cần coding rules của dự án trước khi triển khai tính năng.")
            setup = self.project_setup_contract()
            if setup["environment_names"]:
                require(self.project / ".env.example" in paths, "Cần mẫu môi trường an toàn cho các cấu hình đã thiết kế.")
        if task["stage"] == "setup":
            self.validate_readiness(tid, json_object(directory / "readiness.json"), blocked=bool(result.get("blocker")))
        if task["stage"] == "retro":
            retro = json_object(directory / "retro.json")
            require(isinstance(retro.get("observations"), list) and isinstance(retro.get("improvements"), list), "Retro cần quan sát và đề xuất cải thiện.")
            for improvement in retro["improvements"]:
                require(isinstance(improvement, dict) and improvement.get("change") and improvement.get("eval_case") and improvement.get("evidence_ids"), "Đề xuất retro cần bằng chứng và tình huống đánh giá.")
                known = {row[0] for row in self.db.execute("SELECT id FROM evidence")}
                require(isinstance(improvement["evidence_ids"], list) and set(improvement["evidence_ids"]) <= known,
                        "Retro tham chiếu bằng chứng không tồn tại.")
                case = improvement["eval_case"]
                require(isinstance(case, dict) and isinstance(case.get("input"), str) and case["input"].strip() and
                        isinstance(case.get("expected"), str) and case["expected"].strip(), "Tình huống đánh giá cần input và expected rõ ràng.")
        return paths

    def requirement_ids(self):
        task = self.task("analysis")
        require(task["status"] == "done", "Phân tích chưa được chấp nhận.")
        records = self.current_evidence("analysis")
        self.intact(records)
        for item in records:
            if Path(item["source"]).name == "requirements.json":
                return validate_requirements(json_object(self.root / item["object_path"]))
        raise WorkflowError("Thiếu danh sách yêu cầu đã chốt.")

    def approved_plan(self):
        require(self.task("plan")["status"] == "done", "Kế hoạch chưa được chấp nhận.")
        records = self.current_evidence("plan")
        self.intact(records)
        for item in records:
            if Path(item["source"]).name == "plan.json":
                return json_object(self.root / item["object_path"])
        raise WorkflowError("Thiếu kế hoạch đã chốt.")

    def sealed_document(self, tid, filename):
        records = self.current_evidence(tid)
        self.intact(records)
        for item in records:
            if Path(item["source"]).name == filename and item["kind"] == "artifact":
                return json_object(self.root / item["object_path"])
        raise WorkflowError("Thiếu tài liệu đã ghi nhận: " + filename)

    def services(self):
        require(self.task("architecture")["status"] == "done", "Thiết kế kỹ thuật chưa hoàn tất.")
        return validate_services(self.sealed_document("architecture", "services.json"))

    def project_setup_contract(self):
        require(self.task("architecture")["status"] == "done", "Thiết kế kỹ thuật chưa hoàn tất.")
        return validate_project_setup(self.sealed_document("architecture", "project-setup.json"))

    def validate_readiness(self, tid, value, blocked=False):
        services = [service for service in self.services() if "setup-" + service["id"] == tid]
        require(services, "Không tìm thấy dịch vụ được giao cấu hình.")
        rows = value.get("services")
        require(isinstance(rows, list) and len(rows) == len(services) and
                all(isinstance(row, dict) and isinstance(row.get("id"), str) for row in rows) and
                {row["id"] for row in rows} == {service["id"] for service in services},
                "Cấu hình cần bao phủ toàn bộ dịch vụ đã thiết kế.")
        for row in rows:
            require(row.get("status") in {"needs_input", "configuring", "ready", "failed"} and
                    isinstance(row.get("note"), str) and row["note"].strip(), "Dịch vụ cần trạng thái và hướng xử lý rõ ràng.")
            require(isinstance(row.get("input_refs"), list) and all(isinstance(ref, str) for ref in row["input_refs"]),
                    "Chỉ ghi tên hoặc tham chiếu cấu hình, không ghi giá trị bí mật.")
        require(blocked or all(row["status"] == "ready" for row in rows), "Dịch vụ chưa sẵn sàng; bổ sung cấu hình rồi kiểm tra lại.")

    def work_finished(self, tid, aid, result):
        task = self.task(tid)
        self.validate_outputs(tid, result)
        for item in result["artifacts"]:
            self.record_file(tid, item["path"], item["purpose"], item["criteria"], item["requirements"], attempt_id=aid)
        self.attempt_update(aid, status="completed", ended_at=now())
        blocked = bool(result.get("blocker"))
        self.update(tid, result=result, status="blocked" if blocked else "reviewing",
                    reason=result.get("blocker"), fingerprint=fingerprint(self.project))
        self.event(tid, "work.completed", {"summary": result["summary"], "revision": task["revision"]})
        if self.config.get("bootstrap_required"):
            self.event(tid, "repository.observed", {"attempt_id": aid, "phase": "work_finished", **repository_state(self.project)})

    def validate_review(self, tid, review):
        self.validate_foundation()
        task = self.task(tid)
        require(isinstance(review, dict) and isinstance(review.get("decision"), str) and
                review["decision"] in {"approve", "rework", "blocked"}, "Review chưa có quyết định hợp lệ.")
        require(isinstance(review.get("summary"), str) and review["summary"].strip() and
                isinstance(review.get("findings"), list), "Review cần nhận xét rõ ràng.")
        if review["decision"] != "approve":
            return
        require(not task["result"].get("blocker"), "Cần giải quyết vấn đề đang chặn trước khi duyệt.")
        records = self.current_evidence(tid)
        self.intact(records)
        evidence_ids = {item["id"] for item in records}
        expected = {"C" + str(i + 1) for i in range(len(task["criteria"]))}
        rows = review.get("criteria", [])
        require(isinstance(rows, list) and len(rows) == len(expected) and
                all(isinstance(item, dict) and isinstance(item.get("id"), str) for item in rows) and
                {item.get("id") for item in rows} == expected,
                "Review chưa đánh giá đầy đủ tiêu chí.")
        for row in rows:
            require(row.get("passed") is True and isinstance(row.get("evidence"), list) and row["evidence"] and
                    all(isinstance(eid, str) and eid in evidence_ids for eid in row["evidence"]) and row.get("reason"), "Tiêu chí chưa đạt hoặc chưa có bằng chứng hợp lệ.")
            require(any(row["id"] in item["criteria"] for item in records if item["id"] in row["evidence"]), "Bằng chứng chưa liên kết với tiêu chí được review.")
        if task["result"].get("steps") is not None:
            results = {step["id"]: step for step in task["result"]["steps"]}
            step_reviews = review.get("steps")
            require(isinstance(step_reviews, list) and len(step_reviews) == len(results) and
                    all(isinstance(step, dict) and isinstance(step.get("id"), str) for step in step_reviews) and
                    {step.get("id") for step in step_reviews} == set(results), "Review chưa đánh giá đầy đủ các bước nhỏ.")
            for step in step_reviews:
                require(step.get("passed") is True and isinstance(step.get("reason"), str) and step["reason"].strip() and
                        isinstance(step.get("evidence"), list) and step["evidence"] and
                        all(isinstance(eid, str) and eid in evidence_ids for eid in step["evidence"]), "Bước nhỏ chưa đạt hoặc thiếu bằng chứng review.")
                require(any(item["id"] in step["evidence"] and item["source"] in results[step["id"]]["artifacts"]
                            for item in records), "Bằng chứng review chưa đối chiếu đúng đầu ra của bước nhỏ.")
        checks = [item for item in records if item["kind"] == "check"]
        required_checks = self.check_commands(task)
        for command in required_checks:
            matching = [json_object(self.root / item["object_path"]) for item in checks]
            require(any(item.get("argv") == command and item.get("exit_code") == 0 and
                        item.get("source_fingerprint") == task["fingerprint"] for item in matching), "Lệnh kiểm tra chưa thành công trên phiên bản hiện tại.")
        require(task["fingerprint"] == fingerprint(self.project), "Sản phẩm thay đổi sau khi kiểm chứng; cần thực hiện lại kiểm tra.")
        if task["stage"] == "verify" and self.approved_plan().get("browser_required", False):
            browser_records = [json_object(self.root / item["object_path"]) for item in records if item["kind"] == "browser" and item["producer"] == "operator"]
            covered = {rid for item in browser_records if item.get("source_fingerprint") == task["fingerprint"] for rid in item.get("requirements", [])}
            require(covered >= self.requirement_ids(), "Cần kiểm chứng trình duyệt thực tế, bao phủ yêu cầu, cho phiên bản hiện tại.")
        if task["stage"] == "handoff" and self.config.get("service_setup_required"):
            verify = self.task("verify")
            require(verify["status"] == "done", "Chưa kiểm chứng bản local.")
            self.validate_outputs("verify", verify["result"])
            self.validate_review("verify", verify["review"])

    def check_commands(self, task):
        if task["stage"] in {"build", "setup", "project_setup"}:
            return task["checks"]
        if task["stage"] == "verify":
            plan = self.approved_plan()
            return plan.get("verification_commands", [])
        return []

    def owner_gate(self, task):
        return task["stage"] in self.config["gates"] or task["id"] in self.config.get("task_gates", [])

    def owner_input(self, tid, actor, note):
        task = self.task(tid)
        require(task["stage"] in {"analysis", "design"}, "Trao đổi định hướng thuộc bước phân tích hoặc thiết kế.")
        require(task["status"] != "done", "Mở lại bước đã chốt trước khi thay đổi định hướng.")
        require(actor.strip() and note.strip(), "Cần ghi người phản hồi và nội dung trao đổi.")
        self.event(tid, "owner.input", {"revision": task["revision"], "actor": actor, "note": note})

    def owner_inputs(self, tid):
        task = self.task(tid)
        return [dict(json.loads(row["data"]), recorded_at=row["created_at"])
                for row in self.db.execute("SELECT data,created_at FROM events WHERE task_id=? AND type='owner.input' ORDER BY id", (tid,))
                if json.loads(row["data"]).get("revision") == task["revision"]]

    def review_finished(self, tid, aid, review):
        self.validate_review(tid, review)
        self.attempt_update(aid, status="completed", ended_at=now())
        status = {"approve": "awaiting_approval" if self.owner_gate(self.task(tid)) else "done",
                  "rework": "rework", "blocked": "blocked"}[review["decision"]]
        self.update(tid, review=review, status="reviewing" if status == "done" else status,
                    reason=None if status in {"done", "awaiting_approval"} else review["summary"])
        if status == "done":
            self.accept(tid)
        self.event(tid, "review.completed", {"decision": review["decision"], "status": status})

    def accept(self, tid):
        task = self.task(tid)
        self.validate_outputs(tid, task["result"])
        self.validate_review(tid, task["review"])
        if task["stage"] == "analysis" and self.config.get("collaborative_product"):
            direction = self.sealed_document(tid, "product-direction.json")
            require(not direction["open_questions"], "Còn câu hỏi định hướng chưa chốt; trao đổi trong Codex và cập nhật phân tích trước khi chấp nhận.")
        # Gate decisions are tied to the exact files reviewed, not mutable filenames.
        for item in self.current_evidence(tid):
            if item["kind"] == "artifact":
                require(digest(self.safe_path(item["source"])) == item["sha256"], "Đầu ra thay đổi sau review; cần review lại.")
        if task["stage"] == "plan":
            plan = json_object(self.latest_directory(tid) / "plan.json")
            tasks = validate_plan(plan, self.requirement_ids())
            services = self.services() if self.config.get("service_setup_required") else []
            if self.config.get("service_setup_required"):
                validate_local_plan(plan, services)
            setup_tasks = [{"id": "setup-" + service["id"], "stage": "setup",
                            "title": "Cấu hình " + service["provider"], "instructions": service["configuration"],
                            "depends_on": [], "requirements": [], "criteria": CRITERIA["setup"],
                            "checks": service["checks"]} for service in services]
            # Avoid partial expansion: all inserts and dependencies commit together.
            with self.db:
                base = ["plan"]
                if self.config.get("project_setup_required"):
                    setup = self.project_setup_contract()
                    self.db.execute("UPDATE tasks SET instructions=?,checks=? WHERE id='project_setup'",
                                    (setup["instructions"], json.dumps(setup["checks"])))
                    base += ["project_setup"]
                self.db.execute("UPDATE tasks SET status='superseded' WHERE stage IN ('build','setup') AND id != 'project_setup'")
                for item in setup_tasks + tasks:
                    deps = base + item["depends_on"] + ["setup-" + sid for sid in item.get("services", [])]
                    existing = self.db.execute("SELECT id FROM tasks WHERE id=?", (item["id"],)).fetchone()
                    if existing:
                        self.db.execute("UPDATE tasks SET title=?,instructions=?,deps=?,criteria=?,requirements=?,checks=?,status='pending' WHERE id=?",
                                        (item["title"], item["instructions"], json.dumps(deps), json.dumps(item["criteria"]),
                                         json.dumps(item["requirements"]), json.dumps(item.get("checks", [])), item["id"]))
                    else:
                        self.db.execute("INSERT INTO tasks(id,stage,title,instructions,deps,criteria,requirements,checks,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                    (item["id"], item.get("stage", "build"), item["title"], item["instructions"], json.dumps(deps),
                                     json.dumps(item["criteria"]), json.dumps(item["requirements"]), json.dumps(item.get("checks", [])), "pending", now()))
                self.db.execute("UPDATE tasks SET deps=? WHERE id='verify'", (json.dumps([item["id"] for item in tasks]),))
            config = self.config
            config["verification_commands"] = plan.get("verification_commands", [])
            config["browser_required"] = plan.get("browser_required", False)
            checkpoint = plan.get("experience_checkpoint")
            config["task_gates"] = [checkpoint["task_id"]] if self.config.get("experience_checkpoint_required") else []
            write_json(self.root / "config.json", config)
        self.update(tid, status="done", accepted_at=now())
        self.event(tid, "task.accepted", {"revision": task["revision"]})

    def decide(self, tid, action, actor, note):
        task = self.task(tid)
        require(task["status"] == "awaiting_approval", "Công việc chưa chờ quyết định.")
        require(action in {"approve", "reject"} and actor.strip() and note.strip(), "Quyết định cần người xác nhận và lý do.")
        if action == "approve":
            self.accept(tid)
        else:
            self.update(tid, status="rework", reason=note)
        with self.db:
            self.db.execute("INSERT INTO decisions(task_id,revision,action,actor,note,created_at) VALUES(?,?,?,?,?,?)",
                            (tid, task["revision"], action, actor, note, now()))
        self.event(tid, "decision.recorded", {"action": action, "actor": actor, "note": note})

    def reopen(self, tid, reason):
        require(reason.strip(), "Cần ghi lý do mở lại công việc.")
        require(not any(task["status"] in {"running", "reviewing"} for task in self.tasks()), "Dừng phiên đang chạy trước khi thay đổi phạm vi.")
        affected = {tid}
        tasks = self.tasks()
        self.task(tid)
        while True:
            expanded = affected | {task["id"] for task in tasks if set(task["deps"]) & affected}
            if expanded == affected:
                break
            affected = expanded
        with self.db:
            for item in affected:
                self.db.execute("UPDATE tasks SET status='stale',revision=revision+1,attempts=0,result=NULL,review=NULL,accepted_at=NULL,reason=? WHERE id=?", (reason, item))
        self.event(tid, "scope.reopened", {"affected": sorted(affected), "reason": reason})
        return sorted(affected)

    def pause(self, paused):
        with self.db:
            self.db.execute("UPDATE meta SET value=? WHERE key='state'", ("paused" if paused else "active",))
        self.event(None, "cycle.paused" if paused else "cycle.resumed", {})

    def recover(self):
        recovered = []
        with self.db:
            for task in self.tasks():
                if task["status"] in {"running", "reviewing"}:
                    self.db.execute("UPDATE tasks SET status='blocked',reason=? WHERE id=?", ("Phiên trước bị gián đoạn; kiểm tra thay đổi thực tế rồi mở lại công việc.", task["id"]))
                    recovered.append(task["id"])
            self.db.execute("UPDATE attempts SET status='interrupted',ended_at=? WHERE status IN ('running','queued')", (now(),))
        self.event(None, "cycle.recovered", {"tasks": recovered})
        return recovered

    def latest_continuation(self, task, attempt):
        """Read sealed chat reports in turn order, not their ingestion order."""
        from datetime import datetime

        reports = []
        records = self.current_evidence(task["id"])
        for record in records:
            if record["attempt_id"] != attempt["id"] or not Path(record["source"]).name.startswith("continuation-"):
                continue
            try:
                self.intact([record])
                report = json_object(self.root / record["object_path"])
                if report.get("thread_id") != attempt["thread_id"] or report.get("phase") != attempt["phase"]:
                    continue
                turn_id = report["turn_id"]
                stamp = report.get("completed_at")
                if not isinstance(stamp, (int, float)):
                    try:
                        turn_uuid = uuid.UUID(turn_id)
                        require(turn_uuid.version == 7, "Expected a time-ordered turn ID")
                        stamp = (turn_uuid.int >> 80) / 1000
                    except (ValueError, WorkflowError):
                        stamp = datetime.fromisoformat(report["received_at"].replace("Z", "+00:00")).timestamp()
                messages = report["messages"]
                if not isinstance(messages, list) or not messages or not all(isinstance(text, str) for text in messages):
                    continue
                reports.append((stamp, turn_id, record, messages[-1]))
            except (WorkflowError, ValueError, KeyError, TypeError, OSError):
                continue
        if not reports:
            return None
        _, turn_id, record, message = max(reports, key=lambda item: item[:2])
        try:
            json.loads(message)
        except ValueError:
            pass
        else:
            return None  # Structured outputs are shown through the task's criteria, not raw JSON.
        linked = []
        for link in re.findall(r'\]\(<?([^\n)]+)>?\)', message):
            path = (self.project / link.strip().strip("<>")).resolve()
            item = next((item for item in reversed(records) if self.project / item["source"] == path), None)
            if item and Path(item["source"]).suffix.lower() in {".md", ".html", ".pdf"} and item["id"] not in linked:
                linked.append(item["id"])
        return {"turn_id": turn_id, "evidence_id": record["id"], "message": message, "reports": linked}

    def execution_status(self, tasks, events):
        import fcntl
        from datetime import datetime, timezone

        # A stored 'running' status or a leftover PID alone cannot prove a live controller.
        with (self.root / "runner.lock").open("a+") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                active = True
            else:
                active = False
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        task = next((task for task in tasks if task["status"] in {"running", "reviewing"}), None)
        row = self.db.execute("SELECT * FROM attempts ORDER BY rowid DESC LIMIT 1").fetchone()
        attempt = dict(row) if row else None
        observed = next((event for event in events if attempt and event["type"] == "thread.observed" and
                         event["data"].get("attempt_id") == attempt["id"]), None)
        external_active = bool(observed and observed["data"].get("active") and
                               (datetime.now(timezone.utc) - datetime.fromisoformat(observed["created_at"].replace("Z", "+00:00"))).total_seconds() < 45)
        native = self.config.get("executor", "codex-app-server") == "codex-desktop"
        if native:
            active = external_active  # The read-only watcher lock is not proof of AI activity.
        if external_active and not active:
            task = next((item for item in tasks if item["id"] == attempt["task_id"]), None)
            active = True
        activity = next((event for event in events if attempt and event["data"].get("attempt_id") == attempt["id"]
                         and event["type"] in {"runtime.activity", "runtime.retry", "thread.synced", "check.started", "check.completed"}), None)
        stamp = activity["created_at"] if activity else (attempt["ended_at"] or attempt["started_at"]) if attempt else None
        failure_is_latest = bool(not active and attempt and attempt["status"] in {"failed", "interrupted"} and
                                 attempt["ended_at"] and (not stamp or attempt["ended_at"] >= stamp))
        if failure_is_latest:
            stamp = attempt["ended_at"]
        age = max(0, int((datetime.now(timezone.utc) - datetime.fromisoformat(stamp.replace("Z", "+00:00"))).total_seconds())) if stamp else None
        phase = "check" if active and activity and activity["type"] == "check.started" else attempt["phase"] if active and attempt and attempt["status"] == "running" else "controller" if active else None
        if active and activity and activity["type"] == "runtime.retry" and attempt and attempt["status"] == "running":
            phase = "retry"
        if external_active:
            phase = attempt["phase"]
            stamp = observed["created_at"]
            age = max(0, int((datetime.now(timezone.utc) - datetime.fromisoformat(stamp.replace("Z", "+00:00"))).total_seconds()))
        blocked = next((item for item in tasks if item["status"] == "blocked"), None)
        status = "running" if active else "interrupted" if task and attempt and attempt["status"] == "running" else "blocked" if blocked else "idle"
        if native and attempt and attempt["status"] == "queued":
            status, active, phase = "queued", False, attempt["phase"]
            task = next((item for item in tasks if item["id"] == attempt["task_id"]), None)
        elif native and not active and task and attempt and attempt["status"] == "running":
            status = "waiting_native"
        activity_names = {"commandExecution": "Đang chạy công cụ", "fileChange": "Đang cập nhật tệp",
                          "agentMessage": "Đang cập nhật kết quả", "reasoning": "Đang xử lý công việc",
                          "mcpToolCall": "Đang dùng công cụ", "webSearch": "Đang tìm thông tin"}
        description = activity_names.get(activity["data"].get("item_type"), "Đã nhận cập nhật từ AI") if activity else None
        if activity and activity["type"].startswith("check."):
            description = "Đang chạy kiểm tra theo kế hoạch" if activity["type"] == "check.started" else "Đã nhận kết quả kiểm tra"
        if activity and activity["type"] == "runtime.retry":
            description = "Model quá tải; đang chờ thử lại với model đã chọn"
        if activity and activity["type"] == "thread.synced":
            description = "Đã đồng bộ kết quả làm tiếp trong Codex"
        if external_active:
            description = "Chat Codex đang làm việc; chờ kết quả để đồng bộ"
        if failure_is_latest:
            description = "Phiên thực thi đã dừng; cần xử lý để tiếp tục"
        if status == "queued":
            description = "Công việc đã chuẩn bị; chờ thực hiện trong Codex"
        elif status == "waiting_native":
            description = "Đã gắn chat Codex; chưa nhận được xác nhận đang chạy"
        current = task or blocked
        continuation = self.latest_continuation(current, attempt) if current and attempt and attempt["task_id"] == current["id"] else None
        waiting_for_verification = bool(status == "blocked" and current and current["stage"] == "verify" and
                                       (current["reason"] or "").startswith(("Đã nhận kết quả làm tiếp trong Codex.",
                                                                              "Còn thiếu bằng chứng nghiệm thu trình duyệt")))
        return {"status": status, "active": active, "backend": "codex-desktop" if native or external_active else "codex-app-server", "phase": phase,
                "task_id": task["id"] if task else blocked["id"] if blocked else None,
                "task_title": task["title"] if task else blocked["title"] if blocked else None,
                "reason": current["reason"] if not active and current and current["status"] == "blocked" else None,
                "attempt": attempt, "last_activity_at": stamp, "seconds_since_activity": age,
                "activity": description, "continuation": continuation, "waiting_for_verification": waiting_for_verification}

    def snapshot(self, full_history=False):
        from .progress import task_progress, stage_progress, development_progress, service_progress
        tasks = self.tasks()
        config = self.config
        progress_events = [dict(row) for row in self.db.execute("SELECT task_id,type,data,created_at FROM events WHERE type IN ('steps.started','step.progress') ORDER BY id")]
        for event in progress_events:
            event["data"] = json.loads(event["data"])
        decisions = [dict(row) for row in self.db.execute("SELECT * FROM decisions ORDER BY id")]
        for task in tasks:
            history = []
            for revision in range(1, task["revision"] + 1):
                history.extend(self.evidence(task["id"], revision))
            task["evidence"] = history
            task["attempt_history"] = [dict(row) for row in self.db.execute("SELECT * FROM attempts WHERE task_id=? ORDER BY rowid", (task["id"],))]
            task["steps"] = task_progress(task, tasks, config, progress_events, decisions, self.root)
            task["owner_inputs"] = self.owner_inputs(task["id"])
            task["owner_gate"] = self.owner_gate(task)
            if task["stage"] == "analysis":
                task["product_direction"] = self.sealed_document(task["id"], "product-direction.json") if any(Path(item["source"]).name == "product-direction.json" for item in self.current_evidence(task["id"])) else None
            if task["stage"] == "design":
                current = self.current_evidence(task["id"])
                baseline = next((item for item in current if Path(item["source"]).name == "design-baseline.json"), None)
                if baseline:
                    task["design_baseline"] = json_object(self.root / baseline["object_path"])
                    task["design_baseline"]["reference_evidence"] = next((item["id"] for item in current if item["source"] == task["design_baseline"].get("visual_reference")), None)
        events = [dict(row) for row in self.db.execute("SELECT * FROM events ORDER BY id DESC" + ("" if full_history else " LIMIT 250"))]
        for event in events:
            event["data"] = json.loads(event["data"])
        plan_task = next(task for task in tasks if task["id"] == "plan")
        plan = None
        if plan_task["result"]:
            record = next((item for item in self.current_evidence("plan") if Path(item["source"]).name == "plan.json"), None)
            if record:
                self.intact([record])
                plan = json_object(self.root / record["object_path"])
        architecture = next(task for task in tasks if task["id"] == "architecture")
        services = []
        if architecture["result"]:
            record = next((item for item in self.current_evidence("architecture") if Path(item["source"]).name == "services.json"), None)
            if record:
                self.intact([record])
                services = validate_services(json_object(self.root / record["object_path"]))
        readiness = {task["id"]: self.sealed_document(task["id"], "readiness.json")
                     for task in tasks if task["stage"] == "setup" and task["result"] and task["status"] != "superseded"}
        cycle_state = self.db.execute("SELECT value FROM meta WHERE key='state'").fetchone()[0]
        return {"config": config, "project": str(self.project),
                "foundation": self.foundation(),
                "state": cycle_state,
                "tasks": tasks, "stages": stage_progress(tasks, config), "events": events,
                "execution": self.execution_status(tasks, events),
                "development": development_progress(tasks, plan, cycle_state),
                "services": service_progress(services, tasks, readiness, architecture["status"]),
                "delivery": {"mode": config.get("delivery_mode", "local"),
                             "plan": plan.get("delivery") if plan else None,
                             "verification_status": self.task("verify")["status"],
                             "acceptance_status": self.task("handoff")["status"],
                             "release_deferred": config.get("release_deferred", True)},
                "tokens": self.db.execute("SELECT SUM(tokens) FROM attempts").fetchone()[0],
                "token_tracking": {"complete": not any(a[0] is None for a in self.db.execute("SELECT tokens FROM attempts")),
                                   "work": self.db.execute("SELECT SUM(tokens) FROM attempts WHERE phase='work'").fetchone()[0],
                                   "review": self.db.execute("SELECT SUM(tokens) FROM attempts WHERE phase='review'").fetchone()[0]},
                "decisions": decisions}

    def package(self, destination):
        self.validate_foundation()
        require(all(task["status"] in {"done", "superseded"} for task in self.tasks()), "Chỉ đóng gói khi toàn bộ quy trình đã hoàn tất.")
        records = [item for task in self.snapshot()["tasks"] for item in task["evidence"]]
        self.intact(records)
        require(self.task("verify")["fingerprint"] == fingerprint(self.project), "Sản phẩm thay đổi sau nghiệm thu; cần kiểm chứng lại.")
        destination = Path(destination).resolve()
        require(not destination.exists() and not destination.is_relative_to(self.project), "Gói bàn giao cần một thư mục mới nằm ngoài dự án.")
        destination.mkdir(parents=True)
        (destination / "evidence").mkdir()
        (destination / "source").mkdir()
        source_manifest, omitted = [], []
        for source in source_files(self.project):
            relative = source.relative_to(self.project)
            # Include source, not runtime secrets or external symlink targets.
            if source.is_symlink() or (source.name.startswith(".env") and source.name != ".env.example"):
                omitted.append(str(relative))
                continue
            target = destination / "source" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            source_manifest.append({"path": str(relative), "sha256": digest(target)})
        snapshot = self.snapshot(full_history=True)
        write_json(destination / "manifest.json", {"workflow_version": self.config["workflow_version"], "packaged_at": now(),
                  "source_fingerprint": fingerprint(self.project), "mode": self.config["mode"], "snapshot": snapshot,
                  "source_files": source_manifest, "omitted_source_paths": omitted})
        for item in records:
            shutil.copyfile(self.root / item["object_path"], destination / "evidence" / item["sha256"])
        (destination / "brief.md").write_text((self.root / "brief.md").read_text())
        return destination


@contextlib.contextmanager
def runner_lock(store):
    """One controller per project. The OS releases the lock after a crash."""
    import fcntl
    with (store.root / "runner.lock").open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WorkflowError("Một phiên điều phối khác đang hoạt động.") from exc
        lock.seek(0)
        lock.truncate()
        lock.write(str(os.getpid()))
        lock.flush()
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
