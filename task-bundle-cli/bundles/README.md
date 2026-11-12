# qutebrowser example

This example uses a qutebrowser refactor that moves a Qt warning filter and its tests into the Qt logging module. The benchmark row lists four tests that should switch from failing to passing and 52 that should keep passing. [qutebrowser source change](https://github.com/qutebrowser/qutebrowser/commit/f91ace96223cac8161c16dd061907e138fe85111)

From the repository root, with the project’s `hf` extra installed, prepare the example and validate the reference patch. Validation requires a running Docker daemon and the public benchmark image.

```sh
python scripts/prepare_example.py
task validate bundles/qutebrowser-instance-1
```

The preparation script downloads the original 731-row public test split, verifies its SHA-256, selects one instance by ID, and calls the same bundle initializer as `task init from-row`. For an offline build, pass `--parquet PATH` with a copy of the pinned file. The default output is a Git-ignored directory. It contains `task.toml`, `problem.md`, the reference patch, the evaluator’s staging instructions and both lists of test IDs. [Pinned dataset file](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/blob/7ab5114912baf22bb098818e604c02fe7ad2c11f/data/test-00000-of-00001.parquet)

Scale AI published the benchmark. The qutebrowser project supplied the upstream change and tests. Scale’s dataset card explains that task content retains its originating repository’s license. [Dataset card](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro#license) · [qutebrowser’s GPLv3 license at the base commit](https://github.com/qutebrowser/qutebrowser/blob/ebfe9b7aa0c4ba9d451f993e08955004aaec4345/LICENSE)
