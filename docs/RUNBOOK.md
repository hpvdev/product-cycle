# Vận hành

## Bắt đầu

`python3 -m product_cycle doctor` kiểm tra Python, binary, đăng nhập Codex và Jev. Nó không suy ra browser/MCP sẵn có từ ứng dụng desktop. Mọi command chạy từ repository Product-Cycle hoặc dùng lệnh `product-cycle` sau cài đặt.

Brief cần: người dùng, vấn đề, kết quả, phạm vi, ràng buộc, những gì chưa biết. Dùng `init` cho project được chọn; `serve` mở dashboard; `run` bắt đầu công việc sẵn sàng. Kiểm tra trước rằng project và PRODUCT_CYCLE_HOME là vị trí mong muốn.

Skill cài theo project: `python3 scripts/install_skill.py --project /absolute/product`. Script cài 1 skill điều phối và 10 skill chuyên môn (9 giai đoạn cùng review độc lập) vào `.agents/skills/`. Nó kiểm tra xung đột trước khi sao chép, không ghi đè skill có sẵn và không sửa thiết lập Codex toàn cục. Bộ controller vẫn chạy từ repository hoặc executable đã cài.

Một project mới dùng `init --project /absolute/product --brief /absolute/brief.md --name "Tên sản phẩm"`, sau đó `serve --project /absolute/product` để xem dashboard và `run --project /absolute/product` từ terminal khác để thực thi. Cài skill trước init để bộ skill được tính trong phiên bản source ngay từ đầu. Mỗi project có kho trạng thái riêng ngoài thư mục worker được ghi.

## Các bước nhỏ và mốc thiết kế

Dự án mới hiển thị 9 giai đoạn, bao gồm cấu hình dịch vụ; các dự án cũ giữ cấu hình giai đoạn phù hợp. Dashboard hiển thị danh sách đầu việc trong plan ngay khi có đầu ra dự kiến, cùng, các bước nhỏ, kiểm tra theo kế hoạch, review và điểm quyết định. Trước khi plan được chấp nhận, phần phát triển hiển thị các bước dự kiến; sau đó mỗi công việc có tiến độ riêng. Tiến độ là tỷ lệ bước được xác nhận, không phải ước lượng thời gian. Số bước có thể tăng khi công việc hoặc lệnh kiểm tra được mở rộng.

Worker dùng `update_plan` khi công cụ sẵn có và giữ mã S1, S2... trong tên bước để truyền tiến độ trực tiếp. Báo completed chỉ hiển thị “Chờ kiểm chứng”. Mỗi bước cần đầu ra liên kết trong work result; reviewer đánh giá riêng bằng bằng chứng. Nếu runtime không gửi cập nhật kế hoạch, các bước chưa có báo cáo giữ trạng thái chờ cho đến khi kết quả về, không tự suy diễn bước đang chạy. Controller xác nhận kiểm tra và quyết định theo dữ liệu thực tế. Phiên cũ không có dữ liệu từng bước hiển thị “Chưa ghi chi tiết”; mở lại tạo revision mới và giữ nguyên lịch sử.

Dự án mới có gate tại handoff và review độc lập ở từng giai đoạn trước đó. Design tạo `design.md`, `design-baseline.json` cùng hình/prototype cụ thể cho UI. Baseline chứa luồng, trạng thái, quy tắc và tiêu chí nghiệm thu. Baseline được review trước bước kỹ thuật và coding; không yêu cầu quyết định chủ sản phẩm giữa các bước trừ khi cấu hình gate có yêu cầu. Product Design/Image Gen chỉ được sử dụng nếu worker runtime có công cụ tương ứng; việc plugin có sẵn trong desktop không tự cấp nó cho app-server. Ghi rõ khả năng thiếu hoặc dùng reference đã chọn. Không có UI thì ghi hợp đồng tương tác phù hợp. Dự án cũ giữ nguyên gate và hợp đồng của kết quả đã niêm phong.

## Model và giới hạn

`status` trả config và vị trí state. `config.json` trong state có model/effort riêng cho từng role, timeout, ngân sách token, số lần thử, network và các gate. Đổi cấu hình khi không có phiên chạy. Chọn model/effort tài khoản thực tế hỗ trợ. Mỗi attempt giữ cấu hình yêu cầu, thông tin app-server trả lại, thread/turn ID và token khi có.

Mặc định cho dự án mới:

| Vai trò | Model | Effort |
|---|---|---|
| Phân tích, UX/UI, kiến trúc | `gpt-6-astra` | `medium` |
| Kế hoạch, cấu hình dịch vụ, phát triển, nghiệm thu, bàn giao, retro | `gpt-6.1-sol` | `medium` |
| Review độc lập | `gpt-6.1-sol` | `high` |

