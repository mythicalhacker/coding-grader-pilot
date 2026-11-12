"""Compare issue-level results for identical packets reviewed in two panels."""
import argparse
import json
from pathlib import Path


def hits(result, arm, metric):
    return {case for case, arms in result["cases"].items() if arms[arm][metric] == "hit"}


def compare(original, repeat):
    if original["cases"].keys() != repeat["cases"].keys():
        raise ValueError("Panels cover different issues.")
    comparison = {}
    for metric in ("primary", "secondary"):
        arms = {}
        for arm in ("commands_only", "with_notes"):
            before, after = hits(original, arm, metric), hits(repeat, arm, metric)
            arms[arm] = {
                "panel_one_total": len(before), "panel_two_total": len(after),
                "retained": sorted(before & after), "lost": sorted(before - after),
                "gained": sorted(after - before), "identical_set": before == after,
            }
        comparison[metric] = arms
    return comparison


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first_results", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = compare(json.loads(args.first_results.read_text()), json.loads((root/"results.json").read_text()))
    (root/"comparison.json").write_text(json.dumps(output, indent=2)+"\n")
    for arm, data in output["primary"].items():
        print(arm, data["panel_one_total"], data["panel_two_total"], "gained",data["gained"],"lost",data["lost"])
