"""The verdict line: two arms' record files reduced to one comparable line.

The headline divides by the count of records for the arm. The judged count divides by the
records whose `overall` is `pass` or `fail`. Each criterion divides by the records where that
criterion is `pass` or `fail`. A quantity with no input renders `n/a`, never `0` or `0%`.
`overall` is trusted as stored; the runner computes it.
"""

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from evalharness.schema import Json, Schema, validate
from evalharness.stats import Verdict, paired_flips, paired_t_bound

NA = "n/a"
JUDGED: frozenset[str] = frozenset({"pass", "fail"})


class RecordFileError(Exception):
    """A record file that cannot be read: a bad line, a duplicate record, or an OS error."""


@dataclass(frozen=True)
class Record:
    """The fields of one result record that the verdict line uses."""

    case_id: str
    repeat: int
    overall: Verdict
    criteria: Mapping[str, Verdict]


def _as_verdict(value: Json) -> Verdict:
    """Return value as a verdict; the schema has already checked it."""
    if value == "pass":
        return "pass"
    if value == "fail":
        return "fail"
    return "unscored"


def _record(value: Json) -> Record:
    """Return the verdict fields of a decoded record that has passed the schema."""
    if not isinstance(value, Mapping):
        value = {}
    case_id, repeat, criteria = value.get("case_id"), value.get("repeat"), value.get("criteria")
    if not (isinstance(case_id, str) and isinstance(repeat, int) and isinstance(criteria, Mapping)):
        msg = "record fields do not have their schema types; validate the record first"
        raise TypeError(msg)
    verdicts = {
        name: _as_verdict(item["verdict"] if isinstance(item, Mapping) else None)
        for name, item in criteria.items()
    }
    return Record(case_id, repeat, _as_verdict(value.get("overall")), verdicts)


def load_records(path: Path, schema: Schema) -> list[Record]:
    """Return the records in a JSONL file, one per non-blank line.

    Raises:
        RecordFileError: when the file cannot be read, a line is not JSON, a line fails the
            schema, or two lines hold the same case and repeat. The message names the file
            and the line number.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        msg = f"{path}: {e.strerror}"
        raise RecordFileError(msg) from e
    records: list[Record] = []
    seen: dict[tuple[str, int], int] = {}
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            value: Json = json.loads(line)
        except json.JSONDecodeError as e:
            msg = f"{path}:{n}: not JSON: {e.msg}"
            raise RecordFileError(msg) from e
        errors = validate(value, schema)
        if errors:
            msg = f"{path}:{n}: " + "; ".join(errors)
            raise RecordFileError(msg)
        record = _record(value)
        key = (record.case_id, record.repeat)
        if key in seen:
            msg = f"{path}:{n}: duplicate of line {seen[key]} (case {key[0]!r}, repeat {key[1]})"
            raise RecordFileError(msg)
        seen[key] = n
        records.append(record)
    return records


def _fraction(passes: int, total: int) -> str:
    """Return `passes/total`, or `n/a` when total is 0."""
    return f"{passes}/{total}" if total else NA


def _percent(passes: int, total: int) -> str:
    """Return `passes/total (p%)`, rounded half up, or `n/a` when total is 0."""
    if not total:
        return NA
    return f"{passes}/{total} ({math.floor(Fraction(100 * passes, total) + Fraction(1, 2))}%)"


def _passes(verdicts: Sequence[Verdict]) -> int:
    """Return the count of pass verdicts."""
    return sum(1 for v in verdicts if v == "pass")


def _judged(verdicts: Sequence[Verdict]) -> list[Verdict]:
    """Return the verdicts that are pass or fail."""
    return [v for v in verdicts if v in JUDGED]


def _criterion_names(a: Sequence[Record], b: Sequence[Record]) -> list[str]:
    """Return every criterion name over both arms, in first-seen order, a before b."""
    return list(dict.fromkeys(name for r in (*a, *b) for name in r.criteria))


def _criterion(records: Sequence[Record], name: str) -> str:
    """Return one arm's passes over judged count for one criterion."""
    judged = _judged([r.criteria[name] for r in records if name in r.criteria])
    return _fraction(_passes(judged), len(judged))


def _key(record: Record) -> str:
    """Return the pairing key of a record: its case id within its repeat."""
    return f"{record.repeat}:{record.case_id}"


def _paired(a: Sequence[Record], b: Sequence[Record], label_a: str, label_b: str) -> str:
    """Return the paired-flips segment over `overall`, paired by case id and repeat."""
    flips = paired_flips({_key(r): r.overall for r in a}, {_key(r): r.overall for r in b})
    if flips.n_paired:
        net, b_only, a_only = f"{flips.net:+d}", str(flips.b_only), str(flips.a_only)
    else:
        net = b_only = a_only = NA
    return (
        f"paired net {net} ({label_b}>{label_a} {b_only}, {label_a}>{label_b} {a_only}, "
        f"n {flips.n_paired}, excluded {flips.excluded})"
    )


def _rate_by_repeat(records: Sequence[Record]) -> dict[int, Fraction]:
    """Return the headline pass rate of each repeat, in percentage points."""
    by_repeat: dict[int, list[Verdict]] = {}
    for r in records:
        by_repeat.setdefault(r.repeat, []).append(r.overall)
    return {k: Fraction(100 * _passes(v), len(v)) for k, v in by_repeat.items()}


def _bound(a: Sequence[Record], b: Sequence[Record]) -> str:
    """Return the paired-t bound on b's pass rate minus a's, over the repeats both arms ran.

    Each repeat both arms ran gives one difference in percentage points. Fewer than two such
    repeats renders `n/a` with the count.
    """
    rate_a, rate_b = _rate_by_repeat(a), _rate_by_repeat(b)
    common = sorted(rate_a.keys() & rate_b.keys())
    bound = paired_t_bound([float(rate_b[k] - rate_a[k]) for k in common])
    if bound is None:
        return f"bound {NA} ({len(common)} repeat{'' if len(common) == 1 else 's'})"
    return (
        f"bound {bound.mean:+.1f} ± {bound.half_width:.1f} pp "
        f"({bound.confidence:.0%}, {bound.n} repeats)"
    )


def render(a: Sequence[Record], b: Sequence[Record], label_a: str, label_b: str) -> str:
    """Return the one verdict line comparing arm a with arm b."""
    overall_a, overall_b = [r.overall for r in a], [r.overall for r in b]
    judged_a, judged_b = _judged(overall_a), _judged(overall_b)
    names = _criterion_names(a, b)
    criteria = " · ".join(
        f"{name} {label_a} {_criterion(a, name)} {label_b} {_criterion(b, name)}" for name in names
    )
    headline = (
        f"{label_a} {_percent(_passes(overall_a), len(a))}  "
        f"{label_b} {_percent(_passes(overall_b), len(b))} "
    )
    judged = (
        f"judged {label_a} {_fraction(_passes(judged_a), len(judged_a))} "
        f"{label_b} {_fraction(_passes(judged_b), len(judged_b))}"
    )
    segments = [headline, judged, criteria or f"criteria {NA}"]
    return " | ".join([*segments, _paired(a, b, label_a, label_b), _bound(a, b)])
