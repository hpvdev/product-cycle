# Product Cycle

Bộ quy trình phát triển sản phẩm bằng Codex: **chuẩn bị repository → phân tích → UX/UI → kỹ thuật → kế hoạch → cấu hình dịch vụ cần thiết → phát triển (chuẩn bị project/common, rồi tính năng) → nghiệm thu → bàn giao → retro**. Có trạng thái, model/effort, review độc lập, bằng chứng và dashboard.

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

Python 3.9+, Git, Codex đã đăng nhập; macOS/Linux. Jev tùy chọn. Chạy từ repo không cần dependency. Để cài executable và bộ skill đóng gói, dùng môi trường Python riêng với pip mới:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .
```

Sau đó dùng `.venv/bin/product-cycle`.

```sh
python3 -m product_cycle init --project /absolute/product --brief /absolute/brief.md --name "Tên sản phẩm"
python3 -m product_cycle serve --project /absolute/product
python3 -m product_cycle run --project /absolute/product
```

Dự án mới thực thi trong ứng dụng Codex; dashboard chỉ đọc tiến độ, tài liệu và bằng chứng. Bạn cùng AI chốt hướng sản phẩm, UX/UI, dùng thử trải nghiệm cốt lõi và nghiệm thu bàn giao. AI tự triển khai phần đã chốt, có review độc lập từng giai đoạn. Thiết kế kỹ thuật nêu dịch vụ cần dùng và thông tin cần cấp; sau khi plan được review, controller tạo việc cấu hình và chỉ chặn các đầu việc phụ thuộc. VPS và phát hành ra ngoài để sau. Dự án cũ giữ nguyên cấu hình. UI acceptance cần quan sát thực tế; không suy ra công cụ sẵn có ở một runtime khác.

```sh
python3 -m product_cycle decide --project /absolute/product --task handoff --action approve --actor "Chủ sản phẩm" --note "Chấp nhận bản local và kết quả kiểm chứng"
python3 -m product_cycle run --project /absolute/product
```

`run` ở chế độ Codex App chuẩn bị công việc, không tự gọi model. Chat Codex đang hoạt động dùng skill product-cycle để nhận công việc, trao đổi với bạn và gửi kết quả về controller. Xem [vòng thực thi native](skills/product-cycle/references/operating-guide.md#native-codex-loop). Chọn `init --executor codex-app-server` nếu muốn chạy bằng App Server riêng.

`init` tự chuẩn bị Git nếu chưa có, bổ sung `.gitignore`, tạo `AGENTS.md`/`PRODUCT_CYCLE_RULES.md` và cài 14 skill theo project, gồm Frontend App Builder từ repo OpenAI hiện hành và skill làm lại quy trình `product-cycle-reset`. Giữ nguyên Git, hướng dẫn và skill đã có; không tự commit/push. Thiết kế kỹ thuật tạo `project-setup.json`; công việc chuẩn bị bên trong Phát triển tạo coding rules theo stack, cấu trúc code, môi trường, công cụ kiểm tra và phần dùng chung trước mọi task chức năng. State và bằng chứng đã chốt nằm ở `~/.local/share/product-cycle`, ngoài vùng AI được ghi. `PRODUCT_CYCLE_HOME` đổi nơi lưu; giữ nguyên trong một cycle. `PRODUCT_CYCLE_CODEX` chọn binary nếu Codex không nằm trong PATH.

Dự án mới xác định màn hình, trạng thái và đường chuyển trước khi coding. Mỗi trạng thái trong phạm vi phải có ảnh thiết kế để bạn xem và duyệt; có thể dùng ảnh Image Gen hoặc ảnh chụp prototype, tái sử dụng cùng bộ quy tắc thiết kế. Mỗi task UI gắn với đúng màn hình, trạng thái, kích thước và phiên bản mẫu; khi code phải có ảnh giao diện thật và báo cáo đối chiếu, đồng thời kiểm tra logic theo đặc tả. Frontend App Builder hỗ trợ concept, thi công và đối chiếu ảnh UI thật. Bộ cài giữ phiên bản nguồn được ghi trong [SOURCES](docs/SOURCES.md), không tự tải bản mới mỗi lần chạy. Việc cài skill và qua test controller chưa chứng minh chất lượng thị giác của sản phẩm.

## Chuẩn bị và kiểm tra nền tảng

```sh
python3 -m product_cycle doctor --project /absolute/product
python3 -m product_cycle bootstrap --project /absolute/product
python3 -m product_cycle install-skills --project /absolute/product
```

`bootstrap` bổ sung nền tảng cho cycle cũ khi không có phiên chạy; nếu source đã nghiệm thu thay đổi, bước verify và phần phụ thuộc cần thực hiện lại. Nó không tự thêm công việc chuẩn bị theo stack vào cycle cũ. Dùng cycle mới để áp dụng trọn hợp đồng hiện tại. `configure --project ... --executor codex-desktop` chuyển nơi thực thi của cycle cũ, giữ lịch sử và gate cũ; hợp đồng cộng tác cần được áp dụng ở revision được chủ sản phẩm đồng ý mở lại. `install-skills` cài riêng và từ chối ghi đè. Các lệnh có trong wheel, dùng được ngoài checkout sau khi cài bằng pip. Graphify là tùy chọn khi repo đã có quan hệ code phức tạp; không cài mặc định cho project mới nhỏ.

Đồng bộ skill cho project đã sử dụng workflow:

```sh
python3 -m product_cycle update-skills --project /absolute/product
python3 -m product_cycle update-skills --project /absolute/product --apply
```

Lệnh đầu chỉ xem thay đổi; lệnh sau áp dụng khi không có phiên đang chạy. Có thể chọn riêng bằng `--skill product-cycle-analysis` (lặp lại để chọn nhiều skill). Bản gốc đã cài được ghi nhận bằng hash; skill tùy chỉnh hoặc project cũ chưa có bản gốc được báo xung đột. Sau khi xem thay đổi, dùng `--skill <tên> --replace-customized --apply` để thay đúng phần đã chọn và sao lưu bản cũ vào `.product-cycle/skill-backups/`. Lệnh không đổi policy/model, không reset chu kỳ hay tự chạy lại các bước. Chat hiện tại cần đọc lại hướng dẫn mới; muốn thử lại kết quả đã làm thì dùng `product-cycle-reset` riêng.

## Gỡ và cài lại skill

Gỡ bộ skill workflow ở project sử dụng để cài lại:

```sh
python3 -m product_cycle uninstall-skills --project /absolute/product
python3 -m product_cycle uninstall-skills --project /absolute/product --apply
python3 -m product_cycle install-skills --project /absolute/product
```

Lệnh đầu chỉ xem danh sách. Khi gỡ, bản cũ được sao lưu vào `.product-cycle/skill-backups/`; thêm `--force` cùng `--apply` nếu muốn gỡ cả phần đã tùy chỉnh. Mã nguồn, Git, cấu hình, tiến trình, bằng chứng, hướng dẫn chung và skill khác được giữ. Cài lại không làm quy trình chạy lại từ đầu; dùng skill reset riêng khi cần. Kết thúc các phiên thực thi trước khi gỡ/cài lại, rồi mở chat mới để dùng bộ hướng dẫn mới. Các lệnh chạy từ bản Product-Cycle đã clone hoặc gói đã cài, với `--project` trỏ đến project sử dụng.

## Cập nhật bộ workflow từ Git

Repo Product-Cycle là nơi phát triển bộ workflow; `--project` luôn trỏ đến project sử dụng. Dừng phiên thực thi và dashboard trước khi thay bộ chạy. Trong bản clone dùng để cài đặt:

```sh
git pull --ff-only
# Nếu sử dụng executable đã cài vào .venv:
.venv/bin/python -m pip install --upgrade .
# Đồng bộ skill xuống project sử dụng:
python3 -m product_cycle update-skills --project /absolute/product
python3 -m product_cycle update-skills --project /absolute/product --apply
```

Nếu chạy trực tiếp từ checkout, không cần bước pip. Khi có thay đổi local trong bản clone, giữ lại hoặc xử lý chúng trước khi pull; không force reset repository. Khởi động lại dashboard bằng phiên bản mới và mở chat mới sau khi đồng bộ. Cập nhật bộ chạy và cập nhật skill là hai thao tác riêng; `update-skills` không tải code từ Git hoặc cập nhật process đang chạy. Các cấu hình và mốc đã nghiệm thu được giữ; hợp đồng mới cần thay đổi phạm vi phải được áp dụng qua reset có chủ đích, không tự chuyển trạng thái cũ thành đạt.

## Kiểm chứng

```sh
python3 -m unittest discover -s tests -v
python3 -m product_cycle eval
python3 scripts/live_check.py --output .runtime/live-check
```

Hai lệnh đầu dùng tình huống tổng hợp/adapter giả lập, không gọi model. Live check thực hiện một hợp đồng phân tích và review độc lập bằng Codex thật trong fixture riêng, dùng hạn mức tài khoản. Không phát triển sản phẩm thật hoặc chứng minh toàn bộ SDLC đạt chất lượng.

## Thành phần

- Controller/CLI: phụ thuộc, retry, pause/resume, recover, đổi phạm vi, quyết định, đóng gói.
- Codex adapter: handoff trong Codex App mặc định; App Server là lựa chọn riêng. Work/review độc lập, cấu hình yêu cầu phân biệt với model/effort đã quan sát, token khi có.
- Hợp đồng từng vai trò, skill tái sử dụng, installer cho project được chọn.
- Lệnh kiểm tra thật, bằng chứng có hash/nguồn/phiên bản, manifest bàn giao.
- Dashboard: đủ đầu việc trong plan ngay khi có đầu ra, trạng thái/bước hiện tại, tiêu chí đạt, bằng chứng, cấu hình dịch vụ và nghiệm thu toàn sản phẩm riêng biệt.
- Eval cơ chế và Jev adapter cho nhận định ngữ nghĩa tùy chọn.

## Giới hạn

V0.3 chạy tuần tự; không tự merge/deploy/thông báo bên ngoài/theo dõi production. Không tự mở browser để nghiệm thu, đổi model khi thất bại hoặc áp dụng đề xuất retro. Lệnh kiểm tra chạy cục bộ ngoài sandbox Codex, nên cần lệnh tin cậy thuộc phạm vi đã cấp phép và được review. Chất lượng sản phẩm được kiểm chứng khi áp dụng dự án thật.

Đọc [quy trình](docs/WORKFLOW.md), [kiến trúc](docs/ARCHITECTURE.md), [vận hành](docs/RUNBOOK.md), [đánh giá](evals/README.md).
