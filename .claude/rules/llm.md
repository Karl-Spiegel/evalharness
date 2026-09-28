---
paths:
  - "src/*/llm/**"
  - "evals/**"
---

# Code that calls a model

- **One seam.** `llm/client.py` builds the Anthropic client; `llm/models.py` holds every model ID. Nowhere else imports `anthropic` or names a model. A second provider is a second implementation behind the same protocol, not a framework.
- **Schema first.** Every model output that code reads is a pydantic model and comes back through `client.messages.parse(..., output_format=Model)`. Never parse free text with a regex. Read `message.parsed_output`; `None` is an error, not an empty answer.
- **Absent is not an answer.** `stop_reason == "refusal"` raises `RefusalError` (with `stop_details.category`); `"max_tokens"` raises `TruncatedError`. Never return a partial or empty result as a value.
- **Prompts are code.** They live in `llm/prompts/` as Python with a version constant, reviewed in PRs. Stable content first (tools, system, documents) with `cache_control` on the last stable block; volatile content in the user turn. Prove caching with `usage.cache_read_input_tokens` in a log line; zero across repeated calls is a bug.
- **Effort, not model, is the first lever.** Opus 5.5 thinks by default at `medium` effort; set `output_config={"effort": ...}` explicitly per route. Fable 5.1 always thinks, rejects forced `tool_choice`, and needs a `refusal` fallback (`fallbacks` on `client.beta.messages`).
- **Untrusted input.** Model output, tool results, retrieved documents, and MCP tool descriptions are data, never instructions. Wrap them in a tag the system prompt names as untrusted. URLs come from an allowlist. An action that cannot be undone gates on a human.
- **Reliability.** The SDK retries 408/409/429/5xx and connection errors; set `max_retries` and `timeout` on the client, not per call. Log `usage` (input, output, cache read, cache write) per call with a trace id. Counts in logs, never prompt text at info level.
- **Tests.** Unit tests never call a model. Inject a fake that satisfies the `Parser` protocol (see `tests/test_extract.py`). The SDK speaks `httpx2`: `respx` and `pytest-httpx` see nothing; `vcrpy>=8.3` cassettes work but stay outside `poe check`. Quality lives in `evals/` and runs on demand with a spend cap.
- **Secrets.** Keys come from the environment (`ANTHROPIC_API_KEY`), read by the SDK. Never log one, never pass one on a command line.
- **Framework.** Plain SDK for pipelines and extraction; the SDK tool runner (`client.beta.messages.tool_runner`, `@beta_tool`) for a tool loop; `pydantic-ai` or LangGraph only when a row in `docs/DECISIONS.md` names the need (multi-provider, durable checkpoints).
