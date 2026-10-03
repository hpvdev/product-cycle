"""A synthetic ten-item plan illustrating status and configuration dependencies."""

import sys

from .fixtures import complete_fixture
from .store import Store, write_json


def demo_services():
    return [{"id": sid, "provider": provider, "purpose": purpose,
             "environment": "Tài khoản minh họa, chưa tạo tài nguyên thật",
             "inputs": inputs, "permissions": ["Quyền cấu hình trong dự án được chọn"],
             "configuration": "Cấu hình và kiểm tra theo hợp đồng minh họa, không thao tác tài khoản thật.",
             "verification": "Đăng nhập/lưu dữ liệu" if sid == "firebase" else "Xác nhận domain và khả năng gửi email thử nghiệm",
             "checks": [[sys.executable, "-c", "print('synthetic connection check; not a real provider connection')"]],
             "owner": "Chủ sản phẩm", "cost": "Chưa mua dịch vụ; cần xem hạn mức trước khi dùng thật",
             "fallback": "Ghi phần chưa kiểm chứng; tiếp tục các việc không phụ thuộc"}
            for sid, provider, purpose, inputs in [
                ("firebase", "Firebase", "Đăng nhập và đồng bộ danh sách công việc", ["Dự án Firebase được chọn", "Quyền truy cập cấu hình"]),
                ("resend", "Resend", "Email nhắc việc khi tính năng này được chọn", ["Domain gửi email", "Tham chiếu khóa truy cập được lưu bảo mật"]),
            ]]


def demo_plan():
    specifications = [
        ("Thêm công việc", [], [], "Thêm một công việc và nhìn thấy trong danh sách"),
        ("Sửa tên công việc", ["T1"], [], "Tên đã sửa được hiển thị đúng"),
        ("Đánh dấu hoàn thành", ["T1"], [], "Đổi trạng thái và hoàn tác được"),
        ("Xóa công việc", ["T1"], [], "Xóa đúng công việc đã chọn"),
        ("Lọc danh sách công việc", ["T3"], [], "Bộ lọc đúng với trạng thái công việc"),
        ("Giữ dữ liệu sau khi mở lại", ["T1"], [], "Mở lại vẫn thấy dữ liệu đã lưu"),
        ("Đăng nhập tài khoản", ["T1"], ["firebase"], "Đăng nhập và đăng xuất đúng luồng"),
        ("Đồng bộ danh sách", ["T6", "T7"], ["firebase"], "Đọc lại đúng dữ liệu của tài khoản"),
        ("Email nhắc việc", ["T8"], ["resend"], "Email đến đúng người nhận được phép thử"),
        ("Hoàn thiện giao diện và luồng sử dụng", ["T2", "T3", "T4", "T5", "T8", "T9"], [], "Luồng chính đạt tiêu chí thiết kế"),
    ]
    return {"tasks": [{"id": "T" + str(index + 1), "title": title,
                       "instructions": "Đầu việc minh họa cho Todo-App: " + criterion,
                       "depends_on": deps, "services": services, "requirements": ["R1"],
                       "criteria": [criterion], "checks": []}
                      for index, (title, deps, services, criterion) in enumerate(specifications)],
            "service_ids": ["firebase", "resend"], "verification_commands": [], "browser_required": False,
            "delivery": {"mode": "local", "access": "Xem bản local sau khi phát triển và kiểm thử",
                         "instructions": "Dữ liệu này chỉ minh họa quy trình; chưa có Todo-App thật.",
                         "run_commands": [], "deferred": ["VPS", "Deploy web", "Phân phối app qua DeployGate"]}}


def create_demo(project):
    store = Store.create(project, "Minh họa Todo-App: plan có 10 đầu việc, tích hợp dịch vụ và bàn giao local.",
                         "Product Cycle · 10 đầu việc minh họa", mode="demo")
    try:
        config = store.config
        config.update(service_setup_required=True, project_setup_required=True, gates=["handoff"])
        write_json(store.root / "config.json", config)
        store.bootstrap()
        store.add_task("project_setup", "build", "Chuẩn bị project và phần common", "Thiết lập nền minh họa", ["plan"],
                       ["Nền minh họa có đầu ra", "Kiểm tra tổng hợp thành công"], [], [])
        for tid in ["analysis", "design"]:
            complete_fixture(store, tid)
        complete_fixture(store, "architecture", services=demo_services())
        complete_fixture(store, "plan", plan=demo_plan())
        complete_fixture(store, "project_setup")
        complete_fixture(store, "setup-firebase")
        complete_fixture(store, "setup-resend", readiness={"services": [{"id": "resend", "status": "needs_input",
                         "note": "Cần bạn chọn domain gửi email và cấp tham chiếu khóa truy cập. Đây là tình huống minh họa.",
                         "input_refs": ["Domain gửi email", "Tham chiếu khóa truy cập"]}]}, blocker="Chờ thông tin cấu hình email trong tình huống minh họa.")
        complete_fixture(store, "T1")
        complete_fixture(store, "T2")
        complete_fixture(store, "T3", review_decision="rework")
    finally:
        store.close()
