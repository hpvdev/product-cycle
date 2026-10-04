import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .contracts import WorkflowError, require
from .runner import execute, review_task, run_cycle, sync_task, continue_task
from .server import serve
from .store import Store, fingerprint, now, write_json, runner_lock, state_root
from .bootstrap import prepare_project, repository_state
from .installer import install_skills
from . import desktop


def parser():
    cli = argparse.ArgumentParser(description="Product Cycle — quy trình phát triển có bằng chứng")
    sub = cli.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Khởi tạo quy trình cho một dự án")
    init.add_argument("--project", required=True)
    init.add_argument("--brief", required=True, help="File mô tả mục tiêu sản phẩm")
    init.add_argument("--name", required=True)
    init.add_argument("--executor", choices=["codex-desktop", "codex-app-server"], default="codex-desktop")
    init.add_argument("--model", help="Dùng model này cho mọi bước thay cho cấu hình theo vai trò")
    init.add_argument("--max-turn-tokens", type=int, help="Ngân sách token mỗi phiên; mặc định chỉ theo dõi")
    init.add_argument("--max-cycle-tokens", type=int, help="Ngân sách token toàn quy trình; mặc định chỉ theo dõi")
    init.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max", "ultra"],
                      help="Dùng effort này cho mọi bước thay cho cấu hình theo vai trò")
    for name in ["bootstrap", "install-skills", "status", "run", "work", "review", "decide", "reopen", "pause", "resume", "recover", "sync", "continue", "serve", "package", "browser-evidence", "judge", "configure", "owner-input", "desktop-bind", "desktop-submit", "desktop-progress"]:
        cmd = sub.add_parser(name)
        cmd.add_argument("--project", required=True)
        if name in {"work", "review", "decide", "reopen", "browser-evidence", "judge", "sync", "continue", "owner-input", "desktop-bind", "desktop-submit", "desktop-progress"}:
            cmd.add_argument("--task", required=True)
        if name == "configure":
            cmd.add_argument("--executor", choices=["codex-desktop", "codex-app-server"], required=True)
        if name == "owner-input":
            cmd.add_argument("--actor", required=True)
            cmd.add_argument("--note", required=True)
        if name in {"desktop-bind", "desktop-submit", "desktop-progress"}:
            cmd.add_argument("--attempt", required=True)
        if name == "desktop-bind":
            cmd.add_argument("--thread", required=True)
        if name in {"desktop-submit", "desktop-progress"}:
            cmd.add_argument("--file", required=True)
        if name == "run":
            cmd.add_argument("--max-tasks", type=int, default=50)
            cmd.add_argument("--continue-blocked", action="store_true", help="Đồng bộ chat Codex và khôi phục các công việc bị chặn trước khi chạy tiếp")
        if name == "serve":
            cmd.add_argument("--port", type=int, default=8787)
        if name in {"decide", "reopen", "browser-evidence"}:
            cmd.add_argument("--note", required=True)
        if name in {"decide", "browser-evidence"}:
            cmd.add_argument("--actor", required=True)
        if name == "decide":
            cmd.add_argument("--action", choices=["approve", "reject"], required=True)
        if name == "package":
            cmd.add_argument("--output", required=True)
        if name == "browser-evidence":
            cmd.add_argument("--screenshot", required=True, help="File ảnh nằm trong dự án")
            cmd.add_argument("--url", required=True)
            cmd.add_argument("--requirements", nargs="+", required=True)
        if name == "judge":
            cmd.add_argument("--text", required=True, help="Đoạn nội dung không nhạy cảm được gửi tới Jev")
            cmd.add_argument("--question", required=True)
    doctor_cli = sub.add_parser("doctor", help="Kiểm tra môi trường, không đọc thông tin bí mật")
    doctor_cli.add_argument("--project", help="Kiểm tra nền tảng của dự án đã chọn")
    demo = sub.add_parser("demo", help="Tạo dữ liệu minh họa, không gọi model")
    demo.add_argument("--project", required=True)
    sub.add_parser("eval", help="Chạy bộ đánh giá quy trình cục bộ")
    return cli


