"""`extract` against a fake parser. No test here calls a model."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import cast

import pytest
from anthropic.types import (
    MessageParam,
    ParsedMessage,
    ParsedTextBlock,
    StopReason,
    TextBlockParam,
    Usage,
)
from pydantic import BaseModel

from evalharness.llm.extract import ExtractError, RefusalError, TruncatedError, extract


class Invoice(BaseModel):
    total: float
    currency: str


@dataclass
class FakeParser:
    """Records the request and returns one canned reply."""

    reply: ParsedMessage[Invoice]
    calls: list[dict[str, object]] = field(default_factory=list)

    def parse[T: BaseModel](
        self,
        *,
        model: str,
        max_tokens: int,
        system: Iterable[TextBlockParam],
        messages: Iterable[MessageParam],
        output_format: type[T],
    ) -> ParsedMessage[T]:
        self.calls.append(
            {
                "model": model,
                "max_tokens": max_tokens,
                "system": list(system),
                "messages": list(messages),
                "output_format": output_format,
            }
        )
        return cast("ParsedMessage[T]", self.reply)


def reply(parsed: Invoice | None, stop_reason: StopReason = "end_turn") -> ParsedMessage[Invoice]:
    return ParsedMessage[Invoice](
        id="msg_1",
        type="message",
        role="assistant",
        model="claude-opus-5-5",
        stop_reason=stop_reason,
        stop_sequence=None,
        content=[ParsedTextBlock[Invoice](type="text", text="{}", parsed_output=parsed)],
        usage=Usage(
            input_tokens=10,
            output_tokens=5,
            cache_read_input_tokens=8,
            cache_creation_input_tokens=0,
        ),
    )


def test_returns_the_parsed_value_and_usage() -> None:
    parser = FakeParser(reply(Invoice(total=12.5, currency="AUD")))
    r = extract(parser, Invoice, system="Extract the invoice.", user="Total: $12.50 AUD")
    assert r.value == Invoice(total=12.5, currency="AUD")
    assert (r.usage.input, r.usage.output, r.usage.cache_read, r.usage.cache_write) == (10, 5, 8, 0)


def test_marks_the_system_prompt_as_a_cache_breakpoint() -> None:
    parser = FakeParser(reply(Invoice(total=1, currency="AUD")))
    extract(parser, Invoice, system="S", user="U")
    assert parser.calls[0]["system"] == [
        {"type": "text", "text": "S", "cache_control": {"type": "ephemeral"}}
    ]
    assert parser.calls[0]["output_format"] is Invoice


def test_raises_on_refusal() -> None:
    parser = FakeParser(reply(None, stop_reason="refusal"))
    with pytest.raises(RefusalError, match="refused"):
        extract(parser, Invoice, system="S", user="U")


def test_raises_on_truncation() -> None:
    parser = FakeParser(reply(None, stop_reason="max_tokens"))
    with pytest.raises(TruncatedError):
        extract(parser, Invoice, system="S", user="U")


def test_raises_when_nothing_parses() -> None:
    parser = FakeParser(reply(None))
    with pytest.raises(ExtractError, match="no parseable output"):
        extract(parser, Invoice, system="S", user="U")
