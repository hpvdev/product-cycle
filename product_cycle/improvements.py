"""Controller-owned experiments for bounded, versioned workflow guidance.

An agent can propose guidance and produce forward-test/review artifacts. Only
this controller executes registered checks or changes installed skills. A
successful command is never sufficient evidence of a behavioral improvement.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import uuid
from pathlib import Path

from .contracts import WorkflowError, require
from .installer import skill_hashes, skill_manifest, save_skill_manifest
from .store import digest, fingerprint, now, runner_lock, write_json


GUIDANCE = "references/learned-guidance.md"
LINK = "\n\nFor recorded workflow guidance, read [references/learned-guidance.md](references/learned-guidance.md).\n"
PHASES = {"propose": "improve_propose", "evaluate": "improve_evaluate", "review": "improve_review"}
SPECIALTIES = {"propose": "skill_engineer", "evaluate": "evaluation_engineer", "review": "improvement_reviewer"}


def _schema(properties):
    return {"type":"object","properties":properties,"required":list(properties),"additionalProperties":False}


_STRING = {"type":"string"}
_STRINGS = {"type":"array","items":_STRING}
_PRESERVATION = {k:{"type":"boolean"} for k in ["permissions_preserved","goals_preserved","acceptance_preserved"]}
CANDIDATE_SCHEMA = _schema({"schema_version":{"type":"integer","enum":[1]},"title":_STRING,"rationale":_STRING,"hypothesis":_STRING,"case_ids":_STRINGS,
    "changes":{"type":"array","items":_schema({"target_id":_STRING,"before_sha256":_STRING,"guidance":_STRING})},"evidence":_STRINGS})
FORWARD_SCHEMA = _schema({"candidate_hash":_STRING,"context_hash":_STRING,"decision":{"type":"string","enum":["pass","fail"]},**_PRESERVATION,
    "cases":{"type":"array","items":_schema({"case_id":_STRING,"input_artifact":_STRING,"input_sha256":_STRING,"before_artifacts":_STRINGS,"after_artifacts":_STRINGS,"improved":{"type":"boolean"},"regressed":{"type":"boolean"},"reason":_STRING})}})
REVIEW_SCHEMA = _schema({"candidate_hash":_STRING,"context_hash":_STRING,"decision":{"type":"string","enum":["approve","reject"]},"reason":_STRING,"findings":_STRINGS,"artifacts":_STRINGS,
    **_PRESERVATION,"evidence_verified":{"type":"boolean"}})
PROPOSE_SCHEMA = _schema({"candidate":{"anyOf":[CANDIDATE_SCHEMA,{"type":"null"}]},"reason":_STRING})
EVALUATE_SCHEMA = _schema({"evaluation":{"anyOf":[FORWARD_SCHEMA,{"type":"null"}]},"reason":_STRING})
IMPROVEMENT_REVIEW_SCHEMA = _schema({"review":{"anyOf":[REVIEW_SCHEMA,{"type":"null"}]},"reason":_STRING})


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode()


def _guidance(text):
    require(isinstance(text, str) and 0 < len(text.strip()) <= 12000, "Hãy viết hướng dẫn ngắn gọn, có nội dung rõ ràng.")
    normalized = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    # This conservative boundary complements independent semantic review. It
    # is not a claim that a regex can recognize every policy-changing sentence.
    forbidden = r"\b(permission|authorize\w*|approval|policy|policies|gate\w*|acceptance|criteria|goals?|bypass\w*|ignore|override\w*|disable\w*|sandbox|credential\w*|secret\w*|human|owner|quyen|phe duyet|nghiem thu|muc tieu|bo qua|vo hieu|chu san pham)\b"
    require(not re.search(forbidden, normalized), "Cải tiến này không được thay quyền thực hiện, mục tiêu hay điều kiện nghiệm thu.")
    require(not re.search(r"(?m)^\s*```|<script|app://|file://|\$\(|https?://", text), "Hướng dẫn cải tiến không được chứa mã thực thi hoặc liên kết bên ngoài.")


def default_trusted_targets(store):
    """Only installer-known originals; custom skill folders are never adopted."""
    destination = store.project / ".agents" / "skills"
    _, manifest = skill_manifest(destination)
    result = {}
    for name, known in manifest["skills"].items():
        folder = destination / name
        if name.startswith("product-cycle") and folder.is_dir() and skill_hashes(folder) == known:
            result[name] = {"path": str(folder.relative_to(store.project)), "known_hashes": known,
                            "guidance_sha256":known.get(GUIDANCE,_hash(b"")),"checks": list(default_trusted_checks())}
    return result


_FRONTMATTER_CHECK = """import pathlib,sys
p=pathlib.Path(sys.argv[1])
for folder in p.iterdir():
 if not folder.is_dir(): continue
 text=(folder/'SKILL.md').read_text()
 assert text.startswith('---\\n'), 'Missing skill frontmatter'
 end=text.find('\\n---',4); assert end>0, 'Unclosed skill frontmatter'
 header=text[4:end]
 assert any(x.startswith('name:') and x[5:].strip() for x in header.splitlines())
 assert any(x.startswith('description:') and x[12:].strip() for x in header.splitlines())
 assert not any(x.is_symlink() for x in folder.rglob('*'))
