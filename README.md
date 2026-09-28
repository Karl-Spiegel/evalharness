# evalharness

A record-first harness for LLM evals. Each case run makes one result record. Statistics and verdicts read those records and nothing else. A value that is absent stays absent; it never becomes zero.

```
uv sync            # install (Python 3.14 via .python-version, tools from mise.toml)
uv run poe check   # the gate: lint, types, tests, dependency hygiene
uv run poe hooks   # arm the git hooks once per clone
```

## What a record carries

One record per case, per arm, per repeat. The full contract is `docs/contract/record.schema.json`.

- `case_id`, `arm`, `repeat`: which case, which configuration, which run.
- `response_text` and `response_sha256`: the answer and its digest, or null for no answer.
- `criteria`: one verdict per criterion, `pass`, `fail` or `unscored`, and whether it gates.
- `overall`: the case verdict, computed by the harness.
- `judge`: the judge model and the digest of its prompt, or null when unjudged.
- `cost`: a basis of `priced`, `self_hosted` or `unpriced`, and an amount only when priced.
- `latency`: raw wall clock and harness time, in milliseconds.
- `failure_class`: `none`, or how the run failed.
- `provenance`: the model and provider that served the case, the sampling settings, the weights digest.
- `started_at`: the UTC start time.

Each run of an arm also writes one coverage record (`docs/contract/coverage.schema.json`): the case-set digest, the counts of cases defined, run and judged, the pinned clock, and every pre-flight check with its result.

## Why absent is never zero

A zero that means "no data" looks the same as a real zero. An unpriced run with cost 0 reads as free. An arm with no judged cases at 0% reads as a bad arm, not a missing measurement. So a missing value is null in a record and `n/a` in output, and a cost states its basis.

## Why the judge does not compute `overall`

The judge returns one verdict per criterion. The harness computes `overall` from them: `fail` if any gating criterion fails, else `unscored` if any gating criterion is unscored, else `pass`. A judge's own aggregation cannot be checked, and it changes when its prompt changes. A rule in code can be read and tested.

## Why the headline divides by every case run

The headline pass rate is passes over every case the arm ran. A case that failed, stayed unscored, or gave no answer counts against the arm. If the denominator were only the cases the judge could grade, an arm would score better by crashing. Per-criterion detail divides, for each criterion, by the cases where the judge scored that criterion, because it describes the answers the judge saw.

## What exists today

- The contract: the record and coverage schemas in `docs/contract/`, the campaign protocol in `docs/protocol.md`, and four proposed rulings in `docs/DECISIONS.md`.
- The statistics: `src/evalharness/stats.py`, with paired flips, Cohen's kappa, Krippendorff's alpha, the single-run rule and the paired Student-t bound, each tested against a published example.
- The verdict command: `uv run evalharness verdict --a A.jsonl --b B.jsonl` prints one line that compares two arms.

## What is deliberately absent

Each of these has its own issue. Nothing here stands in for them.

- The runner: #2.
- Adapters for the systems under test: #3.
- Judge calls: #4.
- Calibration and labelling: #5.
- Fixture gates: #6.
- The exporter: #7.
- A consumer of the records: #8.

Agent contract: `AGENTS.md`. Rulings: `docs/DECISIONS.md`.
