#!/usr/bin/env python3
"""Check Docker and the generated example before a full validation run."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence


DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "bundles/qutebrowser-instance-1/task.toml"


class GateFailure(Exception):
    """A preflight gate failed with an actionable user-facing message."""

    def __init__(self, gate: str, command: str, suggested_fix: str, detail: str = "") -> None:
        super().__init__(detail or gate)
        self.gate = gate
        self.command = command
        self.suggested_fix = suggested_fix
        self.detail = detail


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def rendered_command(self) -> str:
        return " ".join(self.command)


def run_command(command: Sequence[str], timeout: int) -> CommandResult:
    completed = subprocess.run(
        list(command),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(
        command=list(command),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def docker_daemon_reachable() -> bool:
    try:
        result = run_command(["docker", "info"], timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def fail(gate: str, command: str, suggested_fix: str, detail: str = "") -> None:
    if detail:
        print(f"ERROR: preflight failed. {detail}", file=sys.stderr)
    else:
        print("ERROR: preflight failed.", file=sys.stderr)
    print(f"gate: {gate}", file=sys.stderr)
    print(f"command: {command}", file=sys.stderr)
    print(f"suggested fix: {suggested_fix}", file=sys.stderr)


def gate_image_pull(image_tag: str) -> None:
    command = ["docker", "pull", image_tag]
    try:
        result = run_command(command, timeout=600)
    except subprocess.TimeoutExpired as exc:
        raise GateFailure(
            "IMAGE_PULL",
            " ".join(command),
            "Confirm the image tag and network access, then re-run preflight.",
            "docker pull timed out after 600 seconds.",
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise GateFailure(
            "IMAGE_PULL",
            result.rendered_command,
            "Confirm the image tag exists and Docker can pull it.",
            detail[0] if detail else "docker pull returned non-zero.",
        )


def gate_instance_commit(image_tag: str, workdir: str, instance_commit: str) -> None:
    command = [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--entrypoint", "git",
        image_tag,
        "-C",
        workdir,
        "cat-file",
        "-e",
        f"{instance_commit}^{{commit}}",
    ]
    result = run_command(command, timeout=120)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise GateFailure(
            "INSTANCE_COMMIT_PRESENT",
            result.rendered_command,
            (
                "The image appears shallow or mismatched. Use staging.assert_instance_present "
                "against the correct image/instance pair, or select a matching bundle."
            ),
            detail[0] if detail else "instance commit was not found in the image.",
        )


def gate_pytest_collect(image_tag: str, workdir: str, selected_files: Sequence[str]) -> None:
    command = [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--workdir", workdir,
        "--entrypoint", "pytest",
        image_tag,
        "--collect-only",
        "-q",
        *selected_files,
    ]
    result = run_command(command, timeout=300)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise GateFailure(
            "PYTEST_COLLECT_OFFLINE",
            result.rendered_command,
            "Confirm the selected test files exist and collect without network access.",
            detail[0] if detail else "pytest collection returned non-zero.",
        )


def gate_workdir(image_tag: str, workdir: str) -> None:
    command = ["docker", "run", "--rm", "--network=none", "--entrypoint", "ls", image_tag, workdir]
    result = run_command(command, timeout=60)
    if result.returncode != 0 or not result.stdout.strip():
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise GateFailure(
            "WORKDIR",
            result.rendered_command,
            "Confirm the bundle workdir matches the image repository checkout path.",
            detail[0] if detail else f"{workdir} was missing or empty.",
        )


def gate_user(image_tag: str) -> tuple[int, str]:
    uid_result = run_command(["docker", "run", "--rm", "--network=none", "--entrypoint", "id", image_tag, "-u"], timeout=60)
    if uid_result.returncode != 0:
        detail = (uid_result.stderr or uid_result.stdout).strip().splitlines()
        raise GateFailure(
            "USER",
            uid_result.rendered_command,
            "Confirm the image can run id -u or add a non-root agent user.",
            detail[0] if detail else "id -u returned non-zero.",
        )
    raw_uid = uid_result.stdout.strip()
    try:
        uid = int(raw_uid)
    except ValueError as exc:
        raise GateFailure(
            "USER",
            uid_result.rendered_command,
            "Confirm id -u returns a numeric uid.",
            f"unexpected uid output: {raw_uid!r}",
        ) from exc

    name_result = run_command(["docker", "run", "--rm", "--network=none", "--entrypoint", "id", image_tag, "-un"], timeout=60)
    name = name_result.stdout.strip() if name_result.returncode == 0 else ""
    if uid == 0:
        return 1000, "uid-1000-fallback"
    return uid, name or f"uid-{uid}"


def image_digest(image_tag: str) -> str:
    result = run_command(["docker", "image", "inspect", image_tag, "--format", "{{json .RepoDigests}}"], 60)
    if result.returncode != 0:
        return ""
    try:
        digests = json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.strip()
    if isinstance(digests, list) and digests:
        return str(digests[0])
    return ""


def write_preflight(
    project_root: Path,
    image_tag: str,
    instance_commit_present: bool,
    pytest_collect_ok: bool,
    workdir: str,
    user_uid: int,
    user_name: str,
) -> None:
    payload = {
        "image_tag": image_tag,
        "image_digest": image_digest(image_tag),
        "instance_commit_present": instance_commit_present,
        "pytest_collect_ok": pytest_collect_ok,
        "workdir": workdir,
        "user_uid": user_uid,
        "user_name": user_name,
        "timestamp_iso": datetime.now(UTC).isoformat(),
    }
    (project_root / ".preflight.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST,
                        help="Bundle task.toml supplying defaults for the arguments below.")
    parser.add_argument("--image", help="Docker image tag to verify.")
    parser.add_argument("--instance-commit", help="Git commit expected in the image.")
    parser.add_argument("--selected-files", help="Comma-separated test files for offline collection.")
    parser.add_argument("--workdir", help="Repository workdir inside the image.")
    args = parser.parse_args(argv)
    if any(value is None for value in (args.image, args.instance_commit, args.selected_files, args.workdir)):
        if not args.manifest.is_file():
            parser.error("bundle manifest missing. Run python scripts/prepare_example.py or pass --manifest.")
        with args.manifest.open("rb") as handle:
            manifest = tomllib.load(handle)
        if args.image is None:
            args.image = manifest["image_ref"]
        if args.instance_commit is None:
            args.instance_commit = manifest["instance_commit"]
        if args.selected_files is None:
            args.selected_files = ",".join(manifest["selected_test_files"])
        if args.workdir is None:
            args.workdir = manifest["workdir"]
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project_root = Path(__file__).resolve().parents[1]
    selected_files = tuple(part.strip() for part in args.selected_files.split(",") if part.strip())

    if not docker_daemon_reachable():
        print(
            "Docker daemon unreachable; start Docker Desktop or `dockerd` and re-run preflight.",
            file=sys.stderr,
        )
        return 2

    try:
        gate_image_pull(args.image)
        gate_instance_commit(args.image, args.workdir, args.instance_commit)
        gate_pytest_collect(args.image, args.workdir, selected_files)
        gate_workdir(args.image, args.workdir)
        user_uid, user_name = gate_user(args.image)
    except GateFailure as exc:
        fail(exc.gate, exc.command, exc.suggested_fix, exc.detail)
        return 2

    write_preflight(
        project_root=project_root,
        image_tag=args.image,
        instance_commit_present=True,
        pytest_collect_ok=True,
        workdir=args.workdir,
        user_uid=user_uid,
        user_name=user_name,
    )
    print("preflight ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
