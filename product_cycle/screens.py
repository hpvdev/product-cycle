"""Screen references and observed comparisons; structural checks do not judge beauty."""

import struct

from .contracts import require

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def image_size(path):
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24 and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        position = 2
        while position + 4 <= len(data):
            if data[position] != 255:
                break
            marker = data[position + 1]
            if marker == 255:
                position += 1
                continue
            size = int.from_bytes(data[position + 2:position + 4], "big")
            if marker in {192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 205, 206, 207} and size >= 7 and position + 9 <= len(data):
                height, width = struct.unpack(">HH", data[position + 5:position + 9])
                return width, height
            if size < 2:
                break
            position += size + 2
    if len(data) >= 30 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = data[12:16]
        if kind == b"VP8X":
            return int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1
        if kind == b"VP8L" and data[20] == 47:
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 16383) + 1, ((bits >> 14) & 16383) + 1
        if kind == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
            width, height = struct.unpack("<HH", data[26:30])
            return width & 16383, height & 16383
    require(False, "Chưa đọc được ảnh màn hình; hãy lưu lại ảnh PNG, JPEG hoặc WebP hợp lệ.")


def target_key(target):
    viewport = target.get("viewport")
    require(isinstance(viewport, dict) and all(type(viewport.get(key)) is int and viewport[key] > 0
            for key in ["width", "height"]), "Mẫu màn hình cần kích thước hiển thị cụ thể.")
    require(text(target.get("screen_id")) and text(target.get("state")), "Cần xác định màn hình và trạng thái để đối chiếu.")
    return target["screen_id"], target["state"], viewport["width"], viewport["height"]


def design_targets(baseline):
    return [dict(ref, screen_id=screen["id"], screen_name=screen["name"])
            for screen in baseline.get("screens", []) for ref in screen["references"]]


def validate_screen_design(baseline, requirements, artifacts):
    require(text(baseline.get("version")), "Bộ thiết kế cần phiên bản để các công việc dùng đúng mẫu.")
    screens = baseline.get("screens")
    require(isinstance(screens, list), "Bộ thiết kế cần danh sách màn hình.")
    if not baseline["has_ui"]:
        require(not screens, "Sản phẩm không có giao diện dùng danh sách màn hình rỗng.")
        return
    require(screens, "Thiết kế cần xác định các màn hình trước khi phát triển.")
    ids, states_by_screen = set(), {}
    for screen in screens:
        require(isinstance(screen, dict) and text(screen.get("id")) and text(screen.get("name")), "Mỗi màn hình cần mã riêng và tên dễ đọc.")
        require(screen["id"] not in ids, "Danh sách màn hình có mã bị trùng.")
        ids.add(screen["id"])
        links = screen.get("requirements")
        require(isinstance(links, list) and links and all(text(rid) for rid in links) and set(links) <= requirements,
                "Mỗi màn hình cần liên kết với yêu cầu đã chốt.")
        states = screen.get("states")
        require(isinstance(states, list) and states and all(isinstance(state, dict) and
                all(text(state.get(key)) for key in ["id", "name", "description"]) for state in states),
                "Màn hình cần các trạng thái, nội dung và hành vi cụ thể.")
        state_ids = {state["id"] for state in states}
        require(len(state_ids) == len(states), "Trạng thái màn hình có mã bị trùng.")
        states_by_screen[screen["id"]] = state_ids
        refs = screen.get("references")
        require(isinstance(refs, list) and refs and all(isinstance(ref, dict) for ref in refs), "Mỗi màn hình cần ảnh thiết kế để xem trước.")
        keys = []
        for ref in refs:
            keys.append(target_key(dict(ref, screen_id=screen["id"])))
            require(text(ref.get("image")) and ref["state"] in state_ids and ref["image"] in artifacts and
                    artifacts[ref["image"]].suffix.lower() in IMAGE_SUFFIXES,
                    "Mẫu phải là ảnh đã đăng ký, đúng trạng thái của màn hình.")
            require(image_size(artifacts[ref["image"]]) == keys[-1][2:], "Ảnh thiết kế cần đúng kích thước hiển thị đã ghi.")
        require(len(set(keys)) == len(keys) and {ref["state"] for ref in refs} == state_ids,
                "Bộ ảnh cần bao phủ từng trạng thái đã thiết kế, không trùng mẫu.")
        assets = screen.get("assets")
        require(isinstance(assets, list) and all(isinstance(asset, dict) and text(asset.get("name")) and
                text(asset.get("usage")) and text(asset.get("path")) and asset["path"] in artifacts for asset in assets),
                "Hình minh họa cần tài nguyên riêng đã đăng ký; dùng danh sách rỗng khi không cần.")
    for screen in screens:
        transitions = screen.get("transitions")
        require(isinstance(transitions, list), "Mỗi màn hình cần mô tả đường chuyển và tương tác.")
        for edge in transitions:
            require(isinstance(edge, dict) and text(edge.get("action")) and
                    all(text(edge.get(field)) for field in ["from_state", "to_screen", "to_state"]) and
                    edge["from_state"] in states_by_screen[screen["id"]] and edge["to_screen"] in ids and
                    edge.get("to_state") in states_by_screen[edge["to_screen"]],
                    "Đường chuyển cần thao tác và trạng thái đích có trong bộ thiết kế.")


