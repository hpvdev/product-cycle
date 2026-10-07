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

## Mở công ty trước, rồi giao yêu cầu

Trong chat Codex, dùng skill `product-cycle-onboard` và chọn thư mục dự án. Chưa cần mô tả sản phẩm đầy đủ:

```sh
product-cycle onboard --project /absolute/new-project --name "Công ty của tôi" --open
```

Lệnh chuẩn bị Git, rules và skills rồi mở dashboard trên cổng trống, trả đúng link dự án. Nhân viên hiện “Chờ nhận yêu cầu”; chưa có worker chạy. Bạn xem văn phòng trước, sau đó mô tả sản phẩm trong chat Codex. AI lưu mô tả thật, rồi thực hiện:

```sh
product-cycle onboard --project /absolute/new-project --brief /absolute/request.md --start
product-cycle onboard --project /absolute/new-project
```

Bộ điều phối mới bắt đầu giao việc. BA phân tích và review theo chế độ đã chọn; brief ban đầu chưa phải đặc tả được chấp nhận. Project có sẵn giữ nguyên chính sách và lịch sử. Một process vừa khởi động chưa chứng minh đội ngũ đang chạy; bản ghi phiên và trạng thái kết nối xác nhận hoạt động.

Dashboard nhận cập nhật trực tiếp qua kết nối sự kiện, tự kết nối lại với trạng thái đầy đủ và báo khi dữ liệu có thể đã cũ. Trạng thái công ty, danh sách nhân viên/chức danh, công việc và hoạt động đã ghi nhận hiện rõ mà không phụ thuộc zoom. Chỉ tạo link phiên khi có danh tính thật; phiên App Server chưa được xác nhận xuất hiện trong danh sách chat Codex App. Chưa có công cụ hoặc dữ liệu thật thì không giả lập hoạt động.

## Đội ngũ tự động và văn phòng

Chọn chế độ đội ngũ khi tạo dự án để bộ điều phối chạy nền qua Codex App Server:

```sh
python3 -m product_cycle init --project /absolute/product --brief /absolute/brief.md --name "Tên sản phẩm" --team
python3 -m product_cycle serve --project /absolute/product --port 8788
# Chạy trong terminal khác, giữ process hoạt động:
python3 -m product_cycle supervise --project /absolute/product
```

Dashboard mở ở màn hình văn phòng: chọn nhân viên để xem việc được giao, các bước, phiên Codex, mức sử dụng đã ghi nhận, đầu ra và trao đổi. Có thể thu gọn panel, kéo/phóng to văn phòng và lọc lịch sử trao đổi. Nhân vật và đường trao đổi phản ánh bản ghi hoạt động; ảnh minh họa không chứng minh AI đang chạy. Các trang kế hoạch, quy trình và bằng chứng vẫn được giữ.

Supervisor độc lập với dashboard, tự giao việc đủ đầu vào, kiểm tra, mở review độc lập và xử lý sửa lại theo chính sách. `max_concurrent = 0` cho phép giao việc theo nhu cầu, không đặt trần phiên cố định của project; giá trị dương giữ giới hạn đã chọn. Giới hạn nhà cung cấp vẫn có hiệu lực. Worker được phép dùng workspace riêng có thể chạy song song; source chung chỉ có một writer tích hợp. Không mở mọi vị trí chỉ để làm văn phòng trông bận rộn.

Với chính sách công ty `autonomous` được chọn rõ, BA tự phân tích brief và ghi rõ giả định hợp lý trong phạm vi đã giao, không bắt buộc phỏng vấn hay duyệt phân tích; review độc lập vẫn bắt buộc. Sau khi phân tích được review chấp nhận, Design Director và Art Director chọn thiết kế trong phạm vi đã chốt; triển khai, kiểm chứng và review độc lập vẫn bắt buộc. Quyết định của công ty không được ghi thành người dùng đã duyệt. Nghiệm thu cuối của người dùng là tùy chọn theo chính sách này. Chế độ `supervised` và project cũ giữ nguyên các gate đã cấu hình cho đến khi người dùng đổi chính sách. Các câu hỏi còn thiếu có lý do, lựa chọn và đề xuất; dashboard chỉ đọc, câu trả lời và quyết định được ghi qua Codex hoặc luồng chủ sản phẩm được hỗ trợ.

