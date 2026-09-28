"""Tests for evalharness.stats. Each statistic is checked against its cited worked example."""

import math

import pytest

from evalharness.stats import (
    T_CRITICAL,
    TBound,
    Verdict,
    _critical_value,
    cohen_kappa,
    krippendorff_alpha,
    paired_flips,
    paired_t_bound,
    single_run_rule,
)

THREE_DP = 5e-4


def _two_rater_lists(cells: dict[tuple[str, str], int]) -> tuple[list[str], list[str]]:
    """Expand a (rater b, rater a) -> count table into two aligned label lists."""
    a: list[str] = []
    b: list[str] = []
    for (label_b, label_a), count in cells.items():
        a += [label_a] * count
        b += [label_b] * count
    return a, b


# Cohen (1960), Table 2, frequencies. Key: (Judge B category, Judge A category).
COHEN_1960_TABLE_2 = {
    ("1", "1"): 88,
    ("1", "2"): 14,
    ("1", "3"): 18,
    ("2", "1"): 10,
    ("2", "2"): 40,
    ("2", "3"): 10,
    ("3", "1"): 2,
    ("3", "2"): 6,
    ("3", "3"): 12,
}

# Krippendorff (2011), section C: rows are observers A to D, columns are units 1 to 12.
_N = None
KRIPPENDORFF_2011_C = [
    ["1", "2", "3", "3", "2", "1", "4", "1", "2", _N, _N, _N],
    ["1", "2", "3", "3", "2", "2", "4", "1", "2", "5", _N, "3"],
    [_N, "3", "3", "3", "2", "3", "4", "2", "2", "5", "1", _N],
    ["1", "2", "3", "3", "2", "4", "4", "1", "2", "5", "1", _N],
]
KRIPPENDORFF_2011_C_UNITS = [list(unit) for unit in zip(*KRIPPENDORFF_2011_C, strict=True)]

# Student (1908) sleep data, as in R datasets::sleep: extra hours of sleep per patient.
SLEEP_DRUG_1 = [0.7, -1.6, -0.2, -1.2, -0.1, 3.4, 3.7, 0.8, 0.0, 2.0]
SLEEP_DRUG_2 = [1.9, 0.8, 1.1, 0.1, -0.1, 4.4, 5.5, 1.6, 4.6, 3.4]
SLEEP_DIFFS = [d2 - d1 for d1, d2 in zip(SLEEP_DRUG_1, SLEEP_DRUG_2, strict=True)]


def _approval_surveys() -> tuple[dict[str, Verdict], dict[str, Verdict]]:
    """Agresti (1990) p. 350: 794 approve twice, 150 approve then not, 86 not then approve."""
    rows: list[tuple[Verdict, Verdict, int]] = [
        ("pass", "pass", 794),
        ("pass", "fail", 150),
        ("fail", "pass", 86),
        ("fail", "fail", 570),
    ]
    first: dict[str, Verdict] = {}
    second: dict[str, Verdict] = {}
    for va, vb, count in rows:
        for _ in range(count):
            case_id = f"r{len(first):04d}"
            first[case_id] = va
            second[case_id] = vb
    return first, second


def test_paired_flips_matches_agresti_approval_table() -> None:
    first, second = _approval_surveys()
    flips = paired_flips(first, second)
    assert (flips.n_paired, flips.a_only, flips.b_only, flips.both, flips.neither) == (
        1600,
        150,
        86,
        794,
        570,
    )
    assert flips.excluded == 0
    assert flips.net == -64


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ({"c1": "pass", "c2": "unscored"}, {"c1": "pass", "c2": "pass"}),
        ({"c1": "pass", "c2": "fail"}, {"c1": "pass", "c2": "unscored"}),
        ({"c1": "pass"}, {"c1": "pass", "c2": "fail"}),
        ({"c1": "pass", "c2": "pass"}, {"c1": "pass"}),
    ],
    ids=["unscored-in-a", "unscored-in-b", "missing-from-a", "missing-from-b"],
)
def test_paired_flips_excludes_and_counts_unscored_or_missing(
    a: dict[str, Verdict], b: dict[str, Verdict]
) -> None:
    flips = paired_flips(a, b)
    assert (flips.n_paired, flips.both, flips.excluded) == (1, 1, 1)


