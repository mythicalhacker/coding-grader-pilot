"""Give a scorer the question, proposed probe, and run results without arm labels."""
import hashlib
import json
from pathlib import Path
import random
import re
import sys

root = Path(__file__).resolve().parent
group = sys.argv[1]
records = json.loads((root / f"assignment-{group}.json").read_text())
random.Random(1089).shuffle(records)
runs = json.loads((root / f"runs-{group}.json").read_text())["replays"]
scoring = root / "audit"
scoring.mkdir(exist_ok=True)
parts = []
for rec in records:
    slot = rec["slot"]
    case = rec["issue"]
    code = (root / "responses" / f"{slot}.py").read_text().strip()
    label = hashlib.sha256(("blind-audit-19"+slot).encode()).hexdigest()[:7]
    case_problem = (root / "inputs" / case / "problem.txt").read_text().strip()
    parts.extend([f"## Probe {label} for {case}", case_problem, f"Proposed test\n\n```python\n{code}\n```"])
    for run in (r for r in runs if r["slot"] == slot):
        variant = {"haiku":"candidate 1","sonnet":"candidate 2"}.get(run["variant"],run["variant"])
        output = run.get("stderr","").strip()
        output = re.sub(r'File "[^"]*responses/[^"]+.py"', 'File "[submitted probe]"', output)
        output = re.sub(r'File "[^"]*/trees/[^/]+/[^/]+/', 'File "[checkout]/', output)
        output = re.sub(r'/[^\s"]*/trees/[^/\s]+/(?:base|gold|haiku|sonnet)/', '[checkout]/', output)
        parts.append(f"{variant}: {run['status']}\n" + "\n".join(output.splitlines()[-9:]))
(scoring/f"blind-{group}.md").write_text("\n\n".join(parts)+"\n")