Máy và supervisor phải hoạt động để tiếp tục khi đóng trình duyệt. `team-status` xem trạng thái, `team-stop` yêu cầu dừng. Xem [cách vận hành đội ngũ](skills/product-cycle/references/team-operation.md) và [nhiệm vụ các vị trí](skills/product-cycle/references/company-roles.md). Task trong plan có thể chọn `worker` là `build`, `frontend`, `backend`, `mobile` hoặc `game_engineer`; lựa chọn này chỉ đổi chuyên môn thực hiện, giữ nguyên phạm vi, tiêu chí và ranh giới workspace/tích hợp. Chế độ đội ngũ và chính sách công ty cần được chọn rõ; project đang chạy không tự đổi chế độ.

`init` tự chuẩn bị Git nếu chưa có, bổ sung `.gitignore`, tạo `AGENTS.md`/`PRODUCT_CYCLE_RULES.md` và cài bộ skill theo project, gồm Frontend App Builder từ repo OpenAI hiện hành và skill làm lại quy trình `product-cycle-reset`. Giữ nguyên Git, hướng dẫn và skill đã có; không tự commit/push. Thiết kế kỹ thuật tạo `project-setup.json`; công việc chuẩn bị bên trong Phát triển tạo coding rules theo stack, cấu trúc code, môi trường, công cụ kiểm tra và phần dùng chung trước mọi task chức năng. State và bằng chứng đã chốt nằm ở `~/.local/share/product-cycle`, ngoài vùng AI được ghi. `PRODUCT_CYCLE_HOME` đổi nơi lưu; giữ nguyên trong một cycle. `PRODUCT_CYCLE_CODEX` chọn binary nếu Codex không nằm trong PATH.

Dự án mới xác định màn hình, trạng thái và đường chuyển trước khi coding. Mỗi trạng thái được mô tả và liên kết ảnh tham chiếu; trạng thái chỉ đổi chữ/số/nút có thể dùng chung ảnh. Ảnh Image Gen được chọn có thể trực tiếp làm baseline; Figma tùy chọn, không dựng HTML/CSS hay chạy server chỉ để tạo ảnh thiết kế. Kích thước ảnh không phải gate tuyệt đối; design.md xác định viewport mục tiêu, responsive và các chỉnh sửa nhãn/ký hiệu. Mỗi task UI gắn với đúng màn hình, trạng thái, kích thước và phiên bản mẫu; khi code phải có ảnh giao diện thật và báo cáo đối chiếu, đồng thời kiểm tra logic theo đặc tả. Frontend App Builder hỗ trợ concept, thi công và đối chiếu ảnh UI thật. Bộ cài giữ phiên bản nguồn được ghi trong [SOURCES](docs/SOURCES.md), không tự tải bản mới mỗi lần chạy. Việc cài skill và qua test controller chưa chứng minh chất lượng thị giác của sản phẩm.

## Công cụ native cho công ty

App Server không mặc nhiên có ImageGen hay công cụ trình duyệt của Codex Desktop. Khi worker thiếu công cụ thật, nó gửi yêu cầu qua công cụ được phiên đó cung cấp và chờ ở ranh giới task. Khởi động supervisor bằng lệnh ở trên; trong chat Codex Desktop đang dùng cho đúng project, người dùng cho phép xử lý các yêu cầu công cụ, chẳng hạn: “Dùng $product-cycle-company-worker để xử lý yêu cầu native của project /absolute/product trong chat này, trong phạm vi đã giao.” Chat đọc [skill worker](skills/product-cycle-company-worker/SKILL.md) và hàng đợi:

```sh
python3 -m product_cycle company-work --project /absolute/product
```

Worker xác nhận danh tính chat thật, claim và bind job trước khi dùng ImageGen hoặc CUA thực sự có trong chat, rồi gửi file, hash, prompt và quan sát thật theo hợp đồng. Công cụ thiếu thì báo thiếu, không tạo ảnh hoặc ảnh chụp giả. Kết quả công cụ cần được worker và reviewer đánh giá; gửi file thành công chưa phải thiết kế đạt, test pass hay người dùng duyệt. Không cần tạo chat khác hoặc supervisor thứ hai. Chat native phải đang hoạt động để làm việc; đóng chat không biến nó thành dịch vụ công cụ chạy nền. Lần chạy bị gián đoạn có kết quả chưa rõ cần đối chiếu trước khi thực hiện lại.

