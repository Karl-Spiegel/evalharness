"""Campaign statistics: paired flips, their exact test, agreement, the single-run rule, the t bound.

Every function is pure. Agreement coefficients and the t quantile come from reference
implementations (statsmodels, the `krippendorff` package, scipy); this module writes only the
paired count and the constant it minted, and its tests prove the reference is called right.
A function returns `None` when its input cannot support the statistic; the docstring states the
condition. Absent is never zero.
"""

import math
import statistics
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from krippendorff import alpha as _krippendorff_alpha
from scipy.stats import t as _student_t
from statsmodels.stats.contingency_tables import mcnemar as _mcnemar
from statsmodels.stats.inter_rater import cohens_kappa as _cohens_kappa

type Verdict = Literal["pass", "fail", "unscored"]


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


def case_flips(
    a: Mapping[str, Mapping[int, Verdict]], b: Mapping[str, Mapping[int, Verdict]]
) -> PairedFlips:
    """Return the paired table over cases, each case decided once across its shared repeats.

    `a` and `b` map a case id to its verdicts by repeat. For each case, the repeats both arms
    judged (pass or fail) are the shared repeats; the arm with more passes over them wins the
    case, a tie with passes is `both`, a tie without is `neither`. A case with no shared judged
    repeat is excluded. One case is one pair, however many repeats it ran, so a test over this
    table never counts a repeated case twice. The function never returns `None`: an empty table
    is a real count.

    Worked example: ten cases run once, b passes eight that a fails and a passes two that b
    fails: a_only = 2, b_only = 8. The same ten cases run twice with identical outcomes give the
    same table, where the per-repeat table of `paired_flips` would give a_only = 4, b_only = 16.
    """
    a_only = b_only = both = neither = excluded = 0
    for case_id in a.keys() | b.keys():
        ra, rb = a.get(case_id, {}), b.get(case_id, {})
        shared = [r for r in ra.keys() & rb.keys() if ra[r] != "unscored" and rb[r] != "unscored"]
        if not shared:
            excluded += 1
            continue
        pa = sum(ra[r] == "pass" for r in shared)
        pb = sum(rb[r] == "pass" for r in shared)
        if pb > pa:
            b_only += 1
        elif pa > pb:
            a_only += 1
        elif pa:
            both += 1
        else:
            neither += 1
    return PairedFlips(
        n_paired=a_only + b_only + both + neither,
        a_only=a_only,
        b_only=b_only,
        both=both,
        neither=neither,
        excluded=excluded,
    )


@dataclass(frozen=True)
class ExactMcNemar:
    """The exact McNemar test on the discordant cases of a paired table.

    Attributes:
        discordant: cases the two arms decided differently, a_only + b_only.
        p_value: the two-sided exact binomial p-value that b wins a discordant case half the time.
    """

    discordant: int
    p_value: float


