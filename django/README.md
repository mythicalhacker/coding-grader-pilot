# A passing check on unchanged code

On SWE-bench Verified issue `django__django-12754`, Django needed to remove a field from the base model before creating an inherited model. A script in Haiku’s submitted patch constructed and checked its own migration operations without invoking Django’s migration detector. It passed on the original Django code and both submitted patches. The upstream test created the before and after model states and invoked Django’s migration detector. Its results differed across all three versions.

| Source under test | Author’s script | Upstream regression |
|---|---|---|
| Unchanged Django | Passed | Failed: create came before remove |
| Sonnet’s submitted patch (A) | Passed | Passed |
| Haiku’s submitted patch (B) | Passed | Errored while looking up a field’s related model |

The labels A and B are local to this case. This was a follow-up chosen after inspection of the submissions. One authentic weak check establishes a control for a grading experiment. It does not estimate how often checks miss defects.

## Replay

Use Python 3.10 and Git. Create an environment and run the six checks from this directory:

```sh
python3.10 -m venv .venv
.venv/bin/python -m pip install asgiref==3.4.1 pytz==2024.2 sqlparse==0.4.4
.venv/bin/python django-replay.py
```

The script downloads and verifies the four public inputs in [the manifest](django-manifest.json). To reuse downloaded files, supply `--inputs DIRECTORY` containing `django.tar.gz`, `A.diff`, `B.diff`, and `eval.sh`. The replay extracts the benchmark test addition from the evaluation script, then runs that one named regression and the original author’s check on each version. It applies the public changes under `django/` and omits auxiliary files and scratch databases. It verifies the hash of the author’s script and checks the expected exit codes and failure messages. The recorded run used Python 3.10.20 on macOS arm64. The official evaluation ran a larger test set under Python 3.6 on Linux.

[Recorded native process outputs](django-results.json) · [Upstream fix and test](https://github.com/django/django/pull/12754/files) · [Sonnet’s official test output](https://swe-bench-submissions.s3.amazonaws.com/verified/20241022_tools_claude-3-5-sonnet-updated/logs/django__django-12754/test_output.txt) · [Haiku’s official test output](https://swe-bench-submissions.s3.amazonaws.com/verified/20241022_tools_claude-3-5-haiku/logs/django__django-12754/test_output.txt)
