#!/usr/bin/env python3
"""Install the workflow skill bundle into a selected project, without overwriting."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from product_cycle.cli import main as run_cli


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    run_cli(["install-skills", "--project", args.project])


if __name__ == "__main__":
    main()
