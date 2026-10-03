# Vận hành

## Bắt đầu

`python3 -m product_cycle doctor` kiểm tra Python, binary, đăng nhập Codex và Jev. Nó không suy ra browser/MCP sẵn có từ ứng dụng desktop. Mọi command chạy từ repository Product-Cycle hoặc dùng lệnh `product-cycle` sau cài đặt.

Brief cần: người dùng, vấn đề, kết quả, phạm vi, ràng buộc, những gì chưa biết. Dùng `init` cho project được chọn; `serve` mở dashboard; `run` bắt đầu công việc sẵn sàng. Kiểm tra trước rằng project và PRODUCT_CYCLE_HOME là vị trí mong muốn.

Skill cài theo project: `python3 scripts/install_skill.py --project /absolute/product`. Không ghi đè skill có sẵn và không sửa thiết lập Codex toàn cục. Bộ controller vẫn chạy từ repository hoặc executable đã cài.

## Model và giới hạn

`status` trả config và vị trí state. `config.json` trong state có model/effort riêng cho từng role, timeout, ngân sách token, số lần thử, network và các gate. Đổi cấu hình khi không có phiên chạy. Chọn model/effort tài khoản thực tế hỗ trợ. Mỗi attempt giữ cấu hình yêu cầu, thông tin app-server trả lại, thread/turn ID và token khi có.

Số lần thử giới hạn theo revision. Hết số lần thử: xác định nguyên nhân, thay cấu hình/công cụ nếu cần, rồi `reopen` với lý do. Không đổi tiêu chí chỉ để báo đạt. Khi ngữ cảnh thiếu, bổ sung brief hoặc mở lại phần liên quan. Không tự tăng effort để xử lý lỗi môi trường.

## Quyết định

Dashboard cho xem tiêu chí, đầu ra, bằng chứng và review trước khi chấp nhận. Người xác nhận và ghi chú là một bản ghi quyết định; gói này không có dịch vụ xác thực nhiều người dùng. CLI tương đương:

```sh
python3 -m product_cycle decide --project /absolute/product --task plan --action approve --actor "Chủ sản phẩm" --note "Chấp nhận phạm vi, công việc và lệnh kiểm tra này"
```

Quyết định chấp nhận plan cho phép controller chạy các argv kiểm tra cụ thể trong kế hoạch ở project cục bộ. Đọc chúng trước khi chấp nhận.

## Browser acceptance

Operator thao tác sản phẩm thật và lưu screenshot trong project. Ghi nhận rõ kịch bản đã thử, kết quả thực tế và yêu cầu được bao phủ:

```sh
python3 -m product_cycle browser-evidence --project /absolute/product --task verify --screenshot .product-cycle/evidence/acceptance.png --url http://127.0.0.1:5173 --requirements R1 R2 --actor "Người kiểm chứng" --note "Đã thực hiện các hành vi R1 và R2; tải lại trang giữ dữ liệu"
python3 -m product_cycle review --project /absolute/product --task verify
```

Chỉ khai các yêu cầu đã thử thật. Có thể ghi nhiều quan sát cho nhiều nhóm yêu cầu. Đây là bằng chứng do người quan sát cung cấp, không phải kiểm chứng tự động. Screenshot nên nằm trong `.product-cycle/` nếu không thuộc source để tránh làm đổi fingerprint sản phẩm khi ghi bằng chứng.

## Gián đoạn và thay đổi

`pause` có hiệu lực tại ranh giới công việc; lượt đang chạy hoàn tất. `resume` bỏ tạm dừng; `run` tiếp tục. Ctrl-C dừng controller và process group Codex; phiên không hoàn tất không trở thành done.

Sau crash: `recover` chỉ chạy khi lock không bị giữ. Kiểm tra thay đổi thực tế và trace trong work directory. `reopen --task ... --note ...` tạo revision mới, giữ phiên/bằng chứng cũ, đánh dấu phụ thuộc cần xem lại. Không chạy lại thao tác bên ngoài khi chưa biết lần trước có thành công không.

## Bàn giao và vòng sau

Sau khi chấp nhận handoff và hoàn tất retro:

```sh
python3 -m product_cycle package --project /absolute/product --output /absolute/delivery/new-package
```

Manifest chứa toàn bộ lịch sử, source fingerprint, quyết định, evidence IDs và hash các file nguồn đã sao chép. `source/` chứa source, `evidence/` chứa bằng chứng. File .env và symlink được bỏ qua, có danh sách rõ trong manifest; .env.example được giữ. Handoff ghi cách thiết lập môi trường. Publication/deployment là công việc riêng cần quyền tương ứng.

Retro chỉ đề xuất. Chạy eval cơ chế, live check phù hợp và các tình huống chất lượng đại diện trước khi chọn thay đổi. Vòng sản phẩm tiếp theo bắt đầu bằng mục tiêu mới hoặc `reopen` phần cần thay đổi. Không suy ra nhu cầu người dùng từ việc test kỹ thuật thành công.
