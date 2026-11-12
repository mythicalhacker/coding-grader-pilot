# Do closing notes help reviewers find defects? A second panel on the same eight issues

With the last verification commands and their outputs, both panels found an issue-related defect on the **same six of eight** Django and SymPy issues. With the coding agents’ closing notes added, reviewers found all six in the first panel and **five of those six** in the second. Neither panel found an additional issue with notes. [Issue-by-issue comparison](comparison.json) · [First panel and source versions](https://github.com/mythicalhacker/coding-grader-pilot/tree/8654f7bb080134859148967e8245c90cd9c6fc5f/closing-note-defect-discovery)

## Results by issue

“Found” means the test passed on the maintainer’s fix and exposed a failure in at least one candidate on behavior required by the issue. “Miss” means a test ran but did not establish such a defect. Each column includes all eight assigned issues. [Second-panel labels and process outcomes](results.json)

| Issue | First, commands | First, + notes | Second, commands | Second, + notes | What the second-panel tests checked |
|---|---|---|---|---|---|
| Django 11211 | Found | Found | Found | Found | Both candidates failed to retrieve the prefetched target when its UUID was stored as unhyphenated text. |
| Django 11532 | Miss | Miss | Miss | Miss | The tests supplied an ASCII Message-ID, bypassing hostname-based generation. They exposed a separate change in email subject encoding. |
| Django 11740 | Found | Found | Found | Found | A candidate omitted a migration dependency when a UUID field became a foreign key. |
| Django 12193 | Found | Found | Found | Found | A candidate rendered incorrect checkbox states when the widget used a custom predicate. |
| SymPy 12419 | Miss | Miss | Miss | Miss | Both candidates miscounted three selected identity-matrix entries. The report concerned the sum across every row and column. |
| SymPy 14531 | Found | Found | Found | Unscorable | The commands reviewer tested generated Python for a symbolic limit. The notes reviewer specified a left-hand limit, which also failed on the maintainer’s fix. |
| SymPy 14976 | Found | Found | Found | Found | A candidate lost precision evaluating exact rational numbers with the mpmath backend. |
| SymPy 15809 | Found | Found | Found | Found | A candidate returned the wrong infinities for the minimum and maximum of an empty input. |

On SymPy 14531, the commands reviewer’s test passed on the maintainer’s fix and exposed a printing error in one candidate. The notes reviewer’s test asked the printer to reconstruct a limit approached from the left. The maintainer’s own code generated `- = Symbol('-')`, which raised a `SyntaxError`. Both scorers classified that test as unscorable. SymPy 14531 stayed in the denominator. The second panel thus had five issues found in both conditions, one with commands alone, zero with notes alone, and two in neither. [Commands test](responses/drum.py) · [Notes test](responses/pearl.py) · [SymPy execution log](runs-sympy.json)

## Design and checks

On November 13, 2026, Codex assigned the 16 first-panel packets to 16 new model-reviewer contexts with fresh identifiers. Each saw one issue, two candidate patches in the same order, and the authors’ last verification commands and outputs. One reviewer per issue also saw the closing notes. Reviewers could see whether notes were present. Each could propose one test, without a trial run or feedback. Comparing corresponding files across panels confirmed all 16 packets were byte-for-byte identical. [Locked protocol](PROTOCOL.md) · [Django assignments](assignment-django.json) · [SymPy assignments](assignment-sympy.json)

Each locked test ran in a fresh process against the original code, both candidate patches and the maintainer’s fix. Scorers saw the issue, test and execution results with the condition hidden. One primary scorer assessed each repository, and a separate scorer assessed all 16 tests. They agreed on every label. A second execution reproduced all 64 exit statuses, 32 per repository. [Django scores](audit/django-scores.json) · [SymPy scores](audit/sympy-scores.json) · [Sensitivity scores](audit/secondary-scores.json) · [Repeat execution check](repeat-check.json)

The panels reused eight deliberately selected historical issues with different benchmark verdicts for the two patches. They measure how fresh model reviewers responded to the same evidence. A single changed outcome cannot establish that the notes caused the difference. Discovery on new issues and repositories remains an open question.

## Reproduce the comparison

The saved packets, Python tests, execution logs and labels are included. The [pinned first-panel release](https://github.com/mythicalhacker/coding-grader-pilot/tree/8654f7bb080134859148967e8245c90cd9c6fc5f/closing-note-defect-discovery) supplies the source hashes and restoration scripts. From the `closing-note-defect-discovery/second-panel` directory in a checkout of this repository, rebuild both summaries from the saved observations. The first panel’s result is one directory above.

```sh
python3 summarize.py
python3 compare_panels.py ../results.json
```

To run the submitted tests again, use the same historical trees. Each tree directory contains one subdirectory per issue with `base`, `gold`, `haiku` and `sonnet` variants. The original SymPy runtime used Python 3.8.20 and mpmath 1.1.0. The Django runtime used Python 3.10.20, asgiref 3.4.1, pytz 2024.2, sqlparse 0.4.4 and psycopg2-binary 2.9.10. If the trees are unavailable, restore SymPy with the first panel’s `restore_sympy.py` and follow its [Django restoration guide](https://github.com/mythicalhacker/coding-grader-pilot/blob/8654f7bb080134859148967e8245c90cd9c6fc5f/closing-note-defect-discovery/infra-django/README.md).

Run these commands inside a working copy. Set `SYMPY_TREES` and `DJANGO_TREES` to the absolute paths of the restored tree directories, and `SYMPY_PYTHON` and `DJANGO_PYTHON` to the corresponding interpreter paths. The runner replaces each repository’s execution log. Save the original logs before running it. The final check compares each return code by reviewer and variant.

```sh
cp runs-sympy.json saved-sympy.json
cp runs-django.json saved-django.json
python3 run_probes.py sympy --trees "$SYMPY_TREES" --python "$SYMPY_PYTHON"
python3 run_probes.py django --trees "$DJANGO_TREES" --python "$DJANGO_PYTHON"
python3 - <<'PY'
import json
from pathlib import Path

def statuses(path):
    rows = json.loads(Path(path).read_text())["replays"]
    return {(r["slot"], r["variant"]): (r["status"], r.get("returncode")) for r in rows}

for repository in ("sympy", "django"):
    recorded = statuses(f"saved-{repository}.json")
    repeated = statuses(f"runs-{repository}.json")
    assert len(recorded) == 32 and recorded == repeated, repository
    print(repository, "32 of 32 exit statuses reproduced")
PY
```

The public logs use portable path prefixes for the replay environment. Reviewer packets, submitted tests, scores and issue outcomes retain their recorded contents. Historical source excerpts and issue text have the same provenance as the [first panel’s source manifests and license notices](../README.md#source-and-release-notes).
