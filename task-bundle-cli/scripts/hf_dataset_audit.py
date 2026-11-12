#!/usr/bin/env python3
"""Audit every row in the local Hugging Face parquet at the bundle boundary."""

from __future__ import annotations

import ast
import json
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from task_bundle.bundle import init_from_row, load


DATASET_PATH = Path(os.environ.get("TASK_BUNDLE_PARQUET", "hf_cache/data/test-00000-of-00001.parquet"))
OUTDIR = Path("scripts/transcripts/hf_dataset_audit")


def main() -> int:
    outdir = Path(os.environ.get("HF_AUDIT_OUTDIR", str(OUTDIR)))
    bundles = outdir / "bundle_load_check"
    outdir.mkdir(parents=True, exist_ok=True)
    if bundles.exists():
        shutil.rmtree(bundles, ignore_errors=True)
    if bundles.exists():
        bundles = outdir / f"bundle_load_check_{len(list(outdir.glob('bundle_load_check*'))):02d}"
    bundles.mkdir()

    df = pd.read_parquet(DATASET_PATH)
    rows: list[dict[str, Any]] = []
    init_errors: list[dict[str, Any]] = []

    for idx, series in df.iterrows():
        row = series.to_dict()
        f2p = _parse_list(row.get("fail_to_pass"))
        p2p = _parse_list(row.get("pass_to_pass"))
        selected_files = _parse_list(row.get("selected_test_files_to_run"))
        bundle = bundles / f"row_{idx:04d}"
        status = "load_ok"
        error = None
        try:
            init_from_row(row, bundle, force=True)
            load(bundle)
        except Exception as exc:  # audit should keep going across malformed rows.
            status = "load_error"
            error = f"{type(exc).__name__}: {exc}"
            init_errors.append({"idx": int(idx), "instance_id": row.get("instance_id"), "error": error})

        rows.append(
            {
                "idx": int(idx),
                "instance_id": row.get("instance_id"),
                "repo": row.get("repo"),
                "repo_language": row.get("repo_language"),
                "dockerhub_tag": row.get("dockerhub_tag"),
                "f2p_count": len(f2p),
                "p2p_count": len(p2p),
                "selected_file_count": len(selected_files),
                "bad_f2p_ids": _bad_ids(f2p),
                "bad_p2p_ids": _bad_ids(p2p),
                "status": status,
                "error": error,
            }
        )

    summary = _summary(df, rows, init_errors)
    (outdir / "rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (outdir / "summary.md").write_text(_summary_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {outdir}")
    return 0


def _parse_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if value is None:
        return []
    if not isinstance(value, str):
        return []
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(value)
        except Exception:
            continue
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, str)]
    return []


def _bad_ids(values: list[str]) -> list[str]:
    return [value for value in values if value.count("[") != value.count("]")]


def _summary(df: pd.DataFrame, rows: list[dict[str, Any]], init_errors: list[dict[str, Any]]) -> dict[str, Any]:
    languages = Counter(str(row["repo_language"]) for row in rows)
    repos = Counter(str(row["repo"]) for row in rows)
    p2p_zero = Counter(str(row["repo_language"]) for row in rows if row["p2p_count"] == 0)
    return {
        "rows_total": len(rows),
        "bundle_load": dict(Counter(str(row["status"]) for row in rows)),
        "by_language": dict(languages),
        "by_repo": dict(repos),
        "unique_docker_tags": int(df["dockerhub_tag"].nunique()),
        "pytest_supported_now": {
            "python_rows": languages.get("python", 0),
            "non_python_rows": len(rows) - languages.get("python", 0),
        },
        "p2p_zero_by_language": dict(p2p_zero),
        "bad_test_ids": {
            "rows_with_bad_f2p_ids": sum(bool(row["bad_f2p_ids"]) for row in rows),
            "rows_with_bad_p2p_ids": sum(bool(row["bad_p2p_ids"]) for row in rows),
            "bad_f2p_id_total": sum(len(row["bad_f2p_ids"]) for row in rows),
            "bad_p2p_id_total": sum(len(row["bad_p2p_ids"]) for row in rows),
        },
        "test_count_stats": {
            "f2p_total": sum(int(row["f2p_count"]) for row in rows),
            "p2p_total": sum(int(row["p2p_count"]) for row in rows),
            "selected_files_total": sum(int(row["selected_file_count"]) for row in rows),
            "max_f2p": max(int(row["f2p_count"]) for row in rows),
            "max_p2p": max(int(row["p2p_count"]) for row in rows),
            "max_selected_files": max(int(row["selected_file_count"]) for row in rows),
        },
        "init_error_count": len(init_errors),
        "init_error_examples": init_errors[:20],
    }


def _summary_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Hugging Face Dataset Audit",
            "",
            f"Rows: {summary['rows_total']}",
            f"Bundle load: {summary['bundle_load']}",
            f"By language: {summary['by_language']}",
            f"By repo: {summary['by_repo']}",
            f"Unique Docker tags: {summary['unique_docker_tags']}",
            f"Current pytest-only support: {summary['pytest_supported_now']}",
            f"Rows with p2p_count=0 by language: {summary['p2p_zero_by_language']}",
            f"Bad/truncated test IDs: {summary['bad_test_ids']}",
            f"Test count stats: {summary['test_count_stats']}",
            f"Bundle init/load errors: {summary['init_error_count']}",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
