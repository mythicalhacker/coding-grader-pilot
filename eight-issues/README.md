# Did the closing notes change patch preferences?

Eight previously sampled SWE-bench Verified issues had a named target test with different outcomes for two submissions and closing notes in both runs. The sample had been filtered for this property. The reference winner below is the patch that passed the benchmark target. Passing a benchmark does not establish that a patch meets every requirement.

Eight fresh Codex contexts each saw the eight different issues once, with conditions interleaved. Each issue was graded in four conditions, twice per condition, with patch order reversed and a different reader for the second presentation. Readers chose the first patch, the second patch, or abstained. The time-ordered action and observation histories, problem statement and patches were available in all conditions. Benchmark outcomes were hidden.

| Extra evidence presented | Benchmark winner chosen in 16 readings | Benchmark loser chosen | Abstentions | Issues with same winning patch in both orders (of 8) |
|---|---:|---:|---:|---:|
| None | 8 | 0 | 8 | 4 |
| Highlighted historical command and result | 7 | 0 | 9 | 3 |
| Same highlights plus both original closing notes | 6 | 0 | 10 | 3 |
| Matched excerpts from the end of the logs | 6 | 0 | 10 | 3 |

Two earlier note readers agreed that five of the sixteen closing notes described an identifiable check. Only those five were highlighted under the selection rule. Each of the five identified the final verification command. Matched log excerpts and selected highlights produced byte-identical inputs for each displayed order. Readers still differed once on identical inputs.

A stable decision required readers to pick the same patch across both orders. A split, including a vote paired with an abstention, counted as an issue-level abstention:

| Issue | Histories only | Highlights | Highlights + notes | Log excerpts |
|---|---|---|---|---|
| django-13346 | Abstain | Abstain | Abstain | Abstain |
| sphinx-7985 | Abstain | Abstain | Abstain | Abstain |
| django-14053 | Abstain | Abstain | Abstain | Abstain |
| django-15103 | Winner | Winner | Winner | Winner |
| scikit-learn-14983 | Winner | Winner | Winner | Winner |
| sphinx-7910 | Winner | Winner | Winner | Winner |
| django-12754 | Abstain | Abstain | Abstain | Abstain |
| django-13112 | Winner | Abstain | Abstain | Abstain |

On django-13112, readers with highlighted checks split between choosing the benchmark winner and abstaining. Both readers with the notes abstained. The same three issues yielded stable winners with and without the notes in the highlighted conditions. The fourth issue that histories alone retained changed *which examples qualified*. No comparison yielded opposing stable winners on the same issue. Eight issues, not 64 independent cases, support these counts. The two Sphinx action histories included work on an extra file absent from the evaluated patches. The same indexed patches were presented in all conditions.

[Choices and versioned public patch sources](eight-issue-choices.json) preserve the reader’s first/second/abstain choice separately for each presentation. The file also links the two official results indexes and records the public source hashes. Run `python3 score-eight-issues.py` to recompute the two tables. This reanalysis uses previously recorded decisions; it does not dispatch graders or train a model. The separate xarray case was outside this sample.
