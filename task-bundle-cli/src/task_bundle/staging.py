"""Git working-tree staging, patch application, history scrubbing, and diff extraction."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from task_bundle.errors import PhaseError, TaxonomyCode, TerminalState


CHECKOUT_OVERLAY_RE = re.compile(r"\bgit\s+checkout\s+([0-9a-f]{40})\s+--\s+(.+)")
BINARY_EXCLUDES = ("*.pyc", "*.so", "*.o", "*.dylib", "*.dll", "*.exe", "*.pyo", "*.bin")


class StagingParseError(Exception):
    """Stage script could not be decomposed into prefix and overlay."""


@dataclass(frozen=True)
class SetupPlan:
    prefix_commands: tuple[str, ...]
    overlay_commands: tuple[str, ...]
    instance_commit: str


@dataclass(frozen=True)
class ApplyResult:
    winner: Literal["git_apply", "git_apply_reject", "patch_fuzz"] | None
    partial: bool
    rejected_files: tuple[str, ...]


@dataclass(frozen=True)
class ExtractResult:
    candidate_diff_path: Path
    no_patch: bool
    reserved_path_collisions: tuple[str, ...]


def parse_setup(stage_script: str, base_commit: str) -> SetupPlan:
    prefix: list[str] = []
    overlay: list[str] = []
    instance_commit: str | None = None
    for raw_line in stage_script.splitlines():
        command = raw_line.strip()
        if not command:
            continue
        match = CHECKOUT_OVERLAY_RE.search(command)
        if match and match.group(1) != base_commit:
            overlay.append(command)
            if instance_commit is None:
                instance_commit = match.group(1)
        else:
            prefix.append(command)
    if instance_commit is None:
        raise StagingParseError("stage script does not contain an overlay checkout command")
    return SetupPlan(tuple(prefix), tuple(overlay), instance_commit)


def assert_instance_present(container: object, instance_commit: str, workdir: str) -> None:
    result = container.exec(
        ["git", "cat-file", "-e", f"{instance_commit}^{{commit}}"],
        workdir=workdir,
        timeout_seconds=120,
    )
    if result.exit_code != 0:
        raise PhaseError(
            TerminalState.ERROR,
            TaxonomyCode.HIDDEN_STAGE_FAILED,
            "instance commit object not present in image; image may be shallow",
        )


def prepare_base(container: object, plan: SetupPlan, workdir: str) -> None:
    _run_or_phase_error(
        container,
        "rm -f .git/index.lock",
        workdir,
        TaxonomyCode.BASE_CHECKOUT_FAILED,
        "failed to remove stale git index lock",
    )
    for command in plan.prefix_commands:
        _run_or_phase_error(
            container,
            command,
            workdir,
            TaxonomyCode.BASE_CHECKOUT_FAILED,
            f"base preparation command failed: {command}",
        )


def inject_hidden(container: object, plan: SetupPlan, workdir: str) -> None:
    for command in plan.overlay_commands:
        _run_or_phase_error(
            container,
            command,
            workdir,
            TaxonomyCode.HIDDEN_STAGE_FAILED,
            f"hidden stage command failed: {command}",
        )


def apply_patch(container: object, patch_path_in_container: str, workdir: str) -> ApplyResult:
    empty_check = container.exec(
        f"test -s {shlex.quote(patch_path_in_container)}",
        workdir=workdir,
        timeout_seconds=30,
    )
    if empty_check.exit_code != 0:
        return ApplyResult(winner=None, partial=False, rejected_files=())

    rung1 = container.exec(
        f"git apply --verbose {shlex.quote(patch_path_in_container)}",
        workdir=workdir,
        timeout_seconds=300,
    )
    if rung1.exit_code == 0:
        return ApplyResult(winner="git_apply", partial=False, rejected_files=())

    rung2 = container.exec(
        f"git apply --verbose --reject {shlex.quote(patch_path_in_container)}",
        workdir=workdir,
        timeout_seconds=300,
    )
    if rung2.exit_code == 0:
        rejected = _find_rejects(container, workdir)
        return ApplyResult(winner="git_apply_reject", partial=bool(rejected), rejected_files=rejected)

    rung3 = container.exec(
        f"patch --batch --fuzz=1 -p1 -i {shlex.quote(patch_path_in_container)}",
        workdir=workdir,
        timeout_seconds=300,
    )
    if rung3.exit_code == 0:
        return ApplyResult(winner="patch_fuzz", partial=False, rejected_files=())

    raise PhaseError(
        TerminalState.DONE_UNRESOLVED,
        TaxonomyCode.PATCH_APPLY_FAILED,
        "candidate patch did not apply with any ladder rung",
    )


def scrub_history(container: object, workdir: str) -> None:
    commands = (
        "rm -rf .git",
        "git init",
        'git config user.email "task-bundle@local"',
        'git config user.name "task-bundle"',
        "git add .",
        'git commit -m "synthetic baseline"',
    )
    for command in commands:
        _run_or_phase_error(
            container,
            command,
            workdir,
            TaxonomyCode.BASE_CHECKOUT_FAILED,
            f"history scrub command failed: {command}",
        )


def seal(container: object, reserved_paths: Iterable[str], workdir: str) -> None:
    for path in reserved_paths:
        result = container.exec(f"rm -f {shlex.quote(path)}", workdir=workdir, timeout_seconds=60)
        if result.exit_code != 0:
            raise PhaseError(
                TerminalState.ERROR,
                TaxonomyCode.SEAL_FAILED,
                f"failed to remove reserved path from solve container: {path}",
            )


def extract_candidate(
    container: object,
    reserved_paths: set[str],
    workdir: str,
    output_path_on_host: Path,
) -> ExtractResult:
    normalized_reserved = {_normalize_path(path) for path in reserved_paths}
    _run_or_phase_error(
        container,
        "rm -f .git/index.lock",
        workdir,
        TaxonomyCode.BASE_CHECKOUT_FAILED,
        "failed to remove stale git index lock",
    )
    excludes = " ".join(f":!{pattern}" for pattern in BINARY_EXCLUDES)
    _run_or_phase_error(
        container,
        f"git add -A -- . {excludes}",
        workdir,
        TaxonomyCode.BASE_CHECKOUT_FAILED,
        "failed to stage candidate changes",
    )
    diff_result = container.exec("git diff --cached --no-color", workdir=workdir, timeout_seconds=300)
    if diff_result.exit_code != 0:
        raise PhaseError(
            TerminalState.ERROR,
            TaxonomyCode.BASE_CHECKOUT_FAILED,
            "failed to extract candidate diff",
        )
    diff_text = Path(diff_result.stdout_path).read_text(encoding="utf-8")
    filtered, collisions = _strip_reserved_sections(diff_text, normalized_reserved)
    output_path_on_host.parent.mkdir(parents=True, exist_ok=True)
    output_path_on_host.write_bytes(filtered.encode("utf-8"))
    return ExtractResult(
        candidate_diff_path=output_path_on_host,
        no_patch=filtered.strip() == "",
        reserved_path_collisions=tuple(sorted(collisions)),
    )


def _run_or_phase_error(
    container: object,
    command: str,
    workdir: str,
    code: TaxonomyCode,
    message: str,
) -> None:
    result = container.exec(command, workdir=workdir, timeout_seconds=300)
    if result.exit_code != 0:
        terminal = TerminalState.ERROR
        raise PhaseError(terminal, code, message)


def _find_rejects(container: object, workdir: str) -> tuple[str, ...]:
    result = container.exec(
        "find . -name '*.rej' -type f -not -path './.git/*'",
        workdir=workdir,
        timeout_seconds=60,
    )
    if result.exit_code != 0:
        return ()
    return tuple(line.strip() for line in Path(result.stdout_path).read_text(encoding="utf-8").splitlines() if line.strip())


def _strip_reserved_sections(diff_text: str, reserved_paths: set[str]) -> tuple[str, set[str]]:
    if not diff_text.strip():
        return "", set()
    sections = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)
    kept: list[str] = []
    collisions: set[str] = set()
    for section in sections:
        if not section.strip():
            continue
        old_path, new_path = _paths_from_section(section)
        touched = {path for path in (old_path, new_path) if path and path != "/dev/null"}
        overlap = touched & reserved_paths
        if overlap:
            collisions.update(overlap)
            continue
        kept.append(section)
    return "".join(kept), collisions


def _paths_from_section(section: str) -> tuple[str | None, str | None]:
    first = section.splitlines()[0] if section.splitlines() else ""
    match = re.match(r"diff --git a/(.+?) b/(.+)$", first)
    if match:
        return _normalize_path(match.group(1)), _normalize_path(match.group(2))
    old_path = new_path = None
    for line in section.splitlines():
        if line.startswith("--- "):
            old_path = _clean_diff_path(line[4:].strip())
        elif line.startswith("+++ "):
            new_path = _clean_diff_path(line[4:].strip())
    return old_path, new_path


def _clean_diff_path(path: str) -> str:
    if path == "/dev/null":
        return path
    if path.startswith("a/") or path.startswith("b/"):
        path = path[2:]
    return _normalize_path(path)


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/")
