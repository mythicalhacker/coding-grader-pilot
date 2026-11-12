"""Fetch the locked public SWE-bench records and upstream Django sources."""

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import urllib.request

import pyarrow.parquet as parquet


ISSUES = tuple(f"django__django-{n}" for n in (11211, 11532, 11740, 12193))
RUNS = {
    "haiku": "20241022_tools_claude-3-5-haiku",
    "sonnet": "20241022_tools_claude-3-5-sonnet-updated",
}
PINS = json.loads(Path(__file__).with_name("source-pins.json").read_text())
PINNED_FILES = {record["file"]:record for record in PINS["archive"]}


def fetch(job):
    url, path = job
    pin = PINNED_FILES[path.name]
    if pin["url"] != url:
        raise ValueError("URL does not match the pinned source for "+path.name)
    if not path.exists():
        with urllib.request.urlopen(url, timeout=120) as response:
            body = response.read()
        if hashlib.sha256(body).hexdigest() != pin["sha256"]:
            raise ValueError("Downloaded content failed digest check for "+path.name)
        with NamedTemporaryFile(dir=path.parent,delete=False) as stream:
            stream.write(body)
            tmp=stream.name
        os.replace(tmp,path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != pin["sha256"]:
        raise ValueError("Cached content failed digest check for "+path.name)
    return {"file":path.name,"url":url,"sha256":pin["sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    args.cache.mkdir(exist_ok=True, parents=True)
    if hashlib.sha256(args.dataset.read_bytes()).hexdigest() != PINS["dataset_sha256"]:
        raise ValueError("Unexpected SWE-bench Verified dataset revision")
    rows = {row["instance_id"]: row for row in parquet.read_table(args.dataset).to_pylist()}
    jobs = []
    for issue in ISSUES:
        row = rows[issue]
        (args.cache / (issue + ".json")).write_text(json.dumps(row, default=str, indent=2))
        jobs.append(("https://codeload.github.com/django/django/tar.gz/" + row["base_commit"],
                     args.cache / (issue + ".tar.gz")))
        for model, run in RUNS.items():
            root = f"https://swe-bench-submissions.s3.amazonaws.com/verified/{run}"
            jobs.extend([
                (f"{root}/trajs/{issue}.log", args.cache / f"{issue}-{model}.log"),
                (f"{root}/logs/{issue}/patch.diff", args.cache / f"{issue}-{model}.diff"),
            ])
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as workers:
        items = list(workers.map(fetch, jobs))
    (args.cache/"downloads.json").write_text(json.dumps(items, indent=2) + "\n")
