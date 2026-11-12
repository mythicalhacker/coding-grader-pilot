# Task Bundle CLI

Can a grading environment recognize a known fix before it scores a coding agent? On a May 2026 snapshot of SWE-bench Pro, 188 of 266 Python tasks passed this harness's validation checks. All 188 then passed grading in a fresh container with the supplied reference patch. On the remaining 78 Python tasks the harness stopped before grading. It recorded 465 unsupported Go, JavaScript and TypeScript tasks separately. [Results and limitations](results/README.md) · [All 731 final outcomes](results/outcomes.csv)

This agent-assisted Python CLI packages issues as tasks, runs baseline and reference checks, extracts a candidate patch from a solver workspace and grades it in a separate Docker container. SQLite stores run IDs, events, test outcomes and artifact locations. The trusted reference adapter exercises the grading path using the known patch. A separate adapter is needed to evaluate a model's ability to produce a patch.

## Install

Start in the `task-bundle-cli` directory. Use Python 3.11 or newer. The dataset tools need the `hf` extra. Validating or grading a task also requires Docker and access to its benchmark image. The qutebrowser example image targets Linux on AMD64.

```sh
python -m venv .venv
```

On macOS or Linux, activate it with `source .venv/bin/activate`. In Windows PowerShell use `.\.venv\Scripts\Activate.ps1`.

```sh
python -m pip install -e ".[dev,hf]"
task --help
```

## Try one task

Generate the qutebrowser example from the pinned public test split. The loader verifies the dataset file and writes the example locally. The benchmark authors publish the problem text, test identifiers and reference patch under their source repositories' terms. [Dataset snapshot](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/7ab5114912baf22bb098818e604c02fe7ad2c11f/data) · [Dataset licensing](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro#license)

```sh
python scripts/prepare_example.py
task validate bundles/qutebrowser-instance-1
task run bundles/qutebrowser-instance-1 --solver trusted-golden-stub
task list --limit 10
```

The validation checks that the original code exhibits the expected failures and that the reference patch meets the task's behavioral checks. The final command with `--solver trusted-golden-stub` then exercises patch extraction and grading. Use `task logs <run_id> --json` to inspect an individual run. The CLI prints the run ID on the first output line.

## Run your own task

```sh
task init from-row row.json bundles/my-task
task init manual bundles/manual-task
task validate bundles/my-task
task run bundles/my-task --solver my_adapter:Solver
```

Replace `my_adapter:Solver` with your installed adapter's Python module and class. A bundle has a manifest, a solver-visible problem description, and evaluation material for baseline checks, reference-patch checks and grading. The orchestrator tears down the solve container before it starts the grade container. External Python solver adapters run in the host process and must be trusted. Docker restrictions apply to code executed inside the containers. The built-in reference adapter deliberately has access to the expected patch.

By default the database is `~/.swe-task/runs.db` and artifacts go in `~/.swe-task/artifacts`. Set `--db` and `--artifacts` to separate independent runs. Run `task doctor --help` to see the available Docker checks.

## Verify and repeat

Run the local regression suite from this directory.

```sh
python -m pytest tests -q
```

For the full benchmark sweep, download the same 731-row snapshot and use a new output directory. The runner pulls benchmark images and can consume substantial time, disk and bandwidth.

```sh
hf download ScaleAI/SWE-bench_Pro data/test-00000-of-00001.parquet --repo-type dataset --revision 7ab5114912baf22bb098818e604c02fe7ad2c11f --local-dir hf_cache
python scripts/hf_dataset_audit.py
python scripts/hf_full_dataset_runner.py --run-valid --wall-clock-seconds 300 --outdir scripts/transcripts/replay
```

The row export records the last result per task after retries. Image tags are resolved at run time, so the image digest belongs with each execution record. [Design](DESIGN.md) · [Verification matrix](TEST_MATRIX.md) · [Historical verification report](verification_report.md)