def exact_mcnemar(flips: PairedFlips) -> ExactMcNemar | None:
    """Return the exact McNemar test over the discordant cases of `flips`.

    The test is the sign test on the discordant pairs: under the null, each case the arms
    decide differently falls to b with probability one half. Give it the table of `case_flips`,
    one pair per case, not the per-repeat table of `paired_flips`: repeats of one case are not
    independent pairs, and pooling them inflates the sample. The test is two-sided; it says
    the arms differ, not which is better. Read the direction from `PairedFlips.net`. The
    p-value comes from `statsmodels.stats.contingency_tables.mcnemar(exact=True)`, which reads
    only the off-diagonal counts. This is the per-case gate of a climb step; the paired-t
    bound measures repeat noise and needs several repeats before it says anything.

    Returns `None` when there are no discordant cases: the reference call would print 1.0, and a
    test that could not run is not a p-value.

    Worked example: the matched-pairs sign test of Zar (1999), Biostatistical Analysis, 4th ed.,
    as given on Wikipedia, "Sign test", section "Example of two-sided sign test for matched
    pairs": 10 deer, the right hind leg longer in 8 and the left in 2, two-sided p = 0.109375.
    """
    discordant = flips.a_only + flips.b_only
    if discordant == 0:
        return None
    result: object = _mcnemar([[0, flips.b_only], [flips.a_only, 0]], exact=True)
    p_value = getattr(result, "pvalue", None)  # statsmodels returns an untyped Bunch
    if not isinstance(p_value, float | np.floating):
        msg = f"statsmodels returned {type(p_value).__name__} for pvalue, not a number"
        raise TypeError(msg)
    return ExactMcNemar(discordant=discordant, p_value=float(p_value))


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    """Return Cohen's kappa for two raters who label the same items in the same order.

    The coefficient is `statsmodels.stats.inter_rater.cohens_kappa` over the square
    contingency table of the two label sequences; this function builds the table.

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
    categories = sorted(set(a) | set(b))
    if len(categories) < 2:
        return None
    index = {c: i for i, c in enumerate(categories)}
    table = np.zeros((len(categories), len(categories)), dtype=np.int64)
    for x, y in zip(a, b, strict=True):
        table[index[x], index[y]] += 1
    kappa: object = _cohens_kappa(table, return_results=False)
    if not isinstance(kappa, float | np.floating):
        msg = f"statsmodels returned {type(kappa).__name__}, not a number"
        raise TypeError(msg)
    return float(kappa)


def krippendorff_alpha(
    units: Sequence[Sequence[str | None]],
    level: Literal["nominal", "ordinal"] = "nominal",
) -> float | None:
    """Return Krippendorff's alpha over units rated by any number of raters.

    The coefficient is `krippendorff.alpha` (Castro, https://github.com/pln-fing-udelar/fast-krippendorff)
    over a raters-by-units matrix; this function builds the matrix and codes the values.
    `units[i]` holds the ratings of unit i, one per rater, `None` where a rater gave none. At
    the ordinal level every value must be an integer string (for example the 0..5 `graded`
    score); the integers give the order.

    Returns `None` when fewer than two units have two or more ratings, when the pairable values
    hold only one distinct value (expected disagreement is 0 and alpha is 0/0), or, at the
    ordinal level, when a value is not an integer string.

    Worked example: Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability",
    University of Pennsylvania, section C: 4 observers, 12 units, 7 missing values; nominal
    alpha = 0.743, and section D gives the same data as ordinal, alpha = 0.815.
    """
    pairable = [unit for unit in units if sum(v is not None for v in unit) >= 2]
    if len(pairable) < 2:
        return None
    values = {v for unit in pairable for v in unit if v is not None}
    if len(values) < 2:
        return None
    if level == "ordinal":
        try:
            code = {v: float(int(v)) for v in values}
        except ValueError:
            return None
    else:
        code = {v: float(i) for i, v in enumerate(sorted(values))}
    raters = max(len(unit) for unit in pairable)
    matrix = np.full((raters, len(pairable)), np.nan)
    for j, unit in enumerate(pairable):
        for i, v in enumerate(unit):
            if v is not None:
                matrix[i, j] = code[v]
    return float(_krippendorff_alpha(reliability_data=matrix, level_of_measurement=level))


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


def paired_t_bound(diffs: Sequence[float], confidence: float = 0.95) -> TBound | None:
    """Return the two-sided Student-t bound on the mean of paired differences.

    The half-width is t(confidence, n - 1) * s / sqrt(n), with s the sample standard deviation
    (n - 1) and the critical value the (1 + confidence) / 2 quantile of Student's t from
    `scipy.stats.t.ppf`.

    Returns `None` when there are fewer than 2 differences.

    Raises:
        ValueError: when `confidence` is not strictly between 0 and 1.

    Worked example: Student's sleep data (Student 1908, "The probable error of a mean",
    Biometrika 6(1), 1-25; the R `datasets::sleep` data), 10 patients, differences of drug 2
    over drug 1. The paired t-test prints mean 1.58 and the 95% interval 0.7001142 to
    2.4598858 (Chang, "Cookbook for R", t-test, http://www.cookbook-r.com/Statistical_analysis/t-test/),
    a half-width of 0.880.
    """
    if not 0 < confidence < 1:
        msg = f"confidence must be strictly between 0 and 1, got {confidence}"
        raise ValueError(msg)
    n = len(diffs)
    if n < 2:
        return None
    df = n - 1
    critical = float(_student_t.ppf((1 + confidence) / 2, df))
    return TBound(
        n=n,
        df=df,
        mean=statistics.fmean(diffs),
        half_width=critical * statistics.stdev(diffs) / math.sqrt(n),
        confidence=confidence,
    )
