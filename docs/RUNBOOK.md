# Vận hành

## Bắt đầu

`python3 -m product_cycle doctor` kiểm tra Python, binary, đăng nhập Codex và Jev. Nó không suy ra browser/MCP sẵn có từ ứng dụng desktop. Mọi command chạy từ repository Product-Cycle hoặc dùng lệnh `product-cycle` sau cài đặt.

Brief cần: người dùng, vấn đề, kết quả, phạm vi, ràng buộc, những gì chưa biết. Dùng `init` cho project được chọn; `serve` mở dashboard; `run` bắt đầu công việc sẵn sàng. Kiểm tra trước rằng project và PRODUCT_CYCLE_HOME là vị trí mong muốn.

Skill cài theo project: `python3 scripts/install_skill.py --project /absolute/product`. Script cài 1 skill điều phối, 11 skill chuyên môn (9 bước lớn, một skill chuẩn bị code và review độc lập), Frontend App Builder và `product-cycle-reset` vào `.agents/skills/`. Nó kiểm tra xung đột trước khi sao chép, không ghi đè skill có sẵn và không sửa thiết lập Codex toàn cục. Bộ controller vẫn chạy từ repository hoặc executable đã cài.

Để thử lại workflow, dùng [skill làm lại quy trình](../skills/product-cycle-reset/SKILL.md) trong chat Codex: “Dùng $product-cycle-reset làm lại từ bước 01” hoặc “Làm lại từ bước 02 UI/UX và tiếp tục bước này”. Skill dùng `reopen` để tạo phiên bản mới và vô hiệu hóa kết quả phụ thuộc, giữ mã nguồn, Git và lịch sử. Reset riêng mặc định để cycle tạm dừng; yêu cầu tiếp tục mới thực thi. Việc reset không tự cập nhật skill đã cài hoặc xóa cấu hình dịch vụ thật.

Làm lại dùng chat mới, không tiếp tục hoặc fork chat cũ. Skill chuẩn bị bản giao việc ngắn trong `.product-cycle/restarts/`, chỉ gồm yêu cầu hiện tại, ranh giới làm lại, đầu vào phía trước còn hiệu lực và lựa chọn chủ sản phẩm yêu cầu giữ. Phản hồi revision cũ không được đưa vào packet mới; lịch sử vẫn lưu để audit. Bạn mở chat mới với bản giao việc đó, hoặc yêu cầu rõ việc tạo chat mới. Mã nguồn và hướng dẫn dự án vẫn còn; reset workflow không đồng nghĩa xóa sạch project hay buộc chat cũ quên nội dung.

Frontend App Builder hỗ trợ concept trong Thiết kế, dùng mẫu đã duyệt trong Phát triển và so sánh concept với ảnh render trong Nghiệm thu. Prompt cung cấp đường dẫn skill cho Thiết kế và cho công việc Phát triển/Nghiệm thu khi baseline đã chốt có UI; backend và reviewer không tự nhận toàn bộ hướng dẫn frontend. Ưu tiên skill theo project, sau đó skill cá nhân nếu có; thiếu skill hoặc công cụ thì ghi nhận hạn chế. Giữ scope, stack, schema, bằng chứng và quyết định chủ sản phẩm của workflow; không tự coi điểm tự chấm là nghiệm thu. Cycle cũ không tự được ghi đè skill đã cài.

### Cập nhật skill ở project đã cài

Chạy từ checkout Product-Cycle có bản hướng dẫn muốn áp dụng, hoặc executable của gói đã cập nhật. `update-skills --project /absolute/product` chỉ đọc, liệt kê skill và file khác biệt. `--skill <tên>` giới hạn phạm vi; `--apply` mới thay file. Với cycle đã khởi tạo, lệnh apply giữ runner lock, từ chối phiên chưa kết thúc và kiểm tra nền tảng ngoài skill trước khi thay; sau đó ghi nhận nền tảng và sự kiện cập nhật. Skill bổ sung cũng được cài. Các skill khác của project không thuộc bundle được giữ nguyên.

Lần cài mới lưu `.agents/.product-cycle-skills.json` để nhận biết bản gốc. Nếu thư mục skill đã thay đổi hoặc không có bản gốc đáng tin cậy, apply dừng trước khi thay bất kỳ skill nào. Xem các file khác biệt và nội dung thực tế; có thể hợp nhất chỉnh sửa thủ công, hoặc chọn rõ `--skill <tên> --replace-customized --apply` để thay toàn bộ skill đó. Bản cũ, gồm file tùy chỉnh, được giữ trong đường dẫn backup mà lệnh trả về. Project cũ có cùng nội dung bundle hiện tại có thể được ghi nhận làm bản gốc; không tự suy bản khác là không có tùy chỉnh. Không dùng hash nền tảng đã ghi nhận làm chứng minh rằng skill đó là bản upstream.