Đây là cấu hình khởi đầu của Product Cycle dựa trên hướng dẫn chọn model của OpenAI, chưa phải kết quả tối ưu đã được kiểm chứng trên dự án thật. Các dự án đã khởi tạo giữ cấu hình riêng; thay đổi mặc định không viết lại lịch sử phiên. `init --model ...` ghi đè model cho mọi vai trò; `--effort ...` ghi đè effort cho mọi vai trò. Hai tùy chọn độc lập, phần không ghi đè vẫn dùng mặc định theo vai trò.

Tăng effort khi công việc cần lập luận sâu hơn; cân nhắc Astra cho lượt review có quyết định khó hoặc rủi ro lớn. Việc đổi cấu hình là chủ động, chưa có tự động tăng effort hay chuyển model. So sánh chất lượng, thời gian, token và số lần sửa trên cùng đầu vào trước khi chọn cấu hình cho vòng sau. Dùng `model/list` của Codex App Server để xác nhận model và effort tài khoản hỗ trợ.

Số lần thử giới hạn theo revision. Hết số lần thử: xác định nguyên nhân, thay cấu hình/công cụ nếu cần, rồi `reopen` với lý do. Không đổi tiêu chí chỉ để báo đạt. Khi ngữ cảnh thiếu, bổ sung brief hoặc mở lại phần liên quan. Không tự tăng effort để xử lý lỗi môi trường.

## Quyết định

Dashboard cho xem tiêu chí, đầu ra, bằng chứng và review trước khi chấp nhận. Người xác nhận và ghi chú là một bản ghi quyết định; gói này không có dịch vụ xác thực nhiều người dùng. CLI tương đương:

```sh
python3 -m product_cycle decide --project /absolute/product --task handoff --action approve --actor "Chủ sản phẩm" --note "Chấp nhận bản local và kết quả kiểm chứng này"
```

Plan mới được review trước thực thi; các argv chỉ là lệnh kiểm tra tin cậy trong phạm vi dự án đã cấp phép. Các cycle cũ còn gate plan giữ nguyên điểm quyết định đó.

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

Manifest chứa toàn bộ lịch sử, source fingerprint, quyết định, evidence IDs và hash các file nguồn đã sao chép. `source/` chứa source, `evidence/` chứa bằng chứng. File .env và symlink được bỏ qua, có danh sách rõ trong manifest; .env.example được giữ. Handoff ghi cách thiết lập môi trường. Gói này bàn giao bản local. VPS và phát hành ra ngoài là giai đoạn sau theo yêu cầu, chưa được thực thi.

Retro chỉ đề xuất. Chạy eval cơ chế, live check phù hợp và các tình huống chất lượng đại diện trước khi chọn thay đổi. Vòng sản phẩm tiếp theo bắt đầu bằng mục tiêu mới hoặc `reopen` phần cần thay đổi. Không suy ra nhu cầu người dùng từ việc test kỹ thuật thành công.

## Cấu hình dịch vụ sau thiết kế

services.json được tạo ở bước kỹ thuật sau phân tích và UX/UI. Plan khai service_ids và danh sách services cho từng đầu việc. Controller tạo việc cấu hình riêng theo dịch vụ, sau review plan; các đầu việc chỉ phụ thuộc đúng dịch vụ cần dùng. Không có dịch vụ thì giai đoạn này được ghi không yêu cầu.

Dashboard chỉ hiển thị tên/tham chiếu đầu vào, quyền và trạng thái. Cấp bí mật qua nơi lưu bảo mật hoặc cấu hình môi trường của project, không qua ghi chú dashboard. Khi worker thiếu công cụ/quyền hoặc thông tin, readiness.json vẫn được niêm phong để hiện yêu cầu cần cấp. Sau khi cung cấp, mở lại đúng việc cấu hình để chạy và kiểm tra lại. Các đầu việc không phụ thuộc vẫn có thể tiếp tục.

Đăng nhập sẵn trong Chrome không tự cấp computer use cho app-server. Xác nhận công cụ và profile đúng trong phiên thực thi; không dùng hungpv@hblab.vn / HungPV hoặc profile chưa xác định. Chưa có adapter tự động browser/mobile nghiệm thu; giữ trạng thái chưa kiểm chứng nếu thiếu quan sát thực tế. VPS, deploy web và DeployGate được để sau; không mua hoặc cấu hình hạ tầng phát hành trong cycle local.
