# Amendment 1. A secondary estimate for masked check exits

13 November 2026. This amendment was written after the five excluded feasibility controls, before the sample was drawn and before any sampled check was parsed.

In the controls, a shell pipeline sometimes stored the exit code of an output filter and left the test runner's exit unknown. Three of the five controls had at least one such segment. This can reduce the number of runs that contribute to the primary estimate. A secondary analysis will measure how the Empty rate changes if a successful replay on the agent's own patch supplies the missing evidence.

Start with runs classified as unresolved solely because at least one historical check exit is masked. For each such run, verify that no archived check segment has an attributable nonzero exit. If every segment of the combined check passes on the agent's own patch in replay with Bash `pipefail`, label the pass **inferred**. Apply the published State 2 and State 3 rules to classify the check as Empty, Informative or Wrong. A failed or unusable own-patch replay leaves the run unresolved. The published rules for unusable replays on other required states still apply.

For the secondary rate, use the same failed, submitted, agent-written or mixed population as the primary rate. Add the inferred checks with valid classifications to the primary denominator and their Empty checks to its numerator. Report both fractions, the number added, the issue-bootstrap 95% interval and the Wilson 95% interval. Keep the inferred label in the run records and report.

The primary analysis retains its original treatment of unresolved runs. Only the primary result is used to evaluate the 30% prediction and the one-sided falsifier. All other rules in the [published design](DESIGN.md) continue to apply.
