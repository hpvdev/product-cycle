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

## Phân biệt nguồn và quyết định của gói

**Có nguồn OpenAI:** mục tiêu và tiêu chí đo được; công việc có phạm vi và phụ thuộc; kế hoạch khác với bằng chứng đã quan sát; giữ quyết định/ngữ cảnh để tiếp tục; đánh giá skill bằng kết quả, quá trình, phong cách và hiệu suất. Cookbook là ví dụ có thể điều chỉnh, không phải một quy trình SDLC duy nhất được OpenAI chứng nhận.

**Thiết kế riêng theo yêu cầu người dùng:** 9 giai đoạn, SQLite và tên trạng thái; cấu hình dịch vụ sau phân tích/UX/UI/kỹ thuật/plan; chỉ chặn đầu việc phụ thuộc dịch vụ thiếu; bàn giao local; để VPS và phát hành ra ngoài lại; review độc lập mỗi bước và chủ sản phẩm nghiệm thu tại handoff. Cookbook có ví dụ human gate từng phase; việc giảm các gate trong gói này là lựa chọn riêng, không được trình bày như khuyến nghị phổ quát của OpenAI.

**Cần kiểm chứng thêm:** chọn model/effort tối ưu, worker thật thao tác các tab đã đăng nhập, kết nối dịch vụ thật, kiểm thử UI/mobile tự động, sửa lỗi xuyên suốt và chất lượng bàn giao của một sản phẩm thực tế. Test cơ chế và demo tổng hợp chưa chứng minh các khả năng này. Không tự nâng mức xác nhận chỉ vì có skill hay dashboard.
