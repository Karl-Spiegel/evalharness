"""Shared helpers for the Claude Code hooks in this directory. Standard library only."""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def payload() -> dict[str, object]:
    """Read the hook payload from stdin; an unreadable payload is an empty dict."""
    try:
        data: object = json.load(sys.stdin)
    except json.JSONDecodeError, OSError:
        return {}
    return data if isinstance(data, dict) else {}


def tool_input(p: dict[str, object]) -> dict[str, object]:
    """The `tool_input` object of a PreToolUse or PostToolUse payload."""
    ti = p.get("tool_input")
    return ti if isinstance(ti, dict) else {}


def root(p: dict[str, object]) -> Path:
    """The project root: the payload's cwd, else the process cwd."""
    cwd = p.get("cwd")
    return Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()


def tool(name: str, project: Path) -> list[str]:
    """Command prefix for a dev tool: the venv binary when present, else `uv run`."""
    venv_bin = project / ".venv" / "bin" / name
    if venv_bin.exists():
        return [str(venv_bin)]
    if shutil.which("uv"):
        return ["uv", "run", "--no-sync", name]
    return [name]


def run(cmd: list[str], cwd: Path, timeout: float) -> subprocess.CompletedProcess[str] | None:
    """Run a command with stderr merged into stdout; None when it could not run or timed out."""
    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    except OSError, subprocess.TimeoutExpired:
        return None


def deny(event: str, reason: str) -> None:
    """Emit a PreToolUse deny decision and exit 0 (the decision rides the JSON)."""
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def cap(text: str, limit: int) -> list[str]:
    """The first `limit` non-empty lines of `text`, without tool chatter (pyrefly INFO lines)."""
    return [line for line in text.splitlines() if line.strip() and not line.startswith(" INFO")][
        :limit
    ]
