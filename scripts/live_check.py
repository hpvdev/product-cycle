#!/usr/bin/env python3
"""Exercise a real work/review contract in an isolated synthetic project."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product_cycle.runner import execute
from product_cycle.store import Store, write_json
from product_cycle.contracts import WorkflowError


def main():
    parser = argparse.ArgumentParser(description="Live Codex adapter and analysis-contract check")
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--effort", default="high")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        raise SystemExit("Use a new output directory to preserve earlier evidence.")
    output.mkdir(parents=True)
    os.environ["PRODUCT_CYCLE_HOME"] = str(output / "state")
    brief = """Synthetic evaluation fixture, not a real product launch.
Design the requirements for a local command-line note utility for one developer.
Known facts: one user; no cloud or accounts; a note has a short title and text;
the user must save a note and retrieve it in a later invocation on the same machine.
Scope: save and retrieve only. Exclude collaboration, UI, reminders, and deployment.
Separate facts from assumptions. Produce a brief, testable analysis and requirement list.
Do not claim user interviews or implement the product. This check only evaluates analysis.
"""
    store = Store.create(output / "project", brief, "Live adapter check", args.model, args.effort)
    try:
        config = store.config
        config.update(executor="codex-app-server", collaborative_product=False, experience_checkpoint_required=False)
        write_json(store.root / "config.json", config)
        print("Running real Codex work and independent review…", flush=True)
        execute(store, "analysis")
        snapshot = store.snapshot()
        task = store.task("analysis")
        passed = task["status"] == "awaiting_approval"
        report = {"passed": passed, "scope": "Real Codex transport, analysis output contract, separate read-only review; no product implementation.",
                  "status": task["status"], "snapshot": snapshot}
        write_json(output / "report.json", report)
        print(json.dumps({"passed": passed, "status": task["status"], "report": str(output / "report.json")}, indent=2))
        if not passed:
            raise SystemExit(1)
    except WorkflowError as exc:
        write_json(output / "report.json", {"passed": False, "error": str(exc), "snapshot": store.snapshot()})
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    finally:
        store.close()


if __name__ == "__main__":
    main()