Ví dụ cập nhật phần phân tích và review sau khi đã xem bản khác biệt:

```sh
python3 -m product_cycle update-skills --project /absolute/product --skill product-cycle-analysis --skill product-cycle-review
python3 -m product_cycle update-skills --project /absolute/product --skill product-cycle-analysis --skill product-cycle-review --apply
```

Nếu có xung đột và chủ dự án đã chọn thay các skill trên, thêm `--replace-customized`. Khi phiên bị ngắt, xác nhận không còn writer rồi mới `recover`; không tự dùng recover để bỏ qua phiên đang chạy. Trong chat Codex, yêu cầu đọc lại các skill vừa cập nhật. Lệnh không cập nhật controller executable/server đang chạy, không di chuyển schema/policy/model, không xóa source/lịch sử hay đánh dấu kết quả cũ là đã chạy bằng skill mới. Muốn thử lại một bước dùng skill reset theo phạm vi được chọn. Không tự áp dụng cho mọi project chỉ vì một project đã đồng ý cập nhật.

Một project mới dùng `init --project /absolute/product --brief /absolute/brief.md --name "Tên sản phẩm"`, sau đó `serve --project /absolute/product` để xem dashboard và `run --project /absolute/product` từ terminal khác để thực thi. `init` tự chuẩn bị Git, file loại trừ, hướng dẫn chung và bộ skill trước khi bắt đầu phân tích. Không tự commit/push hoặc đổi Git có sẵn. Mỗi project có kho trạng thái riêng ngoài thư mục worker được ghi.

### Gỡ để cài lại

Trong checkout Product-Cycle, chạy với đường dẫn project sử dụng:

```sh
python3 -m product_cycle uninstall-skills --project /absolute/product
python3 -m product_cycle uninstall-skills --project /absolute/product --apply
python3 -m product_cycle install-skills --project /absolute/product
```

Uninstall chỉ gỡ các skill nằm trong bundle hiện tại khỏi `.agents/skills/` và cập nhật bản ghi phiên bản. Mặc định xem trước; `--apply` chuyển chúng vào `.product-cycle/skill-backups/` cùng bản manifest cũ. Nếu có tùy chỉnh hoặc chưa xác định được bản gốc, cần `--force --apply` để gỡ cả phần đó sau khi xem danh sách. Skill ngoài bundle, Git, mã nguồn, AGENTS.md, coding/common rules, kho trạng thái, token, quyết định và bằng chứng vẫn được giữ. Không gỡ bản CLI đã cài trong môi trường Python. Không dùng uninstall để reset tiến trình; skill reset vẫn nằm trong bundle và được cài lại.

Kết thúc các worker/chat đang thực thi trước khi gỡ hoặc cài. Với cycle đã khởi tạo, CLI giữ runner lock và từ chối queued/running attempt. Sau khi gỡ, nền tảng báo thiếu skill; cài lại ghi nhận bộ skill mới và nền tảng mà không chạy model. Mở chat mới để tránh dùng hướng dẫn còn trong context cũ. Không gọi bootstrap giữa uninstall và reinstall vì bootstrap tự bổ sung skill thiếu.

### Lấy phiên bản workflow mới

Dừng worker và server của project, rồi cập nhật bản clone dùng để cài bằng `git pull --ff-only`. Nếu chạy executable trong môi trường Python, chạy `.venv/bin/python -m pip install --upgrade .` từ clone đó; nếu chạy trực tiếp bằng `python3 -m product_cycle` trong checkout thì bỏ qua bước pip. Tiếp theo preview/apply `update-skills` cho từng project được chọn, xử lý tùy chỉnh bằng các tùy chọn đã mô tả, rồi khởi động dashboard bằng bộ chạy mới và mở chat mới. Không tự pull/reset repo phát triển khi còn thay đổi local. CLI không tự tải bản mới từ mạng hay nâng cấp process đang chạy; các lệnh này tách rõ bộ chạy với skill theo project và không tự thay schema/policy của cycle cũ.

## Các bước nhỏ và mốc thiết kế

