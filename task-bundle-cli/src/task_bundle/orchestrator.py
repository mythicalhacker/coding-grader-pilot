"""State-machine sequencing, trust-boundary preconditions, and persist-on-exit."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import shlex
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from task_bundle import grader, parser, solver, staging
from task_bundle.bundle import Task
from task_bundle.container import Container, ContainerManager, ImageRef, NetworkPolicy, ResourceLimits
from task_bundle.errors import ImageUnavailableError, PhaseError, TaxonomyCode, TerminalState
from task_bundle.store import Store, TestOutcomeRow


class State(str, Enum):
    START_VALIDATE = "START_VALIDATE"
    START_RUN = "START_RUN"
    ACQUIRE_IMAGE = "ACQUIRE_IMAGE"
    PROVISION_VALIDATE = "PROVISION_VALIDATE"
    PROVISION_SOLVE = "PROVISION_SOLVE"
    PROVISION_GRADE = "PROVISION_GRADE"
    NORMALIZE_BASE = "NORMALIZE_BASE"
    STAGE_FULL = "STAGE_FULL"
    STAGE_OVERLAY = "STAGE_OVERLAY"
    SCRUB_HISTORY = "SCRUB_HISTORY"
    SEAL = "SEAL"
    SOLVE = "SOLVE"
    EXTRACT = "EXTRACT"
    DESTROY_SOLVE = "DESTROY_SOLVE"
    APPLY_CANDIDATE = "APPLY_CANDIDATE"
    APPLY_GOLDEN = "APPLY_GOLDEN"
    RUN_TESTS = "RUN_TESTS"
    PARSE = "PARSE"
    ASSERT_BASELINE = "ASSERT_BASELINE"
    ASSERT_GOLDEN = "ASSERT_GOLDEN"
    GRADE = "GRADE"
    DONE_VALID = "DONE_VALID"
    DONE_INVALID = "DONE_INVALID"
    DONE_RESOLVED = "DONE_RESOLVED"
    DONE_UNRESOLVED = "DONE_UNRESOLVED"
    ERROR = "ERROR"


TERMINAL_STATES = {
    State.DONE_VALID,
    State.DONE_INVALID,
    State.DONE_RESOLVED,
    State.DONE_UNRESOLVED,
    State.ERROR,
}
START = {"validate": State.START_VALIDATE, "run": State.START_RUN}
EXIT = {
    State.DONE_VALID: 0,
    State.DONE_RESOLVED: 0,
    State.DONE_INVALID: 1,
    State.DONE_UNRESOLVED: 1,
    State.ERROR: 2,
}


@dataclass
class Context:
    task: Task
    run_id: str
    store: Store
    artifact_dir: Path
    container_manager: ContainerManager
    image: ImageRef | None = None
    active_container: Container | None = None
    solve_container: Container | None = None
    grade_container: Container | None = None
    parsed_results: dict[str, parser.ParseResult] = field(default_factory=dict)
    candidate_patch_path: Path | None = None
    no_patch: bool = False
    apply_result: staging.ApplyResult | None = None
    reserved_path_collisions: tuple[str, ...] = ()
    verdict: str | None = None
    taxonomy_code: str | None = None
    failure_class: str | None = None
    message: str | None = None
    terminal_state: State | None = None
    exit_code: int | None = None
    timings: dict[str, float] = field(default_factory=dict)
    setup_plan: staging.SetupPlan | None = None
    validate_leg: str = "baseline"
    last_test_phase: str | None = None
    last_junit_path: Path | None = None
    last_stdout_path: Path | None = None
    verb: str | None = None
    solver_name: str = "trusted-golden-stub"
    solver_result: solver.SolverResult | None = None
    isolation_snapshot: dict[str, Any] = field(default_factory=dict)
    workspace_dir: str | None = None
    failed_phase: str | None = None


Phase = Callable[[Context], State]


def requires_role_not_solve(func: Phase) -> Phase:
    def wrapper(ctx: Context) -> State:
        if ctx.active_container is not None and getattr(ctx.active_container, "role", None) == "solve":
            raise PhaseError(
                State.ERROR,
                TaxonomyCode.BOUNDARY_VIOLATION,
                "trust boundary violation: hidden material cannot enter solve container",
            )
        return func(ctx)

    return wrapper


def requires_solve_destroyed(func: Phase) -> Phase:
    def wrapper(ctx: Context) -> State:
        if ctx.solve_container is not None:
            raise PhaseError(
                State.ERROR,
                TaxonomyCode.BOUNDARY_VIOLATION,
                "trust boundary violation: grade container provisioned before solve destruction",
            )
        return func(ctx)

    return wrapper


def run(ctx: Context, verb: str) -> int:
    state = START[verb]
    ctx.verb = verb
    ctx.store.create_run(
        ctx.run_id,
        verb,
        ctx.task.task_id,
        ctx.task.bundle_hash,
        ctx.task.image_ref,
        ctx.task.base_commit,
        ctx.task.instance_commit,
        ctx.task.repo_language,
        parser_version="pytest-junit-xunit2-v1",
    )
    try:
        while state not in TERMINAL_STATES:
            phase_name = state.value
            ctx.store.append_event(ctx.run_id, "phase_start", {"state": phase_name})
            start = time.monotonic()
            state = TABLE[(verb, state)](ctx)
            duration = time.monotonic() - start
            ctx.timings[phase_name] = duration
            ctx.store.append_event(ctx.run_id, "phase_end", {"state": phase_name, "duration_seconds": duration})
    except PhaseError as exc:
        ctx.failed_phase = phase_name if "phase_name" in locals() else state.value
        ctx.taxonomy_code = exc.code
        ctx.message = exc.render(ctx)
        state = _state_from_any(exc.terminal_state)
    except Exception as exc:
        ctx.failed_phase = phase_name if "phase_name" in locals() else state.value
        ctx.taxonomy_code = "UNEXPECTED"
        ctx.message = f"Unhandled: {type(exc).__name__}: {exc}"
        state = State.ERROR
    finally:
        try:
            ctx.container_manager.cleanup_orphans(ctx.run_id)
        except Exception:
            pass
        ctx.terminal_state = state
        ctx.exit_code = EXIT[state]
        if ctx.verdict is None:
            ctx.verdict = _verdict_for_state(state)
        ctx.store.finalize_run(
            ctx.run_id,
            _now_iso(),
            state.value,
            ctx.taxonomy_code,
            ctx.verdict,
            ctx.failure_class,
            ctx.exit_code,
            ctx.message,
            ctx.apply_result.winner if ctx.apply_result else None,
            int(ctx.apply_result.partial) if ctx.apply_result else None,
            _json_tuple(ctx.reserved_path_collisions),
            None,
            json.dumps(ctx.isolation_snapshot, sort_keys=True) if ctx.isolation_snapshot else None,
            ctx.image.digest if ctx.image else None,
        )
    return ctx.exit_code


def phase_start_validate(_ctx: Context) -> State:
    _raise_if_framework_unsupported(_ctx, "validate")
    return State.ACQUIRE_IMAGE


def phase_start_run(_ctx: Context) -> State:
    _raise_if_framework_unsupported(_ctx, "run")
    return State.ACQUIRE_IMAGE


def phase_acquire_image(ctx: Context) -> State:
    try:
        ctx.image = ctx.container_manager.acquire_image(ctx.task.image_ref)
    except ImageUnavailableError as exc:
        raise PhaseError(State.ERROR, TaxonomyCode.IMAGE_UNAVAILABLE, str(exc)) from exc
    return State.PROVISION_VALIDATE if ctx.verb == "validate" else State.PROVISION_SOLVE


def phase_provision_validate(ctx: Context) -> State:
    assert ctx.image is not None
    limits = ResourceLimits(
        cpu_quota=ctx.task.limits.cpu_quota,
        memory_gb=ctx.task.limits.memory_gb,
        wall_clock_seconds=ctx.task.limits.wall_clock_seconds,
    )
    ctx.active_container = ctx.container_manager.create(
        ctx.image,
        role="validate",
        limits=limits,
        network=NetworkPolicy.NONE,
        labels={"run_id": ctx.run_id},
    )
    _record_container_event(ctx, "container_created", "validate", ctx.active_container)
    _prepare_workspace(ctx, ctx.active_container)
    _capture_isolation(ctx, "validate", ctx.active_container)
    staging.assert_instance_present(ctx.active_container, ctx.task.instance_commit, _workdir(ctx))
    return State.NORMALIZE_BASE


def phase_provision_solve(ctx: Context) -> State:
    assert ctx.image is not None
    limits = _limits_from_task(ctx)
    ctx.solve_container = ctx.container_manager.create(
        ctx.image,
        role="solve",
        limits=limits,
        network=NetworkPolicy.NONE,
        labels={"run_id": ctx.run_id},
    )
    ctx.active_container = ctx.solve_container
    _record_container_event(ctx, "container_created", "solve", ctx.active_container)
    _prepare_workspace(ctx, ctx.active_container)
    _capture_isolation(ctx, "solve", ctx.active_container)
    staging.assert_instance_present(ctx.active_container, ctx.task.instance_commit, _workdir(ctx))
    return State.NORMALIZE_BASE


@requires_solve_destroyed
def phase_provision_grade(ctx: Context) -> State:
    assert ctx.image is not None
    limits = _limits_from_task(ctx)
    ctx.grade_container = ctx.container_manager.create(
        ctx.image,
        role="grade",
        limits=limits,
        network=NetworkPolicy.NONE,
        labels={"run_id": ctx.run_id},
    )
    ctx.active_container = ctx.grade_container
    _record_container_event(ctx, "container_created", "grade", ctx.active_container)
    _prepare_workspace(ctx, ctx.active_container)
    _capture_isolation(ctx, "grade", ctx.active_container)
    return State.NORMALIZE_BASE


def phase_normalize_base(ctx: Context) -> State:
    if ctx.setup_plan is None:
        ctx.setup_plan = staging.parse_setup(ctx.task.stage_sh_path.read_text(encoding="utf-8"), ctx.task.base_commit)
    assert ctx.active_container is not None
    staging.prepare_base(ctx.active_container, ctx.setup_plan, _workdir(ctx))
    if ctx.verb == "run":
        if getattr(ctx.active_container, "role", None) == "solve":
            return State.SCRUB_HISTORY
        return State.APPLY_CANDIDATE
    return State.STAGE_FULL


@requires_role_not_solve
def phase_stage_full(ctx: Context) -> State:
    assert ctx.active_container is not None
    assert ctx.setup_plan is not None
    staging.inject_hidden(ctx.active_container, ctx.setup_plan, _workdir(ctx))
    if ctx.validate_leg == "golden_apply":
        return State.APPLY_GOLDEN
    return State.RUN_TESTS


def phase_run_tests(ctx: Context) -> State:
    assert ctx.active_container is not None
    phase = "solver" if ctx.verb == "run" else ("baseline" if ctx.validate_leg == "baseline" else "golden")
    ctx.last_test_phase = phase
    if ctx.task.repo_language != "python" or ctx.task.test.framework != "pytest":
        message = _unsupported_framework_message(ctx.task)
        if ctx.verb == "run":
            ctx.failure_class = "build_failed"
            raise PhaseError(State.DONE_UNRESOLVED, TaxonomyCode.BUILD_FAILED, message)
        raise PhaseError(State.DONE_INVALID, TaxonomyCode.TEST_EXEC_FAILED, message)
    junit_host = ctx.artifact_dir / f"{phase}_junit.xml"
    stdout_host = ctx.artifact_dir / f"{phase}_stdout.txt"
    stderr_host = ctx.artifact_dir / f"{phase}_stderr.txt"
    command_host = ctx.artifact_dir / f"{phase}_test_command.sh"
    container_junit = f"/tmp/task-bundle-{phase}.xml"
    command = [
        "pytest",
        "-o",
        "junit_family=xunit2",
        "-p",
        "no:cacheprovider",
        "-p",
        "no:randomly",
        "--tb=short",
        "--no-header",
        "-W",
        "ignore:The --strict option is deprecated",
        "-q",
        f"--junitxml={container_junit}",
        *ctx.task.selected_test_files,
    ]
    _write_test_command_artifact(ctx, command_host, command)
    if phase == "solver":
        grade_script = ctx.artifact_dir / "grade_command.sh"
        shutil.copyfile(command_host, grade_script)
        _record_path_artifact(ctx, "grade_script", grade_script)
    result = ctx.active_container.exec(
        command,
        workdir=_workdir(ctx),
        env=_test_env(ctx.task, _workdir(ctx)),
        timeout_seconds=ctx.task.limits.wall_clock_seconds,
    )
    _copy_if_exists(getattr(result, "stdout_path", None), stdout_host)
    _copy_if_exists(getattr(result, "stderr_path", None), stderr_host)
    _record_path_artifact(ctx, f"{phase}_stdout", stdout_host)
    _record_path_artifact(ctx, f"{phase}_stderr", stderr_host)
    if hasattr(ctx.active_container, "copy_out"):
        try:
            ctx.active_container.copy_out(container_junit, junit_host)
        except Exception:
            pass
    _record_path_artifact(ctx, f"{phase}_junit", junit_host)
    ctx.last_junit_path = junit_host
    ctx.last_stdout_path = stdout_host
    if result.exit_code != 0 and _junit_is_execution_failure(junit_host):
        if ctx.verb == "run":
            ctx.failure_class = "build_failed"
            raise PhaseError(State.DONE_UNRESOLVED, TaxonomyCode.BUILD_FAILED, f"test execution failed during {phase}")
        raise PhaseError(State.DONE_INVALID, TaxonomyCode.TEST_EXEC_FAILED, f"test execution failed during {phase}")
    return State.PARSE


def phase_parse(ctx: Context) -> State:
    assert ctx.last_junit_path is not None
    assert ctx.last_stdout_path is not None
    assert ctx.last_test_phase is not None
    try:
        result = parser.parse(ctx.task.test.framework, ctx.last_junit_path, ctx.last_stdout_path)
    except NotImplementedError as exc:
        if ctx.verb == "run":
            ctx.failure_class = "build_failed"
            raise PhaseError(State.DONE_UNRESOLVED, TaxonomyCode.BUILD_FAILED, str(exc)) from exc
        raise PhaseError(State.DONE_INVALID, TaxonomyCode.TEST_EXEC_FAILED, str(exc)) from exc
    ctx.parsed_results[ctx.last_test_phase] = result
    missing = parser.verify_coverage(result, (*ctx.task.fail_to_pass, *ctx.task.pass_to_pass))
    if missing:
        _cover_truncated_param_ids(result, missing)
        missing = parser.verify_coverage(result, (*ctx.task.fail_to_pass, *ctx.task.pass_to_pass))
    if missing:
        _cover_pytest_collection_failures(ctx, result, missing)
        missing = parser.verify_coverage(result, (*ctx.task.fail_to_pass, *ctx.task.pass_to_pass))
    if missing:
        if ctx.verb == "run":
            raise PhaseError(
                State.ERROR,
                TaxonomyCode.PARSER_UNKNOWN,
                f"parser could not resolve required tests: {', '.join(sorted(missing))}",
            )
        raise PhaseError(
            State.DONE_INVALID,
            TaxonomyCode.PARSER_UNKNOWN,
            f"parser could not resolve required tests: {', '.join(sorted(missing))}",
        )
    if ctx.last_test_phase == "baseline":
        return State.ASSERT_BASELINE
    if ctx.last_test_phase == "solver":
        return State.GRADE
    return State.ASSERT_GOLDEN


def phase_assert_baseline(ctx: Context) -> State:
    result = ctx.parsed_results["baseline"]
    outcome = grader.grade_baseline(result.status_map, ctx.task.fail_to_pass, ctx.task.pass_to_pass)
    _record_outcomes(ctx, "baseline_pre", outcome.per_test, result)
    if not outcome.satisfied:
        raise PhaseError(State.DONE_INVALID, TaxonomyCode(outcome.reason), outcome.reason or "baseline invalid")
    ctx.validate_leg = "golden_apply"
    return State.NORMALIZE_BASE


@requires_role_not_solve
def phase_apply_golden(ctx: Context) -> State:
    assert ctx.active_container is not None
    patch_dest = "/tmp/task-bundle-golden.patch"
    if hasattr(ctx.active_container, "copy_in"):
        ctx.active_container.copy_in(ctx.task.golden_patch_path, patch_dest)
    try:
        ctx.apply_result = staging.apply_patch(ctx.active_container, patch_dest, _workdir(ctx))
    except PhaseError as exc:
        if exc.code == TaxonomyCode.PATCH_APPLY_FAILED.value:
            raise PhaseError(State.DONE_INVALID, TaxonomyCode.GOLDEN_NOT_APPLYING, "golden patch did not apply") from exc
        raise
    ctx.validate_leg = "golden"
    return State.RUN_TESTS


def phase_assert_golden(ctx: Context) -> State:
    result = ctx.parsed_results["golden"]
    outcome = grader.grade_golden(result.status_map, ctx.task.fail_to_pass, ctx.task.pass_to_pass)
    _record_outcomes(ctx, "baseline_post_golden", outcome.per_test, result)
    if not outcome.satisfied:
        raise PhaseError(State.DONE_INVALID, TaxonomyCode.GOLDEN_TESTS_FAILING, outcome.reason or "golden tests failed")
    ctx.verdict = "VALID"
    return State.DONE_VALID


def phase_scrub_history(ctx: Context) -> State:
    assert ctx.active_container is not None
    staging.scrub_history(ctx.active_container, _workdir(ctx))
    return State.SEAL


def phase_seal(ctx: Context) -> State:
    assert ctx.active_container is not None
    staging.seal(ctx.active_container, ctx.task.selected_test_files, _workdir(ctx))
    _record_solve_boundary_snapshot(ctx)
    _record_solver_visible_tests_manifest(ctx)
    return State.SOLVE


solver_loader = solver.load_solver


def phase_solve(ctx: Context) -> State:
    assert ctx.active_container is not None
    view = solver.SolverTaskView(
        task_id=ctx.task.task_id,
        repo=ctx.task.repo,
        problem_text=ctx.task.problem_md_path.read_text(encoding="utf-8"),
        repo_language=ctx.task.repo_language,
        workdir=_workdir(ctx),
        public_test_command=None,
    )
    loaded = solver_loader(ctx.solver_name, ctx.task)
    deadline = time.time() + ctx.task.limits.wall_clock_seconds
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(loaded.solve, view, ctx.active_container, deadline)
            ctx.solver_result = future.result(timeout=ctx.task.limits.wall_clock_seconds)
    except (concurrent.futures.TimeoutError, TimeoutError) as exc:
        ctx.failure_class = "solver_timeout"
        try:
            ctx.active_container.exec(["pkill", "-9", "-f", "solver"], workdir=_workdir(ctx), timeout_seconds=5)
        except Exception:
            pass
        raise PhaseError(State.DONE_UNRESOLVED, TaxonomyCode.SOLVER_TIMEOUT, "solver timed out") from exc
    except Exception as exc:
        raise PhaseError(State.ERROR, TaxonomyCode.SOLVER_CRASHED, f"solver crashed: {exc}") from exc
    _record_solver_artifact(ctx)
    return State.EXTRACT


def phase_extract(ctx: Context) -> State:
    assert ctx.active_container is not None
    result = staging.extract_candidate(
        ctx.active_container,
        set(ctx.task.selected_test_files),
        _workdir(ctx),
        ctx.artifact_dir / "candidate.patch",
    )
    ctx.candidate_patch_path = result.candidate_diff_path
    ctx.no_patch = result.no_patch
    ctx.reserved_path_collisions = result.reserved_path_collisions
    _record_path_artifact(ctx, "candidate_patch", ctx.candidate_patch_path)
    return State.DESTROY_SOLVE


def phase_destroy_solve(ctx: Context) -> State:
    if ctx.solve_container is not None:
        _record_container_event(ctx, "container_destroy_start", "solve", ctx.solve_container)
        ctx.solve_container.destroy()
        _record_container_event(ctx, "container_destroyed", "solve", ctx.solve_container)
    ctx.solve_container = None
    ctx.active_container = None
    return State.PROVISION_GRADE


def phase_apply_candidate(ctx: Context) -> State:
    assert ctx.active_container is not None
    if ctx.no_patch:
        ctx.apply_result = staging.ApplyResult(winner=None, partial=False, rejected_files=())
        return State.STAGE_OVERLAY
    assert ctx.candidate_patch_path is not None
    candidate_dest = "/tmp/candidate.patch"
    ctx.active_container.copy_in(ctx.candidate_patch_path, candidate_dest)
    try:
        ctx.apply_result = staging.apply_patch(ctx.active_container, candidate_dest, _workdir(ctx))
    except PhaseError as exc:
        if exc.code == TaxonomyCode.PATCH_APPLY_FAILED.value:
            ctx.failure_class = "patch_apply_failed"
            raise PhaseError(State.DONE_UNRESOLVED, TaxonomyCode.PATCH_APPLY_FAILED, "candidate patch did not apply") from exc
        raise
    return State.STAGE_OVERLAY


@requires_role_not_solve
def phase_stage_overlay(ctx: Context) -> State:
    assert ctx.active_container is not None
    assert ctx.setup_plan is not None
    staging.inject_hidden(ctx.active_container, ctx.setup_plan, _workdir(ctx))
    return State.RUN_TESTS


def phase_grade(ctx: Context) -> State:
    result = ctx.parsed_results["solver"]
    outcome = grader.grade_run(
        result.status_map,
        ctx.task.fail_to_pass,
        ctx.task.pass_to_pass,
        grader.GradeContext(
            no_patch=ctx.no_patch,
            patch_apply_partial=ctx.apply_result.partial if ctx.apply_result else False,
        ),
    )
    _record_outcomes(ctx, "solver", outcome.per_test, result)
    ctx.verdict = outcome.verdict
    ctx.failure_class = outcome.failure_class.value if outcome.failure_class else None
    if outcome.verdict == "RESOLVED":
        return State.DONE_RESOLVED
    if outcome.failure_class is not None:
        ctx.taxonomy_code = outcome.failure_class.value
        ctx.message = f"DONE_UNRESOLVED: {ctx.taxonomy_code}: candidate classified as {ctx.taxonomy_code}"
    return State.DONE_UNRESOLVED


def phase_stub_done_resolved(ctx: Context) -> State:
    ctx.verdict = "RESOLVED"
    return State.DONE_RESOLVED


def phase_stub_done_valid(ctx: Context) -> State:
    ctx.verdict = "VALID"
    return State.DONE_VALID


TABLE: dict[tuple[str, State], Phase] = {
    ("validate", State.START_VALIDATE): phase_start_validate,
    ("validate", State.ACQUIRE_IMAGE): phase_acquire_image,
    ("validate", State.PROVISION_VALIDATE): phase_provision_validate,
    ("validate", State.NORMALIZE_BASE): phase_normalize_base,
    ("validate", State.STAGE_FULL): phase_stage_full,
    ("validate", State.RUN_TESTS): phase_run_tests,
    ("validate", State.PARSE): phase_parse,
    ("validate", State.ASSERT_BASELINE): phase_assert_baseline,
    ("validate", State.APPLY_GOLDEN): phase_apply_golden,
    ("validate", State.ASSERT_GOLDEN): phase_assert_golden,
    ("run", State.START_RUN): phase_start_run,
    ("run", State.ACQUIRE_IMAGE): phase_acquire_image,
    ("run", State.PROVISION_SOLVE): phase_provision_solve,
    ("run", State.NORMALIZE_BASE): phase_normalize_base,
    ("run", State.SCRUB_HISTORY): phase_scrub_history,
    ("run", State.SEAL): phase_seal,
    ("run", State.SOLVE): phase_solve,
    ("run", State.EXTRACT): phase_extract,
    ("run", State.DESTROY_SOLVE): phase_destroy_solve,
    ("run", State.PROVISION_GRADE): phase_provision_grade,
    ("run", State.APPLY_CANDIDATE): phase_apply_candidate,
    ("run", State.STAGE_OVERLAY): phase_stage_overlay,
    ("run", State.RUN_TESTS): phase_run_tests,
    ("run", State.PARSE): phase_parse,
    ("run", State.GRADE): phase_grade,
}


def _record_outcomes(
    ctx: Context,
    phase: str,
    outcomes: tuple[grader.TestOutcome, ...],
    parse_result: parser.ParseResult,
) -> None:
    rows = tuple(
        TestOutcomeRow(
            run_id=ctx.run_id,
            phase=phase,
            test_id=outcome.test_id,
            expected=outcome.expected,
            actual_status=outcome.actual_status.value,
            satisfied=outcome.satisfied,
            duration_ms=parse_result.durations_ms.get(outcome.test_id, 0),
        )
        for outcome in outcomes
    )
    ctx.store.record_test_outcomes(ctx.run_id, phase, rows)


def _limits_from_task(ctx: Context) -> ResourceLimits:
    return ResourceLimits(
        cpu_quota=ctx.task.limits.cpu_quota,
        memory_gb=ctx.task.limits.memory_gb,
        wall_clock_seconds=ctx.task.limits.wall_clock_seconds,
    )


def _raise_if_framework_unsupported(ctx: Context, verb: str) -> None:
    if ctx.task.repo_language == "python" and ctx.task.test.framework == "pytest":
        return
    message = _unsupported_framework_message(ctx.task)
    if verb == "run":
        ctx.failure_class = "build_failed"
        raise PhaseError(State.DONE_UNRESOLVED, TaxonomyCode.BUILD_FAILED, message)
    raise PhaseError(State.DONE_INVALID, TaxonomyCode.TEST_EXEC_FAILED, message)


def _unsupported_framework_message(task: Task) -> str:
    return (
        "unsupported test framework: "
        f"repo_language={task.repo_language}, framework={task.test.framework}; "
        "only python/pytest is implemented"
    )


def _test_env(task: Task, workdir: str) -> dict[str, str] | None:
    if task.repo_language != "python":
        return None
    return {
        "PYTHONPATH": f"{workdir}/lib:{workdir}",
        "QT_QPA_PLATFORM": "offscreen",
        "XDG_RUNTIME_DIR": "/tmp/task-bundle-runtime",
    }


def _record_solver_artifact(ctx: Context) -> None:
    if ctx.solver_result is None:
        return
    path = ctx.artifact_dir / "solver_transcript.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "completed": ctx.solver_result.completed,
        "transcript": list(ctx.solver_result.transcript),
        "metadata": ctx.solver_result.metadata,
    }
    data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    path.write_bytes(data)
    ctx.store.record_artifact(ctx.run_id, "solver_transcript", str(path), hashlib.sha256(data).hexdigest(), len(data))


def _record_path_artifact(ctx: Context, kind: str, path: Path) -> None:
    if not hasattr(ctx.store, "record_artifact"):
        return
    if not path.exists() or not path.is_file():
        return
    data = path.read_bytes()
    ctx.store.record_artifact(ctx.run_id, kind, str(path), hashlib.sha256(data).hexdigest(), len(data))


def _write_test_command_artifact(ctx: Context, path: Path, command: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workdir = _workdir(ctx)
    env = _test_env(ctx.task, workdir) or {}
    env_prefix = " ".join(f"{key}={shlex.quote(value)}" for key, value in sorted(env.items()))
    rendered = shlex.join(command)
    line = f"{env_prefix} {rendered}".strip()
    body = f"#!/bin/sh\ncd {shlex.quote(workdir)}\nexec {line}\n"
    path.write_text(body, encoding="utf-8", newline="\n")
    _record_path_artifact(ctx, f"{ctx.last_test_phase}_test_command", path)


def _capture_isolation(ctx: Context, role: str, container: Container) -> None:
    if hasattr(ctx.container_manager, "verify_isolation"):
        try:
            ctx.isolation_snapshot[role] = ctx.container_manager.verify_isolation(container)
        except Exception:
            pass


def _prepare_workspace(ctx: Context, container: Container) -> None:
    if not hasattr(ctx.container_manager, "prepare_workspace"):
        return
    try:
        ctx.workspace_dir = ctx.container_manager.prepare_workspace(container, ctx.task.workdir)
    except Exception as exc:
        raise PhaseError(
            State.ERROR,
            TaxonomyCode.PROVISION_FAILED,
            f"container workspace preparation failed for {ctx.task.workdir}: {exc}",
        ) from exc


def _record_container_event(ctx: Context, kind: str, role: str, container: Container) -> None:
    container_id = getattr(container, "id", "")
    ctx.store.append_event(
        ctx.run_id,
        kind,
        {
            "role": role,
            "container_id": container_id,
        },
    )


def _workdir(ctx: Context) -> str:
    return ctx.workspace_dir or ctx.task.workdir


def _record_solve_boundary_snapshot(ctx: Context) -> None:
    if ctx.active_container is None:
        return
    workdir = _workdir(ctx)
    quoted_paths = " ".join(shlex.quote(path) for path in ctx.task.selected_test_files)
    selected_result = ctx.active_container.exec(
        f"for p in {quoted_paths}; do if [ -e \"$p\" ]; then echo \"$p\"; fi; done",
        workdir=workdir,
        timeout_seconds=60,
    )
    existing_selected = _read_lines(selected_result.stdout_path) if selected_result.exit_code == 0 else ["<probe_failed>"]
    log_result = ctx.active_container.exec("git log --all --format=oneline", workdir=workdir, timeout_seconds=60)
    git_log_lines = _read_lines(log_result.stdout_path) if log_result.exit_code == 0 else ["<probe_failed>"]
    instance_result = ctx.active_container.exec(
        ["git", "cat-file", "-e", f"{ctx.task.instance_commit}^{{commit}}"],
        workdir=workdir,
        timeout_seconds=60,
    )
    hidden_result = ctx.active_container.exec("test ! -d hidden", workdir=workdir, timeout_seconds=60)
    ctx.store.append_event(
        ctx.run_id,
        "solve_boundary_snapshot",
        {
            "selected_files_absent": selected_result.exit_code == 0 and not existing_selected,
            "existing_selected_files": existing_selected,
            "git_log_oneline_count": len(git_log_lines),
            "git_log_oneline_first": git_log_lines[0] if git_log_lines else "",
            "instance_commit_reachable": instance_result.exit_code == 0,
            "hidden_dir_absent": hidden_result.exit_code == 0,
            "workdir": workdir,
        },
    )


def _record_solver_visible_tests_manifest(ctx: Context) -> None:
    """Record which test files remain in the solve workspace after sealing."""
    if ctx.active_container is None:
        return
    workdir = _workdir(ctx)
    listing = ctx.active_container.exec(
        ["sh", "-c",
         "find . -type f \\( -name 'test_*.py' -o -name '*_test.py' "
         "-o -name 'test_*.js' -o -name '*.test.js' -o -name '*.test.ts' "
         "-o -name '*_test.go' \\) -not -path '*/.git/*' 2>/dev/null | "
         "sed 's|^\\./||' | sort"],
        workdir=workdir, timeout_seconds=60,
    )
    visible = _read_lines(listing.stdout_path) if listing.exit_code == 0 else []
    reserved = set(ctx.task.selected_test_files)
    manifest = {
        "workdir": workdir,
        "visible_test_files_count": len(visible),
        "visible_test_files": visible,
        "reserved_test_files_count": len(reserved),
        "reserved_test_files_withheld_from_solver": sorted(reserved),
        "any_reserved_leaked_into_visible": sorted(reserved & set(visible)),
    }
    manifest_path = ctx.artifact_dir / "solver_visible_tests_manifest.json"
    try:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        try:
            ctx.store.record_artifact(
                ctx.run_id, kind="solver_visible_tests_manifest",
                path=str(manifest_path), bytes=manifest_path.stat().st_size)
        except Exception:
            pass
    except Exception:
        pass
    ctx.store.append_event(
        ctx.run_id,
        "solver_visible_tests_manifest",
        {"visible_count": len(visible),
         "reserved_count": len(reserved),
         "leaks": manifest["any_reserved_leaked_into_visible"]},
    )


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]


def _state_from_any(value: Any) -> State:
    if isinstance(value, State):
        return value
    if isinstance(value, TerminalState):
        return State[value.name]
    return State(str(value))


def _verdict_for_state(state: State) -> str | None:
    return {
        State.DONE_VALID: "VALID",
        State.DONE_INVALID: "INVALID",
        State.DONE_RESOLVED: "RESOLVED",
        State.DONE_UNRESOLVED: "UNRESOLVED",
        State.ERROR: "ERROR",
    }[state]


def _now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def _json_tuple(values: tuple[str, ...]) -> str | None:
    if not values:
        return None
    import json

    return json.dumps(list(values))


def _copy_if_exists(src: Path | str | None, dest: Path) -> None:
    if src is None:
        return
    path = Path(src)
    if not path.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, dest)


def _junit_is_execution_failure(junit_path: Path) -> bool:
    if not junit_path.exists():
        return True


def _cover_pytest_collection_failures(ctx: Context, result: parser.ParseResult, missing: set[str]) -> None:
    if ctx.task.test.framework != "pytest" or ctx.last_stdout_path is None:
        return
    error_files = _pytest_collection_error_files(ctx.last_stdout_path)
    if not error_files:
        return
    for test_id in missing:
        file_path = test_id.split("::", 1)[0]
        if file_path in error_files:
            result.status_map[test_id] = grader.TestStatus.FAIL
            result.durations_ms.setdefault(test_id, 0)


def _cover_truncated_param_ids(result: parser.ParseResult, missing: set[str]) -> None:
    for test_id in tuple(missing):
        candidates = [nodeid for nodeid in result.status_map if nodeid.startswith(test_id)]
        statuses = {result.status_map[nodeid] for nodeid in candidates}
        if not candidates or len(statuses) != 1:
            continue
        candidate = candidates[0]
        result.status_map[test_id] = result.status_map[candidate]
        result.durations_ms[test_id] = result.durations_ms.get(candidate, 0)


def _pytest_collection_error_files(stdout_path: Path) -> set[str]:
    if not stdout_path.exists():
        return set()
    text = stdout_path.read_text(encoding="utf-8", errors="replace")
    files: set[str] = set()
    for match in re.finditer(r"ERROR collecting ([^\s]+\.py)", text):
        files.add(match.group(1).replace("\\", "/"))
    for match in re.finditer(r"^ERROR ([^\s]+\.py)(?:\s|$)", text, flags=re.MULTILINE):
        files.add(match.group(1).replace("\\", "/"))
    return files
    try:
        from xml.etree import ElementTree

        root = ElementTree.parse(junit_path).getroot()
        has_testcase = any(True for _ in root.iter("testcase"))
        has_file_error = root.find(".//error") is not None and not has_testcase
        return (not has_testcase) or has_file_error
    except Exception:
        return True
