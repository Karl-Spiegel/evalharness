"""The contract schemas parse, and every fixture record validates against the record schema."""

import json
from pathlib import Path

import pytest

from evalharness.schema import CONTRACT, load_schema, validate

SCHEMAS = ("record.schema.json", "coverage.schema.json")
FIXTURES = Path(__file__).parent / "fixtures"
DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_parses_and_declares_draft_2020_12(name: str) -> None:
    assert load_schema(CONTRACT / name)["$schema"] == DRAFT_2020_12


def test_every_fixture_record_validates() -> None:
    fixtures = sorted(FIXTURES.glob("*.jsonl"))
    assert fixtures, "tests/fixtures/*.jsonl is missing; finding nothing must fail, not pass"
    schema = load_schema(CONTRACT / "record.schema.json")
    errors = [
        f"{path.name}:{n}: {error}"
        for path in fixtures
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if line.strip()
        for error in validate(json.loads(line), schema)
    ]
    assert not errors, "\n".join(errors)
