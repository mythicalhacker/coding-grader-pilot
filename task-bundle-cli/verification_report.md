# Verification report

The May 2026 run recorded **731 distinct SWE-bench Pro instance IDs**. Of 266 Python instances, **188** passed baseline and reference validation, then passed candidate grading when the trusted adapter supplied the known reference patch. These are replay results for the harness. No model generated the patches in this sweep.

## Recount of the archived run

The counts below come from grouping the archived per-instance records by final status and checking their validation and grading fields. There was one record for each row index from 0 through 730. Only rows with a valid bundle advanced to candidate grading. The public dataset is available from its [upstream publisher](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro).

| Recorded outcome | Instances | Interpretation |
| --- | ---: | --- |
| Reference patch resolved | 188 | Both validation legs passed. The subsequent reference-patch replay satisfied the grader. |
| Invalid during Python validation | 52 | Required outcomes could not be established or failed to match the expected behavior. |
| Python test execution failed | 26 | The runner classified the failure during test execution. |
| Unsupported framework | 465 | 280 Go, 165 JavaScript and 20 TypeScript rows reached the unsupported-framework path. |
| **Total** | **731** | **188** candidate grades and **543** rows that stopped at validation. |

Within the 52 invalid Python rows, 38 had `PARSER_UNKNOWN`, 12 had `P2P_NOT_PASSING` and two had `GOLDEN_TESTS_FAILING`. The middle group failed a test the baseline was expected to pass. The last group failed with the reference patch applied. At the lower-level validation step, 491 rows shared the code `TEST_EXEC_FAILED`. The per-row classification distinguishes the 465 unsupported-framework cases from the 26 Python execution failures.

## What changed during the run

- **Pytest compatibility.** A targeted filter for a deprecated pytest option led to a rerun of 32 Python cases previously classified as execution failures. Two then passed validation and reference replay. Four acquired specific invalid outcomes, leaving 26 execution failures.
- **Test identity.** A JUnit case name containing a lone surrogate previously failed on persistence. Escaping those code points allowed the affected Ansible case to complete. Missing test IDs still affect coverage, especially where collection behavior or parameter naming differs between repositories.
- **Large images.** Some Open Library images needed more writable space than the temporary filesystem provided. Moving the fallback workspace outside that filesystem and adjusting extraction ownership allowed previously affected examples to finish.
- **Repeatability.** In the recorded qutebrowser example, two reference runs produced the same verdict and outcomes for all 56 required tests, four expected repairs and 52 regression checks. This comparison covers that fixture on the recorded setup.

## Reading the failure labels

The harness accepts some indirect evidence. A collection error associated with a selected Python file can supply a failure status for an individual test that never executed. A matching group of longer parameter IDs with a common status can stand in for a shortened expected ID. For a disputed case, compare the raw pytest output, JUnit cases and expected IDs before attributing the result to a patch.

The archived implementation's early JUnit check recognizes an absent report following an unsuccessful test command. For an existing file the helper returns without inspecting the contents. Malformed XML can then raise a parsing error. A well-formed file with no test cases can reach the missing-ID path and be classified as unknown if reconciliation supplies no evidence. The recorded execution and parsing categories therefore reflect this version's diagnostics. [Orchestrator](src/task_bundle/orchestrator.py) · [Parser](src/task_bundle/parser.py)

## Verification coverage

On November 12, 2026, the public release passed its 53 local unit tests and initialized and loaded all 731 rows again from the pinned dataset with zero initialization errors. The example loader fetched the dataset anonymously and reproduced the archived qutebrowser bundle's six runtime files byte for byte. These checks exercise packaging and bundle construction. The 188 container grading verdicts in the table are from the May run.

The May report marked all 50 items in its historical matrix as passing and recorded 53 fast tests. Its evidence included source inspection, unit tests, Docker runs, stored events and cross-instance outcomes. For the qutebrowser run, the report recorded distinct solve and grade container IDs, solve teardown before grade creation, a one-commit working repository, and absence of selected test paths in the solve working tree immediately after preparation.

The [public matrix](TEST_MATRIX.md) defines A9 as a documentation check for dataset provenance. The historical count does not score that revised check. This report recounts stored records and does not claim a fresh Docker sweep, a rerun of each matrix item or a model success rate. To reproduce a particular grade, acquire the upstream data and image, run validation, run the trusted reference adapter, and compare the saved per-test statuses, commits, image identifier and parser version. [CLI guide](README.md) · [Design](DESIGN.md)
