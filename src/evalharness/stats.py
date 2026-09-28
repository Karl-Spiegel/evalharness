"""Campaign statistics: paired flips, agreement, the single-run rule and the paired-t bound.

Every function is pure and uses the standard library only. A function returns `None` when its
input cannot support the statistic; the docstring states the condition. Absent is never zero.
"""

import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, Literal

type Verdict = Literal["pass", "fail", "unscored"]

# Two-sided critical values of Student's t: T_CRITICAL[confidence][df]. The 0.95 row is the
# 0.975 quantile and the 0.99 row is the 0.995 quantile.
# Source for df 1..30, 40, 60 and the infinity row (the normal quantile): NIST/SEMATECH
# e-Handbook of Statistical Methods, section 1.3.6.7.2, "Critical Values of the Student's t
# Distribution", https://www.itl.nist.gov/div898/handbook/eda/section3/eda3672.htm
# (columns 0.975 and 0.995). NIST tabulates df 1..100 and infinity, so df 120 comes from
# "Critical Values for Student's t-Distribution", Purdue University STAT 503,
# https://www.stat.purdue.edu/~lfindsen/stat503/t-Dist.pdf (columns 0.025 and 0.005), which
# agrees with NIST on every row the two tables share. Both fetched 2026-09-29.
# The key math.inf holds the normal quantile, used for every df above 120.
T_CRITICAL: Final[Mapping[float, Mapping[int | float, float]]] = {
    0.95: {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        11: 2.201,
        12: 2.179,
        13: 2.160,
        14: 2.145,
        15: 2.131,
        16: 2.120,
        17: 2.110,
        18: 2.101,
        19: 2.093,
        20: 2.086,
        21: 2.080,
        22: 2.074,
        23: 2.069,
        24: 2.064,
        25: 2.060,
        26: 2.056,
        27: 2.052,
        28: 2.048,
        29: 2.045,
        30: 2.042,
        40: 2.021,
        60: 2.000,
        120: 1.980,
        math.inf: 1.960,
    },
    0.99: {
        1: 63.657,
        2: 9.925,
        3: 5.841,
        4: 4.604,
        5: 4.032,
        6: 3.707,
        7: 3.499,
        8: 3.355,
        9: 3.250,
        10: 3.169,
        11: 3.106,
        12: 3.055,
        13: 3.012,
        14: 2.977,
        15: 2.947,
        16: 2.921,
        17: 2.898,
        18: 2.878,
        19: 2.861,
        20: 2.845,
        21: 2.831,
        22: 2.819,
        23: 2.807,
        24: 2.797,
        25: 2.787,
        26: 2.779,
        27: 2.771,
        28: 2.763,
        29: 2.756,
        30: 2.750,
        40: 2.704,
        60: 2.660,
        120: 2.617,
        math.inf: 2.576,
    },
}


@dataclass(frozen=True)
class PairedFlips:
    """Per-case agreement of two arms on cases that both judged.

    Attributes:
        n_paired: cases judged (pass or fail) on both sides.
        a_only: cases where a passes and b fails.
        b_only: cases where b passes and a fails.
        both: cases where both pass.
        neither: cases where both fail.
        excluded: cases unscored or missing on either side.
    """

    n_paired: int
    a_only: int
    b_only: int
    both: int
    neither: int
    excluded: int

    @property
    def net(self) -> int:
        """Return b_only minus a_only: positive when b wins more cases than it loses."""
        return self.b_only - self.a_only


def paired_flips(a: Mapping[str, Verdict], b: Mapping[str, Verdict]) -> PairedFlips:
    """Return the 2x2 paired table of two arms' verdicts, keyed by case_id.

    A case that is missing from either side, or `unscored` on either side, is excluded and
    counted in `excluded`. The function never returns `None`: an empty table is a real count.

    Worked example: the presidential approval table of Agresti (1990), Categorical Data
    Analysis, p. 350, as reproduced in the R `stats::mcnemar.test` documentation: 1600
    respondents, 794 approve twice, 150 approve then disapprove, 86 disapprove then approve,
    570 disapprove twice. With a = first survey and b = second survey, a_only = 150,
    b_only = 86, net = -64.
    """
    counts: Counter[tuple[Verdict, Verdict]] = Counter()
    excluded = 0
    for case_id in a.keys() | b.keys():
        va = a.get(case_id)
        vb = b.get(case_id)
        if va is None or vb is None or "unscored" in {va, vb}:
            excluded += 1
            continue
        counts[va, vb] += 1
    return PairedFlips(
        n_paired=counts.total(),
        a_only=counts["pass", "fail"],
        b_only=counts["fail", "pass"],
        both=counts["pass", "pass"],
        neither=counts["fail", "fail"],
        excluded=excluded,
    )


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    """Return Cohen's kappa for two raters who label the same items in the same order.

    Returns `None` when there are no items, when the two sequences differ in length, or when
    fewer than two categories appear over both raters (chance agreement is then 1 and kappa is
    0/0).

    Worked example: Cohen (1960), "A Coefficient of Agreement for Nominal Scales", Educational
    and Psychological Measurement 20(1), 37-46, Table 2 (p. 45): 200 items, three categories,
    observed agreement 140/200 = .70, chance agreement 82/200 = .41, kappa = .492.
    """
    n = len(a)
    if n < 1 or len(b) != n:
        return None
    count_a = Counter(a)
    count_b = Counter(b)
    if len(count_a.keys() | count_b.keys()) < 2:
        return None
    observed = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    chance = sum(count_a[k] * count_b[k] for k in count_a) / (n * n)
    return (observed - chance) / (1 - chance)


