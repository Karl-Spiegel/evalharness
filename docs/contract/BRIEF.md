# Brief for the contract and statistics lanes

This file is the fixed contract between the build lanes for issue #1. It was written before any lane launched. A lane that finds it wrong stops and reports; it does not amend this file.

## Boundaries every lane obeys

- Nothing from an employer repository or a hiring assignment enters this repo: no code, identifier, case name, fixture, price, result or number. Designs only, restated in this repo's words. `AGENTS.md` carries the rule.
- Build only what issue #1 names. No runner, adapter, judge call, calibration tool or exporter. No speculative fields, options or abstractions. A gap is filled by a later ticket; overbuilding is the failure mode.
- Standard library only for the statistics. No scipy, no numpy. Student-t critical values come from a small table with its source cited.
- The house rule: absent is never zero. A quantity with no input is `None` in code and `n/a` in output.
- `uv run poe check` passes before a lane reports done.

## The record: one result per case per arm per repeat

Field names are final. Types are JSON Schema draft 2020-12.

| Field | Type | Notes |
|---|---|---|
| `schema_version` | const `"1"` | |
| `case_id` | string | stable across arms and repeats |
| `arm` | string | the label of the configuration under test |
| `repeat` | integer ≥ 0 | 0 for a single run |
| `response_text` | string or null | null when the system produced no answer |
| `response_sha256` | string (64 hex) or null | of `response_text`; null when null |
| `criteria` | object: criterion name → verdict object | verdict object: `{ "verdict": "pass" \| "fail" \| "unscored", "gating": bool, "reason": string \| null, "graded": integer 0..5 \| null }` |
| `overall` | `"pass"` \| `"fail"` \| `"unscored"` | computed by the harness: `fail` if any gating criterion is `fail`; else `unscored` if any gating criterion is `unscored`; else `pass`. Never supplied by a judge. |
| `judge` | object or null | `{ "model": string, "prompt_sha256": string, "provider": string \| null }`; null when unjudged |
| `cost` | object | `{ "basis": "priced" \| "self_hosted" \| "unpriced", "amount": number \| null, "currency": string \| null, "price_snapshot_date": date \| null }`. `amount` is non-null only when `basis` is `priced`. |
| `latency` | object | `{ "wall_ms": integer, "harness_ms": integer }`. The model latency is `wall_ms - harness_ms`, derived in reports, never stored. |
| `failure_class` | `"none"` \| `"no_answer"` \| `"parse_error"` \| `"tool_error"` \| `"iteration_cap"` \| `"timeout"` \| `"framework_error"` | |
| `provenance` | object | `{ "served_model": string \| null, "provider": string \| null, "sampling": object \| null, "weights_digest": string \| null }` |
| `started_at` | date-time | UTC |

`additionalProperties: false` at every level.

## Coverage: one record per run

| Field | Type |
|---|---|
| `schema_version` | const `"1"` |
| `arm` | string |
| `case_set_sha256` | string: sha256 over the sorted case ids and their definitions |
| `cases_defined` | integer |
| `cases_run` | integer |
| `cases_judged` | integer |
| `clock` | `{ "pinned_at": date-time \| null, "source": string \| null }` |
| `fixture_manifest_sha256` | string or null |
| `checks` | array of `{ "name": string, "result": "ok" \| "warn" \| "refuse", "reason": string \| null }` |
| `commit` | string or null: the commit under test |

## The four rules the contract settles

Write each as a proposed row in `docs/DECISIONS.md` in the register's table shape. Proposed, never admitted: only Karl admits.

