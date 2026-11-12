"""Docker lifecycle, isolation, command execution, and artifact copy seam.

The create API deliberately exposes no bind-mount or volume parameter. Bundles
move through copy operations only, so callers cannot accidentally mount the host
filesystem or Docker socket into an untrusted container.
"""

from __future__ import annotations

import io
import posixpath
import shlex
import tarfile
import threading
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import docker
from docker.errors import APIError, DockerException, ImageNotFound, NotFound

from task_bundle.errors import (
    ContainerError,
    CopyFailedError,
    DestroyFailedError,
    ExecFailedError,
    ImageUnavailableError,
    ProvisionFailedError,
)


ARTIFACT_CAP_BYTES = 50 * 1024 * 1024
TRUNCATION_MARKER = b"\n[task-bundle output truncated]\n"
TASK_BUNDLE_HOME = "/tmp/task-bundle-home"


class NetworkPolicy(str, Enum):
    NONE = "none"
    BRIDGE = "bridge"


@dataclass(frozen=True)
class ResourceLimits:
    cpu_quota: int = 2
    memory_gb: int = 2
    pids_limit: int = 1024
    wall_clock_seconds: int = 1800
    tmpfs_mb: int = 512


@dataclass(frozen=True)
class ImageRef:
    tag: str
    digest: str


@dataclass(frozen=True)
class ExecResult:
    exit_code: int
    stdout_path: Path
    stderr_path: Path
    duration_seconds: float
    timed_out: bool


@dataclass(frozen=True)
class Container:
    handle: Any
    role: Literal["validate", "solve", "grade"]
    artifact_dir: Path
    manager: "ContainerManager"

    def __post_init__(self) -> None:
        if self.role not in {"validate", "solve", "grade"}:
            raise ValueError(f"invalid container role: {self.role}")

    @property
    def id(self) -> str:
        return str(self.handle.id)

    def exec(
        self,
        command: list[str] | str,
        workdir: str = "/",
        env: dict[str, str] | None = None,
        timeout_seconds: int = 300,
    ) -> ExecResult:
        return self.manager.exec(self, command, workdir=workdir, env=env, timeout_seconds=timeout_seconds)

    def copy_in(self, host_bytes_or_path: bytes | Path | str, dest_path: str) -> None:
        self.manager.copy_in(self, host_bytes_or_path, dest_path)

    def copy_out(self, src_path: str, dest_host_path: Path | str) -> None:
        self.manager.copy_out(self, src_path, dest_host_path)

    def destroy(self) -> None:
        self.manager.destroy(self)


