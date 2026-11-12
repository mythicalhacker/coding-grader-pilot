#!/usr/bin/env python3
"""Run every cached Hugging Face row through the task-bundle harness.

The runner is intentionally resumeable. It writes one JSON record per dataset
row after each validate/run attempt so an interrupted Docker pull or long test
suite does not discard earlier evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from task_bundle.bundle import init_from_row, load
from task_bundle.container import ContainerManager
from task_bundle.orchestrator import Context, run as orchestrator_run
from task_bundle.store import Store


DATASET_PATH = Path(os.environ.get("TASK_BUNDLE_PARQUET", "hf_cache/data/test-00000-of-00001.parquet"))
DEFAULT_OUTDIR = Path("scripts/transcripts/hf_full_dataset_20260520")


def main() -> int:
    args = _parse_args()
    outdir = Path(args.outdir)
    bundles = outdir / "bundles"
    artifacts = outdir / "artifacts"
    db = outdir / "runs.db"
    rows_path = outdir / "rows.jsonl"
    summary_path = outdir / "summary.json"
    outdir.mkdir(parents=True, exist_ok=True)
    bundles.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)

    existing = _read_existing(rows_path)
    df = pd.read_parquet(DATASET_PATH)
    selected = df.iloc[args.start :]
    if args.limit is not None:
        selected = selected.iloc[: args.limit]

    with Store(db_path=db, artifact_root=artifacts) as store:
        for idx, series in selected.iterrows():
            row = series.to_dict()
            instance_id = str(row["instance_id"])
            if instance_id in existing and not args.force:
                continue
            record = _run_row(
                idx=int(idx),
                row=row,
                bundles=bundles,
                store=store,
                run_valid=args.run_valid,
                wall_clock_seconds=args.wall_clock_seconds,
            )
            _upsert_jsonl(rows_path, record)
            existing[instance_id] = record
            print(json.dumps(record, sort_keys=True), flush=True)

    rows = list(_read_existing(rows_path).values())
    for row in rows:
        row["status"] = _classify(row)
    _write_jsonl(rows_path, rows)
    summary = _summary(rows)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"wrote {outdir}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true", help="Re-run rows already present in rows.jsonl.")
    parser.add_argument("--run-valid", action="store_true", help="Run trusted-golden-stub after validate returns VALID.")
    parser.add_argument(
        "--wall-clock-seconds",
        type=int,
        default=300,
        help="Per-row Docker exec wall budget override for dataset verification.",
    )
    return parser.parse_args()


def _run_row(
    *,
    idx: int,
    row: dict[str, Any],
    bundles: Path,
    store: Store,
    run_valid: bool,
    wall_clock_seconds: int,
) -> dict[str, Any]:
    start = time.monotonic()
    bundle_dir = bundles / f"row_{idx:04d}_{_safe_name(str(row['instance_id']))}"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir, ignore_errors=True)
    record: dict[str, Any] = {
        "idx": idx,
        "instance_id": row.get("instance_id"),
        "repo": row.get("repo"),
        "repo_language": row.get("repo_language"),
        "dockerhub_tag": row.get("dockerhub_tag"),
        "bundle": str(bundle_dir),
        "validate": None,
        "run": None,
        "status": "not_started",
        "seconds": None,
    }
    try:
        init_from_row(row, bundle_dir, force=True)
        task = load(bundle_dir)
        if wall_clock_seconds > 0:
            task = task.model_copy(
                update={"limits": task.limits.model_copy(update={"wall_clock_seconds": wall_clock_seconds})}
            )
        validate = _execute(store, task, "validate")
        record["validate"] = validate
        if validate["verdict"] == "VALID" and run_valid:
            record["run"] = _execute(store, task, "run")
        record["status"] = _classify(record)
    except Exception as exc:  # keep the all-row run moving and record the failure.
        record["status"] = "runner_error"
        record["runner_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        record["seconds"] = round(time.monotonic() - start, 3)
    return record


def _execute(store: Store, task: object, verb: str) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    artifact_dir = store.artifact_dir(run_id).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    ctx = Context(
        task=task,
        run_id=run_id,
        store=store,
        artifact_dir=artifact_dir,
        container_manager=ContainerManager(store.artifact_base),
    )
    exit_code = orchestrator_run(ctx, verb)
    return {
        "run_id": run_id,
        "exit_code": exit_code,
        "verdict": ctx.verdict,
        "terminal_state": ctx.terminal_state.value if ctx.terminal_state else None,
        "taxonomy_code": ctx.taxonomy_code,
        "failure_class": ctx.failure_class,
        "message": ctx.message,
    }


def _classify(record: dict[str, Any]) -> str:
    if record.get("runner_error"):
        return "runner_error"
    validate = record.get("validate") or {}
    run = record.get("run") or {}
    if run.get("verdict") == "RESOLVED":
        return "resolved"
    if validate.get("verdict") == "VALID":
        return "valid"
    if validate.get("taxonomy_code") == "TEST_EXEC_FAILED":
        message = str(validate.get("message") or "").lower()
        if "unsupported test framework" in message:
            return "unsupported_framework"
        return "test_exec_failed"
    if validate.get("verdict") == "INVALID":
        return "invalid"
    if validate.get("verdict") == "ERROR":
        return "error"
    return "other"


def _read_existing(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        rows[str(record["instance_id"])] = record
    return rows


def _upsert_jsonl(path: Path, record: dict[str, Any]) -> None:
    rows = _read_existing(path)
    rows[str(record["instance_id"])] = record
    _write_jsonl(path, list(rows.values()))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in sorted(rows, key=lambda item: item["idx"])),
        encoding="utf-8",
    )


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rows_recorded": len(rows),
        "by_status": _counts(row["status"] for row in rows),
        "by_language": _counts(str(row["repo_language"]) for row in rows),
        "by_validate_verdict": _counts(((row.get("validate") or {}).get("verdict") or "none") for row in rows),
        "by_taxonomy": _counts(((row.get("validate") or {}).get("taxonomy_code") or "none") for row in rows),
        "run_valid_enabled": any(row.get("run") for row in rows),
        "resolved_rows": sum(1 for row in rows if (row.get("run") or {}).get("verdict") == "RESOLVED"),
        "total_seconds": round(sum(float(row.get("seconds") or 0) for row in rows), 3),
    }


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)[:140]


if __name__ == "__main__":
    raise SystemExit(main())
