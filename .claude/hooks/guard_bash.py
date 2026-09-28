#!/usr/bin/env python3
"""PreToolUse guard for the Bash tool.

Deliberately small: only the actions with a track record of agents doing them
and nobody wanting it. Always exits 0; the decision rides the JSON on stdout.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import deny, payload, tool_input

RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\s--no-verify\b"), "git hooks are the gate. Do not bypass them."),
    (
        re.compile(r"\b(LEFTHOOK|HUSKY|SKIP_HOOKS?|PRE_COMMIT_ALLOW_NO_CONFIG)="),
        "git hooks are the gate. Do not disable them.",
    ),
    (re.compile(r"\bgit\s+push\b[^|;&]*\s(-f|--force)\b"), "force push. Ask the operator."),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "discards commits or work. Ask the operator."),
]


def main() -> None:
    """Deny the command when a rule matches; otherwise stay silent."""
    p = payload()
    cmd = str(tool_input(p).get("command", ""))
    for pattern, why in RULES:
        if pattern.search(cmd):
            deny("PreToolUse", f"guard-bash: {why} Command: {cmd[:200]}")


if __name__ == "__main__":
    main()
