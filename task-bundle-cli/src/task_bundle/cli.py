"""Typer command surface for argument parsing, verb dispatch, and exit codes."""

from __future__ import annotations

import dataclasses
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from task_bundle import bundle
from task_bundle.container import ContainerManager, NetworkPolicy, ResourceLimits
from task_bundle.errors import BundleError, BundleInitError
from task_bundle.orchestrator import Context, State, run as orchestrator_run
from task_bundle.render import render_terminal
from task_bundle.store import Store


app = typer.Typer(no_args_is_help=True, help="Validate and run solver-agnostic task bundles.")
init_app = typer.Typer(no_args_is_help=True, help="Create task bundle directories.")
app.add_typer(init_app, name="init")

store_factory = Store
container_manager_factory = ContainerManager


@app.callback()
def main(
    verbose: Annotated[bool, typer.Option("--verbose", help="Print verbose progress.")] = False,
) -> None:
    """Task Bundle CLI."""


@init_app.command("from-row")
def init_from_row_command(
    row_json: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    target_dir: Annotated[Path, typer.Argument()],
    force: Annotated[bool, typer.Option("--force", help="Replace an existing target directory.")] = False,
) -> None:
    """Create a schema-valid bundle from one SWE-bench Pro row JSON."""

    try:
        row = json.loads(row_json.read_text(encoding="utf-8"))
        bundle.init_from_row(row, target_dir, force=force)
    except (json.JSONDecodeError, BundleInitError, BundleError) as exc:
        _render_init_error(exc, phase="INIT_FROM_ROW", artifact=row_json)
        raise typer.Exit(2) from exc
    typer.echo(str(target_dir))


@init_app.command("manual")
def init_manual_command(
    target_dir: Annotated[Path, typer.Argument()],
    force: Annotated[bool, typer.Option("--force", help="Replace an existing target directory.")] = False,
) -> None:
    """Create a TODO-marked manual bundle skeleton matching the bundle schema."""

    try:
        bundle.init_manual(target_dir, force=force)
    except (BundleInitError, BundleError) as exc:
        _render_init_error(exc, phase="INIT_MANUAL", artifact=target_dir)
        raise typer.Exit(2) from exc
    typer.echo("bundle written; fill TODOs and run task validate to confirm")


@init_app.command("from-spec")
def init_from_spec_command(
    target_dir: Annotated[Path, typer.Argument()],
    repo: Annotated[str, typer.Option("--repo", help="Repository identifier, e.g. owner/name.")],
    commit: Annotated[str, typer.Option("--commit", help="Instance commit SHA (40-char hex).")],
    image: Annotated[str, typer.Option("--image", help="Docker image ref, e.g. registry/image:tag.")],
    base: Annotated[str | None, typer.Option("--base", help="Optional base commit SHA. Defaults to a placeholder distinct from --commit.")] = None,
    language: Annotated[str, typer.Option("--language", help="Repo language: python|js|ts|go.")] = "python",
    tests: Annotated[list[str] | None, typer.Option("--tests", help="Test file path (repeatable).")] = None,
    workdir: Annotated[str, typer.Option("--workdir", help="Container workdir holding the repo.")] = "/testbed",
    framework: Annotated[str, typer.Option("--framework", help="Test framework: pytest|junit|exit_code.")] = "pytest",
    force: Annotated[bool, typer.Option("--force", help="Replace an existing target directory.")] = False,
) -> None:
    """Create a bundle scaffold from --repo + --commit.

    Produces a structurally complete bundle; fill golden.patch and fail_to_pass.txt
    before running `task validate`.
    """
    try:
        bundle.init_from_spec(
            repo=repo, commit=commit, image_ref=image,
            target_dir=target_dir, base_commit=base,
            repo_language=language,
            selected_test_files=list(tests or []),
            workdir=workdir, framework=framework, force=force,
        )
    except (BundleInitError, BundleError) as exc:
        _render_init_error(exc, phase="INIT_FROM_SPEC", artifact=target_dir)
        raise typer.Exit(2) from exc
    typer.echo(f"scaffold written to {target_dir}; fill hidden/golden.patch + hidden/fail_to_pass.txt then run task validate")


@app.command()
def validate(
    bundle_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    db: Annotated[Path | None, typer.Option("--db", help="Override runs database path.")] = None,
    artifacts: Annotated[Path | None, typer.Option("--artifacts", help="Override artifact root path.")] = None,
) -> None:
    """Validate bundle quality: broken base fails F2P, golden patch resolves it."""

    try:
        task = bundle.load(bundle_dir)
    except BundleError as exc:
        _render_init_error(exc, phase="BUNDLE_LOAD", artifact=bundle_dir)
        raise typer.Exit(2) from exc

    run_id = str(uuid.uuid4())
    typer.echo(run_id)
    try:
        with store_factory(db_path=db, artifact_root=artifacts) as store:
            artifact_dir = store.artifact_dir(run_id).resolve()
            artifact_dir.mkdir(parents=True, exist_ok=True)
            manager = container_manager_factory(artifact_dir)
            ctx = Context(
                task=task,
                run_id=run_id,
                store=store,
                artifact_dir=artifact_dir,
                container_manager=manager,
            )
            exit_code = orchestrator_run(ctx, "validate")
            typer.echo(render_terminal(ctx), err=True)
    except Exception as exc:
        typer.echo(f"ERROR: {type(exc).__name__}: {exc}", err=True)
        raise typer.Exit(2) from exc
    raise typer.Exit(exit_code)


