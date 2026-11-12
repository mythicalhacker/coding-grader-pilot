"""Replay locked probes in the four historical trees for each issue."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def replay(job):
    name, probe, python, tree, variant = job
    if not probe.read_text().strip():
        return dict(slot=name, variant=variant, status="abstained")
    with tempfile.TemporaryDirectory() as scratch:
        env = {"PATH": os.defpath, "HOME": scratch, "TMPDIR": scratch, "PYTHONHASHSEED": "0",
               "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "TZ": "UTC",
               "PYTHONPATH": os.pathsep.join([str(tree), str(tree / "tests")])}
        try:
            result = subprocess.run([str(python), str(probe)], cwd=scratch, env=env, timeout=60,
                                    capture_output=True, text=True)
        except subprocess.TimeoutExpired:
            return dict(slot=name, variant=variant, status="timeout")
        return dict(slot=name, variant=variant, status="pass" if result.returncode==0 else "fail",
                    returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("group", choices=["sympy","django"])
    parser.add_argument("--trees", required=True, type=Path)
    parser.add_argument("--python", required=True, type=Path)
    args = parser.parse_args()
    assignments=json.loads((ROOT/f"assignment-{args.group}.json").read_text())
    jobs=[]
    digests={}
    for a in assignments:
        name=a["slot"]
        probe=ROOT/"responses"/(name+".py")
        digests[name]=hashlib.sha256(probe.read_bytes()).hexdigest()
        for variant in ("base","gold","haiku","sonnet"):
            tree=args.trees.resolve()/a["issue"]/variant
            if not tree.is_dir():
                raise FileNotFoundError(tree)
            jobs.append((name,probe,args.python.absolute(),tree,variant))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(replay,jobs))
    report={"group":args.group,"python":subprocess.check_output([str(args.python),"-V"],text=True).strip(),
            "probe_sha256":digests,"replays":results}
    (ROOT/f"runs-{args.group}.json").write_text(json.dumps(report,indent=2)+"\n")
    print(f"{len(results)} replays recorded for {args.group}")


if __name__ == "__main__":
    main()
