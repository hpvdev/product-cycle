# Đánh giá quy trình

`python3 -m product_cycle eval`: 8 tình huống cơ chế trong thư mục tạm, không gọi model. `unittest` bổ sung adapter protocol, lệnh kiểm tra thật và toàn bộ vòng có dữ liệu tổng hợp.

`python3 scripts/live_check.py --output .runtime/live-check`: kiểm tra Codex thật trên hợp đồng phân tích và review độc lập. Có dùng hạn mức tài khoản. Kết quả và trace giữ riêng, không áp dụng sản phẩm.

Các tầng đánh giá:

1. Controller invariants: không vượt gate, nhận bằng chứng giả/thiếu, tạo DAG vòng lặp, mất lịch sử hoặc đóng gói trước nghiệm thu.
2. Adapter: handshake, model/effort, sự kiện, trạng thái lỗi, timeout, yêu cầu tương tác.
3. Model/skill quality: tình huống thực tế, đánh giá nội dung theo rubric, lặp lại đủ để thấy độ ổn định.
4. Product quality: yêu cầu và trải nghiệm thực tế trên dự án được chọn.

Hai tầng đầu được tự động hóa trong gói. Live check là tín hiệu ban đầu cho tầng 3, không thay bộ đo chất lượng đầy đủ hoặc tầng 4. Bộ tình huống trong cases.json là điểm bắt đầu để so phiên bản; giữ các lỗi thật thành tình huống mới.
