"""Recover paired historical evidence and create four independent checkout variants."""

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

PINS = json.loads(Path(__file__).with_name("source-pins.json").read_text())
MARKERS = re.compile(rb"^\x1b\[(?:32|34|36)m(THOUGHT:|ACTION \([^)]+\):|OBSERVATION:|Initial prompt:|No tool use\. Submitting\.)", re.M)
COLOR = re.compile(rb"\x1b\[[0-9;]*m")

def digest(payload):
    return hashlib.sha256(payload).hexdigest()

def extract(source, model, folder, expected_note):
    data = source.read_bytes()
    markers = list(MARKERS.finditer(data))
    def body(i):
        block = data[markers[i].end():markers[i+1].start()]
        assert block.startswith(b"\n") and block.endswith(b"\x1b[0m\n")
        return COLOR.sub(b"", block[1:-len(b"\x1b[0m\n")])
    assert markers[-2][1] == b"THOUGHT:" and markers[-1][1] == b"No tool use. Submitting."
    note = body(len(markers)-2).strip()
    assert digest(note) == expected_note
    idx = max(i for i,m in enumerate(markers) if m[1] == b"ACTION (bash):")
    command = body(idx).removeprefix(b"command:\n")
    assert re.fullmatch(rb"cd /(?:repo|tmp/test_project) && (?:PYTHONPATH=/repo )?python3? [\w./]+\.py(?: migrate)?\s*", command)
    assert markers[idx+1][1] == b"OBSERVATION:"
    observation = body(idx+1)
    check = b"Command:\n"+command+b"\n\nObserved output:\n"+(observation or b"[Empty observation in archived trajectory]")+b"\n"
    (folder/f"{model}-check.txt").write_bytes(check)
    (folder/f"{model}-note.txt").write_bytes(note)
    return {"command":command.decode(),"source_line":data[:markers[idx].start()].count(b"\n")+1,
            "observation_line":data[:markers[idx+1].start()].count(b"\n")+1,"check_sha256":digest(check),"note_sha256":digest(note)}

def trees(cache, issue, folder):
    root = cache/"trees"/issue
    base = root/"base"
    base.mkdir(parents=True,exist_ok=True)
    with tarfile.open(cache/(issue+".tar.gz")) as archive:
        for member in archive:
            if not member.isfile():
                continue
            path=Path(member.name)
            relative=path.relative_to(path.parts[0])
            assert not relative.is_absolute() and ".." not in relative.parts
            output=base/relative
            output.parent.mkdir(parents=True,exist_ok=True)
            with output.open("wb") as stream:
                shutil.copyfileobj(archive.extractfile(member),stream)
            output.chmod(member.mode & 0o777)
    for variant in ("haiku","sonnet","gold"):
        dest = root/variant
        if not dest.exists():
            with tempfile.TemporaryDirectory(dir=root) as stage:
                copy=Path(stage)/"copy"
                shutil.copytree(base,copy)
                subprocess.run(["git","apply","--whitespace=nowarn",str((folder/(variant+".diff")).resolve())],cwd=copy,check=True)
                copy.rename(dest)

def prepare(args):
    sources = {f["file"]:f for f in PINS["archive"]}
    for name,source in sources.items():
        assert digest((args.cache/name).read_bytes())==source["sha256"],name
    results = {}
    for issue in PINS["issues"]:
        row = json.loads((args.cache/(issue+".json")).read_text())
        folder = args.inputs/issue
        folder.mkdir(exist_ok=True,parents=True)
        (folder/"problem.txt").write_text(row["problem_statement"])
        (folder/"gold.diff").write_text(row["patch"])
        info = {"repo":row["repo"], "base_commit":row["base_commit"], "authors":{}}
        for model in ("haiku","sonnet"):
            log = f"{issue}-{model}.log"
            info["authors"][model] = extract(args.cache/log,model,folder,sources[log]["terminal_sha256"])
            shutil.copyfile(args.cache/f"{issue}-{model}.diff", folder/f"{model}.diff")
        results[issue] = info
    (args.inputs/"django-source-manifest.json").write_text(json.dumps(results,indent=2)+"\n")
    if args.trees:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as workers:
            list(workers.map(lambda task: trees(args.cache,task,args.inputs/task), PINS["issues"]))

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--cache",type=Path,required=True)
    parser.add_argument("--inputs",type=Path,required=True)
    parser.add_argument("--trees",action="store_true")
    prepare(parser.parse_args())
