"""Recount the 64 recorded decisions and eight order-consistent issue labels."""
from collections import Counter
import json
from pathlib import Path

issues = json.loads(Path(__file__).with_name("eight-issue-choices.json").read_text())["issues"]
arms = ("base", "selected", "with_report", "tail")
raw = {arm: Counter() for arm in arms}
stable = {arm: Counter() for arm in arms}


def canonical(order, choice):
    return {"first": order[0], "second": order[1], "abstain": "-"}[choice]


def outcome(pick, benchmark_winner):
    if pick == "-":
        return "abstain"
    return "winner" if pick == benchmark_winner else "loser"


print("Issue\t" + "\t".join(arms))
for issue in issues:
    winner = issue["benchmark_winner"]
    row = []
    for arm in arms:
        picks = issue["choices"][arm]
        if set(picks) != {"AB", "BA"}:
            raise ValueError(f"Missing presentation order for {issue['issue']}, {arm}")
        ab, ba = [canonical(order, picks[order]) for order in ("AB", "BA")]
        raw[arm].update(outcome(pick, winner) for pick in (ab, ba))
        both = ab if ab == ba else "-"
        stable[arm][outcome(both, winner)] += 1
        row.append(both)
    print(issue["issue"] + "\t" + "\t".join(row))

for label, counts in (("Reading", raw), ("Issue", stable)):
    print(f"\n{label}\tbenchmark winner\tbenchmark loser\tabstained")
    for arm, count in counts.items():
        print(arm, count["winner"], count["loser"], count["abstain"], sep="\t")