@app.command()
def run(
    bundle_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    solver: Annotated[str, typer.Option("--solver", help="Solver adapter name.")] = "trusted-golden-stub",
    db: Annotated[Path | None, typer.Option("--db", help="Override runs database path.")] = None,
    artifacts: Annotated[Path | None, typer.Option("--artifacts", help="Override artifact root path.")] = None,
) -> None:
    """Run a solver in sealed solve isolation, then grade hidden tests separately."""

    try:
        task = bundle.load(bundle_dir)
    except BundleError as exc:
        _render_init_error(exc, phase="BUNDLE_LOAD", artifact=bundle_dir)
        raise typer.Exit(2) from exc

    run_id = str(uuid.uuid4())
    typer.echo(run_id)
    try:
        with store_factory(db_path=db, artifact_root=artifacts) as store:
            artifact_dir = store.artifact_dir(run_id).resolve()
            artifact_dir.mkdir(parents=True, exist_ok=True)
            manager = container_manager_factory(artifact_dir)
            ctx = Context(
                task=task,
                run_id=run_id,
                store=store,
                artifact_dir=artifact_dir,
                container_manager=manager,
                solver_name=solver,
            )
            exit_code = orchestrator_run(ctx, "run")
            typer.echo(render_terminal(ctx), err=True)
    except Exception as exc:
        typer.echo(f"ERROR: {type(exc).__name__}: {exc}", err=True)
        raise typer.Exit(2) from exc
    raise typer.Exit(exit_code)


@app.command()
def logs(
    run_id: Annotated[str, typer.Argument()],
    json_output: Annotated[bool, typer.Option("--json", help="Emit FullRunReport JSON.")] = False,
    db: Annotated[Path | None, typer.Option("--db", help="Override runs database path.")] = None,
) -> None:
    """Show the full hydrated run record, including events, tests, and artifacts."""

    try:
        with store_factory(db_path=db) as store:
            report = store.get_run_full(run_id)
    except Exception as exc:
        typer.echo(f"ERROR: {type(exc).__name__}: {exc}", err=True)
        raise typer.Exit(2) from exc
    if json_output:
        typer.echo(json.dumps(dataclasses.asdict(report), sort_keys=True))
        return
    typer.echo(_render_full_report(report))


