---
paths:
  - "tests/**"
---

# Tests

- pytest. Tests live in `tests/`, named `test_<module>.py`. One behaviour per test; the name states it: `test_rejects_empty_id`, not `test_works`.
- Arrange, act, assert. No logic in tests; no loops that hide which case failed. Use `pytest.mark.parametrize` for cases.
- Mock at the boundary (network, clock, filesystem, model), never the unit under test. Prefer `monkeypatch` and a fake object over `unittest.mock.patch` of internals.
- Hermetic (full spec: `~/.claude/skills/test-invariants/`). `tests/conftest.py` enforces: `$HOME` and every XDG path point into the per-test tmp dir, the env is a closed allowlist, cloud CLIs are poisoned on PATH, and pytest-socket blocks the network. Do not work around any of these.
- No timing gates: never assert a duration, never add a time budget. A slow test is fixed by shrinking scale or stubbing the sleep or exec seam. No real `time.sleep`; inject the sleeper.
- Miniature scale by default. A test that must run at production scale carries `@pytest.mark.full_scale` and its node id sits in `FULL_SCALE_TESTS` in `tests/conftest.py`; the drift test fails until both are true.
- Deterministic: `pytest-randomly` shuffles order; a test that depends on order is a bug. No real LLM calls; no wall clock without a fake.
- Snapshot tests only for stable serialised output. Never for prose or model output.
- A failing test is information. Fix the code under test. Do not skip, xfail, delete, or loosen the assertion. If the test itself is wrong, say so and ask.
- Cover the error path: every `raise` has one test. Use `pytest.raises(SpecificError, match=...)`.
- Property tests (`hypothesis`) where a parser or codec justifies them; add the dependency with a sentence on why.
- `uv run pytest tests/test_x.py -k name` runs one test. Use it while you iterate; run `uv run poe check` before you finish.
