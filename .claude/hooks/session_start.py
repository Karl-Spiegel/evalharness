#!/usr/bin/env python3
"""SessionStart hook.

Prints a short orientation that lands in context: branch, dirty files, the
gate command, and whether the git hooks are armed. AGENTS.md carries the rules.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import payload, root, run


def git(project: Path, *args: str) -> str:
    """Stdout of a git command, or an empty string."""
    r = run(["git", *args], project, 10)
    return r.stdout.strip() if r is not None and r.returncode == 0 else ""


def main() -> None:
    """Write the orientation lines to stdout."""
    project = root(payload())
    branch = git(project, "symbolic-ref", "--short", "HEAD") or "detached or no git"
    dirty = len([ln for ln in git(project, "status", "--porcelain").splitlines() if ln.strip()])
    last = git(project, "log", "-1", "--format=%h %s (%cr)") or "none"
    hooks = git(project, "config", "core.hooksPath")
    print(f"Repo: branch {branch}, {dirty} dirty file(s). Last commit: {last}.")
    print("Gate: `uv run poe check` (lint, types, tests, deps).")
    print("Rules: AGENTS.md. Rulings: docs/DECISIONS.md.")
    if hooks != ".githooks":
        print("Git hooks are NOT armed: run `uv run poe hooks` once.")


if __name__ == "__main__":
    main()
