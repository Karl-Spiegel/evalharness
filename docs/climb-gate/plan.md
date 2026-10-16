# Climb gate: evalharness as the accept/reject gate of a hill-climb

Plan for the program of work that started 2026-10-16 in session `try-hill-climb-optimizer`.
Written by the `goal-prompt` skill. Karl arms each stage's goal himself.

## Settled scope

The program answers one question: can the kit gate a hill-climb step, and what does it lack?
Two climbs ran as the trial. The arm C prompt climb (issue #12, the decision-only models spike)
finished: the calibration gain did not replicate on held-out, arm C keeps v1, finding in
`spikes/decision-models/CLIMB-C.md` on branch `spike/12-decision-models`. The skill-description
climb (skill-creator `run_loop.py` on `refine-prompt`) stopped twice: once invalid (three
measurement traps, now fixed), once killed by the host for memory.

What the trial showed the kit lacks:

- A per-case paired test. The `verdict` line's paired-t bound runs over repeats and is useless
  under about five repeats (`±15.9 pp` at two, `n/a` at one). The per-case flips carried every
  decision, but the kit prints counts only, no p-value. The two climb steps were judged by a
  sign test computed by hand outside the kit.
- A stated place for a deterministic grader. The schema forces `overall` to `unscored` when
  `judge` is null, so an exact-match grader is recorded as a judge. Boundary choice, in the
  runner docstring. Not a row.
- Protocol step 8 (interleave the arms) was not followed by the climb runner: arms ran one after
  the other. Step 9 (noise floor first) was followed only through the two repeats.

Rulings consulted: `docs/DECISIONS.md` has four proposed rows (denominator, `overall`, cost
basis, latency). None covers the climb-step statistic or its acceptance threshold. Both are
unrecorded. This plan does not settle them; stage 1's PR proposes a default in its Decisions
block and Karl rules at the seam.

## Stages

### Stage 1: the per-case paired test in the kit (one PR)

Adds the one statistic the climb needed and removes the hand computation. Stacked on
`contract-and-stats` (PR #9, the contract and statistics lane, open against `main`); re-targeted
to `main` when #9 merges.

- `src/evalharness/stats.py`: one function, the exact McNemar test over the discordant flips
  (the sign test on `b_only` against `a_only`), calling the reference implementation
  (`scipy.stats.binomtest` or `statsmodels.stats.contingency_tables.mcnemar`, whichever the
  worked example checks cleanly). Returns `None` when there are no discordant pairs. A worked
  example from a published source is the test, per `AGENTS.md`.
- `src/evalharness/verdict.py`: the line gains one segment after the paired flips: the p-value
  and the discordant count, `n/a` when there are none. No other segment changes.
- `README.md` and `docs/protocol.md` step 9: name the per-case test as the climb-step gate and
  the repeat bound as the repeat-noise measure, in one sentence each.
- `spikes/decision-models/CLIMB-C.md`: the p-values in its tables come from the kit's command
  over the records in `spikes/decision-models/out/`, and the sentence "computed by hand" goes.
  The records stay untracked; the finding quotes the command.

Riskiest step first: the worked example. If no published McNemar or sign-test example
reproduces through the reference call within one hour, the stage stops with a report.

Deliberately absent: a bootstrap interval on the pass-rate difference, a confidence interval
segment, any change to the record or coverage schema, any change to the climb runner, and
interleaved arm execution (a runner concern, recorded as a follow-up).

### Seam 1: PR review of stage 1

Karl reviews the diff. The PR body opens with a Decisions block:

1. Acceptance threshold for a climb step: proposed default, two-sided p below 0.05 on the
   per-case test, fixed before any future climb's scores are seen. Karl accepts or rules.
2. Grader as judge for deterministic grading: current reading, unbound, stays on the ticket.
3. Interleaving in the climb runner: follow-up ticket, not in this PR.

Reviewer per the review rule in Karl's global `CLAUDE.md`: Codex `gpt-6-astra`, since Claude
built the change, through the `review-loop` skill. Overbuilding is an explicit criterion.

### Stage 2: the skill-description climb, rerun

Blocked twice: the host was at 56 of 60 GB with the clawdbot replay running, and the one clean
iteration showed zero triggers on all 36 should-trigger runs for the original description, so
the lever under test may be absent, not weak. Karl decides before this stage runs:

- rerun as is (about 300 Opus sessions, 25 minutes, expect a flat result), or
- change what is measured: queries that name the skill's job, or a skill with marginal
  triggering (`ticket` fired first-turn in the control), or
- drop the stage.

Workspace: `~/.cache/tmp/claude-1000/-home-trix-proj/34a8d2e3-bc5d-4ffa-9c72-7aee7c1edcdb/scratchpad/climb`
(patched detector in `patched/`, namespace wrapper `with-hidden-skill.sh`, eval set
`trigger-eval.json`, filtered skills copy `skills-filtered/`, empty project root `proj/`).
Setup facts are in memory (`skill-trigger-eval-isolation`). The stage's goal is drafted at seam
2, when Karl's choice is in.

Artefacts when it runs: `results3/` and `report3.html` in the workspace; a one-page finding at
`docs/climb-gate/skill-climb.md` that exports the loop's per-query results as kit records and
gates iteration N against N-1 with the stage 1 segment.

### Seam 2: Karl's choice for stage 2

The three options above, with the recommendation: change what is measured, or drop it. The
spend is Opus quota, not dollars.

## Out of this program

- Arms A, B, D, E, F, G of issue #12. They are the spike's own work.
- The claude-api skill's `hillclimb` guide layout and report builder. The kit's records are the
  layout; the guide's discipline (train/test split, one change per round, held-out once) was used.
- A reusable climb command or skill in the kit. No consumer yet beyond the two trials.

## Goal texts

Stage 1 (ready to arm):

> Stage 1 of the climb-gate program is done per docs/climb-gate/plan.md: a pull request is open against `contract-and-stats` in Karl-Spiegel/evalharness with CI green, stacked on PR #9 (the contract and statistics lane) and to be re-targeted to main when #9 merges: `src/evalharness/stats.py` has one per-case paired test over the discordant flips (exact McNemar, a scipy or statsmodels reference call, None with no discordant pairs) with a published worked-example test; the `verdict` line renders its p-value and discordant count as one new segment after the paired flips, `n/a` when there are none, and no other segment changes; README.md and docs/protocol.md step 9 each gain one sentence naming the per-case test as the climb-step gate and the repeat bound as the repeat-noise measure; the tables in spikes/decision-models/CLIMB-C.md on branch spike/12-decision-models carry p-values produced by the kit's command over the records in spikes/decision-models/out/ and the hand computation is gone; the PR body opens with a Decisions block proposing two-sided p below 0.05 as the climb-step acceptance threshold for Karl to accept or rule, lists grader-as-judge as unbound, and names as deliberately absent a bootstrap interval, a confidence-interval segment, any schema change, any climb runner change, and interleaved arm execution (follow-up ticket drafted under docs/climb-gate/drafts/); the riskiest step, the worked example, runs first inside one hour and the stage stops with a report if it fails; review follows the review rule in Karl's global CLAUDE.md with overbuilding as a criterion; no dependency is added without saying why in the PR; nothing beyond that; the scope rule in AGENTS.md applies to every agent that works on it.

Stage 2: drafted at seam 2, unless the whole-program goal below is armed instead.

Whole program (one goal, both stages, seams as recorded stops; Karl asked for this form):

> The climb-gate program is done per docs/climb-gate/plan.md, both stages: STAGE 1: a pull request is open against `contract-and-stats` in Karl-Spiegel/evalharness with CI green, stacked on PR #9 (the contract and statistics lane) and to be re-targeted to main when #9 merges, in which `src/evalharness/stats.py` has one per-case paired test over the discordant flips (exact McNemar, a scipy or statsmodels reference call, None with no discordant pairs) with a published worked-example test, the `verdict` line renders its p-value and discordant count as one new segment after the paired flips with `n/a` when there are none and no other segment changed, README.md and docs/protocol.md step 9 each gain one sentence naming the per-case test as the climb-step gate and the repeat bound as the repeat-noise measure, the tables in spikes/decision-models/CLIMB-C.md on branch spike/12-decision-models carry p-values produced by the kit's command over the records in spikes/decision-models/out/ with the hand computation gone, and the PR body opens with a Decisions block proposing two-sided p below 0.05 as the climb-step acceptance threshold and listing grader-as-judge as unbound; the worked example runs first inside one hour and the program stops with a report if it fails; SEAM 1: the session stops and waits for Karl's review of that PR and his ruling on the threshold, recorded under "Seam 1 answers" in the plan file, and the review follows the review rule in Karl's global CLAUDE.md with overbuilding as a criterion; STAGE 2: the skill-description climb runs on the `ticket` skill unless Karl records a different choice under "Seam 2 answers" in the plan file, from the empty project root in the climb workspace with the patched detector, the real skill hidden by the namespace wrapper, a fresh 20-query eval set of ten should-trigger and ten should-not reviewed by Karl before the first run, three runs per query, at most five iterations, and it starts only when the host shows at least 16 GB available and pages Karl otherwise; every iteration's per-query results are exported as kit records under the workspace and each iteration is gated against the previous one with the stage 1 segment at the seam 1 threshold; the finding is one page at docs/climb-gate/skill-climb.md with the iteration table, the gate verdicts and the best description; the climbed description is written as a draft diff under docs/climb-gate/drafts/ and not applied to the real skill; nothing is pushed or posted beyond the stage 1 PR without Karl's approval of its draft under docs/climb-gate/drafts/; deliberately absent throughout: a bootstrap interval, a confidence-interval segment, any schema change, any change to the climb runner, interleaved arm execution (follow-up ticket drafted under docs/climb-gate/drafts/), any work on arms A to G of issue #12, and any reusable climb command in the kit; no dependency is added without saying why in the PR; nothing beyond that; the scope rule in AGENTS.md applies to every agent that works on it.

### Seam 1 answers

(Karl writes here: the threshold ruling and the PR review outcome.)

### Seam 2 answers

(Karl writes here if the stage 2 choice is not the default `ticket` climb.)
