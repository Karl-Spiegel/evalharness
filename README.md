# evalharness

A record-first harness for LLM evals: one result record per case, campaign statistics, and a protocol that never renders absence as zero.

```
uv sync            # install (Python 3.14 via .python-version, tools from mise.toml)
uv run poe check   # the gate: lint, types, tests, dependency hygiene
uv run poe hooks   # arm the git hooks once per clone
```

Agent contract: `AGENTS.md`. Rulings: `docs/DECISIONS.md`.