1. **Headline denominator.** The headline pass rate is passes over every case the arm ran. A case with `overall` of `fail`, `unscored`, or no record because it produced no answer counts in the denominator and not in the numerator. Per-criterion detail is passes over the judged count, where judged means `overall` is `pass` or `fail`. Rejected: dividing by the gradable count (an arm scores better for crashing).
2. **`overall` is computed by the harness** as described in the record table. Rejected: letting the judge return `overall` (the judge's aggregation is unverifiable and drifts with the prompt).
3. **Cost basis is tri-state.** `priced` with an amount and a price snapshot date, `self_hosted`, or `unpriced`. A zero amount is legal only under `priced`, with the date. Rejected: a numeric field defaulting to 0 (absent reads as free).
4. **Latency stores raw wall clock and harness time.** Reports derive model latency. Rejected: storing a corrected value alone (records before and after a correction change become incomparable).

## The protocol: twelve steps

`docs/protocol.md` states these in this order, one short paragraph each, and states the denominator rule exactly once, in step 7.

1. State the question and name the arms before any code changes.
2. Pin the commit under test in the campaign log before the first case.
3. Gate the run on pre-flight checks: credentials, endpoints, fixture clock, fixture manifest, scope against data. A failed check refuses loudly; a warning is recorded in coverage, never printed alone.
4. Assert provenance after every run: served model, provider, sampling, reasoning settings, weights digest where one exists.
5. Require the full case count or abort the arm.
6. Archive a superseded result with a written reason beside it. Never delete.
7. Decide the headline denominator once as a ruling and make every report obey it: every case the arm ran.
8. Interleave arms under comparison.
9. Measure the noise floor before trusting a single-run delta; measure quality noise apart from latency noise.
10. Keep one append-only campaign log. A correction is a new entry that cites the old one.
11. Separate the hand-written summary header from generated tables and label which is which.
12. Land an instrument fix as its own change, and append a correction to every artefact and ruling measured on the old instrument.

## `src/evalharness/stats.py`: signatures

All functions are pure, typed, stdlib only. Every function returns `None` when its input cannot support the statistic, and the docstring says when.

```python
type Verdict = Literal["pass", "fail", "unscored"]

@dataclass(frozen=True)
class PairedFlips:
    n_paired: int          # cases judged (pass or fail) on both sides
    a_only: int            # a pass, b fail
    b_only: int            # b pass, a fail
    both: int
    neither: int
    excluded: int          # cases unscored or missing on either side
    @property
    def net(self) -> int: ...  # b_only - a_only

def paired_flips(a: Mapping[str, Verdict], b: Mapping[str, Verdict]) -> PairedFlips: ...
    # keyed by case_id; a case missing from either side is excluded and counted

def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None: ...
    # None when len < 1, lengths differ, or fewer than two categories appear overall
    # worked example: Cohen (1960) or the standard two-rater 2x2 example; cite the source and the expected value

def krippendorff_alpha(units: Sequence[Sequence[str | None]], level: Literal["nominal", "ordinal"] = "nominal") -> float | None: ...
    # units[i] is the ratings of unit i by each rater, None for missing
    # None when fewer than two units have two or more ratings
    # worked example: Krippendorff, "Computing Krippendorff's Alpha-Reliability" (2011), the nominal example; cite and match to 3 dp

@dataclass(frozen=True)
class SingleRunRule:
    n_repeats: int
    mean: float
    sd: float
    cov: float
    threshold_cases: float   # the smallest single-run difference the noise supports
    multiplier: float

def single_run_rule(pass_counts: Sequence[int], multiplier: float = 2.77) -> SingleRunRule | None: ...
    # None when fewer than 3 repeats
    # threshold_cases = multiplier * sd (sample sd, n-1); cov = sd / mean; mean of 0 gives cov None-equivalent: return None
    # 2.77 derives from 1.96 * sqrt(2): the 95% two-sided bound on the difference of two draws with equal sd; state the derivation in the docstring

@dataclass(frozen=True)
class TBound:
    n: int
    df: int
    mean: float
    half_width: float
    confidence: float
    @property
    def lower(self) -> float: ...
    @property
    def upper(self) -> float: ...
    @property
    def clear_of_zero(self) -> bool: ...

def paired_t_bound(diffs: Sequence[float], confidence: Literal[0.95, 0.99] = 0.95) -> TBound | None: ...
    # None when n < 2; sample sd; critical value from T_CRITICAL[confidence][df], df capped at the table's largest row with the normal quantile beyond
    # worked example: any standard paired-t textbook example; cite and match half-width to 3 dp

T_CRITICAL: Mapping[float, Mapping[int, float]]  # df 1..30, 40, 60, 120, and "inf" as the normal quantile; cite the table source
```

## Fixture files

`tests/fixtures/arm-a.jsonl` and `arm-b.jsonl`: synthetic, twelve cases with the same ids on both sides, `repeat` 0, three criteria (`correctness`, `completeness` gating; `faithfulness` gating), invented prompts about a fictional inventory system. Include on at least one side: one `no_answer` case with null response; one case with an `unscored` criterion; a `self_hosted` cost and an `unpriced` cost; one `parse_error`. Every record validates against the schema. No real model output, no real prices.

## `evalharness verdict`

`uv run evalharness verdict --a <jsonl> --b <jsonl> [--label-a A --label-b B]` reads two record files, validates each line against the schema (a bad line is an error with its line number, exit 2), and prints one line:

```
A 7/12 (58%)  B 8/12 (67%)  | judged A 7/11 B 8/11 | correctness A 9/11 B 10/11 · completeness A 8/11 B 8/11 · faithfulness A 10/11 B 9/11 | paired net +1 (B>A 2, A>B 1, n 11, excluded 1) | bound n/a (1 repeat)
```

The headline divides by `cases_run` (the count of records for that arm). The detail divides by the judged count. `bound` needs at least two repeats per arm; with one it prints `n/a (1 repeat)`. Any quantity whose input is absent prints `n/a`, never `0` or `0%`. A test feeds two files with no judged records and asserts every judged quantity prints `n/a`.

## Lane assignments

- **Contract lane:** `docs/contract/record.schema.json`, `docs/contract/coverage.schema.json`, `docs/protocol.md`, the four proposed rows appended to `docs/DECISIONS.md`, and `README.md`. No Python. Two tests are allowed: that each schema parses and that each fixture file validates, using `jsonschema` only if the lane can justify the dependency in its report; otherwise a minimal validator in `tests/` is acceptable but must not become a package module.
- **Statistics lane:** `src/evalharness/stats.py` and `tests/test_stats.py`, plus the two fixture files. No CLI changes.
- **Verdict lane (after merge):** `src/evalharness/verdict.py`, the `verdict` subcommand in `cli.py` replacing the sample `greeting`, `tests/test_verdict.py`. Deletes `greeting` and its test.

## Clarifications after the lane reports (2026-09-29)

The body above stays as launched. These settle what the contract lane reported as ambiguous.

- A case that produced no answer has a record with `failure_class` `no_answer` and a null response. "Cases run" is the count of records for the arm. There is no such thing as a case with no record.
- `criteria` uses `additionalProperties` to hold the verdict schema; `provenance.sampling` stays open. Everywhere else `additionalProperties: false` holds.
- Under `priced`, `amount`, `currency` and `price_snapshot_date` are all non-null. Under the other bases `amount` is null.
- Per-criterion detail divides, for each criterion, by the count of cases where that criterion's verdict is `pass` or `fail`. The register row 1 says so.
- All three fixture criteria gate `overall`.
- The verdict command trusts `overall` as stored; recomputing it belongs to the runner (#2).
- A test that finds no fixtures fails; it never skips.
- `paired_t_bound(confidence: float = 0.95)`: Python `Literal` cannot hold floats; a confidence not in the table raises `ValueError` (caller error, not `None`).
- `T_CRITICAL: Mapping[float, Mapping[int | float, float]]`, with `math.inf` as the key for the normal-quantile row. A df between table rows uses the row below (the wider bound); above 120 the normal quantile.
- A `no_answer` record carries `unscored` on every criterion and `judge: null`, so `overall` is `unscored`; it counts in the headline denominator.
- The example verdict line in the body computed per-criterion cells under the older judged-count rule. Under the settled rule the fixtures print `correctness A 9/11 B 11/12 · completeness A 8/11 B 9/12 · faithfulness A 10/11 B 9/11`; the fixtures are unchanged so the difference stays visible.
- Pairs are keyed by `repeat:case_id`, because a case id recurs once per repeat. A duplicate `(case_id, repeat)` within one file is an error, exit 2.
- Counts of records that exist print as real numbers even when zero; only a quantity with no input prints `n/a`.
- The bound prints as `bound <net> ± <half-width> pp (<confidence>, <n> repeats)`, in percentage points of pass rate per repeat.
- The schema is located through the package's `__file__`, so the command works from a source checkout and not from an installed wheel. Known limit; the first ticket that ships a wheel moves the schemas.
- The verdict command validates at runtime, so the minimal validator lives in `evalharness.schema`, not in a test file. `jsonschema` was rejected: the two schemas use a small set of keywords, and the validator raises on any keyword it does not know, so a schema that outgrows it fails loud.
- The record schema enforces two invariants the body only described: `criteria` has at least one entry, and a record with `judge: null` has `overall: unscored`. The full `overall` recomputation stays with the runner (#2).

## Override after review (2026-09-29)

Karl overrode the body's "standard library only" rule for the statistics: as with cryptography, never roll your own when a strong reference implementation exists. `cohen_kappa` calls `statsmodels.stats.inter_rater.cohens_kappa`, `krippendorff_alpha` calls `krippendorff.alpha`, and `paired_t_bound` takes its quantile from `scipy.stats.t.ppf`, so `T_CRITICAL` and the row-below rule are gone and any confidence in (0, 1) is accepted. `paired_flips` (a count) and `single_run_rule` (a minted constant) stay as this repo's code. The worked-example tests now prove the references are called right.
