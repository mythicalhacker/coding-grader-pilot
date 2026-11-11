"""Fetch pinned public source files, run the checks and compare to results.tsv."""
from difflib import unified_diff
from hashlib import sha256
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
BASE = "851dadeb0338403e5021c3fbe80cbc9127ee672d"
MERGED = "0cd5285c56c5375da9f4d27836ec41eea4d069f3"
SUBMISSIONS = "https://swe-bench-submissions.s3.amazonaws.com/verified"
ISSUE = "pydata__xarray-6461"
MODULE = "xarray/core/computation.py"
ARCHIVE = (
    f"https://codeload.github.com/pydata/xarray/tar.gz/{BASE}",
    "2851acdbfc1aae7d7fe2bfe28dea6c119e01a097733057cf077e711d248da60c",
)
PATCHES = {
    "A": (
        f"{SUBMISSIONS}/20241022_tools_claude-3-5-sonnet-updated/logs/{ISSUE}/patch.diff",
        "d8240a09e5bdf9aad82080d55b22952062fed3a2386a7f3ae5c8e65a7924741c",
    ),
    "B": (
        f"{SUBMISSIONS}/20241022_tools_claude-3-5-haiku/logs/{ISSUE}/patch.diff",
        "04f03a6fb1c75989e6c0a6d515e05257e9bafd7bb199ba2b6640f87f65936165",
    ),
    "maintainer": (
        f"https://github.com/pydata/xarray/commit/{MERGED}.diff",
        "82bd92343208fc80f9e109017d015bca49b38cc7ccc3365b4af34d0950e0652a",
    ),
}
MODULE_HASH = {
    "base": "46691cacfd6d0e6a4e11a6a64924a7d32202407e76f10f26bfa04ecdef1d6d35",
    "A": "8fc1cd5c78bc3291e9fd2f6e54591e58911d2b8710efcbfebb39d98d9d6858ea",
    "B": "232eb21894367780f49c0e4bd7571dcd840e043da6b0d78720a4edeb68c2001e",
    "maintainer": "efb0a4c72c514e1e877455829102aab8c3fb926080df4fd49b6c8ac373707b28",
}


def fetch(url, digest):
    with urlopen(url, timeout=60) as response:
        data = response.read()
    if sha256(data).hexdigest() != digest:
        raise ValueError(f"Unexpected SHA-256 for {url}")
    return data


def unpack_package(directory):
    prefix = f"xarray-{BASE}/"
    with tarfile.open(fileobj=io.BytesIO(fetch(*ARCHIVE)), mode="r:gz") as archive:
        for member in archive:
            if member.isfile() and member.name.startswith(prefix + "xarray/"):
                relative = Path(member.name.removeprefix(prefix))
                if ".." in relative.parts:
                    raise ValueError("Unexpected archive entry")
                target = directory / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())


def replay(directory):
    unpack_package(directory)
    target = directory / MODULE
    original = target.read_bytes()
    rows = ["version\tcheck\tstdout (JSON string)\texit detail\n"]
    for version in MODULE_HASH:
        target.write_bytes(original)
        if version in PATCHES:
            subprocess.run(
                ["git", "apply", f"--include={MODULE}", "-"],
                input=fetch(*PATCHES[version]), cwd=directory, check=True,
            )
        if sha256(target.read_bytes()).hexdigest() != MODULE_HASH[version]:
            raise ValueError(f"Unexpected {MODULE} for {version}")
        run = subprocess.run(
            [sys.executable, "-B", str(HERE / "checks.py"), version, str(directory)],
            cwd=directory, env={**os.environ, "PYTHONPATH": str(directory), "PYTHONOPTIMIZE": ""},
            capture_output=True, text=True,
        )
        if run.returncode:
            sys.exit(run.stderr)
        rows.append(run.stdout)
    return "".join(rows)


if __name__ == "__main__":
    if sys.version_info[:2] != (3, 10):
        sys.exit("Use the Python 3.10 environment specified in README.md.")
    with TemporaryDirectory() as tmp:
        observed = replay(Path(tmp))
    sys.stdout.write(observed)
    expected = (HERE / "results.tsv").read_text()
    if observed != expected:
        sys.stderr.writelines(unified_diff(expected.splitlines(True), observed.splitlines(True),
                                           fromfile="recorded", tofile="replayed"))
        sys.exit(1)
    print("All 35 recorded outputs match.", file=sys.stderr)
