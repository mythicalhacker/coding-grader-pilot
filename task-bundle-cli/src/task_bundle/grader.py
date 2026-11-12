"""Pure grading from parsed test statuses and expected F2P/P2P sets to verdicts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class TestStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIP = "SKIP"
    UNKNOWN = "UNKNOWN"


TestStatus.__test__ = False


class FailureClass(str, Enum):
    NO_PATCH = "no_patch"
    HIDDEN_TEST_FAILED = "hidden_test_failed"
    PARTIAL = "partial"
    REGRESSION = "regression"
    MIXED = "mixed"
    PATCH_APPLY_FAILED = "patch_apply_failed"
    BUILD_FAILED = "build_failed"
    SOLVER_TIMEOUT = "solver_timeout"
    PARSER_UNKNOWN = "parser_unknown"


class GraderIntegrityError(AssertionError):
    """Required test ids must be present and known before grading."""


@dataclass(frozen=True)
class TestOutcome:
    test_id: str
    expected: Literal["fail_to_pass", "pass_to_pass", "free"]
    actual_status: TestStatus
    satisfied: bool | None


@dataclass(frozen=True)
class ValidateOutcome:
    satisfied: bool
    reason: str | None
    per_test: tuple[TestOutcome, ...]


@dataclass(frozen=True)
class RunOutcome:
    verdict: Literal["RESOLVED", "UNRESOLVED"]
    failure_class: FailureClass | None
    partial_apply_flag: bool
    per_test: tuple[TestOutcome, ...]


@dataclass(frozen=True)
class GradeContext:
    no_patch: bool
    patch_apply_partial: bool


def grade_baseline(
    parser_map: dict[str, TestStatus],
    f2p: tuple[str, ...],
    p2p: tuple[str, ...],
) -> ValidateOutcome:
    statuses = _normalize_map(parser_map)
    _assert_required_coverage(statuses, f2p, p2p)
    per_test = _per_test(statuses, f2p, p2p, f2p_expected=TestStatus.FAIL)
    f2p_ok = all(statuses[test_id] == TestStatus.FAIL for test_id in f2p)
    if not f2p_ok:
        return ValidateOutcome(False, "F2P_NOT_FAILING", per_test)
    p2p_ok = _p2p_satisfied(statuses, p2p)
    if not p2p_ok:
        return ValidateOutcome(False, "P2P_NOT_PASSING", per_test)
    return ValidateOutcome(True, None, per_test)


def grade_golden(
    parser_map: dict[str, TestStatus],
    f2p: tuple[str, ...],
    p2p: tuple[str, ...],
) -> ValidateOutcome:
    statuses = _normalize_map(parser_map)
    _assert_required_coverage(statuses, f2p, p2p)
    per_test = _per_test(statuses, f2p, p2p, f2p_expected=TestStatus.PASS)
    f2p_ok = all(statuses[test_id] == TestStatus.PASS for test_id in f2p)
    if not f2p_ok:
        return ValidateOutcome(False, "F2P_NOT_PASSING", per_test)
    p2p_ok = _p2p_satisfied(statuses, p2p)
    if not p2p_ok:
        return ValidateOutcome(False, "P2P_NOT_PASSING", per_test)
    return ValidateOutcome(True, None, per_test)


def grade_run(
    parser_map: dict[str, TestStatus],
    f2p: tuple[str, ...],
    p2p: tuple[str, ...],
    ctx: GradeContext,
) -> RunOutcome:
    statuses = _normalize_map(parser_map)
    _assert_required_coverage(statuses, f2p, p2p)
    per_test = _per_test(statuses, f2p, p2p, f2p_expected=TestStatus.PASS)

    if ctx.no_patch:
        return RunOutcome("UNRESOLVED", FailureClass.NO_PATCH, ctx.patch_apply_partial, per_test)

    passing = sum(1 for test_id in f2p if statuses[test_id] == TestStatus.PASS)
    all_f2p = passing == len(f2p)
    none_f2p = passing == 0
    some_f2p = 0 < passing < len(f2p)
    p2p_ok = _p2p_satisfied(statuses, p2p)

    if all_f2p and p2p_ok:
        return RunOutcome("RESOLVED", None, ctx.patch_apply_partial, per_test)
    if all_f2p and not p2p_ok:
        return RunOutcome("UNRESOLVED", FailureClass.REGRESSION, ctx.patch_apply_partial, per_test)
    if some_f2p and p2p_ok:
        return RunOutcome("UNRESOLVED", FailureClass.PARTIAL, ctx.patch_apply_partial, per_test)
    if none_f2p and p2p_ok:
        return RunOutcome("UNRESOLVED", FailureClass.HIDDEN_TEST_FAILED, ctx.patch_apply_partial, per_test)
    return RunOutcome("UNRESOLVED", FailureClass.MIXED, ctx.patch_apply_partial, per_test)


def _normalize_map(parser_map: dict[str, TestStatus]) -> dict[str, TestStatus]:
    normalized = {}
    for test_id, status in parser_map.items():
        normalized[test_id] = status if isinstance(status, TestStatus) else TestStatus(str(status))
    return normalized


def _assert_required_coverage(
    parser_map: dict[str, TestStatus],
    f2p: tuple[str, ...],
    p2p: tuple[str, ...],
) -> None:
    for test_id in (*f2p, *p2p):
        if test_id not in parser_map:
            raise GraderIntegrityError(f"required test id missing from parser output: {test_id}")
        if parser_map[test_id] == TestStatus.UNKNOWN:
            raise GraderIntegrityError(f"required test id has UNKNOWN status: {test_id}")


def _p2p_satisfied(parser_map: dict[str, TestStatus], p2p: tuple[str, ...]) -> bool:
    if not p2p:
        return True
    return all(parser_map[test_id] == TestStatus.PASS for test_id in p2p)


def _per_test(
    parser_map: dict[str, TestStatus],
    f2p: tuple[str, ...],
    p2p: tuple[str, ...],
    *,
    f2p_expected: TestStatus,
) -> tuple[TestOutcome, ...]:
    outcomes: list[TestOutcome] = []
    f2p_set = set(f2p)
    p2p_set = set(p2p)
    for test_id in f2p:
        outcomes.append(
            TestOutcome(
                test_id=test_id,
                expected="fail_to_pass",
                actual_status=parser_map[test_id],
                satisfied=parser_map[test_id] == f2p_expected,
            )
        )
    for test_id in p2p:
        outcomes.append(
            TestOutcome(
                test_id=test_id,
                expected="pass_to_pass",
                actual_status=parser_map[test_id],
                satisfied=parser_map[test_id] == TestStatus.PASS,
            )
        )
    for test_id in sorted(set(parser_map) - f2p_set - p2p_set):
        outcomes.append(
            TestOutcome(
                test_id=test_id,
                expected="free",
                actual_status=parser_map[test_id],
                satisfied=None,
            )
        )
    return tuple(outcomes)
