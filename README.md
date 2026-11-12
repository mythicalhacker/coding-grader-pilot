# When does a passing check tell a grader anything?

This repository contains runnable tests and recorded outputs from two coding-agent patch reviews, and three eight-issue comparisons. They examine whether closing notes help reviewers find bugs, influence which patch a grader selects, or change the grade once test results are fixed. Each case links the public submissions, source revisions and benchmark records.

It also includes [Task Bundle CLI](task-bundle-cli/README.md), the code and row-level results from a separate experiment checking whether a grading environment can recognize known fixes before evaluating a solver.

| Case | Result |
|---|---|
| [xarray metadata](xarray/README.md) | A human reviewer chose A and supplied two tests before seeing their results. The second test and the benchmark distinguished A from B. Four model reviewers proposed a further input. Both submitted patches copied metadata from the wrong array. The maintainers’ fix passed. |
| [Django migrations](django/README.md) | A patch author’s check passed on unchanged Django and both submissions. The regression that ran the migration detector passed only on A. |
| [Closing notes and defect discovery](closing-note-defect-discovery/README.md) | Two blind panels each assigned 16 reviewers to the same eight Django and SymPy issues. Commands and output exposed a reported defect on the same six issues twice. Adding notes yielded six in the first panel and five in the [second panel](closing-note-defect-discovery/second-panel/README.md). |
| [Closing notes and patch selection](eight-issues/README.md) | Adding author notes to highlighted commands yielded the same three benchmark winners and five abstentions when a grader had to select the same winner in both patch orders. The audit includes all 64 recorded choices. |
| [Removing completion claims from closing notes](claim-removal/README.md) | On eight fresh issues, all three note conditions credited zero benchmark-failing patches at the preset cutoff. Selecting eight of sixteen patches per draw admitted the same failing patch under every condition in both draws. |
| [SWE-bench Pro reference-patch validation](task-bundle-cli/results/README.md) | Of 266 Python tasks, 188 passed validation and then passed a separate replay of the known patch. The harness recorded where the other 78 stopped. The remaining 465 tasks used unsupported frameworks. |

Pranav Lakhwara made the blind xarray decision, supplied the first and second tests, and gave the final training label after seeing the follow-up result. Codex selected and prepared the case, ran the tests, arranged the model reviews and conducted the separate Django replay and patch-selection study. Pranav requested the defect-discovery and claim-removal pilots. Codex designed and ran both. The four model reviewers proposed their own tests. The reviewed patches were written by agents in the published SWE-bench submissions.

The xarray case was outside all three eight-issue samples. The studies report observed choices and test behavior. They did not train a model or estimate a deployment-wide error rate.