def validate_screen_plan(plan, baseline):
    expected = {target_key(target) for target in design_targets(baseline)}
    covered = set()
    for task in plan["tasks"]:
        targets = task.get("screen_targets", [] if not expected else None)
        require(isinstance(targets, list) and all(isinstance(target, dict) for target in targets),
                "Mỗi đầu việc cần chỉ rõ mẫu màn hình; dùng danh sách rỗng cho công việc không có giao diện.")
        keys = [target_key(target) for target in targets]
        require(len(keys) == len(set(keys)) and set(keys) <= expected, "Công việc đang tham chiếu mẫu màn hình không có trong thiết kế.")
        covered.update(keys)
    require(covered == expected, "Kế hoạch cần bao phủ toàn bộ màn hình, trạng thái và kích thước đã thiết kế.")
    require(not expected or plan.get("browser_required") is True, "Sản phẩm có giao diện cần kiểm chứng thực tế trước khi nghiệm thu.")


def validate_screen_comparisons(report, baseline, targets, artifacts, fingerprint, digest, reference_records, blocked=False):
    require(report.get("baseline_version") == baseline["version"], "Kết quả đối chiếu đang dùng phiên bản thiết kế khác.")
    require(report.get("source_fingerprint") == fingerprint, "Giao diện đã thay đổi; cần chụp và đối chiếu lại bản hiện tại.")
    rows = report.get("comparisons")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "Cần kết quả đối chiếu theo từng mẫu màn hình.")
    expected = {target_key(target): target for target in targets}
    keys = [target_key(row) for row in rows]
    require(len(keys) == len(set(keys)) and set(keys) <= set(expected), "Kết quả đối chiếu cần đúng mẫu được giao, không trùng.")
    require(blocked or set(keys) == set(expected), "Chưa có ảnh giao diện thật để đối chiếu đầy đủ các mẫu được giao.")
    for row, key in zip(rows, keys):
        target = expected[key]
        ref = reference_records.get(target["image"])
        require(ref and row.get("reference_sha256") == ref["sha256"], "Cần đối chiếu đúng nội dung ảnh thiết kế đã duyệt.")
        rendered = row.get("rendered_image")
        require(text(rendered) and rendered in artifacts and artifacts[rendered].suffix.lower() in IMAGE_SUFFIXES,
                "Ảnh giao diện thật cần được lưu và đăng ký làm bằng chứng.")
        require(image_size(artifacts[rendered]) == key[2:], "Ảnh giao diện thật cần cùng kích thước với mẫu thiết kế.")
        require(digest(artifacts[rendered]) != ref["sha256"], "Ảnh giao diện thật phải được chụp từ sản phẩm, không dùng lại ảnh thiết kế.")
        require(row.get("status") in {"matched", "needs_changes"} and isinstance(row.get("observations"), list) and
                row["observations"] and all(text(note) for note in row["observations"]),
                "Đối chiếu cần nhận xét cụ thể về bố cục, chữ, màu, hình ảnh và tương tác.")
        require(blocked or row["status"] == "matched", "Giao diện còn sai lệch với mẫu; sửa và đối chiếu lại trước khi hoàn tất.")
