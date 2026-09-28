---
name: check
description: Run the repo gate (lint, types, tests, dependency hygiene) and fix what fails without weakening anything. Use before a commit, before you report a task done, or when the user says "check".
allowed-tools: Bash(uv run poe *), Bash(uv run pytest *), Bash(uv run ruff *), Bash(uv run pyrefly *), Bash(uv run deptry *), Read, Edit, Grep, Glob
---

Run `uv run poe check`.

If it passes, report "gate green" in one line and stop.

If it fails, fix the cause and run it again. At most three rounds. Rules for a fix:

- Fix the code, not the check. No `Any`, no `# type: ignore`, no `# noqa` without a reason, no `skip`, no `xfail`, no deleted test, no widened assertion, no lowered `fail_under`.
- A `deptry` finding means an unused or undeclared dependency. Remove the import, or `uv add` the package only after you say why it is needed.
- A lint finding that `uv run poe fix` can fix, let it fix.
- A pyrefly error is a real type mismatch until proven otherwise. Narrow with `isinstance` or `match`, not with a cast.
- If a failure needs a decision (a wrong test, a real behaviour change, a dependency), stop and report it with the exact diagnostic. Do not guess.

Report in at most five lines: what failed, what you changed, what remains.
