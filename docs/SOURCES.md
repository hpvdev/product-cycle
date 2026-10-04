# Nguồn OpenAI và cách áp dụng

Đối chiếu ngày 03/10/2026. Product Cycle là gói do chúng tôi thiết kế, không phải sản phẩm hoặc quy trình nội bộ chuẩn hóa của OpenAI. Tên file/trạng thái là quy ước của gói.

| Nguồn | Điều áp dụng |
|---|---|
| [Iterating Development Workflows](https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex) | Tách kế hoạch, ngữ cảnh quyết định và lịch sử thực tế; tiêu chí quan sát được. Các tên file và human gate trong cookbook là quy ước có thể điều chỉnh. |
| [Codex App Server](https://learn.chatgpt.com/docs/app-server) | Phiên, model/effort, sự kiện và trạng thái thực thi |
| [Model selection](https://developers.openai.com/api/docs/guides/model-selection) | Chọn model theo độ khó, chất lượng và hiệu suất; phân vai Astra/Sol và effort cụ thể trong gói là cấu hình khởi đầu của Product Cycle, chưa được tối ưu bằng so sánh trên dự án thật |
| [Build skills](https://developers.openai.com/plugins/build/skills) | Đóng gói hướng dẫn và tài liệu theo nhu cầu |
| [Rethinking skills and prompts](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) | Hướng dẫn ngắn, ngữ cảnh liên quan, quy trình phù hợp quy mô |
| [Building Consistent Workflows](https://developers.openai.com/cookbook/examples/codex/codex_mcp_agents_sdk/building_consistent_workflows_codex_cli_agents_sdk) | Ví dụ phân vai, kiểm tra đầu ra trước chuyển bước và ghi trace; không chứng minh bộ này tự động hoàn chỉnh |
| [Testing Agent Skills with Evals](https://developers.openai.com/blog/eval-skills) | Đánh giá đầu ra, quá trình và hiệu suất |
| [Evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals) | Trace chẩn đoán và tình huống lặp lại để so sánh |
| [Agent Improvement Loop](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop) | Thực thi, phản hồi, eval và cải thiện |

Nguồn là nền tảng thiết kế, không chứng minh gói đạt chất lượng trên mọi dự án. Kiểm tra controller, adapter thật và áp dụng dự án là ba mức xác minh riêng.

## Frontend hiện hành

Đối chiếu ngày 04/10/2026: đóng gói [Frontend App Builder](https://github.com/openai/plugins/tree/5fd93af4cd0c623e020d0cc7e9ce178b4ac1f70f/plugins/build-web-apps/skills/frontend-app-builder) từ repo `openai/plugins`, commit `5fd93af4cd0c623e020d0cc7e9ce178b4ac1f70f`, là HEAD được quan sát khi cập nhật. Giữ nguyên skill, metadata và reference nguồn. Phiên bản được cố định để tái lập; không tuyên bố luôn là mới nhất về sau hoặc là một thay thế được OpenAI xác nhận.

Không đóng gói `frontend-skill` đã bị gỡ khỏi danh sách curated của `openai/skills`. [Hướng dẫn model hiện hành](https://developers.openai.com/api/docs/guides/latest-model) và [Rethinking skills and prompts](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) là nguồn để cập nhật prompting và giữ hướng dẫn đúng phạm vi. Product Cycle chỉ nạp hướng dẫn frontend cho công việc có UI; quyết định chủ sản phẩm, mẫu đã duyệt, stack và bằng chứng của workflow vẫn là chuẩn. Gen thêm concept khi chi tiết mới chưa rõ, tái sử dụng hệ thiết kế khi đã rõ; so sánh ảnh render thật trong phạm vi kiểm chứng được phép. Đây là cách tích hợp của Product Cycle, chưa chứng minh sản phẩm đầu ra đẹp hoặc đạt nghiệm thu.

## Phân tích sản phẩm: phương pháp và kinh nghiệm cộng đồng

Đối chiếu ngày 04/10/2026. Bước 01 dùng các phương pháp sau để cải thiện phỏng vấn và review nội dung, giữ nguyên năm bước nhỏ và schema hiện tại:

| Nguồn | Điều áp dụng |
|---|---|
| [Jobs to Be Done — Christensen Institute](https://www.christenseninstitute.org/theory/jobs-to-be-done/) | Làm rõ hoàn cảnh và tiến bộ người dùng mong muốn, gồm cả nhu cầu cảm xúc; tránh suy nhu cầu từ tên loại ứng dụng. |
| [Story-based interviews — Product Talk](https://www.producttalk.org/story-based-customer-interviews/) | Khai thác một tình huống đã xảy ra và hỏi tiếp theo câu trả lời. Phân biệt trải nghiệm trực tiếp với hình dung của chủ sản phẩm. |
| [Opportunity Solution Trees — Product Talk](https://www.producttalk.org/opportunity-solution-trees/) | Nối kết quả mong muốn, nhu cầu, giải pháp và giả định cần thử. Với dữ liệu còn thiếu, dùng bản đồ giả thuyết ngắn; không gọi là cơ hội đã được xác thực. |
| [Brainstorming — obra/superpowers](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md) | Tham khảo đối thoại thích ứng, phản ánh lại ý định, so sánh phương án và giữ quyết định của con người. Không cài gói hoặc sao chép quy tắc tự commit, phân loại, gate hay phương thức thực thi của họ. |
| [Product discovery flow — r/ProductManagement](https://www.reddit.com/r/ProductManagement/comments/1oevcrc/whats_your_product_discovery_flow/) | Kinh nghiệm cộng đồng về bắt đầu từ vấn đề/kết quả và dùng AI tổng hợp dữ kiện. Đây là chia sẻ cá nhân, không phải đồng thuận, nghiên cứu người dùng của dự án hay chuẩn OpenAI. |
| [Let Claude interview you — Anthropic](https://code.claude.com/docs/en/best-practices#let-claude-interview-you) | Phỏng vấn trước khi viết đặc tả, khai thác đánh đổi và điểm chưa rõ. Công cụ hỏi đáp cụ thể phụ thuộc runtime; Product Cycle tiếp tục dùng chat Codex. |

Rubric review S1–S5/C1–C2 và cách tách quyết định đã chốt, đề xuất, câu hỏi mở, giả định để kiểm chứng là thiết kế tích hợp của Product Cycle. Đây là cải tiến hướng dẫn, chưa chứng minh AI sẽ phân tích sâu hoặc sản phẩm đạt chất lượng trên dự án thật. Không áp đặt số cuộc phỏng vấn, số câu hỏi, số phương án hay khảo sát thị trường cho mọi sản phẩm.

## Phân biệt nguồn và quyết định của gói

**Có nguồn OpenAI:** mục tiêu và tiêu chí đo được; công việc có phạm vi và phụ thuộc; kế hoạch khác với bằng chứng đã quan sát; giữ quyết định/ngữ cảnh để tiếp tục; đánh giá skill bằng kết quả, quá trình, phong cách và hiệu suất. Cookbook là ví dụ có thể điều chỉnh, không phải một quy trình SDLC duy nhất được OpenAI chứng nhận.

**Thiết kế riêng theo yêu cầu người dùng:** 9 bước lớn với chuẩn bị project/common nằm trong Phát triển, SQLite và tên trạng thái; Git và common rules lúc init; thiết lập dự án/coding rules sau kỹ thuật/plan, trước tính năng; cấu hình dịch vụ sau bước thiết lập; chỉ chặn đầu việc phụ thuộc dịch vụ thiếu; bàn giao local; để VPS và phát hành ra ngoài lại; review độc lập mỗi bước và chủ sản phẩm chốt phân tích, thiết kế, bản trải nghiệm cốt lõi và handoff. Việc chọn các mốc này là thiết kế riêng theo mức tham gia người dùng mong muốn, không được trình bày như khuyến nghị phổ quát của OpenAI.

**Cần kiểm chứng thêm:** chọn model/effort tối ưu, worker thật thao tác các tab đã đăng nhập, kết nối dịch vụ thật, kiểm thử UI/mobile tự động, sửa lỗi xuyên suốt và chất lượng bàn giao của một sản phẩm thực tế. Test cơ chế và demo tổng hợp chưa chứng minh các khả năng này. Không tự nâng mức xác nhận chỉ vì có skill hay dashboard.

Graphify là công cụ bên thứ ba, không phải khuyến nghị OpenAI. [Repository chính thức](https://github.com/Graphify-Labs/graphify) mô tả code graph local và hỗ trợ Codex; gói chỉ coi đây là lựa chọn theo độ phức tạp code, chưa cài hoặc kiểm chứng tích hợp.


| [Claude Code best practices](https://code.claude.com/docs/en/best-practices) | Phỏng vấn trước khi viết đặc tả cho tính năng lớn; tìm hiểu, lập kế hoạch rồi triển khai; kiểm chứng bằng kết quả thực tế. Áp dụng nguyên tắc, không tuyên bố Product Cycle là một quy trình chuẩn chính thức. |

Bổ sung cộng tác theo yêu cầu: product-direction và mốc trải nghiệm cốt lõi là hợp đồng của gói này. Tài liệu OpenAI PLANS.md hỗ trợ prototype, mốc có hành vi kiểm chứng được và cập nhật quyết định; tài liệu workflow cookbook hỗ trợ phân biệt đầu ra dự kiến với bằng chứng quan sát và cải tiến từ thất bại. Những nguồn này không bảo đảm sản phẩm độc đáo hay thành công thị trường.
