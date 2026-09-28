"""Shared helpers for the git hooks in this directory.

Git ignores files here that are not hook names. Hooks run with the repo root
as cwd. Standard library only, so a hook works before `uv sync`.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def tool(name: str) -> list[str]:
    """Command prefix for a dev tool: the venv binary when present, else `uv run`."""
    venv_bin = Path(".venv") / "bin" / name
    if venv_bin.exists():
        return [str(venv_bin)]
    if shutil.which("uv"):
        return ["uv", "run", "--no-sync", name]
    print(f"hook: neither .venv/bin/{name} nor uv on PATH; run `uv sync`", file=sys.stderr)
    sys.exit(1)


def sh(cmd: list[str]) -> int:
    """Run a command with inherited stdio; return its exit status."""
    try:
        return subprocess.run(cmd, check=False).returncode
    except OSError as e:
        print(f"hook: cannot run {cmd[0]}: {e}", file=sys.stderr)
        return 1


def out(cmd: list[str]) -> str:
    """Stdout of a command; exit with its status on failure."""
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        sys.exit(r.returncode)
    return r.stdout