def test_cohen_kappa_matches_cohen_1960_table_2() -> None:
    a, b = _two_rater_lists(COHEN_1960_TABLE_2)
    assert cohen_kappa(a, b) == pytest.approx(0.492, abs=THREE_DP)


def test_cohen_kappa_is_none_without_items() -> None:
    assert cohen_kappa([], []) is None


def test_cohen_kappa_is_none_when_lengths_differ() -> None:
    assert cohen_kappa(["x", "y"], ["x"]) is None


def test_cohen_kappa_is_none_with_one_category() -> None:
    assert cohen_kappa(["x", "x"], ["x", "x"]) is None


def test_krippendorff_alpha_nominal_matches_2011_example_c() -> None:
    assert krippendorff_alpha(KRIPPENDORFF_2011_C_UNITS) == pytest.approx(0.743, abs=THREE_DP)


def test_krippendorff_alpha_ordinal_matches_2011_example_c() -> None:
    alpha = krippendorff_alpha(KRIPPENDORFF_2011_C_UNITS, level="ordinal")
    assert alpha == pytest.approx(0.815, abs=THREE_DP)


def test_krippendorff_alpha_is_none_with_fewer_than_two_pairable_units() -> None:
    assert krippendorff_alpha([["1", "2"], ["1", None], [None, None]]) is None


def test_krippendorff_alpha_is_none_with_one_distinct_value() -> None:
    assert krippendorff_alpha([["1", "1"], ["1", "1", None]]) is None


def test_krippendorff_alpha_ordinal_is_none_for_a_non_integer_value() -> None:
    assert krippendorff_alpha([["1", "high"], ["1", "1"]], level="ordinal") is None


def test_single_run_rule_matches_nist_numacc1() -> None:
    rule = single_run_rule([10000001, 10000003, 10000002])
    assert rule is not None
    assert (rule.n_repeats, rule.mean, rule.sd) == (3, 10000002.0, 1.0)
    assert rule.threshold_cases == pytest.approx(2.77, abs=THREE_DP)
    assert rule.cov == pytest.approx(1 / 10000002)
    assert rule.multiplier == 2.77


def test_single_run_rule_is_none_with_fewer_than_three_repeats() -> None:
    assert single_run_rule([5, 6]) is None


def test_single_run_rule_is_none_on_a_zero_mean() -> None:
    assert single_run_rule([0, 0, 0]) is None


def test_paired_t_bound_matches_student_sleep_data() -> None:
    bound = paired_t_bound(SLEEP_DIFFS)
    assert bound is not None
    assert (bound.n, bound.df, bound.confidence) == (10, 9, 0.95)
    assert bound.mean == pytest.approx(1.58, abs=THREE_DP)
    assert bound.half_width == pytest.approx(0.880, abs=THREE_DP)
    assert bound.lower == pytest.approx(0.700, abs=THREE_DP)
    assert bound.upper == pytest.approx(2.460, abs=THREE_DP)


def test_paired_t_bound_is_none_with_fewer_than_two_diffs() -> None:
    assert paired_t_bound([1.0]) is None


def test_paired_t_bound_rejects_an_untabulated_confidence() -> None:
    with pytest.raises(ValueError, match="confidence must be one of"):
        paired_t_bound([1.0, 2.0], confidence=0.9)


@pytest.mark.parametrize(
    ("mean", "clear"),
    [(1.0, True), (-1.0, True), (0.25, False)],
    ids=["above-zero", "below-zero", "straddles-zero"],
)
def test_t_bound_clear_of_zero(mean: float, clear: bool) -> None:
    bound = TBound(n=10, df=9, mean=mean, half_width=0.5, confidence=0.95)
    assert bound.clear_of_zero is clear


@pytest.mark.parametrize("confidence", [0.95, 0.99])
def test_t_critical_holds_the_rows_the_brief_names(confidence: float) -> None:
    assert set(T_CRITICAL[confidence]) == {*range(1, 31), 40, 60, 120, math.inf}


@pytest.mark.parametrize(
    ("df", "tabulated_df"),
    [(9, 9), (35, 30), (119, 60), (120, 120), (121, math.inf)],
    ids=["on-a-row", "between-rows", "below-120", "at-120", "above-120"],
)
def test_critical_value_takes_the_row_at_or_below_df(df: int, tabulated_df: float) -> None:
    assert _critical_value(0.99, df) == T_CRITICAL[0.99][tabulated_df]