Dự án mới hiển thị 9 bước lớn; chuẩn bị project/common là công việc bên trong Phát triển, cấu hình dịch vụ có nhóm riêng; các dự án cũ giữ cấu hình giai đoạn phù hợp. Dashboard hiển thị danh sách đầu việc trong plan ngay khi có đầu ra dự kiến, cùng các bước nhỏ, kiểm tra theo kế hoạch, review và điểm quyết định. Trước khi plan được chấp nhận, phần phát triển hiển thị các bước dự kiến; sau đó mỗi công việc có tiến độ riêng. Tiến độ là tỷ lệ bước được xác nhận, không phải ước lượng thời gian. Số bước có thể tăng khi công việc hoặc lệnh kiểm tra được mở rộng.

Worker dùng `update_plan` khi công cụ sẵn có và giữ mã S1, S2... trong tên bước để truyền tiến độ trực tiếp. Báo completed chỉ hiển thị “Chờ kiểm chứng”. Mỗi bước cần đầu ra liên kết trong work result; reviewer đánh giá riêng bằng bằng chứng. Nếu runtime không gửi cập nhật kế hoạch, các bước chưa có báo cáo giữ trạng thái chờ cho đến khi kết quả về, không tự suy diễn bước đang chạy. Controller xác nhận kiểm tra và quyết định theo dữ liệu thực tế. Phiên cũ không có dữ liệu từng bước hiển thị “Chưa ghi chi tiết”; mở lại tạo revision mới và giữ nguyên lịch sử.

Khối “Phiên thực thi” cho biết controller còn hoạt động hay đã dừng, task hiện tại, pha work/review/check, model/effort, token, thời gian và hoạt động gần nhất. Trạng thái hoạt động dựa trên khóa phiên đang được giữ, không dựa riêng vào trạng thái lưu trong database. Thời điểm hoạt động chỉ xác nhận đã nhận cập nhật, không chứng minh task đã tiến triển hay hoàn tất. Dự án mới chuẩn bị handoff cho Codex App; phiên App Server riêng chỉ dùng khi đã chọn executor đó. Chat được gắn vào đúng task trong lịch sử. Trạng thái native cần quan sát chat đang chạy, không coi lock của watcher là AI đang làm việc. Các phiên được đặt tên theo sản phẩm, công việc và work/review để tìm và mở trong ứng dụng Codex; việc mở lịch sử không tự xác nhận ứng dụng đang nhận luồng cập nhật trực tiếp từ một tiến trình App Server khác. Khi mất kết nối dashboard, không tiếp tục hiển thị trạng thái cũ như một xác nhận đang chạy.

Dashboard đang chạy tự kiểm tra chat của các công việc bị chặn hoặc gián đoạn mỗi 15 giây, khi quy trình không tạm dừng và không có controller khác giữ khóa. Chỉ nhận lượt đã hoàn tất sau lượt được ghi cho đúng task/revision và đúng thư mục dự án. Câu trả lời thường và liên kết file được lưu thành bằng chứng bổ sung; không tự đổi thành nghiệm thu đạt. Kết quả đúng cấu trúc đi qua kiểm tra và review rồi mới cho phép các phụ thuộc chạy. Nếu chat vẫn đang làm việc, controller chờ, không gửi thêm lượt vào chat đó.

Khi nhận thấy chat Codex đang thực thi, dashboard hiển thị hoạt động đó dù controller trước đã dừng. Quan sát hoạt động từ chat hết hiệu lực sau 45 giây nếu không được kiểm tra lại; không coi một trạng thái cũ là bằng chứng phiên vẫn sống.

Trong các dashboard cũ cho phép điều khiển, nút “Tiếp tục quy trình” đồng bộ và khôi phục trước khi chọn việc tiếp theo (`run --continue-blocked`). Chi tiết công việc có “Chỉ đồng bộ kết quả từ Codex” (`sync --task ID`) và “Đồng bộ và tiếp tục công việc” (`continue --task ID`). Tiếp tục dùng chat/đầu ra hiện có, không mở revision mới để né tiêu chí hoặc xóa lịch sử. Lỗi quá tải model được thử lại tối đa hai lần, sau 15 và 30 giây, giữ model/effort đã chọn. Nếu vẫn lỗi, lý do được giữ và lần bấm Tiếp tục sau đó có thể khôi phục. Hết quota, thiếu quyền, thiếu bằng chứng và lỗi sản phẩm không được coi là quá tải. Một task bị chặn không làm dừng các task độc lập đã đủ điều kiện; không bảo đảm hoàn tất khi còn thiếu đầu vào hoặc nghiệm thu thật.