class ContainerManager:
    def __init__(self, artifact_root: Path | str, client: Any | None = None) -> None:
        self.artifact_root = Path(artifact_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.client = client if client is not None else docker.from_env()
        self._image_users: dict[str, str] = {}

    def acquire_image(self, tag: str) -> ImageRef:
        try:
            image = self.client.images.pull(tag)
            attrs = getattr(image, "attrs", {}) or {}
            repo_digests = attrs.get("RepoDigests") or []
            digest = repo_digests[0] if repo_digests else getattr(image, "id", "")
            image_ref = ImageRef(tag=tag, digest=digest)
            self._image_users[tag] = self._resolve_user(tag)
            return image_ref
        except (ImageNotFound, APIError, DockerException) as exc:
            raise ImageUnavailableError(f"image unavailable: {tag}") from exc

    def create(
        self,
        image: ImageRef,
        role: str,
        limits: ResourceLimits,
        network: NetworkPolicy,
        labels: dict[str, str],
    ) -> Container:
        if role not in {"validate", "solve", "grade"}:
            raise ValueError(f"invalid container role: {role}")
        user = self._image_users.get(image.tag, "1000:1000")
        run_id = labels["run_id"]
        create_labels = {"task_bundle.run_id": run_id, "task_bundle.role": role}
        kwargs = {
            "image": image.tag,
            "entrypoint": "/bin/sh",
            "command": ["-lc", "tail -f /dev/null"],
            "user": user,
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
            "pids_limit": limits.pids_limit,
            "mem_limit": f"{limits.memory_gb}g",
            "cpu_quota": limits.cpu_quota * 100000,
            "cpu_period": 100000,
            "tmpfs": {"/tmp": f"size={limits.tmpfs_mb}m"},
            "init": True,
            "auto_remove": False,
            "detach": True,
            "network_mode": network.value,
            "labels": create_labels,
        }
        try:
            handle = self.client.containers.create(**kwargs)
            handle.start()
            artifact_dir = self.artifact_root / run_id / role
            artifact_dir.mkdir(parents=True, exist_ok=True)
            return Container(handle=handle, role=role, artifact_dir=artifact_dir, manager=self)
        except APIError as exc:
            raise ProvisionFailedError(f"container provision failed for role {role}") from exc

    def cleanup_orphans(self, run_id: str) -> int:
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"label": f"task_bundle.run_id={run_id}"},
            )
        except APIError as exc:
            raise DestroyFailedError(f"orphan cleanup failed for run {run_id}") from exc
        count = 0
        for handle in containers:
            container = Container(handle=handle, role=_role_from_labels(handle), artifact_dir=self.artifact_root / run_id, manager=self)
            self.destroy(container)
            count += 1
        return count

    def prepare_workspace(self, container: Container, workdir: str) -> str:
        quoted_home = shlex.quote(TASK_BUNDLE_HOME)
        quoted_workdir = shlex.quote(workdir)
        writable_probe = (
            f"mkdir -p {quoted_home} && "
            f"test -w {quoted_home} && "
            f"test -w {quoted_workdir}"
        )
        probe = container.handle.exec_run(["sh", "-lc", writable_probe])
        probe_code = getattr(probe, "exit_code", probe[0] if isinstance(probe, tuple) else 1)
        if probe_code == 0:
            return workdir

        runtime_workdir = "/task-bundle-workdir"
        quoted_runtime = shlex.quote(runtime_workdir)
        command = (
            f"rm -rf {quoted_runtime} {quoted_home} && "
            f"mkdir -p {quoted_runtime} {quoted_home} && "
            f"cd {quoted_workdir} && "
            f"tar cf - . | tar --no-same-owner -C {quoted_runtime} -xf - && "
            f"chmod -R a+rwX {quoted_runtime} {quoted_home} && "
            f"test -d {quoted_runtime}/.git"
        )
        result = container.handle.exec_run(["sh", "-lc", command], user="0")
        exit_code = getattr(result, "exit_code", result[0] if isinstance(result, tuple) else 1)
        if exit_code != 0:
            output = getattr(result, "output", b"")
            if isinstance(output, bytes):
                rendered = output.decode("utf-8", errors="replace")
            else:
                rendered = str(output)
            raise ProvisionFailedError(f"workspace preparation failed for {workdir}: {rendered[:500]}")
        writable_runtime_probe = (
            f"test -w {quoted_runtime} && "
            f"test -w {quoted_home}"
        )
        result = container.handle.exec_run(["sh", "-lc", writable_runtime_probe])
        exit_code = getattr(result, "exit_code", result[0] if isinstance(result, tuple) else 1)
        if exit_code != 0:
            output = getattr(result, "output", b"")
            if isinstance(output, bytes):
                rendered = output.decode("utf-8", errors="replace")
            else:
                rendered = str(output)
            raise ProvisionFailedError(f"workspace is not writable after preparation for {workdir}: {rendered[:500]}")
        return runtime_workdir

    def exec(
        self,
        container: Container,
        command: list[str] | str,
        workdir: str,
        env: dict[str, str] | None,
        timeout_seconds: int,
    ) -> ExecResult:
        command_value = _exec_command(command, workdir)
        exec_env = _exec_environment(env, workdir)
        stdout_path = container.artifact_dir / f"stdout-{uuid.uuid4().hex}.log"
        stderr_path = container.artifact_dir / f"stderr-{uuid.uuid4().hex}.log"
        start = time.monotonic()
        done = threading.Event()
        result: dict[str, Any] = {"exit_code": 1, "error": None}
        exec_id: dict[str, str | None] = {"value": None}

        def runner() -> None:
            try:
                created = self.client.api.exec_create(
                    container.id,
                    command_value,
                    workdir=workdir,
                    environment=exec_env,
                )
                exec_id["value"] = created["Id"] if isinstance(created, dict) else created
                with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                    stdout_written = 0
                    stderr_written = 0
                    stream = self.client.api.exec_start(exec_id["value"], stream=True, demux=True)
                    for chunk in stream:
                        out, err = _demux_chunk(chunk)
                        stdout_written = _write_capped(stdout, out, stdout_written)
                        stderr_written = _write_capped(stderr, err, stderr_written)
                inspected = self.client.api.exec_inspect(exec_id["value"])
                result["exit_code"] = int(inspected.get("ExitCode") or 0)
            except Exception as exc:  # docker wraps transport errors inconsistently.
                result["error"] = exc
            finally:
                done.set()

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        timed_out = not done.wait(timeout_seconds)
        if timed_out:
            self._kill_exec(container, exec_id["value"])
            done.wait(5)
            if not done.is_set():
                self.destroy(container)
            result["exit_code"] = -1
        if result["error"] is not None and not timed_out:
            raise ExecFailedError(f"docker exec failed: {result['error']}")
        return ExecResult(
            exit_code=int(result["exit_code"]),
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            duration_seconds=time.monotonic() - start,
            timed_out=timed_out,
        )

    def copy_in(self, container: Container, host_bytes_or_path: bytes | Path | str, dest_path: str) -> None:
        try:
            data = _read_payload(host_bytes_or_path)
            normalized_dest = dest_path.replace("\\", "/")
            parent = posixpath.dirname(normalized_dest) or "/"
            staging_name = f".task-bundle-copy-{uuid.uuid4().hex}"
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                info = tarfile.TarInfo(name=staging_name)
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))
            tar_stream.seek(0)
            if not container.handle.put_archive("/", tar_stream.getvalue()):
                raise CopyFailedError(f"docker put_archive returned false for {dest_path}")
            staging_path = "/" + staging_name
            move = (
                f"mkdir -p {shlex.quote(parent)} && "
                f"cp {shlex.quote(staging_path)} {shlex.quote(normalized_dest)} && "
                f"chmod 0644 {shlex.quote(normalized_dest)} && "
                f"rm -f {shlex.quote(staging_path)}"
            )
            result = container.handle.exec_run(["sh", "-c", move], user="0")
            exit_code = getattr(result, "exit_code", result[0] if isinstance(result, tuple) else 1)
            if exit_code != 0:
                raise CopyFailedError(f"copy staging move failed for {dest_path}")
        except Exception as exc:
            if isinstance(exc, CopyFailedError):
                raise
            raise CopyFailedError(f"copy into container failed: {dest_path}") from exc

    def copy_out(self, container: Container, src_path: str, dest_host_path: Path | str) -> None:
        staging_path = f"/.task-bundle-copy-out-{uuid.uuid4().hex}"
        try:
            stage = (
                f"cp {shlex.quote(src_path)} {shlex.quote(staging_path)} && "
                f"chmod 0644 {shlex.quote(staging_path)}"
            )
            result = container.handle.exec_run(["sh", "-c", stage], user="0")
            exit_code = getattr(result, "exit_code", result[0] if isinstance(result, tuple) else 1)
            if exit_code != 0:
                raise CopyFailedError(f"copy-out staging failed for {src_path}")
            chunks, _stat = container.handle.get_archive(staging_path)
            data = b"".join(chunks)
            dest = Path(dest_host_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
                member = tar.getmembers()[0]
                extracted = tar.extractfile(member)
                if extracted is None:
                    raise CopyFailedError(f"copy out produced no file: {src_path}")
                dest.write_bytes(extracted.read())
        except ContainerError:
            raise
        except Exception as exc:
            raise CopyFailedError(f"copy out of container failed: {src_path}") from exc
        finally:
            try:
                container.handle.exec_run(["rm", "-f", staging_path], user="0")
            except Exception:
                pass

    def destroy(self, container: Container) -> None:
        try:
            container.handle.stop(timeout=5)
        except NotFound:
            return
        except APIError:
            pass
        try:
            container.handle.remove(force=True)
        except NotFound:
            return
        except APIError as exc:
            raise DestroyFailedError(f"container destroy failed: {container.id}") from exc

    def verify_isolation(self, container: Container) -> dict[str, Any]:
        inspected = self.client.api.inspect_container(container.id)
        host_config = inspected.get("HostConfig", {})
        config = inspected.get("Config", {})
        user = config.get("User") or ""
        return {
            "user": user,
            "user_non_root": _is_non_root_user(user),
            "cap_drop": host_config.get("CapDrop") or [],
            "security_opt": host_config.get("SecurityOpt") or [],
            "pids_limit": host_config.get("PidsLimit"),
            "memory_bytes": host_config.get("Memory"),
            "cpu_quota": host_config.get("CpuQuota"),
            "cpu_period": host_config.get("CpuPeriod"),
            "tmpfs": host_config.get("Tmpfs") or {},
            "init": host_config.get("Init"),
            "auto_remove": host_config.get("AutoRemove"),
            "network_mode": host_config.get("NetworkMode"),
            "labels": config.get("Labels") or {},
            "mounts": inspected.get("Mounts") or [],
            "privileged": host_config.get("Privileged") or False,
        }

    def assert_isolation_matches(self, container: Container, expected: dict[str, Any]) -> None:
        actual = self.verify_isolation(container)
        divergent = [key for key, value in expected.items() if actual.get(key) != value]
        if divergent:
            raise ExecFailedError(f"isolation mismatch: {', '.join(sorted(divergent))}")

    def _resolve_user(self, tag: str) -> str:
        try:
            self.client.containers.run(tag, ["id", "-u", "agent"], remove=True)
            return "agent"
        except Exception:
            return "1000:1000"

    def _kill_exec(self, container: Container, exec_id: str | None) -> None:
        if not exec_id:
            return
        try:
            inspected = self.client.api.exec_inspect(exec_id)
            pid = inspected.get("Pid")
            if pid:
                container.handle.exec_run(["kill", "-9", str(pid)])
        except Exception:
            try:
                self.destroy(container)
            except ContainerError:
                pass


def _write_capped(handle: Any, data: bytes, written: int) -> int:
    if not data:
        return written
    if written >= ARTIFACT_CAP_BYTES:
        return written
    remaining = ARTIFACT_CAP_BYTES - written
    chunk = data[:remaining]
    handle.write(chunk)
    written += len(chunk)
    if len(data) > remaining:
        handle.write(TRUNCATION_MARKER)
        written = ARTIFACT_CAP_BYTES
    return written


def _demux_chunk(chunk: Any) -> tuple[bytes, bytes]:
    if isinstance(chunk, tuple):
        return chunk[0] or b"", chunk[1] or b""
    return chunk or b"", b""


def _exec_command(command: list[str] | str, workdir: str) -> list[str]:
    if not workdir or workdir == "/":
        return command if isinstance(command, list) else ["sh", "-lc", command]
    safe_prefix = (
        f"mkdir -p {shlex.quote(TASK_BUNDLE_HOME)} /tmp/task-bundle-runtime && "
        f"chmod 700 /tmp/task-bundle-runtime && "
        f"HOME={shlex.quote(TASK_BUNDLE_HOME)} "
        f"git config --global --add safe.directory {shlex.quote(workdir)} >/dev/null 2>&1 || true"
    )
    if isinstance(command, list):
        return ["sh", "-lc", f"{safe_prefix}\nexec {shlex.join(command)}"]
    return ["sh", "-lc", f"{safe_prefix}\n{command}"]


def _exec_environment(env: dict[str, str] | None, workdir: str) -> dict[str, str] | None:
    merged = dict(env or {})
    if workdir and workdir != "/":
        merged.setdefault("HOME", TASK_BUNDLE_HOME)
    return merged or None


def _read_payload(host_bytes_or_path: bytes | Path | str) -> bytes:
    if isinstance(host_bytes_or_path, bytes):
        return host_bytes_or_path
    path = Path(host_bytes_or_path)
    if path.exists():
        return path.read_bytes()
    return str(host_bytes_or_path).encode("utf-8")


def _role_from_labels(handle: Any) -> Literal["validate", "solve", "grade"]:
    labels = getattr(handle, "labels", {}) or {}
    role = labels.get("task_bundle.role", "validate")
    if role not in {"validate", "solve", "grade"}:
        return "validate"
    return role


def _is_non_root_user(user: str) -> bool:
    if user in {"", "0", "0:0", "root"}:
        return False
    return not user.startswith("0:")
