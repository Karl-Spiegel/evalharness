#!/usr/local/bin/bash
# Run a command in a private mount namespace where ~/.claude/skills is replaced by a filtered copy.
# Usage: with-hidden-skill.sh <filtered-skills-dir> <command...>
set -euo pipefail
FILTERED="$1"; shift
exec unshare --user --map-root-user --mount python3 -I - "$FILTERED" "$@" <<'PY'
import ctypes, os, sys
MS_BIND = 4096
libc = ctypes.CDLL(None, use_errno=True)
src, dst = sys.argv[1].encode(), os.path.expanduser("~/.claude/skills").encode()
if libc.mount(src, dst, None, MS_BIND, None) != 0:
    e = ctypes.get_errno(); sys.exit(f"bind mount failed: {os.strerror(e)}")
os.execvp(sys.argv[2], sys.argv[2:])
PY
