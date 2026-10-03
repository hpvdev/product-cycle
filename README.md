# Product Cycle

Bộ quy trình phát triển sản phẩm bằng Codex: **phân tích → UX/UI → kỹ thuật → kế hoạch → phát triển → nghiệm thu → bàn giao → retro**. Có trạng thái, model/effort, review độc lập, bằng chứng và dashboard.

Gói độc lập dựa trên [tài liệu OpenAI](docs/SOURCES.md). Không dùng Symphony. Phiên bản đầu chạy tuần tự và giữ lịch sử; áp dụng được cho repository mới hoặc đang có.

## Xem dữ liệu minh họa

```sh
cd /Users/hungpham/Documents/Product-Cycle
python3 -m product_cycle doctor
python3 -m product_cycle demo --project .runtime/demo-project
python3 -m product_cycle serve --project .runtime/demo-project --port 8787
```

Mở [dashboard](http://127.0.0.1:8787). Demo ghi rõ dữ liệu tổng hợp, không gọi AI hoặc phát triển sản phẩm thật. Dùng đường dẫn project mới nếu đã tạo demo trước đó.

## Áp dụng sau khi chọn dự án

Python 3.9+, Git, Codex đã đăng nhập; macOS/Linux. Jev tùy chọn. Chạy từ repo không cần dependency. Có thể `python3 -m pip install -e .` để dùng lệnh `product-cycle`.

```sh
python3 -m product_cycle init --project /absolute/product --brief /absolute/brief.md --name "Tên sản phẩm"
python3 -m product_cycle serve --project /absolute/product
python3 -m product_cycle run --project /absolute/product
```

Ba gate mặc định: chốt phân tích, duyệt thực thi, chấp nhận bàn giao. Xem đầu ra/bằng chứng rồi quyết định trên dashboard. Chưa phát triển trước khi kế hoạch được chấp nhận. UI acceptance có thể cần operator nếu app-server thiếu browser.

```sh
python3 -m product_cycle decide --project /absolute/product --task analysis --action approve --actor "Chủ sản phẩm" --note "Chấp nhận mục tiêu và phạm vi"
python3 -m product_cycle run --project /absolute/product
```

Khi áp dụng, thêm `.product-cycle/` vào `.gitignore` sản phẩm. State và bằng chứng đã chốt nằm ở `~/.local/share/product-cycle`, ngoài vùng AI được ghi. `PRODUCT_CYCLE_HOME` đổi nơi lưu; giữ nguyên trong một cycle. `PRODUCT_CYCLE_CODEX` chọn binary nếu Codex không nằm trong PATH.

## Kiểm chứng

```sh
python3 -m unittest discover -s tests -v
python3 -m product_cycle eval
python3 scripts/live_check.py --output .runtime/live-check
```

Hai lệnh đầu dùng tình huống tổng hợp/adapter giả lập, không gọi model. Live check thực hiện một hợp đồng phân tích và review độc lập bằng Codex thật trong fixture riêng, dùng hạn mức tài khoản. Không phát triển sản phẩm thật hoặc chứng minh toàn bộ SDLC đạt chất lượng.

## Thành phần

- Controller/CLI: phụ thuộc, retry, pause/resume, recover, đổi phạm vi, quyết định, đóng gói.
- Codex adapter: phiên work/review riêng, model/effort thực tế, trace, lỗi, timeout, token khi có.
- Hợp đồng từng vai trò, skill tái sử dụng, installer cho project được chọn.
- Lệnh kiểm tra thật, bằng chứng có hash/nguồn/phiên bản, manifest bàn giao.
- Dashboard: công việc, phụ thuộc, tiêu chí, đầu ra, review, model, lịch sử.
- Eval cơ chế và Jev adapter cho nhận định ngữ nghĩa tùy chọn.

## Giới hạn

V0.1 chạy tuần tự; không tự merge/deploy/thông báo bên ngoài/theo dõi production. Không tự mở browser để nghiệm thu, đổi model khi thất bại hoặc áp dụng đề xuất retro. Lệnh kiểm tra chạy cục bộ ngoài sandbox Codex, nên cần lệnh tin cậy đã duyệt. Chất lượng sản phẩm được kiểm chứng khi áp dụng dự án thật.

Đọc [quy trình](docs/WORKFLOW.md), [kiến trúc](docs/ARCHITECTURE.md), [vận hành](docs/RUNBOOK.md), [đánh giá](evals/README.md).
