"""Pluggable solver protocol and trusted golden-patch stub seam."""

from __future__ import annotations

import hashlib
import importlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol

from task_bundle.bundle import Task


class Solver(Protocol):
    def solve(self, view: "SolverTaskView", container: object, deadline: float) -> "SolverResult":
        ...


@dataclass(frozen=True)
class SolverTaskView:
    task_id: str
    repo: str
    problem_text: str
    repo_language: str
    workdir: str
    public_test_command: Optional[str]


@dataclass(frozen=True)
class SolverResult:
    completed: bool
    transcript: tuple[dict[str, Any], ...]
    metadata: dict[str, Any]


class TrustedGoldenStub:
    """Privileged internal solver that applies the hidden golden patch."""

    def __init__(self, task: Task) -> None:
        self.task = task

    def solve(self, view: SolverTaskView, container: object, deadline: float) -> SolverResult:
        patch_bytes = self.task.golden_patch_path.read_bytes()
        patch_sha = hashlib.sha256(patch_bytes).hexdigest()
        container.copy_in(patch_bytes, "/tmp/solver_patch.diff")
        apply_result = container.exec(
            ["git", "apply", "--verbose", "/tmp/solver_patch.diff"],
            workdir=view.workdir,
            timeout_seconds=30,
        )
        diff_result = container.exec(["git", "diff", "HEAD"], workdir=view.workdir, timeout_seconds=30)
        diff_text = Path(diff_result.stdout_path).read_text(encoding="utf-8") if Path(diff_result.stdout_path).exists() else ""
        diff_nonempty = bool(diff_text.strip())
        completed = apply_result.exit_code == 0 and diff_nonempty
        return SolverResult(
            completed=completed,
            transcript=(
                {"kind": "apply", "exit": apply_result.exit_code},
                {"kind": "diff_check", "nonempty": diff_nonempty},
            ),
            metadata={
                "patch_sha256": patch_sha,
                "apply_exit": apply_result.exit_code,
                "diff_size": len(diff_text.encode("utf-8")),
            },
        )


class EmptyDiffStub:
    """Solver fixture that intentionally leaves the worktree unchanged."""

    def __init__(self, task: Task) -> None:
        self.task = task

    def solve(self, view: SolverTaskView, container: object, deadline: float) -> SolverResult:
        return SolverResult(
            completed=True,
            transcript=({"kind": "empty_diff"},),
            metadata={"reason": "left worktree unchanged"},
        )


class SleepSolver:
    """Solver fixture that exceeds the wall budget without mutating the tree."""

    def __init__(self, task: Task) -> None:
        self.task = task

    def solve(self, view: SolverTaskView, container: object, deadline: float) -> SolverResult:
        seconds = max(2, int(deadline - time.time()) + 5)
        timeout = max(1, int(deadline - time.time()))
        result = container.exec(["sleep", str(seconds)], workdir=view.workdir, timeout_seconds=timeout)
        if getattr(result, "timed_out", False) or result.exit_code == -1:
            raise TimeoutError("solver wall budget exceeded")
        return SolverResult(
            completed=False,
            transcript=({"kind": "sleep", "seconds": seconds},),
            metadata={"slept_seconds": seconds},
        )


class BinaryWriterStub:
    """Solver fixture that writes a binary-looking file for EXTRACT filtering checks."""

    def __init__(self, task: Task) -> None:
        self.task = task

    def solve(self, view: SolverTaskView, container: object, deadline: float) -> SolverResult:
        write = container.exec(
            "python - <<'PY'\n"
            "from pathlib import Path\n"
            "Path('matrix_check.pyc').write_bytes(b'\\x00\\x01task-bundle-binary\\x02\\x03')\n"
            "PY",
            workdir=view.workdir,
            timeout_seconds=30,
        )
        diff_result = container.exec(["git", "diff", "HEAD"], workdir=view.workdir, timeout_seconds=30)
        diff_text = Path(diff_result.stdout_path).read_text(encoding="utf-8", errors="replace") if Path(diff_result.stdout_path).exists() else ""
        return SolverResult(
            completed=write.exit_code == 0,
            transcript=({"kind": "write_binary", "path": "matrix_check.pyc", "exit": write.exit_code},),
            metadata={"diff_size": len(diff_text.encode("utf-8")), "write_exit": write.exit_code},
        )


class ReservedPathWriterStub:
    """Solver fixture that tries to recreate a reserved hidden test path."""

    def __init__(self, task: Task) -> None:
        self.task = task

    def solve(self, view: SolverTaskView, container: object, deadline: float) -> SolverResult:
        reserved = self.task.selected_test_files[0]
        command = (
            "python - <<'PY'\n"
            "from pathlib import Path\n"
            f"path = Path({reserved!r})\n"
            "path.parent.mkdir(parents=True, exist_ok=True)\n"
            "path.write_text('tampered reserved path\\n', encoding='utf-8')\n"
            "PY"
        )
        result = container.exec(command, workdir=view.workdir, timeout_seconds=30)
        return SolverResult(
            completed=result.exit_code == 0,
            transcript=({"kind": "write_reserved", "path": reserved, "exit": result.exit_code},),
            metadata={"reserved_path": reserved, "write_exit": result.exit_code},
        )


def load_solver(name: str, task: Task) -> Solver:
    if name == "trusted-golden-stub":
        return TrustedGoldenStub(task)
    if name == "empty-diff-stub":
        return EmptyDiffStub(task)
    if name == "sleep-solver":
        return SleepSolver(task)
    if name == "binary-writer-stub":
        return BinaryWriterStub(task)
    if name == "reserved-path-writer-stub":
        return ReservedPathWriterStub(task)
    if ":" in name:
        module_name, class_name = name.split(":", 1)
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        return cls(task)
    raise ValueError(f"unknown solver: {name}")
