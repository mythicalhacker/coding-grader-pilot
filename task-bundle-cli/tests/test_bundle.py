from __future__ import annotations

from pathlib import Path

import pytest

from task_bundle.bundle import load
from task_bundle.errors import (
    BundleInconsistentError,
    BundleIncompleteError,
    BundleInvalidError,
)


BASE = "a" * 40
INSTANCE = "b" * 40


def write_valid_bundle(root: Path, *, pass_to_pass: str = "tests/test_ok.py::test_ok\n") -> Path:
    bundle = root / "bundle"
    hidden = bundle / "hidden"
    hidden.mkdir(parents=True)
    (bundle / "task.toml").write_text(
        f"""
task_id = "example"
repo = "owner/repo"
base_commit = "{BASE}"
instance_commit = "{INSTANCE}"
repo_language = "python"
image_ref = "example/image:tag"
workdir = "/testbed"
selected_test_files = ['tests\\test_bug.py', "tests/test_ok.py"]

[test]
framework = "pytest"

[hidden]
strategy = "checkout_overlay"

[limits]
cpu_quota = 2
memory_gb = 2
wall_clock_seconds = 1800

[network]
policy = "none"
""".lstrip(),
        encoding="utf-8",
    )
    (bundle / "problem.md").write_text("Fix it.\n", encoding="utf-8")
    (hidden / "golden.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (hidden / "fail_to_pass.txt").write_text("tests/test_bug.py::test_bug\n", encoding="utf-8")
    (hidden / "pass_to_pass.txt").write_text(pass_to_pass, encoding="utf-8")
    (hidden / "stage.sh").write_text(
        f"git reset --hard {BASE}\ngit clean -fd\ngit checkout {BASE}\ngit checkout {INSTANCE} -- tests/test_bug.py\n",
        encoding="utf-8",
    )
    return bundle


def test_valid_bundle_loads_all_fields(tmp_path: Path) -> None:
    task = load(write_valid_bundle(tmp_path))

    assert task.task_id == "example"
    assert task.base_commit == BASE
    assert task.instance_commit == INSTANCE
    assert task.fail_to_pass == ("tests/test_bug.py::test_bug",)
    assert task.pass_to_pass == ("tests/test_ok.py::test_ok",)
    assert task.selected_test_files == ("tests/test_bug.py", "tests/test_ok.py")
    assert task.golden_patch_path.name == "golden.patch"
    assert len(task.bundle_hash) == 64


def test_empty_pass_to_pass_is_valid(tmp_path: Path) -> None:
    task = load(write_valid_bundle(tmp_path, pass_to_pass=""))

    assert task.pass_to_pass == ()


def test_equal_base_and_instance_is_invalid(tmp_path: Path) -> None:
    bundle = write_valid_bundle(tmp_path)
    task_toml = bundle / "task.toml"
    task_toml.write_text(task_toml.read_text(encoding="utf-8").replace(INSTANCE, BASE), encoding="utf-8")

    with pytest.raises(BundleInvalidError):
        load(bundle)


def test_non_hex_base_commit_is_invalid(tmp_path: Path) -> None:
    bundle = write_valid_bundle(tmp_path)
    task_toml = bundle / "task.toml"
    task_toml.write_text(task_toml.read_text(encoding="utf-8").replace(BASE, "not-a-sha"), encoding="utf-8")

    with pytest.raises(BundleInvalidError):
        load(bundle)


def test_missing_hidden_directory_is_incomplete(tmp_path: Path) -> None:
    bundle = write_valid_bundle(tmp_path)
    for path in sorted((bundle / "hidden").iterdir()):
        path.unlink()
    (bundle / "hidden").rmdir()

    with pytest.raises(BundleIncompleteError):
        load(bundle)


def test_stage_script_must_name_instance_commit(tmp_path: Path) -> None:
    bundle = write_valid_bundle(tmp_path)
    (bundle / "hidden" / "stage.sh").write_text(f"git checkout {'c' * 40} -- tests/test_bug.py\n", encoding="utf-8")

    with pytest.raises(BundleInconsistentError):
        load(bundle)


def test_bundle_hash_is_deterministic(tmp_path: Path) -> None:
    bundle = write_valid_bundle(tmp_path)

    assert load(bundle).bundle_hash == load(bundle).bundle_hash
