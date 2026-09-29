"""The contract schemas parse, and every fixture record validates against the record schema."""

import json
from pathlib import Path

import pytest

from evalharness.schema import CONTRACT, Json, load_schema, validate

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


def _first_fixture_record() -> dict[str, Json]:
    line = (FIXTURES / "arm-a.jsonl").read_text(encoding="utf-8").splitlines()[0]
    record: Json = json.loads(line)
    assert isinstance(record, dict)
    return record


def _set(record: dict[str, Json], path: str, value: Json) -> None:
    *parents, leaf = path.split(".")
    node: Json = record
    for key in parents:
        assert isinstance(node, dict)
        node = node[key]
    assert isinstance(node, dict)
    node[leaf] = value


@pytest.mark.parametrize(
    ("path", "value", "error"),
    [
        ("cost.amount", None, "$.cost.amount: null is not ['number']"),
        ("judge", None, "$.overall: 'pass' is not 'unscored'"),
        ("criteria", {}, "$.criteria: fewer than 1 properties"),
        ("response_text", None, "$.response_sha256: string is not ['null']"),
        (
            "started_at",
            "2026-09-29 10:00:00Z",
            "$.started_at: '2026-09-29 10:00:00Z' is not a date-time",
        ),
        ("case_id", "", "$.case_id: shorter than 1"),
        (
            "judge.prompt_sha256",
            "xyz",
            "$.judge.prompt_sha256: 'xyz' does not match '^[0-9a-f]{64}$'",
        ),
        ("overall", "maybe", "$.overall: 'maybe' is not one of ['pass', 'fail', 'unscored']"),
    ],
    ids=[
        "priced-without-amount",
        "judge-null-with-pass",
        "no-criteria",
        "null-text-with-digest",
        "date-time-without-T",
        "empty-case-id",
        "bad-digest",
        "bad-overall",
    ],
)
def test_record_schema_rejects(path: str, value: Json, error: str) -> None:
    record = _first_fixture_record()
    if path == "cost.amount":
        _set(record, "cost.basis", "priced")
    _set(record, path, value)
    errors = validate(record, load_schema(CONTRACT / "record.schema.json"))
    assert error in errors, errors