def doctor(project=None):
    codex = os.environ.get("PRODUCT_CYCLE_CODEX") or shutil.which("codex")
    result = {"python": sys.version.split()[0], "platform": sys.platform, "codex": codex,
              "git": shutil.which("git"), "jev": shutil.which("jev"),
              "browser": "Kiểm tra trong phiên Codex được chọn; không suy ra từ ứng dụng desktop."}
    result["codex_authenticated"] = False
    if codex:
        try:
            check = subprocess.run([codex, "login", "status"], capture_output=True, text=True, timeout=15)
            result["codex_authenticated"] = check.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            result["codex_status"] = "Chưa kiểm tra được đăng nhập Codex."
    result["ready"] = bool(result["git"] and result["codex_authenticated"])
    result["model_access"] = "Quyền dùng model và công cụ cần xác nhận ở phiên thực thi; không suy ra từ đăng nhập."
    if project:
        project = Path(project).expanduser().resolve()
        require(project.is_dir(), "Chưa có thư mục dự án được chọn.")
        if (state_root(project) / "state.sqlite3").is_file():
            store = Store(project)
            try:
                result["foundation"] = store.foundation()
            finally:
                store.close()
            result["ready"] = result["ready"] and result["foundation"]["status"] == "done"
        else:
            result["repository"] = repository_state(project) if result["git"] else None
            result["ready"] = False
            result["project_status"] = "Dự án chưa được khởi tạo bằng Product Cycle."
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    store = None
    try:
        if args.command == "doctor":
            result = doctor(args.project)
            require(result["ready"], "Môi trường chưa sẵn sàng; xử lý các mục chưa đạt trong kết quả kiểm tra.")
            return
        if args.command == "install-skills":
            print(json.dumps(install_skills(args.project), ensure_ascii=False, indent=2))
            return
        if args.command == "bootstrap":
            if (state_root(args.project) / "state.sqlite3").is_file():
                store = Store(args.project)
                with runner_lock(store):
                    report = store.bootstrap()
            else:
                report = prepare_project(args.project)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return
        if args.command == "eval":
            from .evals import evaluate
            result = evaluate()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if not result["passed"]:
                raise WorkflowError("Có tình huống đánh giá chưa đạt.")
            return
        if args.command == "demo":
            from .demo import create_demo
            create_demo(args.project)
            print("Đã tạo dữ liệu minh họa; chưa chạy AI hay phát triển dự án thật.")
            return
        if args.command == "init":
            for value in (args.max_turn_tokens, args.max_cycle_tokens):
                require(value is None or value > 0, "Ngân sách token phải là số nguyên dương.")
            store = Store.create(args.project, Path(args.brief).read_text(), args.name, args.model, args.effort)
            config = store.config
            config.update(max_turn_tokens=args.max_turn_tokens, max_cycle_tokens=args.max_cycle_tokens, executor=args.executor)
            write_json(store.root / "config.json", config)
            print("Đã khởi tạo: " + str(store.root))
            return
        if args.command == "serve":
            return serve(args.project, args.port)
        store = Store(args.project)
        if args.command == "status":
            print(json.dumps(store.snapshot(), ensure_ascii=False, indent=2))
        elif args.command == "run":
            outcome = run_cycle(store, args.max_tasks, continue_blocked=args.continue_blocked)
            if outcome:
                print(json.dumps(outcome, ensure_ascii=False, indent=2))
        elif args.command == "work":
            with runner_lock(store):
                outcome = execute(store, args.task)
                if outcome:
                    print(json.dumps(outcome, ensure_ascii=False, indent=2))
        elif args.command == "review":
            with runner_lock(store):
                outcome = review_task(store, args.task)
                if outcome:
                    print(json.dumps(outcome, ensure_ascii=False, indent=2))
        elif args.command == "configure":
            with runner_lock(store):
                require(not store.db.execute("SELECT id FROM attempts WHERE status IN ('running','queued')").fetchone(),
                        "Kết thúc hoặc khôi phục phiên đang chạy trước khi đổi nơi thực thi.")
                config = store.config
                config.update(executor=args.executor, dashboard_read_only=True)
                write_json(store.root / "config.json", config)
                store.event(None, "executor.configured", {"executor": args.executor})
            print("Đã cập nhật nơi thực thi. Lịch sử và quyết định trước đây được giữ nguyên.")
        elif args.command == "owner-input":
            with runner_lock(store):
                store.owner_input(args.task, args.actor, args.note)
        elif args.command in {"desktop-bind", "desktop-submit", "desktop-progress"}:
            with runner_lock(store):
                if args.command == "desktop-bind":
                    outcome = desktop.bind(store, args.task, args.attempt, args.thread)
                elif args.command == "desktop-submit":
                    outcome = desktop.submit(store, args.task, args.attempt, args.file)
                else:
                    attempt = desktop.latest(store, args.task)
                    require(desktop.enabled(store) and attempt and attempt["id"] == args.attempt and attempt["status"] == "running",
                            "Phiên hiện tại chưa sẵn sàng ghi tiến độ.")
                    plan = json.loads(store.safe_path(args.file).read_text())
                    require(isinstance(plan, list), "Cần danh sách tiến độ từng bước.")
                    store.step_progress(args.attempt, plan)
                    outcome = {"ok": True}
            print(json.dumps(outcome, ensure_ascii=False, indent=2))
        elif args.command == "decide":
            with runner_lock(store):
                store.decide(args.task, args.action, args.actor, args.note)
        elif args.command == "reopen":
            with runner_lock(store):
                print(json.dumps(store.reopen(args.task, args.note)))
        elif args.command in {"pause", "resume"}:
            store.pause(args.command == "pause")
        elif args.command == "recover":
            with runner_lock(store):
                print(json.dumps(store.recover()))
        elif args.command in {"sync", "continue"}:
            require(store.config["mode"] == "live", "Dữ liệu minh họa không có phiên Codex thực tế để khôi phục.")
            with runner_lock(store):
                action = sync_task if args.command == "sync" else continue_task
                outcome = action(store, args.task)
                print(json.dumps(outcome, ensure_ascii=False))
            if args.command == "continue" and not outcome.get("active") and not desktop.enabled(store):
                run_cycle(store)
        elif args.command == "package":
            with runner_lock(store):
                print(store.package(args.output))
        elif args.command == "browser-evidence":
            task = store.task(args.task)
            require(task["stage"] == "verify" and task["status"] in {"blocked", "reviewing"}, "Bằng chứng trình duyệt được ghi ở bước nghiệm thu đã có kết quả.")
            require(set(args.requirements) <= store.requirement_ids(), "Mã yêu cầu chưa hợp lệ.")
            screenshot = store.safe_path(args.screenshot)
            require(screenshot.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}, "Cần file ảnh chụp màn hình.")
            directory = store.latest_directory(args.task)
            image_id = store.record_file(args.task, str(screenshot.relative_to(store.project)), args.note,
                                         requirements=args.requirements, producer="operator")
            # This is explicitly a human observation, never an automated pass.
            report = {"actor": args.actor, "url": args.url, "observed_at": now(), "observation": args.note,
                      "screenshot_evidence": image_id, "requirements": args.requirements,
                      "source_fingerprint": fingerprint(store.project), "producer": "operator"}
            path = directory / ("browser-" + image_id + ".json")
            write_json(path, report)
            eid = store.record_file(args.task, str(path.relative_to(store.project)), args.note,
                                    ["C1"], args.requirements, "browser", "operator")
            print(eid)
        elif args.command == "judge":
            from .jev import judge
            result = judge(args.text, args.question)
            path = store.latest_directory(args.task) / ("jev-" + __import__("uuid").uuid4().hex[:10] + ".json")
            write_json(path, result)
            store.record_file(args.task, str(path.relative_to(store.project)), "Nhận định ngữ nghĩa từ Jev", producer="jev")
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except (WorkflowError, OSError) as exc:
        print("Product Cycle: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
    finally:
        if store is not None:
            store.close()
