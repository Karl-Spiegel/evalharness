# The campaign protocol

This document states the twelve steps every eval campaign in this harness follows, in order.
A report that skips a step says which step and why.

1. **State the question and name the arms.** Write down what the campaign must answer and the label of each configuration under test before any code changes. A question written after the results arrive fits the results, not the program.

2. **Pin the commit.** Record the commit under test in the campaign log before the first case runs. Every number in the campaign then traces to one exact state of the code.

3. **Gate on pre-flight checks.** Check the credentials, the endpoints, the fixture clock, the fixture manifest, and the case scope against the data before the run starts. A failed check refuses the run loudly. A warning goes into the coverage record; printed output alone is not a record.

4. **Assert provenance after every run.** Confirm the served model, the provider, the sampling and reasoning settings, and the weights digest where one exists. A run whose provenance differs from the plan is a run of a different arm.

5. **Require the full case count.** Abort an arm that did not run every defined case; do not report it. A partial arm compares a different case set.

6. **Archive, never delete.** A superseded result moves to an archive with a written reason beside it. The record of a mistake is evidence for the next campaign.

7. **Fix the headline denominator.** The denominator is a ruling, decided once, and every report obeys it: the headline pass rate is passes over every case the arm ran. A case whose `overall` is `fail` or `unscored`, or that produced no answer, counts in the denominator and not in the numerator. Per-criterion detail divides, for each criterion, by the count of cases where that criterion's verdict is `pass` or `fail`; an `unscored` criterion drops its case from that criterion's detail only. A smaller denominator would let an arm score better by crashing.

8. **Interleave the arms.** Run the arms under comparison in alternation, not one after the other. Drift in the provider, the network, or the time of day then falls on every arm alike.

9. **Measure the noise floor first.** Repeat one arm enough times to measure run-to-run variation before you trust a single-run difference. Measure quality noise and latency noise apart; one does not predict the other.

10. **Keep one append-only campaign log.** Every run, check, and decision goes into one log, in order. A correction is a new entry that cites the entry it corrects; the old entry stays.

11. **Separate the summary from the tables.** A person writes the summary header; code generates the tables. Label each, so a reader knows which part a tool can reproduce.

12. **Land an instrument fix on its own.** A change to the harness, the judge, or the metrics is its own change, apart from any result. Then append a correction to every artefact and ruling that the old instrument measured.
