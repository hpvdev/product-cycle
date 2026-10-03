#!/usr/bin/env python3
"""Install the workflow skill bundle into a selected project, without overwriting."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_cycle.contracts import WorkflowError
from product_cycle.installer import install_skills


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    try:
        result = install_skills(args.project)
    except WorkflowError as exc:
        raise SystemExit(str(exc))
    print("Installed " + str(len(result["installed"])) + " skills in " + result["directory"])


if __name__ == "__main__":
    main()
