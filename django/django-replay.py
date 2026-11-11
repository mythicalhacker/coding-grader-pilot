"""Replay the historical Django checks using Python with the documented dependencies."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "django-manifest.json").read_text())


def inputs(directory):
    for name, source in MANIFEST["sources"].items():
        path = directory / name
        if not path.exists():
            with urllib.request.urlopen(source["url"], timeout=60) as response:
                path.write_bytes(response.read())
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"Source hash mismatch for {name}")


def extract_source(archive, destination):
    prefix = f"django-{MANIFEST['revision']}/"
    with tarfile.open(archive) as data:
        for member in data:
            if not member.isfile() or not member.name.startswith(prefix):
                continue
            relative = Path(member.name[len(prefix):])
            if relative.parts[0] not in {"django", "tests"} or ".." in relative.parts:
                continue
            path = destination / relative
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_bytes(data.extractfile(member).read())


def run_replay(source_files, work):
    extract_source(source_files / "django.tar.gz", work / "unchanged")
    patch = (source_files / "eval.sh").read_text().split("<<'EOF_114329324912'\n", 1)[1]
    regression = patch.split("\nEOF_114329324912", 1)[0].encode()
    subprocess.run(["git", "apply", "--whitespace=nowarn", "-"], cwd=work / "unchanged",
                   input=regression, check=True)
    losing_diff = (source_files / "B.diff").read_text()
    hunk = losing_diff.split("+++ b/verify_migration_fix.py\n", 1)[1]
    fixture_text = "\n".join(line[1:] for line in hunk.splitlines()
                             if line.startswith("+")) + "\n"
    if hashlib.sha256(fixture_text.encode()).hexdigest() != MANIFEST["fixture_sha256"]:
        raise ValueError("Extracted author check differs from the archived final script")
    fixture = work / "verify_migration_fix.py"
    fixture.write_text(fixture_text)
    results = {}
    for case in ("unchanged", "A", "B"):
        root = work / case
        if case != "unchanged":
            shutil.copytree(work / "unchanged", root)
            subprocess.run(["git", "apply", "--whitespace=nowarn", "--include=django/*", "-"],
                           cwd=root, input=(source_files / f"{case}.diff").read_bytes(), check=True)
        commands = {"author": [str(fixture)], "regression": ["tests/runtests.py", "--verbosity", "2",
                    "--settings", "test_sqlite", "--parallel", "1", MANIFEST["target"]]}
        env = {"PATH": os.defpath, "PYTHONPATH": str(root),
               "PYTHONDONTWRITEBYTECODE": "1", "LANG": "en_US.UTF-8"}
        results[case] = {}
        for check, args in commands.items():
            p = subprocess.run([sys.executable, *args], cwd=root, env=env, timeout=60,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if check == "author":
                expected = "OK: Migration detection test passed successfully!"
            else:
                expected = {"unchanged": "Operation type mismatch", "A": "... ok",
                            "B": "'NoneType' object has no attribute 'model'"}[case]
                if "Ran 1 test" not in p.stdout:
                    raise RuntimeError(p.stdout)
            if p.returncode != MANIFEST["expected_exit_codes"][case][check] or expected not in p.stdout:
                raise RuntimeError(p.stdout)
            results[case][check] = p.returncode
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, help="use/download the four published inputs here")
    args = parser.parse_args()
    for package, version in MANIFEST["dependencies"].items():
        if importlib.metadata.version(package) != version:
            raise RuntimeError(f"Use {package}=={version}")
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        source_files = args.inputs or work / "inputs"
        source_files.mkdir(exist_ok=True, parents=True)
        inputs(source_files)
        print(json.dumps(run_replay(source_files, work), indent=2))
