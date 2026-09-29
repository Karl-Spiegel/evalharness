# DECISIONS: the ruling register

This file lists the operator's rulings for this project. Each row is short. The reasoning lives
in the row's home, which the row links.

## Contract

- Search here before you call a decision open. No row means "unrecorded". Then search the docs,
  the issues, memory, and the session history.
- A ruling the operator gives by word goes on its ticket the same turn, quoted, with the time.
  Under the quote, add one line: "passes the deletion test because …", "code's shape, no row",
  or "unbound, stays on the ticket". That line is the only way an agent proposes a row. Never
  propose a row from a review, an audit, or your own reading of the code.
- Only the operator writes, admits, amends, or removes a row.
- A row records a ruling about the program, never the shape of the code. If the code already
  shows it, it is not a row.
- Two questions decide if a ruling earns a row:
  1. Deletion test. Delete the code and its tests. Does the ruling still bind the rebuild?
     Yes: a row, even when a test pins today's instance.
  2. Tiebreak, for a ruling the code also shows. Would the next agent, reading only the code,
     undo it? Yes: a row. No: the code's shape. Pin it with a test, an error string, or a
     comment. The number in a constant fails this test; the budget it came from passes.
  A case still grey after both questions gets the row. A missing row costs a repeated
  derivation and maybe a regression. A surplus row costs reading time.
- Every row says what being wrong costs.
- A choice the operator does not want to bind yet stays on its ticket as "current reading,
  unbound".
- A reviewer never asks for a row about the code's shape. A reviewer never deletes a row
  because a test also enforces it.
- Add rows at the bottom. Never rewrite a row. Add a superseding row instead.
- Only the operator removes a row, in a commit that does nothing else, and only when a
  superseding row carries its verdict or its subject is gone for good. Never remove a retire,
  keep, or never-retry verdict. Git history is the archive.
- A row has the question, the ruling, the rejected alternatives with why, the home, and what
  it supersedes. "None" under rejected means the operator considered no alternative.

| Date | Question | Ruling | Rejected, and why | Home | Supersedes |
|---|---|---|---|---|---|
| 2026-09-29 | What does the headline pass rate divide by? | Proposed; not admitted. Passes over every case the arm ran. A case with `overall` of `fail` or `unscored`, or with no answer, counts in the denominator and not in the numerator. Per-criterion detail divides, for each criterion, by the count of cases where that criterion's verdict is `pass` or `fail`; an `unscored` criterion drops its case from that criterion's detail only. Wrong costs: every headline number and every comparison between arms. | The gradable count: an arm scores better for crashing. | `docs/protocol.md` step 7; issue #1 d2 | None |
| 2026-09-29 | Who computes a record's `overall`? | Proposed; not admitted. The harness, from the criteria: `fail` if any gating criterion is `fail`; else `unscored` if any gating criterion is `unscored`; else `pass`. A judge never supplies it. Wrong costs: case verdicts that change when the judge prompt changes, with no way to check them. | The judge returns `overall`: its aggregation is unverifiable and drifts with the prompt. | `docs/contract/record.schema.json` `overall`; issue #1 d3 | None |
| 2026-09-29 | How does a record state cost? | Proposed; not admitted. A tri-state basis: `priced` with an amount and a price snapshot date, `self_hosted`, or `unpriced`. A zero amount is legal only under `priced`, with the date. Wrong costs: an unpriced or self-hosted run reads as free, and cost comparisons go false with no error. | A numeric field that defaults to 0: absent reads as free. | `docs/contract/record.schema.json` `cost` | None |
| 2026-09-29 | What latency does a record store? | Proposed; not admitted. The raw wall clock (`wall_ms`) and the harness time (`harness_ms`). Reports derive the model latency as `wall_ms - harness_ms`; no record stores it. Wrong costs: every latency comparison across a change to the harness time is false with no error. | A corrected latency stored alone: records before and after a correction change become incomparable. | `docs/contract/record.schema.json` `latency` | None |
