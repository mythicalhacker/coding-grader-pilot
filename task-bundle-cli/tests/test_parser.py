from __future__ import annotations

from pathlib import Path

import pytest

from task_bundle.grader import TestStatus
from task_bundle.parser import parse, parse_pytest, verify_coverage


def write_xml(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "junit.xml"
    path.write_text(f'<?xml version="1.0" encoding="utf-8"?><testsuite>{body}</testsuite>', encoding="utf-8")
    return path


def parse_body(tmp_path: Path, body: str):
    stdout = tmp_path / "stdout.txt"
    stdout.write_text("", encoding="utf-8")
    return parse_pytest(write_xml(tmp_path, body), stdout)


def test_single_passing_testcase_reconstructs_path_name(tmp_path: Path) -> None:
    result = parse_body(tmp_path, '<testcase file="tests/test_a.py" classname="tests.test_a" name="test_ok" time="0.012" />')

    assert result.status_map["tests/test_a.py::test_ok"] == TestStatus.PASS
    assert result.durations_ms["tests/test_a.py::test_ok"] == 12


def test_class_based_testcase_reconstructs_class_nodeid(tmp_path: Path) -> None:
    result = parse_body(tmp_path, '<testcase file="tests/test_a.py" classname="tests.test_a.TestThing" name="test_ok" />')

    assert "tests/test_a.py::TestThing::test_ok" in result.status_map


def test_parametrized_name_is_preserved(tmp_path: Path) -> None:
    node = "tests/test_a.py::TestThing::test_case[Hello World]"
    result = parse_body(tmp_path, '<testcase file="tests/test_a.py" classname="tests.test_a.TestThing" name="test_case[Hello World]" />')

    assert node in result.status_map


def test_failure_error_and_skipped_statuses(tmp_path: Path) -> None:
    result = parse_body(
        tmp_path,
        """
        <testcase file="tests/test_a.py" classname="tests.test_a" name="test_fail"><failure /></testcase>
        <testcase file="tests/test_a.py" classname="tests.test_a" name="test_error"><error /></testcase>
        <testcase file="tests/test_a.py" classname="tests.test_a" name="test_skip"><skipped /></testcase>
        """,
    )

    assert result.status_map["tests/test_a.py::test_fail"] == TestStatus.FAIL
    assert result.status_map["tests/test_a.py::test_error"] == TestStatus.FAIL
    assert result.status_map["tests/test_a.py::test_skip"] == TestStatus.SKIP


def test_lone_surrogate_escape_stays_sqlite_safe(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    stdout = tmp_path / "stdout.txt"
    junit.write_text(
        """<testsuite><testcase file="tests/test_a.py" classname="tests.test_a" name="test_bad[\\ud83c]" /></testsuite>""",
        encoding="utf-8",
    )
    stdout.write_text("", encoding="utf-8")

    result = parse_pytest(junit, stdout)

    (nodeid,) = result.status_map
    assert "\\ud83c" in nodeid
    assert not any(0xD800 <= ord(ch) <= 0xDFFF for ch in nodeid)


def test_missing_file_attribute_reconstructs_function_nodeid_from_classname(tmp_path: Path) -> None:
    result = parse_body(tmp_path, '<testcase classname="tests.test_a" name="test_ok" />')

    assert result.status_map["tests/test_a.py::test_ok"] == TestStatus.PASS


def test_missing_file_attribute_reconstructs_class_nodeid_from_classname(tmp_path: Path) -> None:
    result = parse_body(tmp_path, '<testcase classname="checks.components.metrics.units.test_counter.TestCounter" name="test_sample_count" />')

    assert "checks/components/metrics/units/test_counter.py::TestCounter::test_sample_count" in result.status_map


def test_verify_coverage_returns_missing_and_unknown_ids(tmp_path: Path) -> None:
    result = parse_body(tmp_path, '<testcase file="tests/test_a.py" classname="tests.test_a" name="test_ok" />')
    result.status_map["known_unknown"] = TestStatus.UNKNOWN

    assert verify_coverage(result, ["tests/test_a.py::test_ok", "missing", "known_unknown"]) == {"missing", "known_unknown"}


def test_parse_junit_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="not implemented"):
        parse("junit")


def test_file_level_error_without_testcases_does_not_crash(tmp_path: Path) -> None:
    result = parse_body(tmp_path, '<error message="collection failed" />')

    assert result.status_map == {}


def test_nested_parametrized_identifier_round_trips(tmp_path: Path) -> None:
    expected = "checks/core/widgets/test_labels.py::TestLabelSet::test_caption[Sample Label]"
    result = parse_body(
        tmp_path,
        '<testcase file="checks/core/widgets/test_labels.py" classname="checks.core.widgets.test_labels.TestLabelSet" name="test_caption[Sample Label]" />',
    )

    assert expected in result.status_map
