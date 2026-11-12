"""Terminal verdict rendering registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MessageTemplate:
    header_template: str
    reason_template: str
    phase_template: str
    artifact_template: str


DONE_INVALID_CODES = (
    "F2P_NOT_FAILING",
    "P2P_NOT_PASSING",
    "GOLDEN_NOT_APPLYING",
    "GOLDEN_TESTS_FAILING",
    "PARSER_UNKNOWN",
    "TEST_EXEC_FAILED",
    "HIDDEN_STAGE_FAILED",
)
DONE_UNRESOLVED_CODES = (
    "no_patch",
    "patch_apply_failed",
    "build_failed",
    "solver_timeout",
    "hidden_test_failed",
    "partial",
    "regression",
    "mixed",
)
ERROR_CODES = (
    "IMAGE_UNAVAILABLE",
    "PROVISION_FAILED",
    "BASE_CHECKOUT_FAILED",
    "SEAL_FAILED",
    "PARSER_UNKNOWN",
    "HIDDEN_STAGE_FAILED",
    "SOLVER_CRASHED",
    "BOUNDARY_VIOLATION",
    "UNEXPECTED",
)


REGISTRY: dict[tuple[str, str | None], MessageTemplate] = {
    ("DONE_VALID", None): MessageTemplate(
        "VALID: task bundle passed validation.",
        "Baseline and golden-patch checks both matched the expected fail_to_pass and pass_to_pass outcomes.",
        "(verdict at ASSERT_GOLDEN)",
        "logs: task logs {run_id}",
    ),
    ("DONE_RESOLVED", None): MessageTemplate(
        "RESOLVED: candidate patch passed all required tests.",
        "All {f2p_count} fail_to_pass tests passed and all {p2p_count} pass_to_pass tests passed.",
        "(verdict at GRADE)",
        "logs: task logs {run_id}",
    ),
}

for code in DONE_INVALID_CODES:
    REGISTRY[("DONE_INVALID", code)] = MessageTemplate(
        f"INVALID: {code}.",
        "{message}",
        "(failed during {phase})",
        "stdout: {artifact_dir}",
    )

REGISTRY[("DONE_INVALID", "F2P_NOT_FAILING")] = MessageTemplate(
    "INVALID: baseline fail_to_pass tests did not all fail.",
    "Test {first_failing_test_id} passed when it was expected to fail; the supposedly broken code is not actually broken at that test, indicating a malformed task.",
    "(failed during ASSERT_BASELINE)",
    "stdout: {baseline_stdout_path}",
)

for code in DONE_UNRESOLVED_CODES:
    REGISTRY[("DONE_UNRESOLVED", code)] = MessageTemplate(
        f"UNRESOLVED: {code}.",
        "{message}",
        "(failed during {phase})",
        "artifacts: {artifact_dir}; logs: task logs {run_id}",
    )

for code in ERROR_CODES:
    REGISTRY[("ERROR", code)] = MessageTemplate(
        f"ERROR: {code}.",
        "{message}",
        "(failed during {phase})",
        "logs: {artifact_dir}",
    )

REGISTRY[("ERROR", "BOUNDARY_VIOLATION")] = MessageTemplate(
    "ERROR: trust boundary violation.",
    "An orchestrator transition asserted role!=solve or solve_container=None and the assertion failed; this is a structural invariant and indicates a bug in the orchestrator phase table.",
    "(failed during {phase})",
    "logs: {artifact_dir}",
)


def render_terminal(ctx: Any) -> str:
    terminal = _name(getattr(ctx, "terminal_state", None) or "ERROR")
    code = getattr(ctx, "taxonomy_code", None)
    key = (terminal, None) if code is None and terminal in {"DONE_VALID", "DONE_RESOLVED"} else (terminal, str(code))
    template = REGISTRY.get(key) or REGISTRY[("ERROR", "UNEXPECTED")]
    values = _values(ctx, terminal, code)
    return "\n".join(
        [
            template.header_template.format(**values),
            template.reason_template.format(**values),
            template.phase_template.format(**values),
            template.artifact_template.format(**values),
        ]
    )


def _values(ctx: Any, terminal: str, code: str | None) -> dict[str, Any]:
    task = getattr(ctx, "task", None)
    artifact_dir = Path(getattr(ctx, "artifact_dir", ".")).resolve()
    return {
        "run_id": getattr(ctx, "run_id", ""),
        "artifact_dir": str(artifact_dir),
        "baseline_stdout_path": str(artifact_dir / "baseline_stdout.txt"),
        "phase": getattr(ctx, "failed_phase", None) or _phase_for(terminal, code),
        "message": _strip_prefix(getattr(ctx, "message", None) or f"{terminal}: {code or 'none'}"),
        "f2p_count": len(getattr(task, "fail_to_pass", ()) or ()),
        "p2p_count": len(getattr(task, "pass_to_pass", ()) or ()),
        "first_failing_test_id": _first_failing_test_id(ctx),
    }


def _name(value: Any) -> str:
    return getattr(value, "value", str(value))


def _phase_for(terminal: str, code: str | None) -> str:
    if terminal == "DONE_RESOLVED":
        return "GRADE"
    if terminal == "DONE_UNRESOLVED":
        return "GRADE"
    if code in {"F2P_NOT_FAILING", "P2P_NOT_PASSING"}:
        return "ASSERT_BASELINE"
    if code in {"GOLDEN_TESTS_FAILING", "GOLDEN_NOT_APPLYING"}:
        return "ASSERT_GOLDEN"
    return terminal


def _strip_prefix(message: str) -> str:
    parts = message.split(": ", 2)
    return parts[2] if len(parts) == 3 else message


def _first_failing_test_id(ctx: Any) -> str:
    task = getattr(ctx, "task", None)
    for test_id in getattr(task, "fail_to_pass", ()) or ():
        for result in getattr(ctx, "parsed_results", {}).values():
            status = result.status_map.get(test_id)
            if getattr(status, "value", status) == "PASS":
                return test_id
    f2p = getattr(task, "fail_to_pass", ()) or ()
    return f2p[0] if f2p else "unknown"
