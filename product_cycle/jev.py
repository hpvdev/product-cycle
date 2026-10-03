"""Optional typed semantic opinion. Never a substitute for execution evidence."""

import json
import shutil
import subprocess

from .contracts import WorkflowError, require


def judge(text, question):
    binary = shutil.which("jev")
    require(binary, "Chưa tìm thấy Jev trong môi trường hiện tại.")
    require(text.strip() and question.strip(), "Cần nội dung và câu hỏi rõ ràng.")
    require(len(text) <= 20000, "Hãy chọn một đoạn nội dung ngắn để đánh giá.")
    result = subprocess.run([binary, "ask", "-", "--noul", "assessment=" + question, "--json"],
                            input=text, capture_output=True, text=True, timeout=90)
    require(result.returncode == 0, "Jev chưa trả được đánh giá; kiểm tra tài khoản và kết nối.")
    try:
        value = json.loads(result.stdout)
    except ValueError as exc:
        raise WorkflowError("Jev chưa trả kết quả JSON hợp lệ.") from exc
    return {"producer": "jev", "question": question, "answer": value, "kind": "semantic_opinion",
            "limitation": "Đây là nhận định ngữ nghĩa, không chứng minh kiểm thử hoặc nghiệm thu đã thành công."}
