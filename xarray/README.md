# One xarray benchmark winner, one metadata bug

Two SWE-bench submissions fixed a crash in `xr.where(condition, x, y, keep_attrs=True)`. In this xarray revision, the result should keep the attributes of `x`. If `x` is an integer, the expected attributes are empty. Patch A passed the benchmark regression. When `x` was an integer and `y` an array with its own attributes, A and B both copied the attributes of `y`. The maintainers’ fix returned the same values with empty attributes. [Original issue](https://github.com/pydata/xarray/issues/6444) · [Merged fix and regression](https://github.com/pydata/xarray/commit/0cd5285c56c5375da9f4d27836ec41eea4d069f3)

| Check | Unchanged xarray | Patch A | Patch B | Maintainers’ fix |
|---|---|---|---|---|
| First input, `condition = attributed_array > 0`, two scalar choices | IndexError | Printed `[1 1 1]` and `{}` | Same | Same |
| Added assertion, attributes assigned directly to the Boolean condition, two scalar choices | IndexError | Passed | Failed, copied condition attributes | Passed |
| Upstream regression, `test_where_attrs`, called locally | IndexError | Passed | Failed | Passed |
| Four model reviewers’ complete tests | 0/4 passed | 0/4 passed | 0/4 passed | 4/4 passed |
| Mixed input alone, `x=1`, `y=[20, 30]` carrying `{"source": "y"}` | Copied y attributes | Copied y attributes | Copied y attributes | Empty attributes |

All four versions returned the expected values `[1, 30]` on the mixed input. The metadata bug was already present in unchanged xarray. Three reviewers tested two scalars first, so some scripts stopped before reaching the mixed input. The last row comes from a separate diagnostic that exercised both inputs individually. The original SWE-bench logs record the target regression passing on A and failing on B. [Official A log](https://swe-bench-submissions.s3.amazonaws.com/verified/20241022_tools_claude-3-5-sonnet-updated/logs/pydata__xarray-6461/test_output.txt) · [Official B log](https://swe-bench-submissions.s3.amazonaws.com/verified/20241022_tools_claude-3-5-haiku/logs/pydata__xarray-6461/test_output.txt)

## Who proposed each test

1. Codex selected a previously unused issue from a pool filtered for short patches and differing benchmark outcomes. Pranav Lakhwara saw the bug report and both production edits. He chose A and proposed the first input, predicting that B would copy the condition’s attributes.
2. After reading the two patch authors’ closing notes, Pranav kept A and added the second assertion. He supplied both inputs before seeing any execution result or benchmark outcome. Codex ran them. The first input printed the expected output on both patches because the comparison had already stripped the condition’s attributes. The added assertion distinguished A from B.
3. Codex then gave four fresh model reviewers the patches, initial decision and first input. Two saw the closing notes and two did not. Each group saw both patch orders across its two reviewers. A’s author had reported success with scalar `x` and array `y`. Each reviewer independently proposed putting attributes on `y`. Codex ran all four tests against all four versions. [A’s original closing note in the archived run](https://swe-bench-submissions.s3.amazonaws.com/verified/20241022_tools_claude-3-5-sonnet-updated/trajs/pydata__xarray-6461.log)
4. The prespecified criterion was a test that passed on A and failed on B. Zero of two tests in each reviewer group met it. Finding a defect in both patches was a secondary result. After seeing this evidence, Pranav judged A better than B and both incomplete. This single case cannot establish whether the notes helped him design his second test.

## Reproduce

From the xarray directory, use Git and Python 3.10 on macOS or Linux to run these commands. The original local execution used macOS arm64. The replay fetches the archived source and the three public diffs, verifies SHA-256 fingerprints and applies each production change to the same base in a temporary directory.

```sh
python3.10 -m venv .venv
.venv/bin/python -m pip install numpy==1.23.0 pandas==1.5.3 packaging==23.1 python-dateutil==2.8.2 pytz==2023.3 six==1.16.0
.venv/bin/python replay.py
```

`checks.py` contains the two original human inputs, four reviewer tests and upstream regression in separate functions, plus the two Codex diagnostics. `results.tsv` contains the recorded standard output and final exception or successful exit for each available check and version. A successful exit for the first input means it printed a result. It contained no assertion. The initial diagnostic covered the base, A and B. The later diagnostic also covered the maintainers’ fix. The replay compares all 35 rows, prints any difference and exits with a failure if they differ.

`replay.py` pins the base commit and archive digest, both complete submission diffs, the maintainer commit diff and the resulting production file for each version. It applies only the change to `xarray/core/computation.py`. The local upstream check calls the published test body with xarray’s labeled-array equality helper. The official logs above give the independent Linux benchmark results. [Base source](https://github.com/pydata/xarray/tree/851dadeb0338403e5021c3fbe80cbc9127ee672d) · [Patch A](https://swe-bench-submissions.s3.amazonaws.com/verified/20241022_tools_claude-3-5-sonnet-updated/logs/pydata__xarray-6461/patch.diff) · [Patch B](https://swe-bench-submissions.s3.amazonaws.com/verified/20241022_tools_claude-3-5-haiku/logs/pydata__xarray-6461/patch.diff) · [Merged commit](https://github.com/pydata/xarray/commit/0cd5285c56c5375da9f4d27836ec41eea4d069f3)

The regression test adapted in checks.py comes from the xarray project. Its [upstream license](upstream-LICENSE.txt) is included here.