Tiêu chí của đầu việc phải hoàn thành được trong phạm vi và các phụ thuộc đã xong; không yêu cầu chức năng của đầu việc phía sau. `browser_required` đặt ở cấp kế hoạch và áp dụng tại verify, sau các increment cần thiết. Giữ kiểm chứng browser thực tế cho nghiệm thu toàn sản phẩm; hoàn tất coding/review từng increment không thay thế nghiệm thu này. Kết quả bị chặn vẫn giữ đầu ra và lý do cụ thể trong lịch sử, không được coi là hoàn tất.

Dự án mới có gate tại phân tích, UX/UI, mốc trải nghiệm cốt lõi và handoff và review độc lập ở từng giai đoạn trước đó. Design tạo `design.md`, `design-baseline.json` cùng bộ ảnh đăng ký theo từng màn hình, trạng thái và kích thước. Baseline chứa luồng, trạng thái, quy tắc và tiêu chí nghiệm thu. Baseline được review rồi chủ sản phẩm chốt trong Codex trước bước kỹ thuật và coding. Product Design/Image Gen chỉ được sử dụng nếu worker runtime có công cụ tương ứng; việc plugin có sẵn trong desktop không tự cấp nó cho app-server. Ghi rõ khả năng thiếu hoặc dùng reference đã chọn. Không có UI thì ghi hợp đồng tương tác phù hợp. Dự án cũ giữ nguyên gate và hợp đồng của kết quả đã niêm phong.

## Model và giới hạn

`status` trả config và vị trí state. `config.json` trong state có model/effort riêng cho từng role, timeout, ngân sách token, số lần thử, network và các gate. Đổi cấu hình khi không có phiên chạy. Chọn model/effort tài khoản thực tế hỗ trợ. Mỗi attempt giữ cấu hình yêu cầu, thông tin app-server trả lại, thread/turn ID và token khi có.

Dự án mới mặc định chỉ ghi nhận token: `max_turn_tokens` và `max_cycle_tokens` là `null`. Chỉ áp trần khi chủ động đặt số nguyên dương qua `init --max-turn-tokens N --max-cycle-tokens N` hoặc sửa config của phiên đang nghỉ; có thể đặt riêng từng trần. Các dự án cũ giữ số đã cấu hình, đặt `null` nếu muốn bỏ trần đó. Timeout 900 giây mỗi phiên và tối đa 2 lần thử mỗi revision vẫn áp dụng. Đây là lựa chọn vận hành của Product Cycle, không phải mức token do OpenAI quy định.

Mặc định cho dự án mới:

| Vai trò | Model | Effort |
|---|---|---|
| Phân tích, UX/UI, kiến trúc | `gpt-6-astra` | `medium` |
| Kế hoạch, thiết lập dự án, cấu hình dịch vụ, phát triển, nghiệm thu, bàn giao, retro | `gpt-6.1-sol` | `medium` |
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

`pause` trong Codex có hiệu lực tại ranh giới công việc; lượt đang chạy hoàn tất. `resume` bỏ tạm dừng; `run` tiếp tục. Ctrl-C dừng controller và process group Codex; phiên không hoàn tất không trở thành done.

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

## Repository, coding rules và phần dùng chung

`init` chuẩn bị một repository độc lập. Repo đã có giữ nguyên nhánh, remote, danh tính, lịch sử và công việc chưa commit. Thư mục chứa code đang được repo cha theo dõi phải chọn repo gốc để tránh tạo nested repo sai. File .env đang được Git theo dõi khiến bootstrap dừng; người vận hành xử lý index, không xóa file local.

`AGENTS.md` trỏ tới `PRODUCT_CYCLE_RULES.md`. Hướng dẫn đã có và skill tùy chỉnh được giữ nguyên. Controller ghi hash hướng dẫn/skill và kiểm tra trước phiên; thay đổi chưa được ghi nhận sẽ chặn chạy. `bootstrap --project ...` ghi nhận thay đổi sau khi đã kiểm tra, khi không có phiên đang chạy. Dashboard hiển thị trạng thái chuẩn bị và Git thực tế; mỗi phiên lưu quan sát repository.

Thiết kế kỹ thuật tạo project-setup.json: stack, cấu trúc, coding rules, công cụ format/lint/typecheck/test (hoặc lý do không cần), common_components, environment_names, instructions và checks. Sau plan, công việc chuẩn bị project/common bên trong Phát triển tạo CODING_RULES.md, runtime, dependency, script, phần dùng chung và mẫu môi trường theo thiết kế. Chỉ cho task chức năng và cấu hình dịch vụ chạy sau checks/review thành công. Coding rules không được sửa âm thầm trong task chức năng; mở lại bước thiết lập để review thay đổi.

