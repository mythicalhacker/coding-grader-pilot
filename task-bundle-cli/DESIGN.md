# Design of the task-bundle grader

A passing test after a patch tells us little unless the test can distinguish the patched program from the starting version. This harness first checks whether a repository snapshot and its reference patch produce the expected change in named pytest results. It can then grade a candidate diff against the same test IDs. The included reference-patch adapter exercises that pipeline without calling a model.

## From a dataset row to a verdict

A bundle describes two Git revisions, a benchmark image, a working directory and selected test files. Test IDs are divided into those expected to change from fail to pass and those expected to stay green. The second list can be empty. The host tracks the problem statement, the reference patch and the commands needed to stage the evaluation files. The CLI can import a dataset row or scaffold a bundle that a developer completes. See the [CLI guide](README.md).

| Phase | What runs | What the result tells you |
| --- | --- | --- |
| Validate the baseline | Prepare the base revision, stage the evaluation files and run pytest. | Each expected failing test failed and each regression test passed under this runner. |
| Validate the reference | Prepare the base again in the same validation container, stage the tests, apply the reference patch and rerun pytest. | All required tests passed with the reference patch. A bundle that satisfies both validation legs receives `VALID`. |
| Obtain a candidate | Start a solve container, replace the working repository's Git history with a synthetic baseline, remove the selected test paths from the working tree and call a host-side adapter. | The adapter leaves edits in the workspace. The harness stages the edits, excludes specified binary file patterns, filters reserved test paths and writes the remaining diff. |
| Grade the diff | Destroy the solve container, start a grading container, restore the base, apply the candidate, overlay the selected evaluation files and run pytest. | A nonempty candidate with passing results for every required test receives `RESOLVED`. The adapter's own completion flag is diagnostic metadata. |

The evaluation overlay runs **after** candidate application. Repeating the full repository setup at that point would reset the candidate's edits. The grading container starts from a separate workspace so ordinary transient files left by the solver do not carry over alongside the exported diff. This costs a second container per candidate.

## Test identity and incomplete evidence

The parser reconstructs pytest node IDs from JUnit XML. The orchestrator compares these IDs with those in the bundle. It can reconcile a shortened parameter ID when all matching reported IDs have the same status. It can also attribute a file-level collection failure to expected tests in that file. That attribution is weaker evidence than an executed test body. An expected ID that still has no recognized result prevents a successful verdict. A skipped test also cannot satisfy a required pass.

When some tests fail, the grader distinguishes a partial repair, a regression on previously passing tests, failure of all required repair tests, and a mixed outcome. The orchestrator records failures outside grading separately, including an empty candidate, a solver timeout and a patch that cannot be applied. These distinctions explain how a row failed and which artifact to inspect. [Parser](src/task_bundle/parser.py) · [Grader](src/task_bundle/grader.py) · [Orchestrator](src/task_bundle/orchestrator.py)

## What the container controls cover

During validation, solving and grading, the harness requests Docker's disabled network mode. The creation settings also request dropped Linux capabilities, no-new-privileges, a process limit, CPU and memory limits and a temporary filesystem for `/tmp`. The code records observed settings, role labels and lifecycle events. It uses the Docker API to transfer files. Workspace preparation may run privileged setup commands as the root user **inside** the container.

The host runs the adapter code. A Python extension receives the task at construction and can access host resources available to the process. The included trusted adapter deliberately reads the reference patch and copies it into the solve container. The post-setup snapshot records selected-path visibility and Git state for the working repository at that moment. It does not establish confidentiality throughout an image or make an arbitrary adapter safe to load. Use trusted adapters, images and bundles. [Docker configuration](src/task_bundle/container.py) · [Adapter interface](src/task_bundle/solver.py)

## Reproducing and inspecting a result

`task logs <run_id>` joins the SQLite run record with its phase events, per-test outcomes and artifact references. Compare the base and evaluation commits, bundle hash, parser version and image identifier before comparing verdicts across runs. The image acquisition code records a resolved digest or local image ID, but container creation uses the configured image reference. An unpinned tag can resolve differently later.

Inspect the candidate diff first if the run reports an empty patch or a reserved-path collision. For collection or parser failures, compare the expected test IDs with the JUnit XML and pytest output. The stored command and the phase where the failure occurred distinguish baseline validation, reference validation and candidate grading. [Storage](src/task_bundle/store.py) · [Verification findings](verification_report.md)

## Implemented scope

Python repositories using pytest have an execution and parsing path. Other language rows can be imported and recorded as unsupported. The historical dataset sweep graded candidates only after their bundles passed validation and used the trusted reference patch for every candidate. It measures how much of that dataset the harness could validate and replay. The [verification matrix](TEST_MATRIX.md) lists checks for exercising the implementation against a prepared bundle.
