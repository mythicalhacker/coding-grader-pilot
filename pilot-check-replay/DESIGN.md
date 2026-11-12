# Can a coding agent's check detect the bug?

## Question and prediction

When a coding agent submits a patch that fails SWE-bench Verified, how often does a check it wrote pass on the buggy original? We call such a check **Empty**. We predict an Empty rate of at least 30%. If the one-sided 95% upper bound is below 20%, we will drop replay on the buggy original as a proposed filter. We will also measure the difference between failed and passing patches.

## Archive and sample

The study uses the February 17, 2026 SWE-bench Verified bash-only submissions for Claude 4.5 Sonnet (high) and Claude 4.6 Opus. Both used mini-SWE-agent 2.0.0. There was no February 13 Verified release for this pair. Their February 13 submissions were for SWE-bench Multilingual. The archive index is pinned at `40f164d5b8f1d249bf95a6df8b74b577fd8e519d`. [Sonnet archive](https://github.com/SWE-bench/experiments/tree/40f164d5b8f1d249bf95a6df8b74b577fd8e519d/evaluation/verified/20260217_mini-v2.0.0_claude-4-5-sonnet-high) · [Opus archive](https://github.com/SWE-bench/experiments/tree/40f164d5b8f1d249bf95a6df8b74b577fd8e519d/evaluation/verified/20260217_mini-v2.0.0_claude-4-6-opus) · [Multilingual index](https://github.com/SWE-bench/experiments/tree/40f164d5b8f1d249bf95a6df8b74b577fd8e519d/evaluation/multilingual)

Exclude the 26 previously studied issues in the union of `excluded_previously_graded` and `selected` in the pinned selection record. For each model, keep runs whose final scaffold status is `Submitted` and whose submitted patch adds or deletes at least one line outside test paths. The benchmark's published result determines whether the patch failed or passed. [Exclusion manifest](https://github.com/mythicalhacker/coding-grader-pilot/blob/48019b73fd266070d97ee4ce7c9c2f84cc479a87/claim-removal/fixtures/selection.json#L29-L58)

For each model, sort the failed and passing lists separately by instance ID. Shuffle each list with a fresh `random.Random(20261113)`. Take the first 80 failed and 50 passing. If the projected full run exceeds 24 hours, take the first 50 failed and 30 passing from the same lists. Record that reduction before inspecting sampled checks. Take all available when a list is shorter. Report failed and passing patches separately, with both issue counts and model-run counts.

## Five feasibility replays

Before sampling, inspect both models' records on five excluded issues. Verify the ordered shell actions, exit codes and output, working directory and environment, submit event, submitted patch and final assistant message. Check that each issue's environment can be rebuilt at its pinned base revision and that the model and gold patches apply separately without the benchmark test patch.

Time the Opus checks on `django__django-11532` and `django__django-14053`, and the Sonnet checks on `pytest-dev__pytest-7490`, `scikit-learn__scikit-learn-12973` and `sphinx-doc__sphinx-7985`. Each has a benchmark-failing counterpart available for the fourth state. Record setup, cold image pulls, concurrency, free disk and elapsed time for all four states. Estimate full-sample wall time from measured throughput at the same concurrency, adding recurring setup costs once per image. State assumptions about retries. If a required input or any of the five full timings is missing, report the shortfall and leave the projection unknown. Pause below 20 GB free disk.

## What counts as a check?

Use this expression on repository-relative paths for eligibility, tracking the last production edit and removing test-file changes from patches.

```regex
(?:^|/)(?:tests?|testing|fixtures)(?:/|$)|(?:^|/)(?:test[^/]*|[^/]+_tests?|conftest|runtests)\.py$
```

Locate the last edit to production code by comparing file contents and Git status across editing steps. A dirty file can be edited twice. Ignore read-only inspection, patch packaging and check-file cleanup. Keep all later bash segments before submission that run pytest, py.test, tox, runtests.py, bin/test, nosetests, or Python running a script, inline check, or the pytest, unittest or nose module. Preserve shell control flow, working directory and environment. A shell action that runs several commands can hide a failed segment. Use its exit code only when it can be attributed to the check. Record missing evidence.

Rebuild untracked and deleted scripts, inline Python, and added or edited test files as they existed when each check ran. Record their source steps and content hashes. Compare with the base revision to tag checks as agent-written, pre-existing or mixed. Mixed checks count as agent-written. A run with no qualifying segment counts as **no post-edit check**.

Replay all segments in order with Bash `pipefail`. The combined check passes only if every segment exits zero. Also record the last segment and any different command cited in the closing note. Count a completion claim when the scaffold accepts the submit action. Separately, record whether the final assistant message contains a standalone sentence in this fixed list.

> all tests pass · all tests passed · all tests are passing · the tests pass · the tests passed · the test suite passes · the test suite passed

Ignore case, extra spaces, list bullets and terminal punctuation. Skip quoted text, code and tool output. Record the phrase, no match, or missing message. This flag does not determine eligibility or the check category.

## Code states

1. The agent's own production patch on the base revision.
2. The buggy original at that revision.
3. The maintainers' production fix on the same base, omitting all benchmark test changes.
4. The other model's failing patch for the same issue, when available. For the main study, finish States 1–3 for the entire sample before running State 4.

Start each state clean. Strip test-path changes from States 1 and 4 before injecting the recorded check artifacts. Allow 120 seconds for each standalone script segment and 900 seconds for a segment that runs a repository test suite, including a suite launched from a script. Report timeout counts by check type.

## Classification

Apply the first matching rule using recorded output and exit codes.

| Category | Rule |
| --- | --- |
| Failed for the agent | The last post-edit check segment actually ran, exited nonzero in the original trajectory, and the agent still submitted. The scaffold's synthetic `-1` or an infrastructure error cannot establish a shell exit. |
| Could not run | The check passed for the agent but fails on State 1, or a required State 1–3 cannot be prepared, times out, or collects zero tests. A standalone script does not need a test collector. Record the reason. |
| Empty | The combined check passes on State 2. Tag it `inverted` if it fails on State 3. |
| Informative | The check fails on State 2 and passes on State 3. Tag State 4 as `catches_other_fail`, `misses_other_fail`, `state4_unavailable` or `state4_timeout`. |
| Wrong | The check fails on both States 2 and 3. On the failed gold-state segment, tag a traceback naming a private-symbol import failure as `private_symbol_import`, then an AssertionError or pytest assertion-failure line as `behavioral_mismatch`. Otherwise leave the subtype open for audit. |

Retry each Could not run once from clean states. Keep the first category and flag any change on retry. Record an unresolved run if an earlier historical segment failed and the last one passed, or if a necessary historical exit is missing. A known failed last segment still establishes Failed for the agent. State 4 cannot change the primary category.

## Analysis and audit

The primary rate is Empty divided by the total of Empty, Informative and Wrong among failed, submitted runs with agent-written or mixed checks, combining the two models. Directly below the primary estimate, report the **count and share of Failed for the agent** among all sampled failed, submitted runs with agent-written or mixed checks. Its denominator includes those historical failures. They are excluded from the primary rate.

Alongside the primary rate, report the rate on passing patches, the failed-minus-passing difference in percentage points, model-specific rates, rates for pre-existing checks, the share of runs with no post-edit check, and every category and exclusion count.

Draw issues with replacement 10,000 times using seed 20261113. Keep all rows for a drawn issue together and retain the number of issues in each observed combination of model and benchmark outcome. Recompute both rates in each draw for their difference. Use the 2.5th and 97.5th percentiles, with linear interpolation, for two-sided intervals and the 95th percentile for the one-sided upper bound. Cross-check the primary rate with a two-sided 95% Wilson interval on run counts. Wilson treats repeated issues as independent. With an empty denominator the rate is undefined. If the bootstrap has no variation, report the observed rate and Wilson interval and leave the falsifier indeterminate.

For the sensitivity check, let E be Empty, V the valid primary denominator and X the excluded failed, submitted runs with an agent-written or mixed check. Include historical failures, replay failures and unresolved runs in X. Report E/(V+X) and (E+X)/(V+X), the rates if none or all of those excluded checks were Empty. If authorship is unknown for additional checks, report their count and repeat the bounds including them. Report no-check runs separately.

Keep JSON lines with the selection counts and, for each sampled run and state, the commands, exits, attempts, durations, tags and log paths. Retain missing-state and no-check records. An independently written second script will recompute the reported numbers from those records.

The hand audit covers every Failed for the agent, Could not run and Wrong run, plus 20% each of Empty and Informative runs. Within each of the latter categories, sort by model and issue, shuffle with a fresh `random.Random(20261113)`, and round the audit count up. Show the command, exits and log link. Keep the machine's suggested reason (old suite, prints and never asserts, omits the trigger, or other) in its own column. The auditor records a tag and whether the reconstruction was correct.

## Interpretation and contributions

A check that passes on both the buggy original and the agent's patch cannot distinguish those two states. An Informative check can still accept an incomplete fix. This study cannot establish whether the agent read its output, whether prose influences a grader, or whether the proposed filter improves training. Its scope is two archived model configurations on one benchmark and one scaffold.

Pranav Lakhwara chose the question and made the eight design decisions. Claude reviewed the protocol and proposed methodological corrections. Codex revised the wording and implemented the sampling and classification rules.