def _ordinal_ranks(values: set[str]) -> dict[str, int] | None:
    """Return each value's integer rank, or `None` when a value is not an integer string."""
    ranks: dict[str, int] = {}
    for value in values:
        try:
            ranks[value] = int(value)
        except ValueError:
            return None
    return ranks


def _coincidences(pairable: Sequence[Sequence[str]]) -> dict[tuple[str, str], Fraction]:
    """Return the coincidence matrix of the pairable units.

    Each ordered pair of values within a unit of m values adds 1 / (m - 1) to its cell.
    """
    coincidence: defaultdict[tuple[str, str], Fraction] = defaultdict(Fraction)
    for unit in pairable:
        weight = Fraction(1, len(unit) - 1)
        for i, c in enumerate(unit):
            for j, k in enumerate(unit):
                if i != j:
                    coincidence[c, k] += weight
    return coincidence


def _ordinal_delta(
    margins: Mapping[str, Fraction], ranks: Mapping[str, int]
) -> dict[tuple[str, str], Fraction]:
    """Return the ordinal squared difference for every pair of values.

    For values c <= k in rank order: (sum of n_g for g from c to k - (n_c + n_k) / 2) ** 2,
    with n_g the coincidence margins (Krippendorff 2011, section D).
    """
    order = sorted(margins, key=lambda v: ranks[v])
    delta: dict[tuple[str, str], Fraction] = {}
    for lo, c in enumerate(order):
        for hi in range(lo, len(order)):
            k = order[hi]
            between = sum((margins[order[g]] for g in range(lo, hi + 1)), Fraction(0))
            d = (between - (margins[c] + margins[k]) / 2) ** 2
            delta[c, k] = d
            delta[k, c] = d
    return delta


def krippendorff_alpha(
    units: Sequence[Sequence[str | None]],
    level: Literal["nominal", "ordinal"] = "nominal",
) -> float | None:
    """Return Krippendorff's alpha over units rated by any number of raters.

    `units[i]` holds the ratings of unit i, one per rater, `None` where a rater gave none. Only
    units with two or more ratings are pairable. At the ordinal level every value must be an
    integer string (for example the 0..5 `graded` score); the integers give the order.

    Returns `None` when fewer than two units have two or more ratings, when the pairable values
    hold only one distinct value (expected disagreement is 0 and alpha is 0/0), or, at the
    ordinal level, when a value is not an integer string.

    Worked example: Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability",
    University of Pennsylvania, section C: 4 observers, 12 units, 7 missing values; nominal
    alpha = 0.743, and section D gives the same data as ordinal, alpha = 0.815.
    """
    pairable = [[v for v in unit if v is not None] for unit in units]
    pairable = [unit for unit in pairable if len(unit) >= 2]
    if len(pairable) < 2:
        return None
    coincidence = _coincidences(pairable)
    margins: defaultdict[str, Fraction] = defaultdict(Fraction)
    for (c, _), o in coincidence.items():
        margins[c] += o
    if len(margins) < 2:
        return None
    if level == "nominal":
        delta = {(c, k): Fraction(int(c != k)) for c in margins for k in margins}
    else:
        ranks = _ordinal_ranks(set(margins))
        if ranks is None:
            return None
        delta = _ordinal_delta(margins, ranks)
    n = sum(margins.values(), Fraction(0))
    observed = sum((o * delta[pair] for pair, o in coincidence.items()), Fraction(0))
    expected = sum(
        (margins[c] * margins[k] * delta[c, k] for c in margins for k in margins), Fraction(0)
    )
    return float(1 - (n - 1) * observed / expected)


