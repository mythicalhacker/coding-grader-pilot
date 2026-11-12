"""Test-runner output parsing into exact per-test statuses.

The pytest invocation expected upstream is:
pytest -o junit_family=xunit2 -p no:cacheprovider -p no:randomly --tb=short --no-header -q --junitxml=<path> <selected_test_files>
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree

from task_bundle.grader import TestStatus


@dataclass(frozen=True)
class ParseResult:
    status_map: dict[str, TestStatus]
    durations_ms: dict[str, int]
    raw_junit_path: str
    raw_stdout_path: str
    pytest_version: str | None


def parse_pytest(junit_xml_path: Path, stdout_path: Path) -> ParseResult:
    junit_xml_path = Path(junit_xml_path)
    stdout_path = Path(stdout_path)
    tree = ElementTree.parse(junit_xml_path)
    root = tree.getroot()
    status_map: dict[str, TestStatus] = {}
    durations_ms: dict[str, int] = {}

    for testcase in root.iter("testcase"):
        nodeid = _nodeid(testcase)
        status = _status(testcase)
        status_map[nodeid] = status
        durations_ms[nodeid] = _duration_ms(testcase.get("time"))

    return ParseResult(
        status_map=status_map,
        durations_ms=durations_ms,
        raw_junit_path=str(junit_xml_path),
        raw_stdout_path=str(stdout_path),
        pytest_version=_pytest_version(root),
    )


def parse(framework: str, *args: object, **kwargs: object) -> ParseResult:
    if framework == "pytest":
        return parse_pytest(*args, **kwargs)
    if framework in {"junit", "exit_code"}:
        raise NotImplementedError(f"{framework} parsing is documented for future support but not implemented")
    raise NotImplementedError(f"unsupported test framework: {framework}")


def verify_coverage(result: ParseResult, expected_ids: Iterable[str]) -> set[str]:
    missing = set()
    for test_id in expected_ids:
        if result.status_map.get(test_id, TestStatus.UNKNOWN) == TestStatus.UNKNOWN:
            missing.add(test_id)
    return missing


def _nodeid(testcase: ElementTree.Element) -> str:
    file_attr = testcase.get("file")
    classname = _normalize(testcase.get("classname", ""))
    name = _normalize(testcase.get("name", ""))
    if not file_attr:
        return _nodeid_from_classname(classname, name)
    file_path = _normalize(file_attr).replace("\\", "/")
    module = file_path[:-3] if file_path.endswith(".py") else file_path
    module = module.replace("/", ".")
    if not classname or classname == module:
        return f"{file_path}::{name}"
    prefix = module + "."
    class_part = classname[len(prefix) :] if classname.startswith(prefix) else classname
    return f"{file_path}::{class_part}::{name}"


def _nodeid_from_classname(classname: str, name: str) -> str:
    if not classname:
        return f"UNKNOWN::{name}"
    parts = classname.split(".")
    class_index = next((idx for idx, part in enumerate(parts) if part[:1].isupper()), len(parts))
    module_parts = parts[:class_index] or parts
    class_parts = parts[class_index:]
    file_path = "/".join(module_parts) + ".py"
    if class_parts:
        return f"{file_path}::{'.'.join(class_parts)}::{name}"
    return f"{file_path}::{name}"


def _status(testcase: ElementTree.Element) -> TestStatus:
    if testcase.find("failure") is not None or testcase.find("error") is not None:
        return TestStatus.FAIL
    if testcase.find("skipped") is not None:
        return TestStatus.SKIP
    return TestStatus.PASS


def _duration_ms(raw: str | None) -> int:
    if not raw:
        return 0
    try:
        return int(round(float(raw) * 1000))
    except ValueError:
        return 0


def _normalize(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    if "\\u" in value or "\\x" in value:
        try:
            value = value.encode("utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            pass
    value = "".join(_escape_surrogate(ch) for ch in value)
    return value


def _escape_surrogate(ch: str) -> str:
    codepoint = ord(ch)
    if 0xD800 <= codepoint <= 0xDFFF:
        return f"\\u{codepoint:04x}"
    return ch


def _pytest_version(root: ElementTree.Element) -> str | None:
    for key in ("pytest_version", "version"):
        if key in root.attrib:
            return root.attrib[key]
    return None
