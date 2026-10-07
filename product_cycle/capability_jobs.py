"""Native-tool handoffs; queueing or submitting never approves product work.

Runtime callers authenticate thread/turn before request. Native operations are
scoped by the project owner's authorization, not by the contents of a job prompt.
The supervisor holds runner_lock around claim/resume and source-state changes.
"""

import hashlib
import json
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from .codex import CodexClient
from .contracts import require
from .store import digest, fingerprint, now, write_json


BLOCKER_PREFIX = "Chờ công cụ: "
SOURCE_CHANGED_REASON = "Phiên bản sản phẩm đã thay đổi trước khi công cụ được nhận việc. Cần kiểm tra lại yêu cầu trên phiên bản hiện tại."
CAPABILITIES = {"image_generation": "Tạo hình ảnh", "computer_use": "Thao tác ứng dụng"}
TOOLS = {"image_generation": "image_gen.imagegen", "computer_use": "mcp__cua_repl.js"}
ACTIVE = "('preparing','dispatching','running','checking','unknown','backoff')"


def migrate(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS capability_jobs(
          id TEXT PRIMARY KEY, source_run_id TEXT NOT NULL REFERENCES team_runs(id),
          source_agent_id TEXT NOT NULL, task_id TEXT NOT NULL REFERENCES tasks(id),
          revision INTEGER NOT NULL, capability TEXT NOT NULL, prompt TEXT NOT NULL,
          client_key TEXT NOT NULL, source_fingerprint TEXT NOT NULL, status TEXT NOT NULL,
          created_at TEXT NOT NULL, actor TEXT, claimed_at TEXT, expires_at REAL,
          thread_id TEXT, bound_at TEXT, completed_at TEXT, manifest TEXT, reason TEXT,
          consumed_at TEXT, UNIQUE(source_run_id,client_key));
    """)
    if "source_root" not in {row[1] for row in db.execute("PRAGMA table_info(capability_jobs)")}:
        db.execute("ALTER TABLE capability_jobs ADD COLUMN source_root TEXT")
    if "resource_key" not in {row[1] for row in db.execute("PRAGMA table_info(capability_jobs)")}:
        db.execute("ALTER TABLE capability_jobs ADD COLUMN resource_key TEXT")
    db.commit()


def resource_in_use(store, resource, exclude=None):
    return bool(resource and store.db.execute("""SELECT id FROM capability_jobs WHERE resource_key=?
        AND status IN ('claimed','bound','unknown') AND id!=? LIMIT 1""", (resource, exclude or "")).fetchone())


def _source(store, job):
    source = Path(job.get("source_root") or store.project).resolve()
    require(source == store.task_source(job["task_id"]) and source.is_dir(),
            "Source được giao cho công cụ đã thay đổi hoặc không còn tồn tại; cần đối chiếu yêu cầu.")
    return source


def _text(value, message):
    require(isinstance(value, str) and value.strip(), message)
    return value.strip()


def _read(store, job_id):
    row = store.db.execute("""SELECT j.*, t.revision AS current_revision,
        t.title AS task_title, t.stage FROM capability_jobs j JOIN tasks t ON t.id=j.task_id
        WHERE j.id=?""", (job_id,)).fetchone()
    require(row is not None, "Không tìm thấy yêu cầu công cụ.")
    job = dict(row)
    job["source_root"] = job.get("source_root") or str(store.project)
    job["manifest"] = json.loads(job["manifest"]) if job["manifest"] else None
    job["capability_name"] = CAPABILITIES[job["capability"]]
    job["is_current"] = job["revision"] == job["current_revision"]
    job["recorded_status"] = job["status"]
    if not job["is_current"]:
        job["status"] = "stale"
    return job


def _event(store, job, kind, **data):
    store.db.execute("INSERT INTO events(task_id,type,data,created_at) VALUES(?,?,?,?)",
                     (job["task_id"], "capability." + kind,
                      json.dumps(dict(data, job_id=job["id"], revision=job["revision"]), ensure_ascii=False), now()))


def _idle(store, job):
    return not store.db.execute("SELECT 1 FROM team_runs WHERE task_id=? AND revision=? AND status IN "
        + ACTIVE + " LIMIT 1", (job["task_id"], job["revision"])).fetchone() and not store.db.execute(
        "SELECT 1 FROM attempts WHERE task_id=? AND revision=? AND status IN ('queued','running') LIMIT 1",
        (job["task_id"], job["revision"])).fetchone()


def _origin_current(store, job):
    return bool(store.db.execute("""SELECT 1 FROM team_runs r JOIN tasks t ON t.id=r.task_id
        LEFT JOIN attempts a ON a.id=r.attempt_id WHERE r.id=? AND r.revision=t.revision
        AND (r.attempt_id IS NULL OR (a.number=t.attempts AND a.revision=t.revision))""",
        (job["source_run_id"],)).fetchone())


def request(store, run, capability, prompt, client_key):
    """Queue a scoped request from a persisted, authenticated current mission."""
    require(capability in CAPABILITIES, "Công cụ được yêu cầu chưa được hỗ trợ.")
    prompt = _text(prompt, "Cần mô tả công việc cần công cụ hỗ trợ.")
    client_key = _text(client_key, "Cần mã yêu cầu để tránh tạo công việc trùng.")
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        origin = store.db.execute("""SELECT r.*, t.revision AS current_revision, t.attempts,
            t.status AS task_status, a.number AS attempt_number, a.revision AS attempt_revision
            FROM team_runs r JOIN tasks t ON t.id=r.task_id LEFT JOIN attempts a ON a.id=r.attempt_id
            WHERE r.id=?""", (run.get("id"),)).fetchone()
        require(origin is not None and all(run.get(key) == origin[key] for key in ("agent_id", "task_id", "revision")),
                "Yêu cầu cần xuất phát từ phiên được giao công việc này.")
        require(origin["status"] == "running" and origin["revision"] == origin["current_revision"]
                and origin["task_status"] != "done", "Yêu cầu không còn thuộc công việc hiện tại.")
        require(origin["attempt_id"] is None or (origin["attempt_number"] == origin["attempts"]
                and origin["attempt_revision"] == origin["revision"]), "Yêu cầu thuộc lần thực hiện trước.")
        previous = store.db.execute("SELECT id FROM capability_jobs WHERE source_run_id=? AND client_key=?",
                                    (origin["id"], client_key)).fetchone()
        if previous:
            job = _read(store, previous["id"])
            require(job["capability"] == capability and job["prompt"] == prompt,
                    "Mã yêu cầu này đã được dùng cho công việc khác.")
            return job
        job_id = "capability-" + uuid.uuid4().hex
        store.db.execute("""INSERT INTO capability_jobs(id,source_run_id,source_agent_id,task_id,
            revision,capability,prompt,client_key,source_fingerprint,status,created_at,source_root,resource_key)
            VALUES(?,?,?,?,?,?,?,?,?,'queued',?,?,?)""", (job_id, origin["id"], origin["agent_id"],
            origin["task_id"], origin["revision"], capability, prompt, client_key, store.task_fingerprint(origin["task_id"]), now(),
            str(store.task_source(origin["task_id"])), origin["resource_key"]))
        job = _read(store, job_id)
        _event(store, job, "requested", capability=capability)
        return job


def expire(store):
    """Expire uncertain claims; safely cancel unclaimed jobs for obsolete source.

    Source inspection waits for active writers to finish. Cancelling a queued job
    invokes no tool and leaves its task blocked for a concrete director repair.
    """
    expired = []
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        rows = store.db.execute("""SELECT id FROM capability_jobs WHERE status IN ('claimed','bound')
            AND expires_at<=?""", (time.time(),)).fetchall()
        for row in rows:
            job = _read(store, row["id"])
            store.db.execute("UPDATE capability_jobs SET status='unknown',reason=? WHERE id=?",
                             ("Chưa xác nhận được kết quả của phiên công cụ đã hết thời gian chờ.", job["id"]))
            _event(store, job, "expired", previous_status=job["recorded_status"], thread_id=job["thread_id"])
            expired.append(job["id"])
        if not store.db.execute("SELECT 1 FROM team_runs WHERE source_writer=1 AND status IN " + ACTIVE
                                + " LIMIT 1").fetchone():
            queued = store.db.execute("""SELECT j.id FROM capability_jobs j JOIN tasks t ON t.id=j.task_id
                WHERE j.status='queued' AND j.revision=t.revision""").fetchall()
            for row in queued:
                job = _read(store, row["id"])
                if not _idle(store, job):
                    continue
                current_source = fingerprint(_source(store, job))
                if job["source_fingerprint"] == current_source:
                    continue
                store.db.execute("UPDATE capability_jobs SET status='cancelled',reason=? WHERE id=?",
                                 (SOURCE_CHANGED_REASON, job["id"]))
                # Keep any owner question in its journal. Management still waits
                # for real answers; answering alone cannot skip the source repair.
                store.db.execute("UPDATE tasks SET reason=? WHERE id=? AND status='blocked'",
                                 (SOURCE_CHANGED_REASON, job["task_id"]))
                _event(store, job, "cancelled", previous_status="queued", reason=SOURCE_CHANGED_REASON,
                       current_source_fingerprint=current_source)
                expired.append(job["id"])
    return expired


def source_in_use(store):
    """Freeze source writes/check barriers while current native outcomes are pending."""
    return bool(store.db.execute("""SELECT 1 FROM capability_jobs j JOIN tasks t ON t.id=j.task_id
        WHERE j.revision=t.revision AND j.status IN ('claimed','bound','unknown') LIMIT 1""").fetchone())


def claim(store, job_id, actor, project, ttl_seconds=1800):
    actor = _text(actor, "Cần ghi người phụ trách công cụ.")
    require(Path(project).expanduser().resolve() == store.project, "Hãy nhận công việc trong đúng dự án.")
    require(isinstance(ttl_seconds, (int, float)) and 0 < ttl_seconds <= 86400,
            "Thời gian nhận công việc cần từ một giây đến một ngày.")
    expire(store)
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        job = _read(store, job_id)
        require(job["is_current"] and _origin_current(store, job),
                "Phạm vi hoặc lần thực hiện đã thay đổi; hãy đọc yêu cầu công cụ mới.")
        if job["status"] in {"claimed", "bound"}:
            require(job["actor"] == actor, "Công việc công cụ đã có người phụ trách.")
            return job
        require(job["status"] == "queued", "Không tự chạy lại công việc đã kết thúc hoặc chưa rõ kết quả.")
        task = store.task(job["task_id"])
        require(task["status"] == "blocked" and (task["reason"] or "").startswith(BLOCKER_PREFIX)
                and _idle(store, job), "Chờ phiên thực hiện dừng ở yêu cầu công cụ trước khi nhận công việc.")
        require(not store.db.execute("SELECT 1 FROM team_runs WHERE source_writer=1 AND status IN " + ACTIVE
                                     + " LIMIT 1").fetchone(), "Chờ phiên đang thay đổi sản phẩm hoàn tất trước khi nhận công cụ.")
        require(not resource_in_use(store, job["resource_key"], job["id"])
                and (not job["resource_key"] or not store.db.execute("SELECT id FROM team_runs WHERE resource_key=? AND status IN " + ACTIVE, (job["resource_key"],)).fetchone()),
                "Chờ instance dùng chung kết thúc hoặc được đối chiếu trước khi nhận công cụ.")
        require(job["source_fingerprint"] == fingerprint(_source(store, job)),
                "Sản phẩm đã thay đổi; cần yêu cầu công cụ cho phiên bản hiện tại.")
        store.db.execute("""UPDATE capability_jobs SET status='claimed',actor=?,claimed_at=?,expires_at=?
            WHERE id=?""", (actor, now(), time.time() + ttl_seconds, job_id))
        _event(store, job, "claimed", actor=actor)
        return _read(store, job_id)


def bind(store, job_id, actor, thread_id, client_factory=CodexClient):
    """Read an existing native thread's identity/cwd; never launch a model turn."""
    actor = _text(actor, "Cần ghi người phụ trách công cụ.")
    thread_id = _text(thread_id, "Cần gắn công việc với chat Codex hiện tại.")
    expire(store)
    job = _read(store, job_id)
    require(job["actor"] == actor and job["status"] in {"claimed", "bound"},
            "Cần nhận công việc trước khi gắn chat.")
    with client_factory(store.project / ".product-cycle" / "capabilities" / job_id) as client:
        thread = client.read_thread(thread_id)
    require(thread.get("id") == thread_id and isinstance(thread.get("cwd"), str)
            and Path(thread["cwd"]).resolve() in {store.project, _source(store, job)},
            "Chat Codex cần thuộc đúng dự án hoặc workspace được giao.")
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        job = _read(store, job_id)
        require(job["is_current"] and job["status"] in {"claimed", "bound"} and job["actor"] == actor
                and job["expires_at"] > time.time(), "Yêu cầu nhận công việc đã thay đổi.")
        require(_idle(store, job) and job["source_fingerprint"] == fingerprint(_source(store, job)),
                "Công việc hoặc phiên bản sản phẩm đã thay đổi; hãy đọc lại yêu cầu hiện tại.")
        require(not job["thread_id"] or job["thread_id"] == thread_id, "Công việc đã gắn với chat khác.")
        require(not store.db.execute("""SELECT 1 FROM capability_jobs WHERE thread_id=? AND id!=?
            AND status IN ('claimed','bound','unknown') LIMIT 1""", (thread_id, job_id)).fetchone(),
            "Chat này còn một công việc công cụ chưa kết thúc.")
        require(not store.db.execute("SELECT 1 FROM team_runs WHERE thread_id=? AND status IN " + ACTIVE,
                                     (thread_id,)).fetchone(), "Chat này đang thực hiện công việc khác.")
        require(not store.db.execute("SELECT 1 FROM attempts WHERE thread_id=? AND status IN ('queued','running')",
                                     (thread_id,)).fetchone(), "Chat này đang thực hiện công việc khác.")
        if job["status"] != "bound":
            store.db.execute("UPDATE capability_jobs SET status='bound',thread_id=?,bound_at=? WHERE id=?",
                             (thread_id, now(), job_id))
            _event(store, job, "bound", actor=actor, thread_id=thread_id)
        return _read(store, job_id)


def _validate_manifest(store, job, manifest):
    require(isinstance(manifest, dict), "Cần gửi danh sách kết quả thực tế của công cụ.")
    require(manifest.get("source_fingerprint") == job["source_fingerprint"]
            and fingerprint(_source(store, job)) == job["source_fingerprint"],
            "Kết quả cần gắn với đúng phiên bản sản phẩm đã yêu cầu.")
    require(manifest.get("source_root", str(store.project)) == str(_source(store, job)),
            "Kết quả công cụ cần ghi đúng source_root đã được giao.")
    observations = manifest.get("observations")
    require(isinstance(observations, list) and observations
            and all(isinstance(item, str) and item.strip() for item in observations),
            "Cần ghi lại những gì thực sự quan sát được khi dùng công cụ.")
    tool = manifest.get("tool")
    require(isinstance(tool, dict) and tool.get("name") == TOOLS[job["capability"]]
            and isinstance(tool.get("prompt"), str) and tool["prompt"].strip(),
            "Cần ghi công cụ và yêu cầu thực tế đã sử dụng.")
    artifacts = manifest.get("artifacts")
    require(isinstance(artifacts, list) and artifacts, "Cần lưu file kết quả thực tế trong dự án.")
    validated, content, paths = [], [], set()
    output_root = (store.project / ".product-cycle" / "capabilities" / job["id"]).resolve()
    for item in artifacts:
        require(isinstance(item, dict), "Danh sách file kết quả chưa hợp lệ.")
        path = store.safe_path(item.get("path"))
        require(path.is_relative_to(output_root), "Lưu kết quả trong thư mục được giao cho công việc công cụ.")
        relative = str(path.relative_to(store.project))
        require(relative not in paths, "Không gửi cùng một file kết quả nhiều lần.")
        paths.add(relative)
        purpose = _text(item.get("purpose"), "Cần mô tả nội dung của mỗi file kết quả.")
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        require(item.get("sha256") == sha, "File kết quả đã thay đổi; kiểm tra và gửi lại dấu xác nhận file.")
        validated.append({"path": relative, "sha256": sha, "purpose": purpose, "object_path": "objects/" + sha})
        content.append((sha, data))
    # Copy only bytes that were validated, preserving evidence if source files change.
    for sha, data in content:
        target = store.root / "objects" / sha
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            require(hashlib.sha256(target.read_bytes()).hexdigest() == sha, "Bản kết quả đã lưu cần được kiểm tra lại.")
        else:
            temporary = target.with_name(target.name + ".tmp-" + uuid.uuid4().hex)
            temporary.write_bytes(data)
            temporary.replace(target)
    return dict(manifest, artifacts=validated)


def _browser_payload(store, job, manifest):
    browser = manifest.get("browser")
    if browser is None:
        return None
    require(job["capability"] == "computer_use" and store.task(job["task_id"])["stage"] == "verify",
            "Bằng chứng trình duyệt cần thuộc công việc nghiệm thu bằng công cụ thao tác ứng dụng.")
    require(isinstance(browser, dict), "Thông tin kiểm chứng trình duyệt chưa hợp lệ.")
    url = _text(browser.get("url"), "Cần ghi địa chỉ đã mở để kiểm chứng.")
    parsed = urlsplit(url)
    require(parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password,
            "Cần địa chỉ trang web hợp lệ, không chứa thông tin đăng nhập.")
    requirements = browser.get("requirements")
    require(isinstance(requirements, list) and requirements
            and all(isinstance(item, str) for item in requirements)
            and len(set(requirements)) == len(requirements)
            and set(requirements) <= store.requirement_ids(), "Cần ghi đúng các yêu cầu đã chốt được kiểm chứng.")
    observation = _text(browser.get("observation"), "Cần ghi điều đã thực sự quan sát trong trình duyệt.")
    require(observation in manifest["observations"], "Nhận xét trình duyệt cần nằm trong các quan sát thực tế đã gửi.")
    screenshot = store.safe_path(browser.get("screenshot"))
    relative = str(screenshot.relative_to(store.project))
    artifact = next((item for item in manifest["artifacts"] if item["path"] == relative), None)
    require(artifact is not None and digest(screenshot) == artifact["sha256"],
            "Ảnh chụp cần là file đã gửi và được xác nhận trong danh sách kết quả.")
    from .screens import IMAGE_SUFFIXES, image_size
    require(screenshot.suffix.lower() in IMAGE_SUFFIXES and all(value > 0 for value in image_size(screenshot)),
            "Cần file ảnh chụp màn hình PNG, JPEG hoặc WebP hợp lệ.")
    return dict(browser, url=url, screenshot=relative, observation=observation, requirements=requirements)


def _register_browser(store, job, manifest):
    """Use ordinary operator evidence records, reusing partial registrations on retry.

    Caller holds runner_lock; record_file commits its own transactions. Keeping the
    job bound until registration finishes also preserves the native source freeze.
    """
    browser = manifest.get("browser")
    if browser is None:
        return None
    task = store.task(job["task_id"])
    require(task["stage"] == "verify" and task["status"] in {"blocked", "reviewing", "running"}
            and task["attempts"] > 0 and task["revision"] == job["revision"]
            and fingerprint(_source(store, job)) == job["source_fingerprint"],
            "Cần phiên nghiệm thu hiện tại cho đúng phiên bản đã quan sát.")
    # The same source version can reuse real observations in a later verify attempt.
    require(set(browser["requirements"]) <= store.requirement_ids(), "Các yêu cầu được kiểm chứng đã thay đổi.")
    artifact = next(item for item in manifest["artifacts"] if item["path"] == browser["screenshot"])
    sealed = store.root / artifact["object_path"]
    require(sealed.is_file() and digest(sealed) == artifact["sha256"], "Bản ảnh chụp đã lưu cần được kiểm tra lại.")
    directory = store.project / ".product-cycle" / "capabilities" / job["id"]
    capture = directory / ("operator-capture-" + artifact["sha256"] + Path(artifact["path"]).suffix.lower())
    if capture.exists():
        require(digest(capture) == artifact["sha256"], "Bản ảnh chụp dùng để ghi bằng chứng đã thay đổi.")
    else:
        capture.write_bytes(sealed.read_bytes())
    capture_path = str(capture.relative_to(store.project))
    records = store.current_evidence(job["task_id"])
    image = next((row for row in records if row["source"] == capture_path and row["producer"] == "operator"
                  and row["sha256"] == artifact["sha256"] and row["kind"] == "artifact"), None)
    image_id = image["id"] if image else store.record_file(job["task_id"], capture_path,
        browser["observation"], requirements=browser["requirements"], producer="operator")
    report_path = directory / ("browser-operator-a" + str(task["attempts"]) + ".json")
    relative = str(report_path.relative_to(store.project))
    existing = next((row for row in store.current_evidence(job["task_id"]) if row["source"] == relative
                     and row["kind"] == "browser" and row["producer"] == "operator"), None)
    if existing:
        store.intact([existing])
        return {"screenshot_evidence": image_id, "browser_evidence": existing["id"], "attempt_id": existing["attempt_id"]}
    report = {"actor": job["actor"], "thread_id": job["thread_id"], "job_id": job["id"],
              "url": browser["url"], "observed_at": browser.get("observed_at") or job["completed_at"] or now(),
              "observation": browser["observation"], "screenshot_evidence": image_id,
              "requirements": browser["requirements"], "source_fingerprint": job["source_fingerprint"],
              "producer": "operator"}
    write_json(report_path, report)
    evidence_id = store.record_file(job["task_id"], relative, browser["observation"], ["C1"],
                                   browser["requirements"], "browser", "operator")
    evidence = next(row for row in store.current_evidence(job["task_id"]) if row["id"] == evidence_id)
    return {"screenshot_evidence": image_id, "browser_evidence": evidence_id, "attempt_id": evidence["attempt_id"]}


def register_browser_evidence(store, job_id):
    """Reattach sealed genuine browser observations to a current verify attempt."""
    job = _read(store, job_id)
    require(job["is_current"] and job["status"] == "completed" and job["capability"] == "computer_use",
            "Cần kết quả công cụ đã hoàn tất của phạm vi nghiệm thu hiện tại.")
    return _register_browser(store, job, job["manifest"])


def completed_context(store, task_id):
    """Expose completed current-revision outputs and immutable paths to workers."""
    task = store.task(task_id)
    current = store.task_fingerprint(task)
    return [dict(job, is_source_current=job["source_fingerprint"] == current and job["source_root"] == str(store.task_source(task)),
                 artifact_paths=[str(store.root / item["object_path"]) for item in job["manifest"]["artifacts"]])
            for job in (_read(store, row["id"]) for row in store.db.execute(
                "SELECT id FROM capability_jobs WHERE task_id=? AND revision=? AND status='completed' ORDER BY rowid",
                (task_id, task["revision"])))]


def fulfill(store, job_id, actor, thread_id, manifest):
    """Validate and seal real files. Unknown jobs may reconcile existing outputs only."""
    expire(store)
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        job = _read(store, job_id)
        require(job["is_current"] and job["actor"] == actor and job["thread_id"] == thread_id
                and bool(thread_id), "Kết quả cần đến từ chat đã nhận công việc hiện tại.")
        if job["status"] == "completed":
            candidate = dict(manifest)
            candidate.pop("browser_evidence", None)
            candidate["artifacts"] = [dict(item,
                                      path=str((store.project / item["path"]).resolve().relative_to(store.project)),
                                      object_path="objects/" + item["sha256"])
                                      for item in candidate.get("artifacts", [])]
            if candidate.get("browser") is not None:
                browser = candidate["browser"]
                candidate["browser"] = dict(browser,
                    screenshot=str((store.project / browser["screenshot"]).resolve().relative_to(store.project)),
                    url=browser["url"].strip(), observation=browser["observation"].strip())
            stored = dict(job["manifest"])
            stored.pop("browser_evidence", None)
            require(candidate == stored, "Công việc này đã lưu một kết quả khác.")
            return job
        require(job["status"] in {"bound", "unknown"}, "Cần gắn chat trước khi gửi kết quả công cụ.")
        require(_idle(store, job), "Chờ phiên thực hiện dừng trước khi gửi kết quả công cụ.")
        validated = _validate_manifest(store, job, manifest)
        browser = _browser_payload(store, job, validated)
        if browser is not None:
            validated["browser"] = browser
    # record_file owns its transactions. Do not nest it in the final job commit.
    browser_evidence = _register_browser(store, job, validated)
    if browser_evidence is not None:
        validated["browser_evidence"] = browser_evidence
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        current = _read(store, job_id)
        require(current["is_current"] and current["status"] in {"bound", "unknown"}
                and current["actor"] == actor and current["thread_id"] == thread_id
                and _idle(store, current) and fingerprint(_source(store, job)) == job["source_fingerprint"],
                "Công việc hoặc phiên bản đã thay đổi trước khi lưu kết quả công cụ.")
        store.db.execute("UPDATE capability_jobs SET status='completed',manifest=?,completed_at=?,reason=NULL WHERE id=?",
                         (json.dumps(validated, ensure_ascii=False), now(), job_id))
        _event(store, job, "completed", actor=actor, thread_id=thread_id,
               reconciled=job["status"] == "unknown", artifacts=validated["artifacts"])
        return _read(store, job_id)


def stop(store, job_id, actor, reason):
    """Preserve completed work; an interrupted claimed job has uncertain outcome."""
    reason = _text(reason, "Cần ghi lý do dừng công việc công cụ.")
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        job = _read(store, job_id)
        require(job["actor"] is None or job["actor"] == actor, "Công việc đã được người khác nhận.")
        if job["recorded_status"] in {"completed", "cancelled", "unknown"}:
            return job
        status = "cancelled" if job["recorded_status"] == "queued" else "unknown"
        store.db.execute("UPDATE capability_jobs SET status=?,reason=? WHERE id=?", (status, reason, job_id))
        _event(store, job, "stopped", actor=actor, previous_status=job["recorded_status"], thread_id=job["thread_id"])
        return _read(store, job_id)


def resume_completed(store, task_id=None):
    """Return a capability-blocked task to normal same-revision rework once."""
    resumed = []
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        rows = store.db.execute("SELECT id,revision,attempts,reason FROM tasks WHERE status='blocked'"
            + (" AND id=?" if task_id is not None else ""), (task_id,) if task_id is not None else ()).fetchall()
        for task in rows:
            if not (task["reason"] or "").startswith(BLOCKER_PREFIX):
                continue
            jobs = [_read(store, row["id"]) for row in store.db.execute(
                "SELECT id FROM capability_jobs WHERE task_id=? AND revision=?", (task["id"], task["revision"]))]
            if not jobs or any(job["status"] != "completed" for job in jobs) or not _idle(store, jobs[0]):
                continue
            current = store.db.execute("""SELECT j.id FROM capability_jobs j JOIN team_runs r ON r.id=j.source_run_id
                LEFT JOIN attempts a ON a.id=r.attempt_id WHERE j.task_id=? AND j.revision=? AND j.consumed_at IS NULL
                AND (r.attempt_id IS NULL OR (a.number=? AND a.revision=?))""",
                (task["id"], task["revision"], task["attempts"], task["revision"])).fetchall()
            if not current or any(job["source_fingerprint"] != fingerprint(_source(store, job)) for job in jobs):
                continue
            ids = [row["id"] for row in current]
            from .team_discussions import pending, BLOCKER_PREFIX as discussion_prefix
            discussion = pending(store, task["id"])
            open_question = store.db.execute("""SELECT question FROM company_questions WHERE task_id=? AND revision=?
                AND status='open' ORDER BY rowid LIMIT 1""", (task["id"], task["revision"])).fetchone()
            if open_question:
                from .company_questions import BLOCKER_PREFIX as question_prefix
                store.db.execute("UPDATE tasks SET reason=? WHERE id=?",
                                 (question_prefix + open_question["question"], task["id"]))
            elif discussion:
                store.db.execute("UPDATE tasks SET reason=? WHERE id=?", (discussion_prefix + discussion["title"], task["id"]))
            else:
                store.db.execute("UPDATE tasks SET status='rework',reason=NULL WHERE id=?", (task["id"],))
            store.db.executemany("UPDATE capability_jobs SET consumed_at=? WHERE id=?", [(now(), jid) for jid in ids])
            result = {"task_id": task["id"], "revision": task["revision"], "job_ids": ids}
            if open_question or discussion:
                result["status"] = "blocked"
            _event(store, jobs[0], "resumed", job_ids=ids)
            resumed.append(result)
    return resumed


def snapshot(store):
    """Readable pending jobs and full history; snapshot never retries external work."""
    rows = [_read(store, row["id"]) for row in store.db.execute("SELECT id FROM capability_jobs ORDER BY rowid DESC")]
    return {"pending": [job for job in rows if job["is_current"] and job["status"] in {"queued", "claimed", "bound", "unknown"}],
            "history": rows}