Không ép một stack hoặc cài sẵn mọi hạ tầng cho mọi sản phẩm. Graphify chỉ cân nhắc khi code hiện có đủ phức tạp để cần bản đồ quan hệ, sau khi architecture ghi lý do; không phải bước bắt buộc.


## Thực thi trong Codex App

Mặc định mới: executor=codex-desktop, dashboard_read_only=true, gates gồm analysis/design/handoff; plan thêm gate ở task trải nghiệm cốt lõi. Cấu hình vẫn là file trong kho state riêng từng project. Không sửa file để tự tạo quyền hoặc giả quyết định. Dashboard từ chối mọi POST khi ở chế độ chỉ đọc; các nút review tài liệu vẫn hoạt động.

`run` trả công việc native cùng prompt, đường dẫn kết quả, title và model/effort yêu cầu. Phiên Codex dùng skill điều phối để gắn chat, thực thi, ghi tiến độ và gửi kết quả. Controller chạy checks và chuẩn bị review riêng. Xem [hướng dẫn vòng native](../skills/product-cycle/references/operating-guide.md#native-codex-loop) cho desktop-bind, desktop-progress, desktop-submit và owner-input. Nếu thiếu phiên reviewer độc lập có thể gắn, dừng với lý do cụ thể; không dùng chính worker để review.

`configure --project ... --executor codex-desktop` chuyển cycle cũ khi không còn phiên đang chạy. Giữ nguyên kết quả và gate cũ. Áp dụng phân tích/thiết kế cộng tác cho sản phẩm cũ phải mở lại phạm vi có sự đồng ý của chủ sản phẩm; không retroactively tạo quyết định.

Token native được đọc từ bộ đếm trong session local do Codex ghi khi có, kiểm tra đúng chat/project. Khi gắn chat, ghi baseline; các lần đồng bộ cập nhật phần tăng thêm và không cộng trùng. Đây là đường đọc tương thích theo phiên bản, không phải API billing. Baseline hoặc bộ đếm thiếu hiển thị chưa đầy đủ. Model/effort yêu cầu trong packet không chứng minh Codex App đã áp dụng nó; dữ liệu chưa quan sát giữ là chưa ghi nhận. Ngân sách native chỉ kiểm tra tại ranh giới dispatch, không tự ngắt lượt đang chạy trong ứng dụng.

## Bộ màn hình và sơ đồ trên dashboard

Dự án mới bật `screen_design_required: true`. Hợp đồng trong [screen-design.md](../product_cycle/resources/screen-design.md) định nghĩa `screens`, tài nguyên và đường chuyển của baseline; kế hoạch khai `screen_targets` cho mỗi task UI. Mẫu được chủ sản phẩm duyệt trong Codex. Build và Verify phải đăng ký ảnh giao diện thật và `screen-comparisons.json`, đúng phiên bản mẫu, hash ảnh và fingerprint source. Review độc lập phải dẫn báo cáo và các ảnh thật ngoài bằng chứng chức năng. Ảnh và báo cáo không chứng minh thao tác tương tác đã hoạt động; kiểm chứng trình duyệt cuối vẫn áp dụng riêng.

Mục **Quy trình** nối giai đoạn → công việc → bước nhỏ; nét đứt là phụ thuộc thật giữa công việc. Có kéo nền, thu phóng, vừa khung, toàn màn hình, ẩn/hiện thanh trái và chi tiết phải. Mục **Màn hình & luồng** hiển thị ảnh từng trạng thái và đường chuyển; chọn một ảnh để xem mẫu cạnh ảnh giao diện thật và công việc liên quan. Dashboard đọc bằng chứng đã ghi, không tự tạo quyết định duyệt.

Cycle cũ không tự đổi hợp đồng hoặc ghi lại lịch sử thành đã duyệt bộ ảnh. Nếu chưa có `screens`, dashboard báo rõ thiếu bộ ảnh. Để áp dụng cho cycle cũ, cài cập nhật workflow theo quy tắc giữ file hiện có, bật `screen_design_required` rồi mở lại Design và các phần phụ thuộc trong Codex; phải tạo và duyệt bộ thiết kế mới trước khi chạy kế hoạch mới. Không sửa bằng chứng đã niêm phong để lấp phần thiếu.
