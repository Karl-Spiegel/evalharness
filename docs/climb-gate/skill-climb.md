# Stage 2: the `ticket` skill's description, climbed and gated

The skill-creator description climber (`run_loop.py`) ran on the `ticket` skill, 2 iterations,
20 queries (10 should-trigger, 10 should-not), 60/40 train/test split, 3 runs per query, Opus, from a
clone of this repo with the real skill hidden and one project root per worker. 120 `claude -p`
runs in all. Each run became one kit record (`export_records.py`); each iteration is one arm. The
gate between iterations is the kit's per-case segment at the seam 1 threshold (`gate.py`).

| Arm | Pass (kit headline) | Train (loop) | Test (loop) | Step vs previous (per-case) |
|---|---|---|---|---|
| iter1 | 57/60 (95%) | train 11/12 | test 8/8 | baseline |
| iter2 | 59/60 (98%) | train 12/12 | test 8/8 | `per-case net +1 (iter2>iter1 1, iter1>iter2 0, cases 20, p 1)` → no decision (net +1, p 1.0 >= 0.05) |

The kit headline counts every run; the loop's train and test counts are its own per-run tallies on
the split. A step's gate reads the per-case segment: one pair per query across its three runs, net
and exact McNemar p, accepted only with net > 0 and p below the threshold.

## Result

Loop exit: all_passed (iteration 2). Best by held-out score: iteration 1.

Original description:

> Use when the user says "file a ticket", "draft an issue", "open an issue for X", "new ticket", asks to refine or audit an existing GitHub issue, or wants a sanity-check on an agent-filed ticket. Applies to all repos.

The loop's best, by held-out score (ties keep the earlier): the original.

Climbed description (iteration 2):

> Use this skill whenever the user wants a single GitHub issue written, filed, or improved, in any phrasing. This includes "file a ticket", "draft an issue", or "create an issue for X". It also includes turning a bug report, reproduction steps, a feature idea, a proposal, or session notes into an issue, with or without labels such as bug or feature. Use it to refine, rewrite, groom, audit, or sanity-check an existing issue, including issues that an agent filed. It applies in every repo and package. Do not use it to list, search, or summarize existing issues. Do not use it for PR review, commits, eval runs, or multi-ticket adversarial planning; /ticket-plan does that planning.

Draft diff of the climbed description against the real skill, not applied: `docs/climb-gate/drafts/ticket-description.diff`. The loop itself did not prefer it: held-out tied, so by its rule the original stands. Karl applies it or not.

## What this says about the climber and the kit

- The climber needed five fixes to measure anything on this host, or to run on it at all (plan file, `stage2/run_eval.patch`). Three earlier attempts read zero recall and were artifacts.
  With them, the original `ticket` description already triggers on nearly every should-trigger
  query and never on the should-not ones, so there is little headroom for a description climb here.
- The kit's per-case segment is the right shape for the loop: one pair per query, repeats folded
  in, direction and p on one line. The gate refuses to decide without a recorded threshold.
- Everything the tables rest on is under `docs/climb-gate/stage2/`: the records (`records/iter*.jsonl`),
  the per-run sidecar (`runs-ticket.jsonl`), the loop output (`loop-ticket.json`), the eval set, the
  exporter, the gate, this page's builder, the namespace wrapper, and the detector patch against the
  stock skill-creator `run_eval.py`. The HTML report stays in the climb workspace.
- The one step that moved, iteration 2, won one query on train and tied on held-out: net +1 over 20
  cases, p 1. The gate gives no decision, and the loop's own tie rule kept the original. On a skill
  that already triggers this well, a description climb has nothing to find; the kit's gate says so
  without a human reading the runs.
