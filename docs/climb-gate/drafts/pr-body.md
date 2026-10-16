## Decisions

1. **Acceptance threshold for a climb step.** Proposed default: the candidate wins more cases than it loses (`net > 0`) and the two-sided exact McNemar p over the per-case flips is below 0.05, fixed before any score of a future climb is seen; a significant loss rejects the candidate. Karl accepts or rules; the answer goes under "Seam 1 answers" in `docs/climb-gate/plan.md`. No row proposed here.
2. **A deterministic grader recorded as the judge.** The schema forces `overall` to `unscored` when `judge` is null, so an exact-match grader is recorded as a judge (`model: exact-match`, digest of the rule). Current reading, unbound, stays on the ticket.
3. **Interleaved arm execution** (protocol step 8) in the climb runner: a follow-up ticket, drafted at `docs/climb-gate/drafts/ticket-interleave.md`. Not in this PR.

## What this PR adds

Stage 1 of the climb-gate program (`docs/climb-gate/plan.md`): the one statistic the arm C prompt climb (issue #12, the decision-only models spike) lacked.

- `stats.py`: `exact_mcnemar(flips)`, the exact McNemar test over the discordant cases of a `PairedFlips`, through `statsmodels.stats.contingency_tables.mcnemar(exact=True)`. Returns `None` when no case is discordant; the reference call would print 1.0, and a test that could not run is not a p-value. Worked example: Zar's deer-legs sign test, p = 0.109375.
- `verdict.py`: one new segment after the paired flips, `per-case net +5 (v2>v1 14, v1>v2 9, cases 200, p 0.541)`, with `n/a` for the p when no case is discordant and for every count when no case is paired. The table reads one pair per case across its shared repeats (`case_flips`), not the per-repeat pairs of the flips segment, so repeating every case does not grow the sample, and the segment carries its own direction because the two tables can disagree. No other segment changes.
- `README.md` and `docs/protocol.md` step 9: one sentence each naming the per-case test as the climb-step gate and the repeat bound as the repeat-noise measure.
- `docs/climb-gate/plan.md`: the program plan, both stages and seams.

On branch `spike/12-decision-models`, `spikes/decision-models/CLIMB-C.md` now carries this segment's output in its tables (commit 722a511) in place of a sign test computed by hand.

## Why

The climb's two steps were judged by paired flips over 400 case-runs. The kit printed the counts but no test; the repeat-based bound read `±15.9 pp` at two repeats. The decision was made by a sign test outside the kit. This PR moves it inside, so a climb can gate on the line.

## Proof

`uv run poe check` green. New tests: the published worked example, the no-discordant `None`, `case_flips` counting a repeated case once and deciding a case by passes over shared repeats, a verdict test proving the segment does not change when every case is repeated, and one where the per-case direction opposes the case-run net. Three verdict fixture lines updated for the new segment.

## Deliberately absent

A bootstrap interval on the pass-rate difference. A confidence-interval segment. Any change to the record or coverage schema. Any change to the climb runner. Interleaved arm execution (follow-up ticket). No dependency added: statsmodels and scipy were already in use.

## Stacking

Against `contract-and-stats` (PR #9, the contract and statistics lane). Re-target to `main` when #9 merges.
