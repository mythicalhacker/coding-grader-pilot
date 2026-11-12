# Replaying reference patches on 266 SWE-bench Pro Python tasks

A May 20, 2026 run of an agent-assisted evaluation harness recorded a final outcome for each of the 731 tasks in the pinned SWE-bench Pro dataset. The harness supported Python and pytest. Of 266 Python tasks, 188 passed validation. All 188 then passed a separate grading run using the benchmark's reference patch as the candidate. No model generated the patches in these runs. [Dataset revision and test split](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/7ab5114912baf22bb098818e604c02fe7ad2c11f/data)

| Language | Final outcome | Tasks |
|---|---|---:|
| Python | Validated and passed the separate reference run | 188 |
| Python | Validation could not interpret the test output | 38 |
| Python | Tests expected to stay passing did not all pass | 12 |
| Python | The reference patch failed the expected checks during validation | 2 |
| Python | Test execution failed | 26 |
| Go, JavaScript, TypeScript | Framework unsupported by this harness | 465 |
| **All** | | **731** |

The 465 unsupported tasks comprised 280 Go, 165 JavaScript and 20 TypeScript rows. Only tasks that passed validation entered the separate grading run. Of the 78 Python tasks that stopped during validation, two had the explicit reference-check failure code. Interpreting all 78 as incorrect reference patches would conflate parser, execution and behavioral outcomes.

## Evidence

[outcomes.csv](outcomes.csv) contains one final record for each zero-based row of the pinned test split, with the harness language, validation verdict, final outcome, validation code and reference-run verdict. The export was checked against the archived per-row records and the corresponding validation and grading entries in SQLite. Some tasks were retried during development. The table counts each task once using its final recorded outcome. The archived containers were not rerun to produce this recount.

The dataset file was `data/test-00000-of-00001.parquet`, SHA-256 `c8cd7115496ad4e9a8b21d088cef576a65bf821bb542b24336f13f714cef13f8`.

To recount the results, run the following from this directory with Python 3.

```python
import csv
from collections import Counter

with open("outcomes.csv", newline="") as source:
    rows = list(csv.DictReader(source))

assert sorted(int(row["dataset_row"]) for row in rows) == list(range(731))
print(Counter(row["outcome"] for row in rows))
print(Counter(row["validation_code"] for row in rows if row["language"] == "python"))
print(Counter(row["reference_run"] for row in rows))
```
