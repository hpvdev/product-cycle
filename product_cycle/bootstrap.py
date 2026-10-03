"""Deterministic repository preparation before any AI product work."""

import hashlib
import shutil
import subprocess
from pathlib import Path

from .contracts import RESOURCES, WorkflowError, require
from .installer import install_skills

RULES_FILE = "PRODUCT_CYCLE_RULES.md"
AGENT_LINK = "Read PRODUCT_CYCLE_RULES.md before starting a Product Cycle task."
IGNORE_RULES = """# Product Cycle: local artifacts and private environment
.product-cycle/
.env
.env.*
!.env.example
node_modules/
.venv/
__pycache__/
*.py[cod]
.DS_Store
"""


def git(project, *args):
    try:
        return subprocess.run(["git", *args], cwd=project, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkflowError("Không chạy được Git. Kiểm tra cài đặt Git và thư mục dự án.") from exc


def repository_state(project):
    project = Path(project).resolve()
    root = git(project, "rev-parse", "--show-toplevel")
    if root.returncode:
        return {"ready": False, "root": None, "branch": None, "head": None, "changed_files": None}
    head = git(project, "rev-parse", "--verify", "HEAD")
    branch = git(project, "symbolic-ref", "--quiet", "--short", "HEAD")
    status = git(project, "status", "--porcelain=v1", "--untracked-files=normal")
    return {"ready": Path(root.stdout.strip()).resolve() == project,
            "root": root.stdout.strip(), "branch": branch.stdout.strip() or None,
            "head": head.stdout.strip() if head.returncode == 0 else None,
            "changed_files": len(status.stdout.splitlines()) if status.returncode == 0 else None}


def tracked_environment_files(project):
    result = git(project, "ls-files", "-z")
    require(result.returncode == 0, "Không đọc được danh sách file Git trong dự án.")
    return [name for name in result.stdout.split("\0") if name and
            Path(name).name.startswith(".env") and Path(name).name != ".env.example"]


def prepare_project(project):
    project = Path(project).expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    require(shutil.which("git"), "Cần cài Git trước khi khởi tạo dự án.")
    for name in ["AGENTS.md", RULES_FILE, ".gitignore"]:
        path = project / name
        require(not path.is_symlink() and (not path.exists() or path.is_file()),
                "File hướng dẫn và cấu hình Git cần nằm trực tiếp trong dự án: " + name)
    state = repository_state(project)
    initialized = not state["ready"]
    if initialized:
        if state["root"]:
            tracked = git(project, "ls-files", "--", ".")
            require(tracked.returncode == 0 and not tracked.stdout.strip(),
                    "Thư mục này thuộc mã nguồn của repository cha. Chọn thư mục gốc repository để giữ nguyên lịch sử.")
        result = git(project, "init", "--initial-branch=main")
        require(result.returncode == 0, "Chưa khởi tạo được Git cho dự án.")
    require(not tracked_environment_files(project),
            "Git đang theo dõi file môi trường riêng tư. Loại file đó khỏi danh sách theo dõi trước khi tiếp tục; không xóa bản local.")
    changes = []

    def write(name, text):
        path = project / name
        existed = path.exists()
        if not existed or path.read_text() != text:
            path.write_text(text)
            changes.append({"path": name, "action": "updated" if existed else "created"})

    ignore = project / ".gitignore"
    existing = ignore.read_text() if ignore.exists() else ""
    if IGNORE_RULES not in existing:
        write(".gitignore", existing + ("\n" if existing and not existing.endswith("\n") else "") + "\n" + IGNORE_RULES)
    rules = project / RULES_FILE
    if not rules.exists():
        write(RULES_FILE, (RESOURCES / "common-rules.md").read_text())
    agents = project / "AGENTS.md"
    existing = agents.read_text() if agents.exists() else ""
    if AGENT_LINK not in existing:
        write("AGENTS.md", existing + ("\n" if existing and not existing.endswith("\n") else "") +
              "\n## Product Cycle\n\n" + AGENT_LINK + "\nExisting repository instructions and explicit user requests take precedence.\n")
    skills = install_skills(project, preserve_existing=True)
    protected = ["AGENTS.md", RULES_FILE] + [str(path.relative_to(project))
                 for path in sorted((project / ".agents" / "skills").glob("product-cycle*/**/*")) if path.is_file()]
    return {"git_initialized": initialized, "repository": repository_state(project),
            "changes": changes, "skills": skills,
            "protected_files": {name: hashlib.sha256((project / name).read_bytes()).hexdigest() for name in protected}}


def foundation_status(project, report=None):
    if not report:
        return {"status": "untracked", "checks": [], "repository": None,
                "note": "Chu trình này chưa ghi nhận bước chuẩn bị dự án. Dùng bootstrap để bổ sung trước khi chạy tiếp."}
    try:
        state = repository_state(project)
        tracked = tracked_environment_files(project) if state["ready"] else []
        ignored = git(project, "check-ignore", "--no-index", ".product-cycle/probe", ".env", ".env.production")
        private_ready = not tracked and len(ignored.stdout.splitlines()) == 3
    except WorkflowError:
        state = {"ready": False, "root": None, "branch": None, "head": None, "changed_files": None}
        private_ready = False
    protected = report["protected_files"]
    unchanged = {name: (Path(project) / name).is_file() and not (Path(project) / name).is_symlink() and
                 hashlib.sha256((Path(project) / name).read_bytes()).hexdigest() == sha for name, sha in protected.items()}
    rules_ready = all(unchanged.get(name, False) for name in ["AGENTS.md", RULES_FILE])
    skill_ready = all(ok for name, ok in unchanged.items() if name.startswith(".agents/skills/"))
    checks = [
        {"id": "git", "title": "Quản lý mã nguồn", "status": "done" if state["ready"] else "blocked",
         "note": ("Git đã sẵn sàng. " + ("Đã có commit." if state["head"] else "Chưa có commit; source đang là bản local.")) if state["ready"] else "Cần kiểm tra lại repository của dự án."},
        {"id": "private-files", "title": "Loại trừ dữ liệu riêng tư", "status": "done" if private_ready else "blocked",
         "note": "File môi trường và dữ liệu workflow đã được loại khỏi Git." if private_ready else "Cần kiểm tra .gitignore và file môi trường đang được theo dõi."},
        {"id": "rules", "title": "Quy tắc làm việc chung", "status": "done" if rules_ready else "blocked",
         "note": "Hướng dẫn chung đã được ghi nhận." if rules_ready else "Hướng dẫn bị thiếu hoặc đã thay đổi; cần ghi nhận lại bằng bootstrap."},
        {"id": "skills", "title": "Bộ skill của dự án", "status": "done" if skill_ready else "blocked",
         "note": "Bộ skill đã được cài và ghi nhận." if skill_ready else "Skill bị thiếu hoặc đã thay đổi; cần kiểm tra rồi ghi nhận lại bằng bootstrap."},
    ]
    return {"status": "done" if all(row["status"] == "done" for row in checks) else "blocked",
            "checks": checks, "repository": state, "prepared_at": report.get("prepared_at"),
            "changes": report["changes"], "note": ""}
