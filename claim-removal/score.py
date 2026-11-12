"""Score the frozen claim-removal pilot with the Python standard library."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
import json
from pathlib import Path

ARMS = ("full", "stripped", "none")
DRAWS = (1, 2)
THRESHOLD = 70


def read(path):
    return json.loads(path.read_text())


def load_grades(root):
    assignments = read(root / "assignments.json")
    truth = read(root / "fixtures/heldout.json")
    edits = {row["stem"]: row for row in read(root / "claim-edits.json")}
    if len(truth) != 8 or any(len(models) != 2 or
                              sorted(item["resolved"] for item in models.values()) != [False, True]
                              for models in truth.values()):
        raise ValueError("Expected one passing and one failing patch for each of eight issues")
    by_slot = defaultdict(list)
    for row in assignments:
        by_slot[row["slot"]].append(row)
    if len(assignments) != 96 or len(by_slot) != 24:
        raise ValueError("Expected 96 assignments across 24 independent reviewers")
    cases = defaultdict(dict)
    for slot, rows in by_slot.items():
        replies = read(root / "responses" / f"{slot}.json")
        expected = {row["item"] for row in rows}
        if len(expected) != 4 or len({r["issue"] for r in rows}) != 4 or len({(r["draw"],r["arm"]) for r in rows}) != 1:
            raise ValueError(f"Invalid reviewer assignment for {slot}")
        if len(replies) != 4 or {reply["id"] for reply in replies} != expected:
            raise ValueError(f"Missing, duplicated or unexpected grades for {slot}")
        answers = {reply["id"]: reply for reply in replies}
        for row in rows:
            reply = answers[row["item"]]
            number = reply["probability"]
            if type(number) is not int or not 0 <= number <= 100 or not isinstance(reply["reason"], str) or not reply["reason"].strip():
                raise ValueError(f"Invalid probability or reason for {slot}/{row['item']}")
            key = row["issue"], row["model"], row["draw"]
            arm = row["arm"]
            if arm in cases[key] or arm not in ARMS:
                raise ValueError(f"Invalid condition for {key}")
            cases[key][arm] = (number, row)
    result = []
    for issue, models in sorted(truth.items()):
        for model, outcome in sorted(models.items()):
            edit = edits[f"{issue}-{model}"]
            for draw in DRAWS:
                items = cases[issue, model, draw]
                if set(items) != set(ARMS) or len({(r["core_sha256"], r["item"], r["block"]) for _,r in items.values()}) != 1:
                    raise ValueError(f"Core data, candidate or block differs between conditions: {issue}/{model}/{draw}")
                different = items["full"][1]["shown_note_sha256"] != items["stripped"][1]["shown_note_sha256"]
                result.append(dict(issue=issue, model=model, draw=draw, benchmark_passed=bool(outcome["resolved"]),
                                   note_changed=different, inseparable_scope=edit["inseparable_scope"],
                                   scores={arm:items[arm][0] for arm in ARMS}))
    return result


def acceptance(rows):
    return {"decisions": len(rows), "issues": len({r["issue"] for r in rows}),
            "accepted": {a: sum(r["scores"][a] >= THRESHOLD for r in rows) for a in ARMS}}


def compare(rows, left="full", right="stripped"):
    flips = {"left_only": [], "right_only": []}
    for r in rows:
        a, b = (r["scores"][arm] >= THRESHOLD for arm in (left, right))
        if a != b:
            flips["left_only" if a else "right_only"].append([r["issue"], r["model"], r["draw"]])
    delta = len(flips["left_only"]) - len(flips["right_only"])
    return {"conditions": [left, right], **acceptance(rows), **flips,
            "flip_issue_counts": {key:len({x[0] for x in values}) for key,values in flips.items()},
            "signed_left_minus_right_pp": 100 * delta / len(rows) if rows else None,
            "absolute_gap_pp": 100 * abs(delta) / len(rows) if rows else None}


def regrade(rows):
    groups = defaultdict(dict)
    for r in rows:
        groups[r["issue"],r["model"]][r["draw"]] = r["scores"]
    out = {}
    for a in ARMS:
        changed = [list(k) for k,d in groups.items() if (d[1][a] >= THRESHOLD) != (d[2][a] >= THRESHOLD)]
        out[a] = {"patches": len(groups), "disagreements": len(changed), "changed_patches": changed}
    return out


def matched_count(rows, arm):
    # Assign fractional weight to tied scores crossing rank eight.
    scores = [r["scores"][arm] for r in rows]
    cutoff = sorted(scores,reverse=True)[7]
    weight = (8 - sum(s > cutoff for s in scores)) / scores.count(cutoff)
    selected_failing = sum((1 if s > cutoff else weight if s == cutoff else 0)
                           for r,s in zip(rows,scores) if not r["benchmark_passed"])
    return {"selected":8, "boundary_score":cutoff, "number_tied_at_boundary":scores.count(cutoff),
            "weight_per_boundary_patch":weight, "benchmark_failing_selected":selected_failing}


def cluster_interval(failing):
    # Enumerate the distribution of the sum of eight independent cluster resamples.
    issue_net = Counter()
    for r in failing:
        issue_net[r["issue"]] += int(r["scores"]["full"] >= THRESHOLD) - int(r["scores"]["stripped"] >= THRESHOLD)
    distribution = {0:1}
    for _ in issue_net:
        next_counts = Counter()
        for old, count in distribution.items():
            for change in issue_net.values():
                next_counts[old+change] += count
        distribution = next_counts
    def quantile(numerator):
        cumulative = 0
        for total,count in sorted(distribution.items()):
            cumulative += count
            if cumulative * 1000 >= numerator * sum(distribution.values()):
                return 100 * total / len(failing)
        raise AssertionError("Unexpected quantile")
    return {"method":"Exact percentile distribution, resampling whole issues with replacement and keeping both draws",
            "metric":"full minus stripped percentage points for benchmark-failing patches",
            "clusters":len(issue_net), "percentile_2_5":quantile(25), "percentile_97_5":quantile(975)}


def analyze(rows):
    failing = [r for r in rows if not r["benchmark_passed"]]
    passing = [r for r in rows if r["benchmark_passed"]]
    per_draw = {}
    for draw in DRAWS:
        current = [r for r in rows if r["draw"] == draw]
        fail = [r for r in current if not r["benchmark_passed"]]
        per_draw[draw] = {"failing":compare(fail), "passing":acceptance([r for r in current if r["benchmark_passed"]]),
                          "overall":acceptance(current), "matched_top_eight":{a:matched_count(current,a) for a in ARMS}}
    return {"credit_threshold":THRESHOLD, "primary_failing_full_vs_stripped":compare(failing),
            "cluster_interval":cluster_interval(failing), "passing":acceptance(passing), "overall":acceptance(rows),
            "companion_failing_full_vs_none":compare(failing,"full","none"),
            "companion_failing_stripped_vs_none":compare(failing,"stripped","none"), "by_draw":per_draw,
            "regrade_disagreement":{k:regrade(v) for k,v in [("failing",failing),("passing",passing),("overall",rows)]},
            "changed_note_failing":compare([r for r in failing if r["note_changed"]]),
            "changed_note_clean_scope_failing":compare([r for r in failing if r["note_changed"] and not r["inseparable_scope"]]),
            "inseparable_scope_failing":compare([r for r in failing if r["inseparable_scope"]]),
            "per_patch_per_draw":rows,
            "limits":"Eight selected issues with opposite historical benchmark outcomes per pair. Two ratings per patch and condition share a model family and block context. The descriptive cluster interval captures within-sample issue variability; it does not account for shared reviewer or selection effects. Benchmark passage does not establish complete correctness. No training or deployment inference."}


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    results = analyze(load_grades(args.root))
    (args.root/"results.json").write_text(json.dumps(results,indent=2)+"\n")
