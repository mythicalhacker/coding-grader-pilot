from __future__ import annotations

import pytest

from task_bundle.grader import (
    FailureClass,
    GradeContext,
    GraderIntegrityError,
    TestStatus,
    grade_baseline,
    grade_golden,
    grade_run,
)


F2P = ("f1", "f2")
P2P = ("p1", "p2")
CTX = GradeContext(no_patch=False, patch_apply_partial=False)


def test_resolved_all_f2p_and_p2p_pass() -> None:
    outcome = grade_run({"f1": TestStatus.PASS, "f2": TestStatus.PASS, "p1": TestStatus.PASS, "p2": TestStatus.PASS}, F2P, P2P, CTX)

    assert outcome.verdict == "RESOLVED"
    assert outcome.failure_class is None


def test_partial_some_f2p_pass_p2p_intact() -> None:
    outcome = grade_run({"f1": TestStatus.PASS, "f2": TestStatus.FAIL, "p1": TestStatus.PASS, "p2": TestStatus.PASS}, F2P, P2P, CTX)

    assert outcome.failure_class == FailureClass.PARTIAL


def test_hidden_test_failed_no_f2p_pass_p2p_intact() -> None:
    outcome = grade_run({"f1": TestStatus.FAIL, "f2": TestStatus.FAIL, "p1": TestStatus.PASS, "p2": TestStatus.PASS}, F2P, P2P, CTX)

    assert outcome.failure_class == FailureClass.HIDDEN_TEST_FAILED


def test_regression_all_f2p_pass_one_p2p_broken() -> None:
    outcome = grade_run({"f1": TestStatus.PASS, "f2": TestStatus.PASS, "p1": TestStatus.FAIL, "p2": TestStatus.PASS}, F2P, P2P, CTX)

    assert outcome.failure_class == FailureClass.REGRESSION


def test_mixed_some_f2p_and_p2p_broken() -> None:
    outcome = grade_run({"f1": TestStatus.PASS, "f2": TestStatus.FAIL, "p1": TestStatus.FAIL, "p2": TestStatus.PASS}, F2P, P2P, CTX)

    assert outcome.failure_class == FailureClass.MIXED


def test_mixed_no_f2p_and_p2p_broken() -> None:
    outcome = grade_run({"f1": TestStatus.FAIL, "f2": TestStatus.ERROR, "p1": TestStatus.FAIL, "p2": TestStatus.PASS}, F2P, P2P, CTX)

    assert outcome.failure_class == FailureClass.MIXED


def test_no_patch_overrides_all_signals() -> None:
    outcome = grade_run(
        {"f1": TestStatus.PASS, "f2": TestStatus.PASS, "p1": TestStatus.PASS, "p2": TestStatus.PASS},
        F2P,
        P2P,
        GradeContext(no_patch=True, patch_apply_partial=True),
    )

    assert outcome.verdict == "UNRESOLVED"
    assert outcome.failure_class == FailureClass.NO_PATCH
    assert outcome.partial_apply_flag is True


def test_empty_p2p_with_all_f2p_passing_is_resolved() -> None:
    outcome = grade_run({"f1": TestStatus.PASS, "f2": TestStatus.PASS}, F2P, (), CTX)

    assert outcome.verdict == "RESOLVED"


def test_empty_p2p_with_all_f2p_failing_is_hidden_test_failed() -> None:
    outcome = grade_run({"f1": TestStatus.FAIL, "f2": TestStatus.FAIL}, F2P, (), CTX)

    assert outcome.failure_class == FailureClass.HIDDEN_TEST_FAILED


def test_skip_of_f2p_is_not_pass() -> None:
    outcome = grade_run({"f1": TestStatus.SKIP, "f2": TestStatus.PASS, "p1": TestStatus.PASS, "p2": TestStatus.PASS}, F2P, P2P, CTX)

    assert outcome.failure_class == FailureClass.PARTIAL


def test_error_of_p2p_is_broken() -> None:
    outcome = grade_run({"f1": TestStatus.PASS, "f2": TestStatus.PASS, "p1": TestStatus.ERROR, "p2": TestStatus.PASS}, F2P, P2P, CTX)

    assert outcome.failure_class == FailureClass.REGRESSION


def test_unknown_required_id_raises() -> None:
    with pytest.raises(GraderIntegrityError):
        grade_run({"f1": TestStatus.UNKNOWN, "f2": TestStatus.PASS}, F2P, (), CTX)


def test_missing_required_id_raises() -> None:
    with pytest.raises(GraderIntegrityError):
        grade_run({"f1": TestStatus.PASS}, F2P, (), CTX)


def test_grade_baseline_satisfied() -> None:
    outcome = grade_baseline({"f1": TestStatus.FAIL, "f2": TestStatus.FAIL, "p1": TestStatus.PASS, "p2": TestStatus.PASS}, F2P, P2P)

    assert outcome.satisfied is True
    assert outcome.reason is None


def test_grade_baseline_f2p_not_failing() -> None:
    outcome = grade_baseline({"f1": TestStatus.PASS, "f2": TestStatus.FAIL, "p1": TestStatus.PASS, "p2": TestStatus.PASS}, F2P, P2P)

    assert outcome.reason == "F2P_NOT_FAILING"


def test_grade_baseline_p2p_not_passing() -> None:
    outcome = grade_baseline({"f1": TestStatus.FAIL, "f2": TestStatus.FAIL, "p1": TestStatus.FAIL, "p2": TestStatus.PASS}, F2P, P2P)

    assert outcome.reason == "P2P_NOT_PASSING"


def test_grade_golden_satisfied() -> None:
    outcome = grade_golden({"f1": TestStatus.PASS, "f2": TestStatus.PASS, "p1": TestStatus.PASS, "p2": TestStatus.PASS}, F2P, P2P)

    assert outcome.satisfied is True


def test_grade_golden_f2p_not_passing() -> None:
    outcome = grade_golden({"f1": TestStatus.FAIL, "f2": TestStatus.PASS, "p1": TestStatus.PASS, "p2": TestStatus.PASS}, F2P, P2P)

    assert outcome.reason == "F2P_NOT_PASSING"


def test_grade_golden_p2p_not_passing() -> None:
    outcome = grade_golden({"f1": TestStatus.PASS, "f2": TestStatus.PASS, "p1": TestStatus.FAIL, "p2": TestStatus.PASS}, F2P, P2P)

    assert outcome.reason == "P2P_NOT_PASSING"


def test_free_tests_appear_with_no_satisfaction() -> None:
    outcome = grade_run({"f1": TestStatus.PASS, "f2": TestStatus.PASS, "free": TestStatus.FAIL}, F2P, (), CTX)

    free = [item for item in outcome.per_test if item.expected == "free"]
    assert free[0].test_id == "free"
    assert free[0].satisfied is None
