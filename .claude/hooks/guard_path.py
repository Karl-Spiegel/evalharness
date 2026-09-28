#!/usr/bin/env python3
"""PreToolUse guard for Edit and Write.

Denies hand edits to the two kinds of file that are never right to edit by
hand: the lockfile and env files. Everything else is the agent's judgement;
the gate catches the rest.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import deny, payload, root, tool_input

NEVER: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^uv\.lock$"), "uv writes the lockfile; use `uv add` or `uv lock`"),
    (
        re.compile(r"(^|/)\.env(?!\.example$)(\.[^/]+)?$"),
        "env files hold secrets; the operator edits them",
    ),
]


def main() -> None:
    """Deny the edit when the path matches a rule; otherwise stay silent."""
    p = payload()
    file = str(tool_input(p).get("file_path", ""))
    if not file:
        return
    try:
        rel = Path(file).resolve().relative_to(root(p).resolve()).as_posix()
    except ValueError:
        rel = file
    for pattern, why in NEVER:
        if pattern.search(rel):
            deny("PreToolUse", f"guard-path: {rel}: {why}")


if __name__ == "__main__":
    main()
