"""The `verdict` subcommand through `run`, with explicit streams."""

import io
import json
import re
from pathlib import Path

import pytest

from evalharness import verdict
from evalharness.cli import run

FIXTURES = Path(__file__).parent / "fixtures"
ARM_A = FIXTURES / "arm-a.jsonl"
ARM_B = FIXTURES / "arm-b.jsonl"

# The brief's example line shows correctness B 10/11 and completeness B 8/11. The ruling in the
# brief's clarifications and register row 1 divides each criterion by its own pass-or-fail
# count. Arm b's inv-11 is unscored only on faithfulness, so b's correctness and completeness
# divide by 12. This line follows the ruling.
FIXTURE_LINE = (
    "A 7/12 (58%)  B 8/12 (67%)  | judged A 7/11 B 8/11 | "
    "correctness A 9/11 B 11/12 · completeness A 8/11 B 9/12 · faithfulness A 10/11 B 9/11 | "
    "paired net +1 (B>A 2, A>B 1, n 11, excluded 1) | bound n/a (1 repeat)\n"
)


def _record(case_id: str, repeat: int, overall: str, criterion: str | None = None) -> str:
    """Return one valid record line; each criterion carries `criterion`, else `overall`."""
    verdict_of = criterion or overall
    return json.dumps(
        {
            "schema_version": "1",
            "case_id": case_id,
            "arm": "x",
            "repeat": repeat,
            "response_text": None,
            "response_sha256": None,
            "criteria": {
                "correctness": {
                    "verdict": verdict_of,
                    "gating": True,
                    "reason": None,
                    "graded": None,
                }
            },
            "overall": overall,
            "judge": None,
            "cost": {
                "basis": "unpriced",
                "amount": None,
                "currency": None,
                "price_snapshot_date": None,
            },
            "latency": {"wall_ms": 10, "harness_ms": 1},
            "failure_class": "none",
            "provenance": {
                "served_model": None,
                "provider": None,
                "sampling": None,
                "weights_digest": None,
            },
            "started_at": "2026-09-29T01:00:00Z",
        }
    )


def _write(path: Path, lines: list[str]) -> Path:
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def _verdict(a: Path, b: Path, *extra: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = run(["verdict", "--a", str(a), "--b", str(b), *extra], out, err)
    return code, out.getvalue(), err.getvalue()


def test_fixture_pair_renders_the_verdict_line() -> None:
    assert _verdict(ARM_A, ARM_B) == (0, FIXTURE_LINE, "")


def test_labels_replace_a_and_b() -> None:
    code, out, _ = _verdict(ARM_A, ARM_B, "--label-a", "base", "--label-b", "cand")
    assert code == 0
    assert out.startswith("base 7/12 (58%)  cand 8/12 (67%)  | judged base 7/11 cand 8/11 |")
    assert "(cand>base 2, base>cand 1," in out


def test_no_judged_records_render_every_judged_quantity_as_na(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.jsonl", [_record("c1", 0, "unscored"), _record("c2", 0, "unscored")])
    b = _write(tmp_path / "b.jsonl", [_record("c1", 0, "unscored"), _record("c2", 0, "unscored")])
    line = (
        "A 0/2 (0%)  B 0/2 (0%)  | judged A n/a B n/a | correctness A n/a B n/a | "
        "paired net n/a (B>A n/a, A>B n/a, n 0, excluded 2) | bound n/a (1 repeat)\n"
    )
    assert _verdict(a, b) == (0, line, "")


def test_empty_files_render_every_quantity_as_na(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.jsonl", [])
    b = _write(tmp_path / "b.jsonl", [])
    line = (
        "A n/a  B n/a  | judged A n/a B n/a | criteria n/a | "
        "paired net n/a (B>A n/a, A>B n/a, n 0, excluded 0) | bound n/a (0 repeats)\n"
    )
    assert _verdict(a, b) == (0, line, "")


def test_multi_repeat_pair_renders_a_numeric_bound(tmp_path: Path) -> None:
    # Pass rates per repeat: a 50, 50, 0 and b 100, 50, 100; differences 50, 0, 100.
    # Mean 50, sd 50, t(0.95, df 2) = 4.303: half-width 4.303 * 50 / sqrt(3) = 124.2.
    a = _write(
        tmp_path / "a.jsonl",
        [
            _record("c1", 0, "pass"),
            _record("c2", 0, "fail"),
            _record("c1", 1, "pass"),
            _record("c2", 1, "fail"),
            _record("c1", 2, "fail"),
            _record("c2", 2, "fail"),
        ],
    )
    b = _write(
        tmp_path / "b.jsonl",
        [
            _record("c1", 0, "pass"),
            _record("c2", 0, "pass"),
            _record("c1", 1, "pass"),
            _record("c2", 1, "fail"),
            _record("c1", 2, "pass"),
            _record("c2", 2, "pass"),
        ],
    )
    code, out, _ = _verdict(a, b)
    assert code == 0
    assert re.search(r"\| bound \+50\.0 ± 124\.2 pp \(95%, 3 repeats\)\n$", out)
    assert "paired net +3 (B>A 3, A>B 0, n 6, excluded 0)" in out


def test_invalid_line_exits_2_naming_file_and_line(tmp_path: Path) -> None:
    bad = _write(tmp_path / "bad.jsonl", [_record("c1", 0, "pass"), _record("c2", 0, "maybe")])
    code, out, err = _verdict(ARM_A, bad)
    assert (code, out) == (2, "")
    assert err.startswith(f"error: {bad}:2: ")
    assert "'maybe' is not one of" in err


def test_line_that_is_not_json_exits_2_naming_file_and_line(tmp_path: Path) -> None:
    bad = _write(tmp_path / "bad.jsonl", ["{not json"])
    code, _, err = _verdict(bad, ARM_B)
    assert code == 2
    assert err.startswith(f"error: {bad}:1: not JSON")


def test_duplicate_case_and_repeat_exits_2_naming_both_lines(tmp_path: Path) -> None:
    bad = _write(tmp_path / "bad.jsonl", [_record("c1", 0, "pass"), _record("c1", 0, "fail")])
    code, _, err = _verdict(bad, ARM_B)
    assert code == 2
    assert err == f"error: {bad}:2: duplicate of line 1 (case 'c1', repeat 0)\n"


def test_missing_file_exits_2_naming_the_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.jsonl"
    code, _, err = _verdict(missing, ARM_B)
    assert code == 2
    assert err.startswith(f"error: {missing}: ")


def test_record_refuses_a_value_the_schema_did_not_check() -> None:
    with pytest.raises(TypeError, match="validate the record first"):
        verdict._record([])
