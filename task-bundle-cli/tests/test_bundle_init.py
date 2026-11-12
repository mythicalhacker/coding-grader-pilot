from __future__ import annotations

import json
from pathlib import Path

import pytest

from task_bundle.bundle import init_from_row, init_manual, load
from task_bundle.errors import BundleError, InitRefusedError


BASE = "1" * 40
INSTANCE = "2" * 40


def synthetic_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "instance_id": "instance_owner__repo-1",
        "repo": "owner/repo",
        "base_commit": BASE,
        "dockerhub_tag": "owner.repo-example",
        "repo_language": "python",
        "problem_statement": "Fix logging.",
        "requirements": None,
        "interface": "No new interfaces are introduced.",
        "golden_patch": "diff --git a/app.py b/app.py\n",
        "fail_to_pass": json.dumps(["tests/test_bug.py::test_a", "tests/test_bug.py::test_b"]),
        "pass_to_pass": json.dumps(["tests/test_ok.py::test_ok"]),
        "selected_test_files_to_run": json.dumps(["tests\\test_bug.py", "tests/test_ok.py"]),
        "issue_categories": json.dumps(["bug"]),
        "issue_specificity": json.dumps(["specific"]),
        "before_repo_set_cmd": (
            f"git reset --hard {BASE}\n"
            "git clean -fd\n"
            f"git checkout {BASE}\n"
            f"git checkout {INSTANCE} -- tests/test_bug.py tests/test_ok.py\n"
        ),
    }
    row.update(overrides)
    return row


def test_init_from_row_produces_loadable_bundle(tmp_path: Path) -> None:
    target = tmp_path / "bundle"

    init_from_row(synthetic_row(), target)
    task = load(target)

    assert task.task_id == "instance_owner__repo-1"
    assert task.image_ref == "jefzda/sweap-images:owner.repo-example"
    assert task.instance_commit == INSTANCE
    assert task.selected_test_files == ("tests/test_bug.py", "tests/test_ok.py")


def test_json_encoded_list_fields_are_parsed(tmp_path: Path) -> None:
    target = tmp_path / "bundle"

    init_from_row(synthetic_row(fail_to_pass='["test_a", "test_b"]'), target)

    assert (target / "hidden" / "fail_to_pass.txt").read_text(encoding="utf-8") == "test_a\ntest_b\n"


def test_patch_and_stage_script_newlines_are_normalized(tmp_path: Path) -> None:
    target = tmp_path / "bundle"

    init_from_row(
        synthetic_row(
            golden_patch="diff --git a/app.py b/app.py\r\n--- a/app.py\r\n+++ b/app.py\r\n",
            before_repo_set_cmd=(
                f"git reset --hard {BASE}\r\n"
                "git clean -fd\r\n"
                f"git checkout {BASE}\r\n"
                f"git checkout {INSTANCE} -- tests/test_bug.py tests/test_ok.py\r\n"
            ),
        ),
        target,
    )

    assert b"\r" not in (target / "hidden" / "golden.patch").read_bytes()
    assert b"\r" not in (target / "hidden" / "stage.sh").read_bytes()


@pytest.mark.parametrize("value", [None, "", "No new interfaces are introduced."])
def test_empty_optional_sections_are_omitted(tmp_path: Path, value: object) -> None:
    target = tmp_path / "bundle"

    init_from_row(synthetic_row(requirements=value, interface=value), target)
    problem = (target / "problem.md").read_text(encoding="utf-8")

    assert "## Requirements" not in problem
    assert "## Interface" not in problem


def test_non_empty_optional_sections_are_included(tmp_path: Path) -> None:
    target = tmp_path / "bundle"

    init_from_row(synthetic_row(requirements="Must preserve x.", interface="def solve(): ..."), target)
    problem = (target / "problem.md").read_text(encoding="utf-8")

    assert "## Requirements" in problem
    assert "Must preserve x." in problem
    assert "## Interface" in problem


def test_instance_commit_is_extracted_from_stage_script(tmp_path: Path) -> None:
    target = tmp_path / "bundle"

    init_from_row(synthetic_row(), target)

    assert f'instance_commit = "{INSTANCE}"' in (target / "task.toml").read_text(encoding="utf-8")


def test_init_refused_when_target_non_empty_without_force(tmp_path: Path) -> None:
    target = tmp_path / "bundle"
    target.mkdir()
    (target / "existing.txt").write_text("x", encoding="utf-8")

    with pytest.raises(InitRefusedError):
        init_from_row(synthetic_row(), target)


def test_manual_init_writes_structure_but_does_not_require_valid_load(tmp_path: Path) -> None:
    target = tmp_path / "manual"

    init_manual(target)

    assert (target / "task.toml").exists()
    assert (target / "problem.md").exists()
    assert (target / "hidden" / "golden.patch").exists()
    with pytest.raises(BundleError):
        load(target)
