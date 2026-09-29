# evalharness

A record-first harness for LLM evals: one result record per case, campaign statistics, and a protocol that never renders absence as zero.

This file is the one instruction file for every coding agent. `CLAUDE.md` imports it.
Keep it under 80 lines. Put long procedures in `.claude/skills/`, path-scoped rules in
`.claude/rules/`, and rulings in `docs/DECISIONS.md`.

## Commands

- `uv run poe check` — the gate: lint, types, tests with coverage, dependency hygiene. Run it before you report a task as done. CI and the pre-push hook run the same command.
- `uv run poe lint`, `uv run poe fix`, `uv run poe typecheck`, `uv run poe test`, `uv run poe deps` — the parts, for narrow iteration.
- `uv run pytest tests/test_thing.py` — one file. Add `-k name` for one test.
- `uv add <pkg>` / `uv add --dev <pkg>` — the only way a dependency enters. Never edit `uv.lock`.
- `uv run evalharness` — run the CLI.

## Rules

- **Types.** Every def is annotated. No `Any` (ruff `ANN401`), no `cast` without a comment, no `# type: ignore` or `# pyrefly: ignore` without a reason after it. Fix the type. pyrefly runs in `strict` preset.
- **Tests.** Never weaken a test to make it pass: no `skip`, no `xfail`, no deleted cases, no lowered `fail_under`. If the test is wrong, say so. Tests live in `tests/`, one behaviour per test, hermetic: no network (pytest-socket blocks it), no `$HOME`, no credentials, no sleeps, no timing assertions. Production-scale fixtures need the `full_scale` marker and a row in `FULL_SCALE_TESTS`.
- **Hands off.** `uv.lock` and `.env*` (a hook denies these). Generated files: change the generator.
- **Dependencies.** Say why before you add one. Prefer the standard library, except for a statistical or numerical method: call the reference implementation (scipy, statsmodels, the field's canonical package), never a hand-rolled formula, and keep a worked-example test that proves the call is right. `deptry` fails the gate on an unused or undeclared import.
- **Absent is not zero.** A missing value is `None` or a typed unavailable state, never `0` or `""`.
- **No employer content.** Nothing from an employer repository enters this repo: no code, identifier, case name, fixture, price, result file or number. Designs only, restated in this repo's words.
- **No take-home content.** Nothing from a hiring assignment enters this repo: no case, document, expected decision or prompt. The same rule; the same reason.
- **Git.** Small commits. Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`). No AI attribution lines (the commit-msg hook strips them). Never bypass git hooks, force push, or `reset --hard`; a hook denies these.
- **Feedback.** A hook formats, lint-fixes, and typechecks after every edit and shows you the diagnostics. Read them. Re-read a file before you edit it again; the formatter may have changed it.
- **Done means.** `uv run poe check` passes, the change is committed, and you report what you did and did not do.

## Layout

- `src/evalharness/` — the package. `cli.py` holds `main(argv)`; keep it thin and testable. Tests in `tests/`.
- `docs/DECISIONS.md` — operator rulings. Search it before you decide anything about the program (not the code's shape). No row means "unrecorded"; say so.
- `.claude/rules/` — rules that load when you touch a path (`tests/**`, `src/*/llm/**`).
- `.claude/skills/check/` — the `/check` fix loop. `.claude/agents/reviewer.md` — adversarial review before a PR.

## Gotchas

- Python 3.14: annotations are lazy (PEP 649). No `from __future__ import annotations`; no string quotes around forward references.
- Use `type X = ...` and PEP 695 generics (`def f[T: Base](x: T) -> T`), not `TypeVar`. ruff `UP` rewrites the old forms.
- `uv run` runs inside the project venv; plain `python` and `pytest` on PATH may be another interpreter.
- The Anthropic SDK 1.x uses `httpx2`. `respx` and anything that patches `httpx` sees nothing; use a fake client (see `.claude/rules/llm.md`).
