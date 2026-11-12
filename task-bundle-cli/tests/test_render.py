from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from task_bundle.grader import TestStatus
from task_bundle.orchestrator import State
from task_bundle.parser import ParseResult
from task_bundle.render import REGISTRY, render_terminal


EXPECTED = [
    ("DONE_VALID", None),
    ("DONE_RESOLVED", None),
    *[
        ("DONE_INVALID", code)
        for code in (
            "F2P_NOT_FAILING",
            "P2P_NOT_PASSING",
            "GOLDEN_NOT_APPLYING",
            "GOLDEN_TESTS_FAILING",
            "PARSER_UNKNOWN",
            "TEST_EXEC_FAILED",
            "HIDDEN_STAGE_FAILED",
        )
    ],
    *[
        ("DONE_UNRESOLVED", code)
        for code in (
            "no_patch",
            "patch_apply_failed",
            "build_failed",
            "solver_timeout",
            "hidden_test_failed",
            "partial",
            "regression",
            "mixed",
        )
    ],
    *[
        ("ERROR", code)
        for code in (
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
    ],
]


def ctx(terminal: str, code: str | None, tmp_path: Path):
    return SimpleNamespace(
        terminal_state=State[terminal],
        taxonomy_code=code,
        message=f"{terminal}: {code}: message",
        artifact_dir=tmp_path,
        run_id="run-1",
        task=SimpleNamespace(fail_to_pass=("f1",), pass_to_pass=("p1",)),
        parsed_results={},
    )


def test_registry_is_complete() -> None:
    assert [item for item in EXPECTED if item not in REGISTRY] == []


def test_every_taxonomy_entry_renders_four_lines(tmp_path: Path) -> None:
    for terminal, code in EXPECTED:
        assert len(render_terminal(ctx(terminal, code, tmp_path)).splitlines()) == 4


def test_f2p_message_includes_first_failing_test_id(tmp_path: Path) -> None:
    context = ctx("DONE_INVALID", "F2P_NOT_FAILING", tmp_path)
    context.parsed_results = {
        "baseline": ParseResult({"f1": TestStatus.PASS}, {"f1": 1}, "junit.xml", "stdout.txt", None)
    }

    assert "f1" in render_terminal(context)


def test_done_resolved_is_success_block(tmp_path: Path) -> None:
    rendered = render_terminal(ctx("DONE_RESOLVED", None, tmp_path))

    assert rendered.startswith("RESOLVED")
    assert "ERROR" not in rendered
