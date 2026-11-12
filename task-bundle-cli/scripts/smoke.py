#!/usr/bin/env python3
"""Sandboxed cold-start smoke runner."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a sandboxed Task Bundle CLI smoke transcript.")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker-dependent validate/run/doctor steps.")
    parser.add_argument("--bundle", type=Path, help="Path to a materialized bundle.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    sandbox = root / "scripts" / "transcripts" / f".smoke_{ts}"
    sandbox.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env["TASK_BUNDLE_DB"] = str(sandbox / "runs.db")
    env["TASK_BUNDLE_ARTIFACTS"] = str(sandbox / "artifacts")

    bundle = (args.bundle or root / "bundles/qutebrowser-instance-1").resolve()
    cli = [sys.executable, "-m", "task_bundle.cli"]
    steps: list[tuple[str, list[str], bool]] = [
        ("load", [sys.executable, "-c",
                  "import sys; from pathlib import Path; from task_bundle.bundle import load; "
                  "print(load(Path(sys.argv[1])).task_id)", str(bundle)], False),
        ("preflight", [sys.executable, "scripts/preflight.py", "--manifest", str(bundle / "task.toml")], True),
        ("validate", [*cli, "validate", str(bundle)], True),
        ("run", [*cli, "run", str(bundle)], True),
        ("doctor", [*cli, "doctor"], True),
    ]
    transcript = []
    failed = []
    for name, command, docker_dependent in steps:
        if args.skip_docker and docker_dependent:
            transcript.append(f"$ {' '.join(command)}\nSKIPPED: --skip-docker\n")
            continue
        if ("load" in failed or "preflight" in failed) and docker_dependent:
            transcript.append(f"$ {' '.join(command)}\nSKIPPED: prerequisite failed\n")
            continue
        result = subprocess.run(command, cwd=root, env=env, text=True, capture_output=True, check=False)
        log = sandbox / f"{name}.log"
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        transcript.append(f"$ {' '.join(command)}\nexit={result.returncode}\n{result.stdout}{result.stderr}\n")
        if result.returncode != 0:
            failed.append(name)

    transcript_path = root / "scripts" / "transcripts" / f"smoke_{ts}.txt"
    transcript_path.write_text("\n".join(transcript), encoding="utf-8")
    print(f"sandbox: {sandbox}")
    print(f"transcript: {transcript_path}")
    if failed:
        print(f"Failed smoke steps: {', '.join(failed)}")
        return 2
    print("PASS: smoke steps completed or were explicitly skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