"""


def default_trusted_checks():
    """Fixed controller argv. Candidates never supply shell commands."""
    repository = Path(__file__).resolve().parent.parent
    checks = {
        "skill_frontmatter": {"argv": [sys.executable, "-c", _FRONTMATTER_CHECK, "{snapshot}"], "timeout": 30},
    }
    if (repository / "tests" / "test_team.py").is_file():
        checks["targeted_controller"] = {"argv": [sys.executable, "-m", "unittest", "discover", "-s", str(repository / "tests"), "-p", "test_team.py"], "cwd": str(repository), "timeout":120}
    return checks


class ImprovementStore:
    def __init__(self, store, targets=None, checks=None):
        self.store, self.db = store, store.db
        self.targets = default_trusted_targets(store) if targets is None else targets
        self.checks = default_trusted_checks() if checks is None else checks
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS improvement_candidates(
            id TEXT PRIMARY KEY, version INTEGER NOT NULL UNIQUE, status TEXT NOT NULL,
            bundle TEXT NOT NULL, candidate_hash TEXT NOT NULL, author_run_id TEXT NOT NULL,
            evaluation TEXT, review TEXT, backup TEXT, monitor TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS improvement_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,candidate_id TEXT NOT NULL,
            kind TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS improvement_sessions(
            thread_id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL, phase TEXT NOT NULL);
          CREATE UNIQUE INDEX IF NOT EXISTS improvement_author_once ON improvement_candidates(author_run_id);
        """)
        self.root = store.root / "improvements"
        self.root.mkdir(exist_ok=True)
        from .learning_trials import migrate
        migrate(self.db)

    def _row(self, cid):
        row = self.db.execute("SELECT * FROM improvement_candidates WHERE id=?", (cid,)).fetchone()
        require(row is not None, "Không tìm thấy bản đề xuất cải tiến.")
        value = dict(row)
        for key in ["bundle", "evaluation", "review", "monitor"]:
            value[key] = json.loads(value[key]) if value[key] else None
        return value

    def _update(self, cid, status, kind, data=None, **fields):
        fields.update(status=status, updated_at=now())
        for key in ["evaluation", "review", "monitor"]:
            if key in fields:
                fields[key] = json.dumps(fields[key], ensure_ascii=False)
        with self.db:
            self.db.execute("UPDATE improvement_candidates SET " + ",".join(k + "=?" for k in fields) + " WHERE id=?", (*fields.values(), cid))
            self.db.execute("INSERT INTO improvement_events(candidate_id,kind,data,created_at) VALUES(?,?,?,?)", (cid, kind, json.dumps(data or {}, ensure_ascii=False), now()))

    def _run(self, rid, phase, different=()):
        from .team import employee_role
        run = self.db.execute("SELECT * FROM team_runs WHERE id=?", (rid,)).fetchone()
        require(run and run["phase"] == PHASES[phase] and run["thread_id"] and run["turn_id"] and not run["source_writer"], "Cần một phiên cải tiến riêng đã được ghi nhận đúng nhiệm vụ.")
        require(run["status"] in {"running", "completed"}, "Phiên cải tiến chưa có trạng thái xác định; hãy kiểm tra trước khi tiếp tục.")
        require(employee_role(self.store,run["agent_id"])["base_role"] == SPECIALTIES[phase], "Nhiệm vụ cần đúng chuyên viên cải tiến được phân công.")
        for prior in different:
            other = self.db.execute("SELECT * FROM team_runs WHERE id=?", (prior,)).fetchone()
            require(other and run["thread_id"] != other["thread_id"] and run["agent_id"] != other["agent_id"], "Người đề xuất, người thử nghiệm và người review cần là các phiên độc lập.")
        require(not self.db.execute("SELECT 1 FROM improvement_sessions WHERE thread_id=?", (run["thread_id"],)).fetchone(), "Hãy dùng phiên mới cho nhiệm vụ cải tiến này.")
        return dict(run)

    def _session(self, run, cid, phase):
        with self.db:
            self.db.execute("INSERT INTO improvement_sessions VALUES(?,?,?)", (run["thread_id"], cid, phase))

    def _folder(self, spec):
        rel = Path(spec["path"])
        require(not rel.is_absolute() and len(rel.parts) == 3 and rel.parts[:2] == (".agents", "skills") and rel.name.startswith("product-cycle"), "Chỉ cập nhật hướng dẫn bổ sung trong skill workflow đã cài.")
        folder = self.store.project / rel
        require(not any((self.store.project / Path(*rel.parts[:n])).is_symlink() for n in range(1, len(rel.parts)+1)), "Thư mục hướng dẫn cần nằm trực tiếp trong dự án.")
        require(skill_hashes(folder) == spec["known_hashes"], "Skill đã có chỉnh sửa riêng; hãy giữ bản hiện tại và kiểm tra thay đổi.")
        return folder

    def _evidence(self, paths):
        require(isinstance(paths, list) and paths and all(isinstance(p, str) for p in paths), "Cần có tệp bằng chứng thực cho đề xuất này.")
        rows = []
        for name in paths:
            relative=Path(name);path = self.store.project / relative
            require(not relative.is_absolute() and relative.parts and relative.parts[0]==".product-cycle" and ".." not in relative.parts and
                    not any(part.startswith('.env') for part in relative.parts) and path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(self.store.project),
                    "Hãy chọn tệp bằng chứng workflow đã lưu trong thư mục sản phẩm; không dùng tệp riêng tư hay tệp nguồn bất kỳ.")
            data = path.read_bytes();sha = _hash(data);sealed = self.store.root / "objects" / sha
            if not sealed.exists():
                sealed.write_bytes(data)
            rows.append({"path": name, "sha256": sha, "object_path": str(sealed)})
        return rows

    def propose(self, bundle, author_run_id):
        require(isinstance(bundle, dict) and set(bundle) == {"schema_version", "title", "rationale", "hypothesis", "case_ids", "changes", "evidence"} and bundle["schema_version"] == 1, "Đề xuất chưa đúng cấu trúc được hỗ trợ.")
        require(all(isinstance(bundle[k], str) and bundle[k].strip() for k in ["title", "rationale", "hypothesis"]), "Hãy nêu vấn đề cụ thể và kết quả mong đợi của cải tiến.")
        require(isinstance(bundle["case_ids"], list) and bundle["case_ids"] and all(isinstance(x, str) and x.strip() for x in bundle["case_ids"]) and len(set(bundle["case_ids"])) == len(bundle["case_ids"]), "Hãy chọn các tình huống thử nghiệm riêng, không trùng nhau.")
        prior=self.db.execute("SELECT id FROM improvement_candidates WHERE author_run_id=?",(author_run_id,)).fetchone()
        if prior:
            row=self._row(prior[0]);self._intact(row)
            require(bundle=={key:row["bundle"][key] for key in CANDIDATE_SCHEMA["required"]},"Phiên đề xuất này đã có nội dung khác; không được ghi đè lịch sử.")
            return row
        changes = bundle["changes"]
        require(isinstance(changes, list) and 0 < len(changes) <= 3 and len({c.get("target_id") for c in changes}) == len(changes), "Mỗi đề xuất chỉ nên thay tối đa ba hướng dẫn riêng.")
        author = self._run(author_run_id, "propose")
        cid = "improvement-" + uuid.uuid4().hex;directory = self.root / cid
        before, after = directory / "before", directory / "after"
        prepared = []
        for change in changes:
            require(set(change) == {"target_id", "before_sha256", "guidance"} and change["target_id"] in self.targets, "Hãy chọn đúng hướng dẫn đã được bộ điều phối cho phép.")
            _guidance(change["guidance"])
            spec = self.targets[change["target_id"]];folder = self._folder(spec)
            require(change["target_id"] == folder.name, "Hãy dùng đúng mã skill đã được đăng ký.")
            require(set(spec["checks"]) <= set(self.checks) and spec["checks"], "Chưa có phép kiểm tra được cấu hình cho hướng dẫn này.")
            old = (folder / GUIDANCE).read_bytes() if (folder / GUIDANCE).exists() else b""
            require(change["before_sha256"] == _hash(old) and old != change["guidance"].encode(), "Bản hướng dẫn gốc đã thay đổi hoặc đề xuất chưa có thay đổi; hãy tạo lại đề xuất.")
            prepared.append((change, spec, folder))
        sealed_evidence = self._evidence(bundle["evidence"])
        require(set(bundle["case_ids"]) <= {item["path"] for item in sealed_evidence}, "Mỗi tình huống cần trỏ tới tệp đầu vào thực đã đăng ký trong bằng chứng.")
        for change, spec, folder in prepared:
            shutil.copytree(folder, before / folder.name);shutil.copytree(folder, after / folder.name)
            tip = after / folder.name / GUIDANCE;tip.parent.mkdir(exist_ok=True);tip.write_text(change["guidance"])
            entry = after / folder.name / "SKILL.md"
            if "[references/learned-guidance.md](references/learned-guidance.md)" not in entry.read_text():
                entry.write_text(entry.read_text() + LINK)
        payload = dict(bundle, evidence_records=sealed_evidence, targets={c["target_id"]:spec for c,spec,_ in prepared},
                       before={p.name:skill_hashes(p) for p in before.iterdir()}, after={p.name:skill_hashes(p) for p in after.iterdir()})
        if self.store.config.get("agent_workflow_version"):
            from .learning_trials import select_holdouts
            remaining = max(0, self.store.config.get("learning_budget", {}).get("max_cases", 4) - len(bundle["case_ids"]))
            payload["held_out_sources"] = select_holdouts(self, bundle["case_ids"], min(2, remaining)) if remaining else []
        candidate_hash = _hash(_encoded(payload));write_json(directory / "candidate.json", payload)
        with self.db:
            version = self.db.execute("SELECT COALESCE(MAX(version),0)+1 FROM improvement_candidates").fetchone()[0]
            self.db.execute("INSERT INTO improvement_candidates(id,version,status,bundle,candidate_hash,author_run_id,created_at,updated_at) VALUES(?,?,'proposed',?,?,?,?,?)", (cid, version, json.dumps(payload, ensure_ascii=False), candidate_hash, author_run_id, now(), now()))
        self._session(author, cid, "propose")
        self._update(cid, "proposed", "candidate.proposed", {"candidate_hash":candidate_hash})
        return self._row(cid)

    def _intact(self, row):
        require(_hash(_encoded(row["bundle"])) == row["candidate_hash"], "Thông tin đề xuất đã thay đổi; hãy kiểm chứng lại.")
        for variant in ["before", "after"]:
            for name, hashes in row["bundle"][variant].items():
                require(skill_hashes(self.root / row["id"] / variant / name) == hashes, "Bản hướng dẫn dùng để thử nghiệm đã thay đổi; hãy kiểm chứng lại.")
        for item in row["bundle"]["evidence_records"] + row["bundle"].get("held_out_sources", []):
            require(digest(item["object_path"]) == item["sha256"], "Bằng chứng đã lưu có thay đổi; hãy kiểm chứng lại.")
        if row["evaluation"]:
            for check in row["evaluation"]["checks"]:
                require(digest(check["log"])==check["sha256"], "Nhật ký kiểm tra đã thay đổi; cần kiểm chứng lại.")
            for item in (row["evaluation"].get("forward_test") or {}).get("evidence_records",[]):
                require(digest(item["object_path"])==item["sha256"], "Bằng chứng thử nghiệm đã thay đổi; cần kiểm chứng lại.")
        if row["review"]:
            for item in row["review"]["evidence_records"]:
                require(digest(item["object_path"])==item["sha256"], "Bằng chứng review đã thay đổi; cần kiểm chứng lại.")

    def _checks(self, row, variants):
        self._intact(row)
        ids = sorted({x for spec in row["bundle"]["targets"].values() for x in spec["checks"]})
        results = []
        for variant in variants:
            snapshot = self.root / row["id"] / variant
            for check_id in ids:
                require(check_id in self.checks, "Phép kiểm tra đã đăng ký chưa sẵn sàng.")
                check = self.checks[check_id]
                argv = [str(snapshot) if arg == "{snapshot}" else arg for arg in check["argv"]]
                require(argv and all(isinstance(arg, str) for arg in argv), "Cấu hình phép kiểm tra chưa hợp lệ.")
                try:
                    result = subprocess.run(argv, cwd=check.get("cwd", snapshot), capture_output=True, timeout=check.get("timeout", 120), shell=False)
                    code, log = result.returncode, result.stdout + result.stderr
                except (OSError, subprocess.TimeoutExpired) as exc:
                    code, log = -1, str(exc).encode()
                path = self.root / row["id"] / ("check-" + uuid.uuid4().hex + ".log");path.write_bytes(log)
                sha=digest(path);sealed=self.store.root/"objects"/sha
                if not sealed.exists():sealed.write_bytes(log)
                results.append({"check_id":check_id,"variant":variant,"argv":argv,"exit_code":code,"log":str(path),"object_path":str(sealed),"sha256":sha,"observed_at":now()})
        # A trusted command also may not rewrite the version under evaluation.
        self._intact(row)
        return results

    def evaluate(self, cid):
        row = self._row(cid)
        if row["status"]=="evaluating" and row["evaluation"] is not None:
            self._intact(row);return row
        require(row["status"] == "proposed" or row["status"]=="evaluating" and row["evaluation"] is None, "Đề xuất chưa sẵn sàng để thử nghiệm.")
        self._update(cid, "evaluating", "evaluation.started")
        checks = self._checks(row, ["before", "after"])
        value = {"checks":checks,"checks_passed":all(x["exit_code"]==0 for x in checks),"forward_test":None}
        self._update(cid, "evaluating" if value["checks_passed"] else "rejected", "evaluation.checks", value, evaluation=value)
        return self._row(cid)

    def evaluation_context(self, cid):
        row=self._row(cid);self._intact(row)
        raw_cases=[item for item in row["bundle"]["evidence_records"] if item["path"] in row["bundle"]["case_ids"]]
        raw_cases += row["bundle"].get("held_out_sources", [])
        packet={"candidate_id":cid,"candidate_hash":row["candidate_hash"],"bundle":row["bundle"],"before_directory":str(self.root/cid/"before"),"after_directory":str(self.root/cid/"after"),"checks":row["evaluation"],"case_ids":row["bundle"]["case_ids"],"raw_case_sources":raw_cases,"instruction":"Forward-test each exact sealed raw input separately against before and after guidance. Copy the original bytes to input_artifact and echo input_sha256; both variants must use that same input. Record actual artifacts and regressions; check success alone is not improvement."}
        packet["case_ids"] = [item["path"] for item in raw_cases]
        return dict(packet,context_hash=_hash(_encoded(packet)))

    def record_evaluation(self, cid, report, evaluator_run_id):
        row=self._row(cid)
        require(isinstance(report,dict) and set(report)==set(FORWARD_SCHEMA["required"]),"Báo cáo thử nghiệm chưa đúng cấu trúc được hỗ trợ.")
        prior=(row["evaluation"] or {}).get("forward_test")
        if prior and prior["run_id"]==evaluator_run_id:
            self._intact(row);require(report=={key:prior[key] for key in FORWARD_SCHEMA["required"]},"Kết quả thử nghiệm đã có nội dung khác; hãy giữ lịch sử hiện hành.");return row
        require(row["status"]=="evaluating" and row["evaluation"] and row["evaluation"]["checks_passed"], "Các phép kiểm tra được cấu hình chưa đạt.")
        run=self._run(evaluator_run_id,"evaluate",[row["author_run_id"]]);packet=self.evaluation_context(cid)
        require(report.get("candidate_hash")==row["candidate_hash"] and report.get("context_hash")==packet["context_hash"], "Báo cáo thử nghiệm chưa khớp đúng phiên bản đề xuất.")
        cases=report.get("cases");require(isinstance(cases,list) and all(isinstance(x,dict) for x in cases) and {x.get("case_id") for x in cases}==set(packet["case_ids"]) and len(cases)==len(packet["case_ids"]), "Hãy thử đủ các tình huống đã chọn, mỗi tình huống một lần.")
        sealed=[]
        for case in cases:
            require(isinstance(case.get("improved"),bool) and isinstance(case.get("regressed"),bool) and isinstance(case.get("reason"),str) and case["reason"].strip(), "Mỗi tình huống cần đánh giá cụ thể kết quả trước và sau.")
            source=next(item for item in packet["raw_case_sources"] if item["path"]==case["case_id"])
            inputs=self._evidence([case.get("input_artifact")])
            require(case.get("input_sha256")==source["sha256"] and inputs[0]["sha256"]==source["sha256"], "Đầu vào thử nghiệm phải khớp chính xác bản đã lưu cho cả hai phương án.")
            sealed.extend(inputs);sealed.extend(self._evidence(case.get("before_artifacts")));sealed.extend(self._evidence(case.get("after_artifacts")))
        require(report.get("decision") in {"pass","fail"} and all(isinstance(report.get(k),bool) for k in _PRESERVATION), "Báo cáo cần đánh giá rõ việc giữ nguyên phạm vi và quyền thực hiện.")
        passed=report["decision"]=="pass" and all(report[k] for k in _PRESERVATION) and any(c["improved"] for c in cases) and not any(c["regressed"] for c in cases)
        value=dict(row["evaluation"],forward_test=dict(report,run_id=evaluator_run_id,thread_id=run["thread_id"],evidence_records=sealed))
        self._session(run,cid,"evaluate");self._update(cid,"evaluated" if passed else "rejected","evaluation.forward",evaluation=value)
        return self._row(cid)

    def review_context(self,cid):
        row=self._row(cid);self._intact(row);require(row["status"]=="evaluated","Đề xuất cần có kết quả thử nghiệm đã kiểm chứng trước khi review.")
        packet={"candidate_id":cid,"candidate_hash":row["candidate_hash"],"bundle":row["bundle"],"evaluation":row["evaluation"],"instruction":"Fresh independent review: inspect original/candidate guidance, exact raw case artifacts and actual check logs. Reject permission, goal, acceptance changes or unsupported benefit. Do not accept author/evaluator opinion as evidence."}
        return dict(packet,context_hash=_hash(_encoded(packet)))

    def record_review(self,cid,report,reviewer_run_id):
        row=self._row(cid)
        require(isinstance(report,dict) and set(report)==set(REVIEW_SCHEMA["required"]),"Báo cáo review chưa đúng cấu trúc được hỗ trợ.")
        if row["review"] and row["review"]["run_id"]==reviewer_run_id:
            self._intact(row);require(report=={key:row["review"][key] for key in REVIEW_SCHEMA["required"]},"Kết quả review đã có nội dung khác; hãy giữ lịch sử hiện hành.");return row
        packet=self.review_context(cid);evaluation=row["evaluation"]["forward_test"]
        run=self._run(reviewer_run_id,"review",[row["author_run_id"],evaluation["run_id"]])
        require(report.get("candidate_hash")==row["candidate_hash"] and report.get("context_hash")==packet["context_hash"] and report.get("decision") in {"approve","reject"}, "Báo cáo review chưa khớp đúng phiên bản thử nghiệm.")
        require(isinstance(report.get("reason"),str) and report["reason"].strip() and isinstance(report.get("findings"),list) and all(isinstance(x,str) for x in report["findings"]), "Review cần lý do và nhận xét cụ thể.")
        require(all(isinstance(report.get(k),bool) for k in [*_PRESERVATION,"evidence_verified"]), "Review cần đánh giá rõ phạm vi và độ tin cậy của bằng chứng.")
        approved=report["decision"]=="approve" and all(report[k] for k in [*_PRESERVATION,"evidence_verified"])
        artifacts=self._evidence(report.get("artifacts"));value=dict(report,run_id=reviewer_run_id,thread_id=run["thread_id"],evidence_records=artifacts,accepted=approved,effective_decision="approve" if approved else "reject")
        self._session(run,cid,"review");self._update(cid,"reviewed" if approved else "rejected","review.recorded",review=value)
        return self._row(cid)

    def _stable(self):
        require(not self.db.execute("SELECT 1 FROM tasks WHERE status IN ('running','reviewing','awaiting_approval') LIMIT 1").fetchone(), "Hãy chờ các phiên và quyết định nghiệm thu hiện hành kết thúc trước khi cập nhật.")
        require(not self.db.execute("SELECT 1 FROM attempts WHERE status IN ('running','queued') LIMIT 1").fetchone(), "Một lượt thực hiện vẫn đang chạy; hãy chờ lượt đó kết thúc.")
        require(not self.db.execute("SELECT 1 FROM team_runs WHERE status IN ('preparing','dispatching','running','checking','unknown','backoff') LIMIT 1").fetchone(), "Một phiên vẫn chạy hoặc chưa rõ kết quả; chưa thể cập nhật hướng dẫn.")

    def apply(self,cid,*,automatic=True,reason=None):
        with runner_lock(self.store):
            row=self._row(cid);require(row["status"]=="reviewed","Chỉ áp dụng cải tiến đã được review độc lập và chấp nhận.");self._stable();self._intact(row)
            if automatic:
                require(all(t["status"] in {"done","superseded"} for t in self.store.tasks()), "Chỉ tự áp dụng cải tiến sau khi chu trình sản phẩm đã hoàn tất.")
            else:
                require(isinstance(reason,str) and reason.strip(), "Cần ghi rõ quyết định cập nhật hướng dẫn tại mốc ổn định này.")
            destination=self.store.project/".agents"/"skills";manifest_path,manifest=skill_manifest(destination)
            for name,spec in row["bundle"]["targets"].items():
                folder=self._folder(spec);require(skill_hashes(folder)==manifest["skills"].get(name),"Skill đã được tùy chỉnh; hãy giữ bản hiện tại.")
            backup=self.store.project/".product-cycle"/"skill-backups"/cid
            require(not any(p.is_symlink() for p in [self.store.project/".product-cycle",backup.parent]),"Thư mục sao lưu cần nằm trực tiếp trong dự án.")
            backup.mkdir(parents=True);shutil.copy2(manifest_path,backup/"manifest.json")
            before_fingerprint=fingerprint(self.store.project)
            self._update(cid,"applying","apply.intent",backup=str(backup))
            replaced=[]
            try:
                for name in row["bundle"]["targets"]:
                    target=destination/name;staging=backup/("new-"+name)
                    shutil.copytree(self.root/cid/"after"/name,staging)
                    os.replace(target,backup/name);replaced.append(name);os.replace(staging,target)
                    manifest["skills"][name]=row["bundle"]["after"][name]
                save_skill_manifest(manifest_path,manifest)
                self.store.bootstrap()
            except BaseException:
                for name in reversed(replaced):
                    if (destination/name).exists():shutil.rmtree(destination/name)
                    os.replace(backup/name,destination/name)
                shutil.copy2(backup/"manifest.json",manifest_path)
                self._update(cid,"apply_attention","apply.failed")
                raise
            self._update(cid,"applied","apply.completed",{"before_fingerprint":before_fingerprint,"after_fingerprint":fingerprint(self.store.project),"backup":str(backup)})
            from .knowledge import publish
            publish(self, self._row(cid))
            self.store.event(None,"workflow.guidance.updated",{"candidate_id":cid,"version":row["version"],"automatic":automatic,"reason":reason,"note":"Phiên bản hướng dẫn và nền tảng đã được ghi nhận lại. Bằng chứng sản phẩm đã nghiệm thu giữ nguyên fingerprint cũ; phiên tiếp theo cần kiểm tra bản source hiện hành."})
            return self._row(cid)

    def rollback(self,cid):
        with runner_lock(self.store):
            row=self._row(cid);require(row["status"] in {"applied","monitoring","rollback_pending"},"Phiên bản này chưa thể tự động khôi phục.");self._stable()
            destination=self.store.project/".agents"/"skills";manifest_path,manifest=skill_manifest(destination)
            for name in row["bundle"]["targets"]:
                require(skill_hashes(destination/name)==row["bundle"]["after"][name],"Hướng dẫn đã có chỉnh sửa mới; hãy giữ thay đổi đó thay vì ghi đè.")
            backup=Path(row["backup"])
            for name in row["bundle"]["targets"]:
                require(skill_hashes(backup/name)==row["bundle"]["before"][name],"Bản sao lưu đã thay đổi; hãy kiểm tra trước khi khôi phục.")
            self._update(cid,"rolling_back","rollback.intent")
            prior_manifest=json.loads(json.dumps(manifest));replaced=[]
            try:
                for name in row["bundle"]["targets"]:
                    removed=backup/("rolled-back-"+name);os.replace(destination/name,removed);replaced.append(name);shutil.copytree(backup/name,destination/name)
                    manifest["skills"][name]=row["bundle"]["before"][name]
                save_skill_manifest(manifest_path,manifest)
                self.store.bootstrap()
            except BaseException:
                for name in reversed(replaced):
                    if (destination/name).exists():shutil.rmtree(destination/name)
                    os.replace(backup/("rolled-back-"+name),destination/name)
                save_skill_manifest(manifest_path,prior_manifest)
                self._update(cid,"rollback_attention","rollback.failed")
                raise
            self._update(cid,"rolled_back","rollback.completed")
            from .knowledge import unpublish
            unpublish(self, row)
            self.store.event(None,"workflow.guidance.rolled_back",{"candidate_id":cid,"version":row["version"],"note":"Đã khôi phục hướng dẫn và ghi nhận lại nền tảng; không sửa bằng chứng sản phẩm cũ."})
            return self._row(cid)

    def monitor(self,cid):
        row=self._row(cid);require(row["status"] in {"applied","monitoring"},"Chỉ theo dõi cải tiến đã được áp dụng.")
        with runner_lock(self.store):
            self._stable()
            for name in row["bundle"]["targets"]:
                require(skill_hashes(self.store.project/".agents"/"skills"/name)==row["bundle"]["after"][name],"Hướng dẫn hiện hành đã thay đổi sau khi áp dụng; hãy kiểm tra lại.")
            checks=self._checks(row,["after"]);value={"checks":checks,"passed":all(x["exit_code"]==0 for x in checks),"observed_at":now(),"limitation":"Theo dõi cấu trúc và bộ điều phối chưa chứng minh chất lượng sản phẩm hay hiệu quả dài hạn."}
            self._update(cid,"monitoring" if value["passed"] else "rollback_pending","monitor.recorded",monitor=value)
        if not value["passed"]:return self.rollback(cid)
        return self._row(cid)

    def snapshot(self):
        rows=[self._row(r[0]) for r in self.db.execute("SELECT id FROM improvement_candidates ORDER BY version DESC")]
        for row in rows:
            current=all((self.store.project/".agents"/"skills"/name).is_dir() and skill_hashes(self.store.project/".agents"/"skills"/name)==hashes for name,hashes in row["bundle"]["after"].items())
            before_versions={}
            for name,hashes in row["bundle"]["before"].items():
                prior=[old["version"] for old in rows if old["version"]<row["version"] and old["bundle"]["after"].get(name)==hashes and self.db.execute("SELECT 1 FROM improvement_events WHERE candidate_id=? AND kind='apply.completed'",(old["id"],)).fetchone()]
                before_versions[name]=max(prior) if prior else "Bản gốc đã cài"
            row.update(title=row["bundle"]["title"],summary=row["bundle"]["rationale"],hypothesis=row["bundle"]["hypothesis"],candidate_version=row["version"],after_version=row["version"],before_version=before_versions,
                       adopted_version=row["version"] if current and row["status"] in {"applied","monitoring","rollback_pending"} else None)
            before_text={name:(self.root/row["id"]/"before"/name/GUIDANCE).read_text() if (self.root/row["id"]/"before"/name/GUIDANCE).exists() else "" for name in row["bundle"]["targets"]}
            after_text={change["target_id"]:change["guidance"] for change in row["bundle"]["changes"]}
            row["before"]={"summary":"Hướng dẫn trước cải tiến","text":"\n\n".join(name+"\n"+(text or "Chưa có hướng dẫn bổ sung.") for name,text in before_text.items())}
            row["after"]={"summary":"Hướng dẫn được đề xuất","text":"\n\n".join(name+"\n"+text for name,text in after_text.items())}
            evidence=list(row["bundle"]["evidence_records"])
            if row["evaluation"]:evidence.extend((row["evaluation"].get("forward_test") or {}).get("evidence_records",[]))
            if row["review"]:evidence.extend(row["review"]["evidence_records"])
            row["evidence"]=[dict(item,title=Path(item["path"]).name) for item in evidence]
            if row["evaluation"]:
                row["evidence"].extend({"title":"Kiểm tra hướng dẫn "+("trước cải tiến" if check["variant"]=="before" else "sau cải tiến"),"sha256":check["sha256"],"object_path":check["object_path"]} for check in row["evaluation"]["checks"])
        events=[dict(r) for r in self.db.execute("SELECT * FROM improvement_events ORDER BY id")]
        for event in events:event["data"]=json.loads(event["data"])
        return {"candidates":rows,"events":events,"guidance_scope":"Chỉ cập nhật hướng dẫn bổ sung trong skill đã cài; không thay quyền điều phối, mục tiêu hoặc điều kiện nghiệm thu."}

    def evidence_path(self,cid,sha256):
        """Safe reader lookup; never accept arbitrary paths from dashboard input."""
        row=next((row for row in self.snapshot()["candidates"] if row["id"]==cid),None)
        require(row is not None,"Không tìm thấy bản đề xuất cải tiến.")
        item=next((item for item in row["evidence"] if item["sha256"]==sha256),None)
        require(item is not None,"Không tìm thấy bằng chứng đã đăng ký cho cải tiến này.")
        path=Path(item["object_path"])
        require(path.parent==self.store.root/"objects" and not path.is_symlink() and digest(path)==sha256,"Bằng chứng không còn khớp bản đã ghi nhận; hãy kiểm tra lại.")
        return path
