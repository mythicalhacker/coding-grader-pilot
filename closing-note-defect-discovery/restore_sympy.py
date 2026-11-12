"""Restore the four pinned SymPy baselines and their three patch variants."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path


def verified_bytes(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"SHA-256 mismatch for {path}")
    return data


def restore_case(inputs, case_id, entry, destination, cache):
    archive = cache / f"{case_id}.tar.gz"
    if not archive.exists():
        with urllib.request.urlopen(entry["base_archive_url"], timeout=90) as response:
            contents = response.read()
        if hashlib.sha256(contents).hexdigest() != entry["source_archive_sha256"]:
            raise ValueError(f"Unexpected archive for {case_id}")
        archive.write_bytes(contents)
    verified_bytes(archive, entry["source_archive_sha256"])

    case = destination / case_id
    base = case / "base"
    base.mkdir(parents=True)
    with tarfile.open(archive) as source:
        prefix = f"sympy-{entry['base_commit']}"
        for member in source:
            if member.isdir():
                continue
            name = Path(member.name).relative_to(prefix)
            if not member.isfile() or name.is_absolute() or ".." in name.parts:
                raise ValueError(f"Unexpected archive member {member.name}")
            output = base / name
            output.parent.mkdir(parents=True, exist_ok=True)
            with source.extractfile(member) as original, output.open("wb") as target:
                shutil.copyfileobj(original, target)
    for label in ("gold", "haiku", "sonnet"):
        expected = (entry["gold_patch_sha256"] if label == "gold"
                    else entry["authors"][label]["patch_sha256"])
        patch = verified_bytes(inputs / case_id / f"{label}.diff", expected)
        target = case / label
        shutil.copytree(base, target)
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        subprocess.run(["git", "apply", "--whitespace=nowarn", "-"],
                       cwd=target, input=patch, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="new directory for restored trees")
    parser.add_argument("--archive-cache", type=Path, help="optional archive cache")
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    cache = args.archive_cache or destination / "archives"
    cache.mkdir(parents=True, exist_ok=True)
    inputs = Path(__file__).resolve().parent / "inputs"
    manifest = json.loads((inputs / "source-manifest.json").read_text())
    for case_id, entry in manifest["cases"].items():
        restore_case(inputs, case_id, entry, destination, cache)


if __name__ == "__main__":
    main()
