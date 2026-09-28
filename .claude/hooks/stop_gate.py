#!/usr/bin/env python3
"""Stop hook.

Runs the repo gate (`uv run poe check`) when code changed and shows the
operator a one-line notice when it is red. It never blocks the stop: the
pre-push hook and CI enforce; this only informs. Keep `check` under about a
minute; move slow suites out of it.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import payload, root, run

CODE = (".py", ".pyi", ".toml", "uv.lock")


def main() -> None:
    """Run the gate on a dirty tree and report the result as a system message."""
    p = payload()
    if p.get("hook_event_name") != "Stop" or p.get("stop_hook_active"):
        return
    project = root(p)
    status = run(["git", "status", "--porcelain"], project, 10)
    if status is None or status.returncode != 0:
        return
    changed = [
        line[3:].strip()
        for line in status.stdout.splitlines()
        if line.strip() and line[3:].strip().endswith(CODE) and not line[3:].startswith(".claude/")
    ]
    if not changed:
        return

    r = run(["uv", "run", "--no-sync", "poe", "check"], project, 280)
    if r is not None and r.returncode == 0:
        return
    if r is None:
        note = "gate NOT verified: `uv run poe check` did not finish (timeout or not runnable)"
    else:
        tail = [line for line in r.stdout.splitlines() if line.strip()][-4:]
        note = "gate RED: " + " | ".join(tail)
    sys.stdout.write(json.dumps({"systemMessage": f"stop-gate: {note}"}))


if __name__ == "__main__":
    main()
