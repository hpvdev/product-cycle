"""Include the single source skill bundle in distributable wheels."""

import shutil
from pathlib import Path

from setuptools.command.build_py import build_py


class BuildWithSkills(build_py):
    def run(self):
        super().run()
        shutil.copytree(Path(__file__).parent / "skills", Path(self.build_lib) / "product_cycle" / "skills", dirs_exist_ok=True)
