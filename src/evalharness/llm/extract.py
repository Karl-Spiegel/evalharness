"""Schema-constrained extraction: one call, one pydantic model back, or a typed error."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from anthropic.types import MessageParam, ParsedMessage, TextBlockParam
from pydantic import BaseModel

from evalharness.llm.models import MODELS


class Parser(Protocol):
    """The slice of `anthropic.Anthropic().messages` that `extract` needs. Tests inject a fake."""

    def parse[T: BaseModel](
        self,
        *,
        model: str,
        max_tokens: int,
        system: Iterable[TextBlockParam],
        messages: Iterable[MessageParam],
        output_format: type[T],
    ) -> ParsedMessage[T]:
        """Create a message and validate its output against `output_format`."""
        ...


class ExtractError(Exception):
    """The model returned nothing that parses as the schema."""


class RefusalError(ExtractError):
    """The model declined (`stop_reason == "refusal"`); `category` is from `stop_details`."""

    def __init__(self, category: str | None) -> None:
        super().__init__(f"model refused (category={category})")
        self.category = category


class TruncatedError(ExtractError):
    """The reply hit `max_tokens`. Raise it or shrink the input; never parse the fragment."""


@dataclass(frozen=True, slots=True)
class Usage:
    """Token counts for one call. Cache fields are None when the API did not report them."""

    input: int
    output: int
    cache_read: int | None
    cache_write: int | None


@dataclass(frozen=True, slots=True)
class Extracted[T: BaseModel]:
    """A validated model output plus what it cost."""

    value: T
    usage: Usage


def extract[T: BaseModel](
    parser: Parser,
    schema: type[T],
    *,
    system: str,
    user: str,
    model: str = MODELS["default"],
    max_tokens: int = 4096,
) -> Extracted[T]:
    """Ask the model for `schema` and return the validated value.

    `system` is the stable instruction text and carries the cache breakpoint; keep volatile
    text (the document, the question, timestamps) in `user`. A reply that does not parse is
    an error, never a guess.

    Raises:
        RefusalError: the model declined.
        TruncatedError: the reply hit `max_tokens`.
        ExtractError: the reply held no parseable output.
    """
    message = parser.parse(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_format=schema,
    )
    if message.stop_reason == "refusal":
        details = message.stop_details
        raise RefusalError(details.category if details is not None else None)
    if message.stop_reason == "max_tokens":
        raise TruncatedError
    value = message.parsed_output
    if value is None:
        msg = f"no parseable output (stop_reason={message.stop_reason})"
        raise ExtractError(msg)
    u = message.usage
    return Extracted(
        value=value,
        usage=Usage(
            input=u.input_tokens,
            output=u.output_tokens,
            cache_read=u.cache_read_input_tokens,
            cache_write=u.cache_creation_input_tokens,
        ),
    )