@app.command("list")
def list_runs(
    task_id: Annotated[str | None, typer.Option("--task-id", help="Filter by task id.")] = None,
    verdict: Annotated[str | None, typer.Option("--verdict", help="Filter by verdict.")] = None,
    verb: Annotated[str | None, typer.Option("--verb", help="Filter by verb.")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum rows.")] = 50,
    db: Annotated[Path | None, typer.Option("--db", help="Override runs database path.")] = None,
) -> None:
    """List recent persisted validate/run records as a table."""

    try:
        with store_factory(db_path=db) as store:
            rows = store.list_runs(task_id=task_id, verdict=verdict, verb=verb, limit=limit)
    except Exception as exc:
        typer.echo(f"ERROR: {type(exc).__name__}: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo("run_id   verb      task_id                        verdict       failure_class       started")
    for row in rows:
        typer.echo(
            f"{row.run_id[:8]:<8} {row.verb:<9} {row.task_id[:30]:<30} "
            f"{(row.verdict or ''):<13} {(row.failure_class or ''):<19} {_relative_time(row.started_at)}"
        )


@app.command()
def doctor(
    image: Annotated[str, typer.Option("--image", help="Image tag to inspect.")] = "alpine:3.19",
    db: Annotated[Path | None, typer.Option("--db", help="Compatibility option; doctor does not write runs.")] = None,
) -> None:
    """Inspect Docker reachability and the isolation flags used by matrix runs."""

    try:
        manager = container_manager_factory(Path(".task-doctor-artifacts").resolve())
        if hasattr(manager, "client") and hasattr(manager.client, "ping"):
            manager.client.ping()
    except Exception as exc:
        typer.echo("ERROR: Docker daemon unreachable; start Docker Desktop or `dockerd` and retry.", err=True)
        raise typer.Exit(2) from exc

    container = None
    try:
        image_ref = manager.acquire_image(image)
        container = manager.create(
            image_ref,
            role="validate",
            limits=ResourceLimits(),
            network=NetworkPolicy.NONE,
            labels={"run_id": "doctor"},
        )
        snapshot = manager.verify_isolation(container)
        expected = {
            "user_non_root": True,
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
            "pids_limit": 1024,
            "memory_bytes": 2147483648,
            "cpu_quota": 200000,
            "cpu_period": 100000,
            "network_mode": "none",
            "tmpfs": {"/tmp": "size=512m"},
            "init": True,
            "mounts": [],
            "privileged": False,
            "auto_remove": False,
        }
        divergent = [key for key, value in expected.items() if snapshot.get(key) != value]
        typer.echo("key requested applied")
        for key, value in expected.items():
            typer.echo(f"{key} {value} {snapshot.get(key)}")
        if divergent:
            typer.echo(f"ERROR: isolation mismatch: {', '.join(divergent)}", err=True)
            raise typer.Exit(2)
    except typer.Exit:
        raise
    except Exception as exc:
        typer.echo(f"ERROR: {type(exc).__name__}: {exc}", err=True)
        raise typer.Exit(2) from exc
    finally:
        if container is not None:
            try:
                container.destroy()
            except Exception:
                pass


def _render_init_error(exc: Exception, *, phase: str, artifact: Path | None = None) -> None:
    code = getattr(exc, "code", None)
    rendered_code = getattr(code, "value", str(code)) if code is not None else type(exc).__name__
    typer.echo(f"{rendered_code}: {exc}", err=True)
    typer.echo(f"phase: {phase}", err=True)
    if artifact is not None:
        typer.echo(f"artifact: {Path(artifact).resolve()}", err=True)

def _render_full_report(report: object) -> str:
    run_record = report.run
    lines = [
        "Run",
        f"run_id: {run_record.run_id}",
        f"task_id: {run_record.task_id}",
        f"verb: {run_record.verb}",
        f"started_at: {run_record.started_at}",
        f"finished_at: {run_record.finished_at or '(in flight)'}",
        f"verdict: {run_record.verdict or '(pending)'}",
        f"taxonomy_code: {run_record.taxonomy_code or ''}",
        f"failure_class: {run_record.failure_class or ''}",
        f"exit_code: {'' if run_record.exit_code is None else run_record.exit_code}",
        "",
        "Reproducibility",
        f"image_tag: {run_record.image_tag}",
        f"image_digest: {run_record.image_digest or ''}",
        f"base_commit: {run_record.base_commit}",
        f"instance_commit: {run_record.instance_commit}",
        f"bundle_hash: {run_record.bundle_hash}",
        f"parser_version: {run_record.parser_version}",
        f"apply_ladder_winner: {run_record.apply_ladder_winner or ''}",
        f"apply_partial: {'' if run_record.apply_partial is None else run_record.apply_partial}",
    ]
    if run_record.isolation_snapshot_json:
        lines.append("isolation_snapshot:")
        try:
            snapshot = json.loads(run_record.isolation_snapshot_json)
        except json.JSONDecodeError:
            snapshot = {"raw": run_record.isolation_snapshot_json}
        for key, value in snapshot.items():
            lines.append(f"{key}: {value}")
    lines.extend(["", "Phase Timeline"])
    events = list(report.events)
    first_ts = events[0].ts if events else None
    for event in events:
        elapsed = 0.0 if first_ts is None else event.ts - first_ts
        lines.append(f"{elapsed:8.3f}s {event.kind}: {event.payload_json}")
    lines.append("")
    lines.append("Test Outcomes")
    phase_order = {"baseline_pre": 0, "baseline_post_golden": 1, "solver": 2}
    outcomes = sorted(report.test_outcomes, key=lambda row: (phase_order.get(row.phase, 99), row.phase, _expected_order(row.expected), row.test_id))
    current_phase = None
    for row in outcomes:
        if row.phase != current_phase:
            current_phase = row.phase
            lines.append(f"[{current_phase}]")
        label = {"fail_to_pass": "F2P", "pass_to_pass": "P2P"}.get(row.expected, "free")
        lines.append(f"[{row.actual_status}] [{label}] {row.test_id} satisfied={row.satisfied}")
    lines.append("")
    lines.append("Artifacts")
    for artifact in report.artifacts:
        lines.append(f"{artifact.kind}: {artifact.path} ({artifact.bytes} bytes)")
    if run_record.error_message:
        lines.extend(["", "Error", run_record.error_message])
    if report.in_flight:
        lines.append("(in flight)")
    return "\n".join(lines)


def _expected_order(expected: str) -> int:
    return {"fail_to_pass": 0, "pass_to_pass": 1, "free": 2}.get(expected, 3)


def _relative_time(started_at: str) -> str:
    try:
        started = datetime.fromisoformat(started_at)
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        seconds = max(0, int((datetime.now(UTC) - started).total_seconds()))
    except ValueError:
        return started_at
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


if __name__ == "__main__":
    app()
