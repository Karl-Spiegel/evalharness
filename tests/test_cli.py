"""CLI behaviour through `run`, with explicit streams."""

import io

import pytest

from evalharness import greeting
from evalharness.cli import run


def test_greets_the_name() -> None:
    out, err = io.StringIO(), io.StringIO()
    assert run(["Ada"], out, err) == 0
    assert out.getvalue() == "Hello, Ada!\n"
    assert err.getvalue() == ""


def test_rejects_an_empty_name() -> None:
    out, err = io.StringIO(), io.StringIO()
    assert run(["  "], out, err) == 2
    assert out.getvalue() == ""
    assert "must not be empty" in err.getvalue()


@pytest.mark.parametrize(("name", "expected"), [("Ada", "Hello, Ada!"), (" Ada ", "Hello, Ada!")])
def test_greeting_trims_whitespace(name: str, expected: str) -> None:
    assert greeting(name) == expected


def test_greeting_raises_on_empty() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        greeting("")
