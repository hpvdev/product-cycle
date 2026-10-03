#!/usr/bin/env python3
"""Install the workflow skill bundle into a selected project, without overwriting."""

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
    sources = sorted((repository / "skills").glob("product-cycle*"))
    destination = project / ".agents" / "skills"
    conflicts = [source.name for source in sources if (destination / source.name).exists()]
    if conflicts:
        raise SystemExit("Installed skills already exist; inspect them before replacing: " + ", ".join(conflicts))
    installed = []
    try:
        for source in sources:
            target = destination / source.name
            installed.append(target)
            shutil.copytree(source, target)
    except BaseException:
        for target in installed:
            if target.is_dir():
                shutil.rmtree(target)
        raise
    target = destination / "product-cycle"
    guide = target / "references" / "operating-guide.md"
    with guide.open("a") as output:
        output.write("\nInstalled controller repository: `" + str(repository) + "`.\n")
    print("Installed " + str(len(sources)) + " skills in " + str(destination))


if __name__ == "__main__":
    main()
