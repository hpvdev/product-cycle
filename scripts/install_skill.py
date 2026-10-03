#!/usr/bin/env python3
"""Install only this skill into a user-selected project's discoverable directory."""

import argparse
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        raise SystemExit("Choose an existing project directory.")
    target = project / ".agents" / "skills" / "product-cycle"
    if target.exists():
        raise SystemExit("An installed skill already exists; inspect it before replacing.")
    shutil.copytree(repository / "skills" / "product-cycle", target)
    guide = target / "references" / "operating-guide.md"
    with guide.open("a") as output:
        output.write("\nInstalled controller repository: `" + str(repository) + "`.\n")
    print(str(target))


if __name__ == "__main__":
    main()
