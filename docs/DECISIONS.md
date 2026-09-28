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
