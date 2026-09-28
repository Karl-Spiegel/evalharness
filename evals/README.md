# Evals

Quality of model output is measured here, not in `uv run poe check`. Unit tests in `tests/` never call a model.

Two jobs, two tools:

- **CI-style assertions** (`pydantic-evals`, or `inspect_ai` for larger suites): a fixed dataset, a fixed judge model and rubric version, pass/fail per case. Runs on demand (`uv run poe eval`, add the task when the first eval lands) with a spend cap in the command line.
- **Traces over time** (Langfuse self-hosted or Logfire, both OpenTelemetry): every production call carries a trace id; a sampled slice becomes the regression dataset.

Rules:

- A dataset row is a real, anonymised input with an expected output a human wrote.
- An eval runs on demand and on a schedule, never on every commit; it costs money and time.
- A prompt change ships with its eval delta in the PR description.
- OpenTelemetry GenAI semantic conventions are still in development (2026-09): emit token counts, latency, model, and stop reason as span attributes; prompt and response text only as span events or a redacted store.
