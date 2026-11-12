# Verification matrix

Use a disposable store and an independently materialized test bundle. A small Python/pytest case with both failing-to-passing tests and previously passing tests covers most of the checks. Several rows call for a second fixture or a deliberately invalid local copy. Inspect a run with `task logs <run_id>`, the artifact directory and, when needed, the SQLite event sequence. Each row below specifies an observation to collect. The [verification report](verification_report.md) distinguishes historical observations from checks to run on this edition.

## Basic operations

| ID | Check |
| --- | --- |
| A1 | Import a public benchmark row. Load the resulting bundle and compare its commits and required test lists with the input row. |
| A2 | Create a manual bundle and verify that a developer can find the fields and files that still need input. |
| A3 | Validate a known-good Python bundle. Expect exit 0 and `VALID`. |
| A4 | Grade its reference patch through the trusted adapter. Expect exit 0 and `RESOLVED`. |
| A5 | Look up that run ID and inspect its metadata, phase history, tests and artifact references. |
| A6 | List recent runs and find the retained validation and grading records. |
| A7 | Open the configured SQLite store independently and find both records. |
| A8 | Open the candidate diff, grading command, test output and adapter transcript referenced by the grading run. |
| A9 | Follow the public README's dataset provenance link to the upstream SWE-bench Pro dataset and locate its usage terms before acquiring benchmark materials. |

## Solver and grader workspaces

| ID | Check |
| --- | --- |
| B10 | Compare lifecycle events. Solve-container teardown must precede grade-container creation. |
| B11 | Inspect the snapshot recorded after workspace preparation. The listed evaluation files should be absent from the solve working tree. |
| B12 | Check that the solve working repository reports one synthetic baseline commit. |
| B13 | Check the snapshot's probe for the evaluation commit. It should be unreachable from this working repository. |
| B14 | Compare the solve and grade container IDs. They must differ. |
| B15 | Inspect the exported candidate diff and collision metadata for reserved test paths. |
| B16 | Confirm the recorded workspace probe found no bundle `hidden/` directory at the checked location. |

## Grading and patch handling

| ID | Check |
| --- | --- |
| C17 | Validate a case with an empty regression-test list and a nonempty repair-test list. |
| C18 | Select an inconsistent baseline that already passes a required repair test. Expect the baseline assertion to reject it. |
| C19 | Supply JUnit results with an expected ID missing and no applicable reconciliation. Expect an unknown-result diagnostic. |
| C20 | Use a skipped required test and verify that it cannot produce a resolved grade. |
| C21 | Confirm from phase events that candidate application ends before evaluation files are overlaid. |
| C22 | Check the patch fallback's fuzz limit of one and the diagnostic for exhausting the available methods. |
| C23 | Inspect the exported diff from the binary-file fixture. The fixture's compiled Python file should be excluded. |
| C24 | Give the loader identical base and evaluation SHAs. Expect a bundle validation error. |
| C25 | Use the reserved-path fixture. Compare its recorded collisions with the paths excluded from the exported diff. |

## Failures and diagnostics

| ID | Check |
| --- | --- |
| D26 | Remove the problem-statement file from a copy. Expect `BUNDLE_INCOMPLETE` and exit 2. |
| D27 | Supply malformed TOML metadata. Expect `BUNDLE_MALFORMED` and exit 2. |
| D28 | Provide an evaluation commit that disagrees with the staging specification. Expect `BUNDLE_INCONSISTENT`. |
| D29 | Validate a case whose reference patch cannot apply. Expect the failure to identify reference-patch application. |
| D30 | Use the timeout fixture with a short budget. Expect an unresolved solver timeout. |
| D31 | Use the empty-diff fixture. Expect `UNRESOLVED` with the `no_patch` classification. |
| D32 | Supply an unavailable image reference. Expect `IMAGE_UNAVAILABLE` and exit 2. |
| D33 | Inspect failure output for the failed phase, reason and evidence location where available. |

## Container settings and replay metadata

| ID | Check |
| --- | --- |
| E34 | Inspect the effective user, capability, privilege, network, process, memory, temporary-filesystem and init settings recorded for solve and grade. |
| E35 | Inspect mount and privilege metadata for the test run. Check host binds, Docker socket exposure and privileged mode. |
| E36 | Inspect the container creation interface for caller-supplied host mounts. |
| F37 | Check that the run records a pulled repo digest or local image ID. Record the requested reference separately when assessing replayability. |
| F38 | Verify that both commits, the bundle hash and the parser version are present. |
| F39 | Repeat the reference-patch run. Compare the verdict and every required test ID and status. |

## Dataset cases and CLI behavior

| ID | Check |
| --- | --- |
| G40 | Validate and grade the reference patch for the qutebrowser example with nonempty regression coverage. |
| G41 | Validate a second qutebrowser case with no required regression tests. |
| G42 | Import a JavaScript case and verify that validation names the unsupported framework. |
| G43 | Validate an Ansible case. Retain the outcome and any image, execution or parsing diagnostic. |
| G44 | Try a Go case and verify the unsupported-framework classification. |
| H45 | Inspect top-level and per-command help for bundle creation, validation, grading and log retrieval. |
| H46 | Omit a required CLI argument. Expect a usage error and exit 2. |
| H47 | Verify a run ID appears on the first stdout line of a valid validation or grading invocation. |
| H48 | Redirect help output to a file and check that it is readable without terminal formatting. |
| H49 | Query an unknown run ID. Expect an explicit lookup error. |
| H50 | Query an unfinished run. Distinguish the partial record from a missing run or completed result. |
