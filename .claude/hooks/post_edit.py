#!/usr/bin/env python3
"""PostToolUse hook for Edit and Write on a Python file.

1. Applies ruff's safe fixes and formats the file.
2. Typechecks the project with pyrefly (fast enough to run after every edit).
Remaining diagnostics go to stderr with exit 2, which Claude Code shows to the
agent. Output is capped so it stays cheap in context.
"""

import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import cap, payload, root, run, tool, tool_input

MAX_LINES = 40
SKIP_DIRS = {".venv", "dist", "build", "htmlcov", ".git"}


def edited_first(rel: Path) -> Callable[[str], bool]:
    """Sort key: lines about the edited file sort before lines about its callers."""
    prefix = str(rel)
    return lambda line: not line.startswith(prefix)


def main() -> int:
    """Format, fix, and typecheck; return 2 when diagnostics remain."""
    p = payload()
    file = str(tool_input(p).get("file_path", ""))
    if not file or not file.endswith((".py", ".pyi")):
        return 0
    project = root(p)
    path = Path(file)
    try:
        rel = path.resolve().relative_to(project.resolve())
    except ValueError:
        return 0
    if SKIP_DIRS & set(rel.parts):
        return 0

    out: list[str] = []
    ruff = tool("ruff", project)
    r = run([*ruff, "check", "--fix", "--output-format", "concise", str(rel)], project, 30)
    if r is not None and r.returncode != 0:
        out += ["ruff:", *cap(r.stdout, MAX_LINES)]
    run([*ruff, "format", str(rel)], project, 30)

    pyrefly = [*tool("pyrefly", project), "check", "--output-format", "min-text", "--summary=none"]
    r = run(pyrefly, project, 60)
    if r is not None and r.returncode != 0:
        lines = cap(r.stdout, MAX_LINES)
        # Errors in the edited file first; the rest are callers it broke.
        lines.sort(key=edited_first(rel))
        out += ["pyrefly:", *lines]

    if out:
        sys.stderr.write("\n".join(out) + "\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