## Cải tiến có bằng chứng

Trong chính sách công ty tự chủ, Process Lead chọn vấn đề thực sự đã quan sát; Skill Engineer đề xuất hướng dẫn nhỏ, Evaluation Engineer đánh giá cùng tình huống đầu vào trước và sau, rồi Improvement Reviewer độc lập kiểm tra phiên bản và kết quả thật. Xem [hợp đồng cải tiến](skills/product-cycle-improve/SKILL.md). Controller chỉ áp dụng phạm vi hướng dẫn đủ điều kiện ở điểm ổn định, giữ bản gốc, bảo vệ tùy chỉnh, ghi phiên bản và đường khôi phục. Retro thông thường vẫn trả đề xuất; worker không tự sửa skill đã cài để vượt qua review.

```sh
python3 -m product_cycle company-improvements --project /absolute/product
```

Dashboard quan sát câu hỏi, đề xuất, trạng thái đánh giá/review, hướng dẫn trước/sau và bằng chứng phiên bản. Một đề xuất được review chưa đồng nghĩa đã áp dụng. Theo dõi và khôi phục cũng cần trạng thái và bằng chứng thực; test cấu trúc hoặc dữ liệu tổng hợp không chứng minh quyết định tốt hơn hay sản phẩm đạt chất lượng. Cải tiến không được đổi mục tiêu, mở rộng quyền hay hạ tiêu chí nghiệm thu. Skill giúp hướng dẫn và sử dụng công cụ tốt hơn; không tăng năng lực nền của model hoặc bảo đảm chất lượng. Không tự chạy sản phẩm thật hay thao tác tài khoản ngoài chỉ để thử đề xuất.

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

Chế độ tuần tự và chế độ đội ngũ có chính sách riêng; không tự merge/deploy/thông báo bên ngoài/theo dõi production. Công cụ native chỉ chạy trong chat đã được cho phép, không được suy từ khả năng của runtime khác. Cải tiến hướng dẫn chỉ được áp dụng qua hợp đồng và review đã mô tả, không phải mọi đề xuất retro đều tự chạy. Lệnh kiểm tra chạy cục bộ ngoài sandbox Codex, nên cần lệnh tin cậy thuộc phạm vi đã cấp phép và được review. Test controller không chứng minh kết nối nhà cung cấp hoặc toàn bộ sản phẩm được giao tự chủ; chất lượng cần đầu ra thật và kiểm chứng thích hợp của phiên bản hiện tại.

Đọc [quy trình](docs/WORKFLOW.md), [kiến trúc](docs/ARCHITECTURE.md), [vận hành](docs/RUNBOOK.md), [đánh giá](evals/README.md).

## Agent workflow 0.4

Cycle live mới có thêm Feature Map trước plan và task tích hợp sau mỗi increment. Kiến trúc cung cấp verification.json; plan gắn feature, procedure và dependency; context pack giữ quyền, quyết định và provenance đã chốt. Builder dùng đúng source_root, review độc lập kiểm chứng bản đó, controller tích hợp rồi kiểm chứng source chung. Whole-product verify vẫn cần hành trình tổng và bằng chứng đúng bản bàn giao.

Cycle cũ không tự đổi hợp đồng. Xem ảnh hưởng rồi áp dụng khi idle:

```sh
python3 -m product_cycle upgrade-workflow --project /absolute/product
python3 -m product_cycle upgrade-workflow --project /absolute/product --apply
python3 -m product_cycle configure --project /absolute/product --workspace-mode isolated
```

Nâng cấp làm các bước bị ảnh hưởng thành stale, giữ lịch sử và model/gate cũ. Cập nhật skill là thao tác riêng cho project được chọn. Routing có thể cấu hình bằng configure --routing-file; profile/capability đã khai báo chưa chứng minh công cụ thực sự kết nối. Instance dùng chung giữ reservation cả khi kết quả phiên chưa rõ. Cải tiến chạy trial có giới hạn, judge nhận opaque labels, reviewer độc lập quyết định; thiếu held-out cases được ghi thành giới hạn. Test controller dùng dữ liệu tổng hợp, không chứng minh chất lượng sản phẩm hay lợi ích của skill trên model thật.
