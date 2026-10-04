"""Install the bundled skills without replacing project customizations."""

import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path

from .contracts import WorkflowError, require


def skill_locations(project):
    project = Path(project).expanduser().resolve()
    require(project.is_dir(), "Chọn thư mục dự án đang có.")
    bundled = Path(__file__).parent / "skills"
    if not bundled.is_dir():
        bundled = Path(__file__).parent.parent / "skills"
    sources = sorted([*bundled.glob("product-cycle*"), bundled / "frontend-app-builder"])
    require(sources and all((source / "SKILL.md").is_file() for source in sources),
            "Bộ cài chưa có đủ skill. Cài lại Product Cycle từ gói đầy đủ.")
    destination = project / ".agents" / "skills"
    require(not any(path.is_symlink() for path in [project / ".agents", destination]),
            "Thư mục cài skill cần nằm trực tiếp trong dự án.")
    return project, sources, destination


def skill_hashes(folder):
    require(not folder.is_symlink() and folder.is_dir(), "Thư mục skill chưa hợp lệ: " + folder.name)
    files = {}
    for path in sorted(folder.rglob("*")):
        require(not path.is_symlink(), "Skill chứa liên kết ngoài; kiểm tra trước khi cập nhật: " + folder.name)
        if path.is_file():
            files[str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def skill_manifest(destination):
    path = destination.parent / ".product-cycle-skills.json"
    require(not path.is_symlink(), "File ghi nhận phiên bản skill cần nằm trực tiếp trong dự án.")
    if not path.exists():
        return path, {"version": 1, "skills": {}}
    try:
        value = json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise WorkflowError("Chưa đọc được phiên bản skill đã cài; kiểm tra file ghi nhận trước khi cập nhật.") from exc
    require(isinstance(value, dict) and value.get("version") == 1 and isinstance(value.get("skills"), dict)
            and all(isinstance(row, dict) and all(isinstance(k, str) and isinstance(v, str)
                    for k, v in row.items()) for row in value["skills"].values()),
            "Thông tin phiên bản skill chưa hợp lệ.")
    return path, value


def save_skill_manifest(path, value):
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def install_skills(project, preserve_existing=False):
    project, sources, destination = skill_locations(project)
    manifest_path, manifest = skill_manifest(destination)
    original_manifest = json.dumps(manifest, sort_keys=True)
    conflicts = [source.name for source in sources if (destination / source.name).exists()]
    require(preserve_existing or not conflicts, "Skill đã có trong dự án; kiểm tra trước khi thay thế: " + ", ".join(conflicts))
    installed = []
    try:
        for source in sources:
            target = destination / source.name
            if target.exists():
                require(target.is_dir() and not target.is_symlink() and (target / "SKILL.md").is_file(),
                        "Skill đang có chưa hợp lệ: " + source.name)
                continue
            installed.append(target)
            shutil.copytree(source, target)
        for source in sources:
            target = destination / source.name
            current = skill_hashes(target)
            # Existing customizations are never adopted as upstream originals.
            if target in installed or (source.name not in manifest["skills"] and current == skill_hashes(source)):
                manifest["skills"][source.name] = current
        if installed or not manifest_path.exists() or json.dumps(manifest, sort_keys=True) != original_manifest:
            save_skill_manifest(manifest_path, manifest)
    except BaseException:
        for target in installed:
            if target.is_dir():
                shutil.rmtree(target)
        raise
    return {"installed": [target.name for target in installed], "preserved": conflicts,
            "directory": str(destination)}


def update_skills(project, apply=False, selected=None, replace_customized=False):
    """Preview by default; replace only known originals, with restorable backups."""
    project, sources, destination = skill_locations(project)
    manifest_path, manifest = skill_manifest(destination)
    require(not replace_customized or selected, "Chọn rõ --skill cần thay trước khi dùng --replace-customized.")
    if selected:
        require(set(selected) <= {source.name for source in sources}, "Chọn skill có trong bộ Product Cycle hiện tại.")
        sources = [source for source in sources if source.name in selected]
    rows = []
    for source in sources:
        target = destination / source.name
        incoming = skill_hashes(source)
        if target.exists() or target.is_symlink():
            require((target / "SKILL.md").is_file(), "Skill đang có chưa hợp lệ: " + source.name)
            current = skill_hashes(target)
            status = "unchanged" if current == incoming else "update" if current == manifest["skills"].get(source.name) else "conflict"
        else:
            current, status = {}, "install"
        rows.append({"name": source.name, "status": status,
                     "files": [name for name in sorted(current.keys() | incoming.keys()) if current.get(name) != incoming.get(name)],
                     "current": current, "incoming": incoming})
    report = {"project": str(project), "applied": False, "backup": None,
              "skills": [{key: row[key] for key in ["name", "status", "files"]} for row in rows]}
    if not apply:
        return report
    require(replace_customized or not any(row["status"] == "conflict" for row in rows),
            "Có skill đã chỉnh sửa riêng hoặc chưa rõ phiên bản gốc. Chọn riêng các skill cần thay và dùng --replace-customized nếu đã xem thay đổi; bản cũ sẽ được sao lưu.")
    changes = [row for row in rows if row["status"] != "unchanged"]
    backup_root = project / ".product-cycle" / "skill-backups"
    require(not any(path.is_symlink() for path in [project / ".product-cycle", backup_root]),
            "Thư mục sao lưu skill cần nằm trực tiếp trong dự án.")
    backup = backup_root / uuid.uuid4().hex if changes else None
    replaced = []
    new_targets = []
    try:
        if backup:
            backup.mkdir(parents=True)
            if manifest_path.exists():
                shutil.copy2(manifest_path, backup / "manifest.json")
        destination.mkdir(parents=True, exist_ok=True)
        for source in sources:
            row = next(row for row in rows if row["name"] == source.name)
            if row["status"] != "unchanged":
                staging = backup / ("new-" + source.name)
                shutil.copytree(source, staging)
                target = destination / source.name
                require(skill_hashes(staging) == row["incoming"], "Bộ skill thay đổi trong lúc cập nhật; xem lại rồi chạy lại.")
                if target.exists():
                    require(skill_hashes(target) == row["current"], "Skill của dự án vừa thay đổi; xem lại trước khi cập nhật.")
                    os.replace(target, backup / source.name)
                    replaced.append(target)
                else:
                    new_targets.append(target)
                os.replace(staging, target)
            manifest["skills"][source.name] = row["incoming"]
        save_skill_manifest(manifest_path, manifest)
    except BaseException:
        for target in reversed(replaced):
            if target.exists():
                shutil.rmtree(target)
            os.replace(backup / target.name, target)
        for target in new_targets:
            if target.exists():
                shutil.rmtree(target)
        raise
    report.update(applied=True, backup=str(backup) if backup else None)
    return report


def uninstall_skills(project, apply=False, force=False):
    """Remove only bundled project skills, preserving a restorable copy."""
    project, sources, destination = skill_locations(project)
    manifest_path, manifest = skill_manifest(destination)
    rows = []
    for source in sources:
        target = destination / source.name
        if target.exists() or target.is_symlink():
            current = skill_hashes(target)
            known = current == manifest["skills"].get(source.name) or current == skill_hashes(source)
            rows.append({"name": source.name, "status": "remove" if known else "customized", "current": current})
    report = {"project": str(project), "applied": False, "backup": None,
              "skills": [{"name": row["name"], "status": row["status"]} for row in rows]}
    if not apply:
        return report
    require(force or all(row["status"] != "customized" for row in rows),
            "Có skill đã chỉnh sửa riêng hoặc chưa rõ bản gốc. Xem danh sách rồi dùng --force để gỡ và sao lưu cả phần tùy chỉnh.")
    remaining = {name: hashes for name, hashes in manifest["skills"].items()
                 if name not in {source.name for source in sources}}
    if not rows and remaining == manifest["skills"]:
        report["applied"] = True
        return report
    backup_root = project / ".product-cycle" / "skill-backups"
    require(not any(path.is_symlink() for path in [project / ".product-cycle", backup_root]),
            "Thư mục sao lưu skill cần nằm trực tiếp trong dự án.")
    backup = backup_root / uuid.uuid4().hex
    backup.mkdir(parents=True)
    moved = []
    try:
        if manifest_path.exists():
            shutil.copy2(manifest_path, backup / "manifest.json")
        for row in rows:
            target = destination / row["name"]
            require(skill_hashes(target) == row["current"], "Skill vừa thay đổi; xem lại trước khi gỡ.")
            os.replace(target, backup / row["name"])
            moved.append(target)
        save_skill_manifest(manifest_path, {"version": 1, "skills": remaining})
    except BaseException:
        for target in reversed(moved):
            os.replace(backup / target.name, target)
        raise
    report.update(applied=True, backup=str(backup))
    return report
