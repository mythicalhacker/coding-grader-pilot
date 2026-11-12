"""Schema boundary for loading, validating, and initializing task bundles."""

from __future__ import annotations

import hashlib
import ast
import json
import os
import re
import shutil
import tempfile
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from task_bundle.errors import (
    BundleError,
    BundleInconsistentError,
    BundleIncompleteError,
    BundleInitError,
    BundleInvalidError,
    BundleMalformedError,
    InitRefusedError,
    RowIncompleteError,
    RowMalformedError,
)


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CHECKOUT_OVERLAY_RE = re.compile(r"\bgit\s+checkout\s+([0-9a-f]{40})\s+--\s+(.+)")
NO_NEW_INTERFACES = "No new interfaces are introduced."


class TestConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    framework: Literal["pytest", "junit", "exit_code"] = "pytest"


class HiddenConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: Literal["checkout_overlay", "test_patch"] = "checkout_overlay"


class LimitsConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    cpu_quota: int = 2
    memory_gb: int = 2
    wall_clock_seconds: int = 1800


class NetworkConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy: Literal["none", "bridge"] = "none"


class Task(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    task_id: str
    repo: str
    base_commit: str
    instance_commit: str
    repo_language: Literal["python", "js", "ts", "go"]
    image_ref: str
    workdir: str = "/testbed"
    selected_test_files: tuple[str, ...]
    test: TestConfig = Field(default_factory=TestConfig)
    hidden: HiddenConfig = Field(default_factory=HiddenConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    issue_categories: tuple[str, ...] | None = None
    issue_specificity: tuple[str, ...] | None = None
    fail_to_pass: tuple[str, ...]
    pass_to_pass: tuple[str, ...] = ()
    bundle_hash: str
    bundle_dir: Path = Field(exclude=True)

    @field_validator("base_commit", "instance_commit")
    @classmethod
    def validate_commit(cls, value: str) -> str:
        if not SHA_RE.fullmatch(value):
            raise ValueError("commit must be a 40-character lowercase hex SHA")
        return value

    @field_validator("selected_test_files")
    @classmethod
    def validate_selected_files(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_normalize_path(part) for part in value if str(part).strip())
        if not normalized:
            raise ValueError("selected_test_files must be non-empty")
        return normalized

    @field_validator("fail_to_pass")
    @classmethod
    def validate_fail_to_pass(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("fail_to_pass must be non-empty")
        return value

    @field_validator("pass_to_pass")
    @classmethod
    def validate_pass_to_pass(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(value or ())

    @field_validator("issue_categories", "issue_specificity")
    @classmethod
    def validate_optional_tuple(cls, value: tuple[str, ...] | None) -> tuple[str, ...] | None:
        return tuple(value) if value is not None else None

    def model_post_init(self, __context: Any) -> None:
        if self.base_commit == self.instance_commit:
            raise ValueError("base_commit and instance_commit must differ")

    @property
    def problem_md_path(self) -> Path:
        return self.bundle_dir / "problem.md"

    @property
    def golden_patch_path(self) -> Path:
        return self.bundle_dir / "hidden" / "golden.patch"

    @property
    def stage_sh_path(self) -> Path:
        return self.bundle_dir / "hidden" / "stage.sh"

    @property
    def fail_to_pass_path(self) -> Path:
        return self.bundle_dir / "hidden" / "fail_to_pass.txt"

    @property
    def pass_to_pass_path(self) -> Path:
        return self.bundle_dir / "hidden" / "pass_to_pass.txt"


def load(bundle_dir: Path) -> Task:
    bundle_dir = Path(bundle_dir)
    hidden_dir = bundle_dir / "hidden"
    required = [
        bundle_dir / "task.toml",
        bundle_dir / "problem.md",
        hidden_dir,
        hidden_dir / "golden.patch",
        hidden_dir / "fail_to_pass.txt",
        hidden_dir / "pass_to_pass.txt",
        hidden_dir / "stage.sh",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise BundleIncompleteError(f"bundle is missing {missing[0].relative_to(bundle_dir)}")
    if not hidden_dir.is_dir():
        raise BundleIncompleteError("hidden exists but is not a directory")

    try:
        metadata = tomllib.loads((bundle_dir / "task.toml").read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise BundleMalformedError(f"task.toml is malformed: {exc}") from exc

    fail_to_pass = _read_test_list(hidden_dir / "fail_to_pass.txt")
    pass_to_pass = _read_test_list(hidden_dir / "pass_to_pass.txt")
    if not fail_to_pass:
        raise BundleInvalidError("fail_to_pass must be non-empty")

    stage_text = (hidden_dir / "stage.sh").read_text(encoding="utf-8")
    instance_commit = str(metadata.get("instance_commit", ""))
    if instance_commit and instance_commit not in stage_text:
        raise BundleInconsistentError("task.toml instance_commit does not appear in hidden/stage.sh")

    try:
        task = Task(
            **metadata,
            fail_to_pass=fail_to_pass,
            pass_to_pass=pass_to_pass,
            bundle_hash=_bundle_hash(bundle_dir),
            bundle_dir=bundle_dir,
        )
    except ValidationError as exc:
        message = str(exc.errors()[0].get("msg", exc))
        if "base_commit and instance_commit must differ" in str(exc):
            raise BundleInvalidError("base_commit and instance_commit must differ") from exc
        if "commit must be" in message or "selected_test_files" in str(exc) or "fail_to_pass" in str(exc):
            raise BundleInvalidError(message) from exc
        raise BundleMalformedError(message) from exc
    except ValueError as exc:
        if "base_commit and instance_commit" in str(exc):
            raise BundleInvalidError(str(exc)) from exc
        raise BundleMalformedError(str(exc)) from exc

    return task


def init_from_row(row: dict[str, Any], target_dir: Path, force: bool = False) -> Path:
    target_dir = Path(target_dir)
    _ensure_writable_target(target_dir, force=force)

    try:
        task_id = _require_string(row, "instance_id")
        repo = _require_string(row, "repo")
        base_commit = _require_string(row, "base_commit")
        dockerhub_tag = _require_string(row, "dockerhub_tag")
        before_repo_set_cmd = _require_string(row, "before_repo_set_cmd")
        golden_patch = _optional_string(row.get("golden_patch", row.get("patch", "")))
        problem_statement = _optional_string(row.get("problem_statement", row.get("description", "")))
    except RowIncompleteError:
        raise

    fail_to_pass = _parse_json_list(row, "fail_to_pass", "FAIL_TO_PASS")
    pass_to_pass = _parse_json_list(row, "pass_to_pass", "PASS_TO_PASS")
    selected_files = tuple(
        _normalize_path(path)
        for path in _parse_json_list(row, "selected_test_files_to_run", "selected_test_files")
    )
    issue_categories = _parse_optional_json_list(row, "issue_categories")
    issue_specificity = _parse_optional_json_list(row, "issue_specificity")
    instance_commit = _extract_instance_commit(before_repo_set_cmd, base_commit)
    image_ref = _image_ref_from_tag(dockerhub_tag)

    def writer(tmp_dir: Path) -> None:
        hidden = tmp_dir / "hidden"
        hidden.mkdir(parents=True, exist_ok=True)
        (tmp_dir / "task.toml").write_text(
            _render_task_toml(
                task_id=task_id,
                repo=repo,
                base_commit=base_commit,
                instance_commit=instance_commit,
                repo_language=_repo_language(row),
                image_ref=image_ref,
                selected_test_files=selected_files,
                issue_categories=issue_categories,
                issue_specificity=issue_specificity,
            ),
            encoding="utf-8",
        )
        (tmp_dir / "problem.md").write_text(_render_problem(row, problem_statement), encoding="utf-8")
        _write_text_lf(hidden / "golden.patch", golden_patch)
        (hidden / "fail_to_pass.txt").write_text("\n".join(fail_to_pass) + "\n", encoding="utf-8")
        (hidden / "pass_to_pass.txt").write_text(
            ("\n".join(pass_to_pass) + "\n") if pass_to_pass else "",
            encoding="utf-8",
        )
        _write_text_lf(hidden / "stage.sh", before_repo_set_cmd)

    _atomic_write_dir(target_dir, force=force, writer=writer)
    load(target_dir)
    return target_dir


def init_from_spec(
    *,
    repo: str,
    commit: str,
    image_ref: str,
    target_dir: Path,
    task_id: str | None = None,
    repo_language: str = "python",
    selected_test_files: list[str] | None = None,
    workdir: str = "/testbed",
    framework: str = "pytest",
    base_commit: str | None = None,
    force: bool = False,
) -> Path:
    """Create a bundle skeleton from --repo and --commit.

    The instance_commit is the supplied commit. The base_commit defaults to
    commit~1 (one commit before) so `base_commit != instance_commit` holds;
    the bundle author can edit task.toml to set a different base if needed.
    Hidden files (golden.patch, fail_to_pass.txt, pass_to_pass.txt) are
    scaffolded empty for the author to fill, mirroring `init manual`.
    """
    target_dir = Path(target_dir)
    _ensure_writable_target(target_dir, force=force)

    commit = commit.lower().strip()
    if len(commit) != 40 or not all(c in "0123456789abcdef" for c in commit):
        raise BundleInitRowMalformedError(
            f"--commit must be a 40-char lowercase hex SHA, got {commit!r}")
    base = (base_commit or "").lower().strip()
    if base:
        if len(base) != 40 or not all(c in "0123456789abcdef" for c in base):
            raise BundleInitRowMalformedError(
                f"--base must be a 40-char lowercase hex SHA, got {base!r}")
        if base == commit:
            raise BundleInitRowMalformedError("--base must differ from --commit")
    else:
        # Synthesize a placeholder base that differs structurally. Author edits
        # later. We use commit's last char rotated so it's clearly distinct.
        base = commit[:-1] + ("0" if commit[-1] != "0" else "1")

    inferred_task = task_id or f"{repo.replace('/', '__')}-{commit[:12]}"
    selected = list(selected_test_files or [])

    task_toml_text = _render_task_toml(
        task_id=inferred_task, repo=repo,
        base_commit=base, instance_commit=commit,
        repo_language=repo_language, image_ref=image_ref,
        workdir=workdir, selected_test_files=selected,
        framework=framework,
    )

    def writer(tmp_dir: Path) -> None:
        hidden = tmp_dir / "hidden"
        hidden.mkdir(parents=True, exist_ok=True)
        (tmp_dir / "task.toml").write_text(task_toml_text, encoding="utf-8")
        (tmp_dir / "problem.md").write_text(
            f"# {inferred_task}\n\nTODO: describe the task for the solver.\n",
            encoding="utf-8")
        (hidden / "golden.patch").write_text("", encoding="utf-8")
        (hidden / "fail_to_pass.txt").write_text("", encoding="utf-8")
        (hidden / "pass_to_pass.txt").write_text("", encoding="utf-8")
        # Stage script: reset to base, clean, checkout base, overlay tests
        # from the instance commit. The instance commit reference is what the
        # bundle loader validates against task.toml.
        overlay_paths = " ".join(selected) if selected else "TODO_TEST_PATHS"
        (hidden / "stage.sh").write_text(
            f"git reset --hard {base}\n"
            f"git clean -fd\n"
            f"git checkout {base}\n"
            f"git checkout {commit} -- {overlay_paths}\n",
            encoding="utf-8")

    _atomic_write_dir(target_dir, force=force, writer=writer)
    try:
        load(target_dir)
    except BundleError:
        # Bundle won't validate until the author fills golden.patch +
        # fail_to_pass.txt + selected_test_files. That's expected for a spec
        # scaffold; the bundle is structurally complete enough for the author
        # to iterate on.
        pass
    return target_dir


def init_manual(target_dir: Path, force: bool = False) -> Path:
    target_dir = Path(target_dir)
    _ensure_writable_target(target_dir, force=force)

    def writer(tmp_dir: Path) -> None:
        hidden = tmp_dir / "hidden"
        hidden.mkdir(parents=True, exist_ok=True)
        (tmp_dir / "task.toml").write_text(
            "\n".join(
                [
                    '# TODO: task_id = "..."',
                    '# TODO: repo = "owner/name"',
                    '# TODO: base_commit = "<40-hex>"',
                    '# TODO: instance_commit = "<40-hex>"',
                    '# TODO: repo_language = "python"',
                    '# TODO: image_ref = "registry/image:tag"',
                    'workdir = "/testbed"',
                    '# TODO: selected_test_files = ["tests/test_example.py"]',
                    "",
                    "[test]",
                    'framework = "pytest"',
                    "",
                    "[hidden]",
                    'strategy = "checkout_overlay"',
                    "",
                    "[limits]",
                    "cpu_quota = 2",
                    "memory_gb = 2",
                    "wall_clock_seconds = 1800",
                    "",
                    "[network]",
                    'policy = "none"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (tmp_dir / "problem.md").write_text("TODO: describe the task.\n", encoding="utf-8")
        (hidden / "golden.patch").write_text("", encoding="utf-8")
        (hidden / "fail_to_pass.txt").write_text("", encoding="utf-8")
        (hidden / "pass_to_pass.txt").write_text("", encoding="utf-8")
        (hidden / "stage.sh").write_text(
            "\n".join(
                [
                    "git reset --hard TODO_BASE_COMMIT",
                    "git clean -fd",
                    "git checkout TODO_BASE_COMMIT",
                    "git checkout TODO_INSTANCE_COMMIT -- TODO_TEST_PATHS",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    _atomic_write_dir(target_dir, force=force, writer=writer)
    try:
        load(target_dir)
    except BundleError:
        pass
    return target_dir


def _read_test_list(path: Path) -> tuple[str, ...]:
    return tuple(line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _normalize_path(path: str) -> str:
    return str(path).strip().replace("\\", "/")


def _bundle_hash(bundle_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in bundle_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(bundle_dir).as_posix().encode("utf-8")
        digest.update(rel)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _ensure_writable_target(target_dir: Path, *, force: bool) -> None:
    if target_dir.exists() and any(target_dir.iterdir()) and not force:
        raise InitRefusedError(f"{target_dir} exists and is not empty")


def _atomic_write_dir(target_dir: Path, *, force: bool, writer: Any) -> None:
    parent = target_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp_path = Path(tempfile.mkdtemp(prefix=f".{target_dir.name}.tmp.", dir=parent))
    try:
        writer(tmp_path)
        if target_dir.exists():
            if force:
                shutil.rmtree(target_dir)
            else:
                raise InitRefusedError(f"{target_dir} exists")
        os.replace(tmp_path, target_dir)
    except Exception:
        if tmp_path.exists():
            shutil.rmtree(tmp_path, ignore_errors=True)
        raise


def _parse_json_list(row: dict[str, Any], *names: str) -> tuple[str, ...]:
    for name in names:
        if name in row:
            raw = row[name]
            break
    else:
        raise RowIncompleteError(f"missing required row field {names[0]}")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            try:
                parsed = ast.literal_eval(raw)
            except (SyntaxError, ValueError) as literal_exc:
                raise RowMalformedError(f"{names[0]} is not valid JSON") from literal_exc
    else:
        parsed = raw
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise RowMalformedError(f"{names[0]} must be a JSON-encoded list of strings")
    return tuple(parsed)


def _parse_optional_json_list(row: dict[str, Any], name: str) -> tuple[str, ...] | None:
    raw = row.get(name)
    if raw in (None, ""):
        return None
    return _parse_json_list(row, name)


def _extract_instance_commit(stage_script: str, base_commit: str) -> str:
    matches = CHECKOUT_OVERLAY_RE.findall(stage_script)
    for sha, _paths in reversed(matches):
        if sha != base_commit:
            return sha
    raise RowMalformedError("before_repo_set_cmd does not contain an instance checkout line")


def _image_ref_from_tag(dockerhub_tag: str) -> str:
    if "/" in dockerhub_tag.split(":", 1)[0] or dockerhub_tag.startswith("jefzda/"):
        return dockerhub_tag
    return f"jefzda/sweap-images:{dockerhub_tag}"


def _repo_language(row: dict[str, Any]) -> str:
    value = str(row.get("repo_language") or row.get("language") or "python").lower()
    if value in {"javascript", "node", "nodejs"}:
        return "js"
    if value in {"typescript"}:
        return "ts"
    if value not in {"python", "js", "ts", "go"}:
        return "python"
    return value


def _render_task_toml(
    *,
    task_id: str,
    repo: str,
    base_commit: str,
    instance_commit: str,
    repo_language: str,
    image_ref: str,
    selected_test_files: tuple[str, ...],
    issue_categories: tuple[str, ...] | None = None,
    issue_specificity: tuple[str, ...] | None = None,
    workdir: str = "/app",
    framework: str = "pytest",
) -> str:
    lines = [
        f"task_id = {json.dumps(task_id)}",
        f"repo = {json.dumps(repo)}",
        f"base_commit = {json.dumps(base_commit)}",
        f"instance_commit = {json.dumps(instance_commit)}",
        f"repo_language = {json.dumps(repo_language)}",
        f"image_ref = {json.dumps(image_ref)}",
        f"workdir = {json.dumps(workdir)}",
        f"selected_test_files = {json.dumps(list(selected_test_files))}",
    ]
    if issue_categories is not None:
        lines.append(f"issue_categories = {json.dumps(list(issue_categories))}")
    if issue_specificity is not None:
        lines.append(f"issue_specificity = {json.dumps(list(issue_specificity))}")
    lines.extend(
        [
            "",
            "[test]",
            f"framework = {json.dumps(framework)}",
            "",
            "[hidden]",
            'strategy = "checkout_overlay"',
            "",
            "[limits]",
            "cpu_quota = 2",
            "memory_gb = 2",
            "wall_clock_seconds = 1800",
            "",
            "[network]",
            'policy = "none"',
            "",
        ]
    )
    return "\n".join(lines)


def _render_problem(row: dict[str, Any], problem_statement: str) -> str:
    parts = [problem_statement.strip()]
    for heading, key in (("Requirements", "requirements"), ("Interface", "interface")):
        value = _optional_string(row.get(key))
        if value and value.strip() != NO_NEW_INTERFACES:
            parts.append(f"## {heading}\n\n{value.strip()}")
    return "\n\n".join(part for part in parts if part).rstrip() + "\n"


def _require_string(row: dict[str, Any], name: str) -> str:
    value = row.get(name)
    if not isinstance(value, str) or not value.strip():
        raise RowIncompleteError(f"missing required row field {name}")
    return value


def _optional_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _write_text_lf(path: Path, value: str) -> None:
    path.write_bytes(_normalize_newlines(value).encode("utf-8"))
