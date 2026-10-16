# Draft ticket: interleave the arms in the arm C climb runner

Class: amendment to `spikes/decision-models/climb_c.py` (issue #12, the decision-only models spike).

## Problem

Protocol step 8 says to run the arms under comparison in alternation, so drift in the provider, the network or the time of day falls on every arm alike. The climb runner runs one arm per invocation, so v1 ran to completion before v2 started. The 2026-10-16 climb (`CLIMB-C.md`) compared arms run about three minutes apart. Step 9's noise floor came from two repeats of each arm, not from an interleaved run.

## Outcome

- `climb_c.py` takes several `--prompt` and `--arm` pairs in one invocation and alternates them case by case, writing each arm's records to its own file as now.
- The ledger entry records the arms that shared the run.
- `CLIMB-C.md` gains one line saying which comparisons were interleaved and which were not.

## Out of scope

Any change to the kit's package, the record schema or the verdict line. Any new arm.

## Ordering

Builds on commit fee917a on `spike/12-decision-models`. No blocker. Spike code: disposable (issue #12 d3).
