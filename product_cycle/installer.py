"""Install the bundled skills without replacing project customizations."""

import shutil
from pathlib import Path

from .contracts import WorkflowError, require


def install_skills(project, preserve_existing=False):
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
    except BaseException:
        for target in installed:
            if target.is_dir():
                shutil.rmtree(target)
        raise
    return {"installed": [target.name for target in installed], "preserved": conflicts,
            "directory": str(destination)}
