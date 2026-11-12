"""Join the concealed condition key to independently recorded scores."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads((ROOT / path).read_text())


def summarize():
    cases = {}
    sensitive = read("audit/secondary-scores.json")
    for family in ("sympy", "django"):
        scores = read(f"audit/{family}-scores.json")
        assignments = read(f"assignment-{family}.json")
        execution = read(f"runs-{family}.json")
        assert len(scores) == len(assignments) == 8
        for assignment in assignments:
            slot = assignment["slot"]
            issue = assignment["issue"]
            audit_id = hashlib.sha256(("blind-audit-19" + slot).encode()).hexdigest()[:7]
            assert hashlib.sha256((ROOT / "responses" / (slot + ".py")).read_bytes()).hexdigest() == execution["probe_sha256"][slot]
            assert hashlib.sha256((ROOT / "packets" / (slot + ".txt")).read_bytes()).hexdigest() == assignment["sha256"]
            statuses = {r["variant"]: r["status"] for r in execution["replays"] if r["slot"] == slot}
            assert set(statuses) == {"base", "haiku", "sonnet", "gold"}
            label = scores[audit_id]["label"]
            assert label in ("hit", "miss", "unscorable")
            signal = statuses["gold"] == "pass" and "fail" in (statuses["sonnet"], statuses["haiku"])
            if label == "hit":
                assert signal
            arm = "with_notes" if assignment["notes"] else "commands_only"
            case = cases.setdefault(issue, {})
            assert arm not in case
            case[arm] = dict(slot=slot, audit_id=audit_id, primary=label,
                             secondary=sensitive[audit_id]["label"], run_signal=signal, statuses=statuses)

    def breakdown(metric, positive):
        counts = Counter()
        for probe_pair in cases.values():
            c = probe_pair["commands_only"][metric] == positive
            n = probe_pair["with_notes"][metric] == positive
            counts[("neither", "notes_only", "commands_only", "both")[2 * c + n]] += 1
        return {k:counts[k] for k in ("both", "commands_only", "notes_only", "neither")}

    output = dict(cases=cases, primary=breakdown("primary", "hit"), secondary=breakdown("secondary", "hit"),
                  gold_passes_and_candidate_fails=breakdown("run_signal", True),
                  unscorable=sum(arm["primary"]=="unscorable" for case in cases.values() for arm in case.values()))
    (ROOT / "results.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({k:v for k,v in output.items() if k!="cases"}, indent=2))


if __name__ == "__main__":
    summarize()