@dataclass(frozen=True)
class SingleRunRule:
    """The noise floor of repeated runs of one arm, and the single-run difference it supports.

    Attributes:
        n_repeats: the number of repeated runs.
        mean: the mean pass count over the repeats.
        sd: the sample standard deviation (n - 1) of the pass counts.
        cov: the coefficient of variation, sd / mean.
        threshold_cases: the smallest single-run difference the noise supports,
            multiplier * sd, in cases.
        multiplier: the factor applied to sd.
    """

    n_repeats: int
    mean: float
    sd: float
    cov: float
    threshold_cases: float
    multiplier: float


def single_run_rule(pass_counts: Sequence[int], multiplier: float = 2.77) -> SingleRunRule | None:
    """Return the single-run rule measured from repeated pass counts of one arm.

    The default multiplier 2.77 = 1.96 * sqrt(2). The difference of two independent runs with
    the same standard deviation sd has standard deviation sqrt(2) * sd, and 95% of such
    differences lie within 1.96 of those standard deviations of zero. A single-run difference
    smaller than 2.77 * sd is inside the noise. Derivation: Bland, "What is the origin of the
    formula for repeatability?", https://www-users.york.ac.uk/~mb55/meas/repeat.htm, and
    Bland & Altman (1996), "Measurement error", BMJ 313:744.

    Returns `None` when there are fewer than 3 repeats, or when the mean is 0 (the coefficient
    of variation is then undefined).

    Worked example: NIST Statistical Reference Datasets, univariate summary statistics,
    NumAcc1 (https://www.itl.nist.gov/div898/strd/univ/data/NumAcc1.dat): the values
    10000001, 10000003, 10000002 have certified mean 10000002 and certified sample standard
    deviation 1 (both exact), so threshold_cases = 2.77.
    """
    n = len(pass_counts)
    if n < 3:
        return None
    mean = statistics.fmean(pass_counts)
    if mean == 0:
        return None
    sd = statistics.stdev(pass_counts)
    return SingleRunRule(
        n_repeats=n,
        mean=mean,
        sd=sd,
        cov=sd / mean,
        threshold_cases=multiplier * sd,
        multiplier=multiplier,
    )


@dataclass(frozen=True)
class TBound:
    """A two-sided Student-t confidence bound on the mean of paired differences.

    Attributes:
        n: the number of paired differences.
        df: the degrees of freedom, n - 1.
        mean: the mean difference.
        half_width: the critical value times the standard error of the mean.
        confidence: the two-sided confidence level.
    """

    n: int
    df: int
    mean: float
    half_width: float
    confidence: float

    @property
    def lower(self) -> float:
        """Return the lower end of the bound."""
        return self.mean - self.half_width

    @property
    def upper(self) -> float:
        """Return the upper end of the bound."""
        return self.mean + self.half_width

    @property
    def clear_of_zero(self) -> bool:
        """Return True when the whole bound lies strictly above or strictly below zero."""
        return self.lower > 0 or self.upper < 0


def _critical_value(confidence: float, df: int) -> float:
    """Return the tabulated critical value for df.

    A df between two table rows takes the row below it, which has the larger critical value
    and so the wider, conservative bound. A df above 120 takes the normal quantile.
    """
    row = T_CRITICAL[confidence]
    if df > 120:
        return row[math.inf]
    return row[max(d for d in row if d <= df)]


def paired_t_bound(diffs: Sequence[float], confidence: float = 0.95) -> TBound | None:
    """Return the two-sided Student-t bound on the mean of paired differences.

    The half-width is t(confidence, n - 1) * s / sqrt(n), with s the sample standard deviation
    (n - 1). The critical value comes from `T_CRITICAL`; see `_critical_value` for df between
    rows and above 120.

    Returns `None` when there are fewer than 2 differences.

    Raises:
        ValueError: when `confidence` is not a key of `T_CRITICAL` (0.95 or 0.99).

    Worked example: Student's sleep data (Student 1908, "The probable error of a mean",
    Biometrika 6(1), 1-25; the R `datasets::sleep` data), 10 patients, differences of drug 2
    over drug 1. The paired t-test prints mean 1.58 and the 95% interval 0.7001142 to
    2.4598858 (Chang, "Cookbook for R", t-test, http://www.cookbook-r.com/Statistical_analysis/t-test/),
    a half-width of 0.880.
    """
    if confidence not in T_CRITICAL:
        msg = f"confidence must be one of {sorted(T_CRITICAL)}, got {confidence}"
        raise ValueError(msg)
    n = len(diffs)
    if n < 2:
        return None
    df = n - 1
    sd = statistics.stdev(diffs)
    return TBound(
        n=n,
        df=df,
        mean=statistics.fmean(diffs),
        half_width=_critical_value(confidence, df) * sd / math.sqrt(n),
        confidence=confidence,
    )
