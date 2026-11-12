# When does a passing check tell a grader anything?

This repository contains runnable tests and recorded outputs from two coding-agent patch reviews, plus the original choices from an eight-issue comparison. Each case links the public submissions, source revisions and benchmark records.

It also includes [Task Bundle CLI](task-bundle-cli/README.md), the code and row-level results from a separate experiment checking whether a grading environment can recognize known fixes before evaluating a solver.

| Case | Result |
|---|---|
| [xarray metadata](xarray/README.md) | A human reviewer chose A and supplied two tests before seeing their results. The second test and the benchmark distinguished A from B. Four model reviewers proposed a further input. Both submitted patches copied metadata from the wrong array. The maintainers’ fix passed. |
| [Django migrations](django/README.md) | A patch author’s check passed on unchanged Django and both submissions. The regression that ran the migration detector passed only on A. |
| [Eight coding issues](eight-issues/README.md) | Adding author notes to highlighted commands yielded the same three benchmark winners and five abstentions when a grader had to select the same winner in both patch orders. The audit includes all 64 recorded choices. |
| [SWE-bench Pro reference-patch validation](task-bundle-cli/results/README.md) | Of 266 Python tasks, 188 passed validation and then passed a separate replay of the known patch. The harness recorded where the other 78 stopped. The remaining 465 tasks used unsupported frameworks. |

Pranav Lakhwara made the blind xarray decision, supplied the first and second tests, and gave the final training label after seeing the follow-up result. Codex selected and prepared the case, ran the tests, arranged the model reviews and conducted the separate Django replay and eight-issue study. The four model reviewers proposed their own tests. The reviewed patches were written by agents in the published SWE-bench submissions.

The xarray case was outside the eight-issue sample. The studies report observed choices and test behavior. They did not train a model or estimate a deployment-wide error rate.
