"""The one Anthropic client. Nothing else in the project imports `anthropic`."""

from functools import cache

from anthropic import Anthropic


@cache
def llm_client() -> Anthropic:
    """The process-wide client. Reads ANTHROPIC_API_KEY from the environment.

    The SDK retries 408, 409, 429, 5xx and connection errors with backoff. Timeouts are
    seconds; the wall clock can reach `timeout * (max_retries + 1)`.
    """
    return Anthropic(max_retries=3, timeout=60.0)
