import json
from pathlib import Path
from argparse import ArgumentParser
from typing import List
from copy import deepcopy


def load_amt_labels(amt_dir: Path):
    all_anns = []
    with open(amt_dir / "full.json", "r") as rf:
        data = json.load(rf)
        for x in data:
            y = deepcopy(x)
            y.update({"label": "full"})
            all_anns += [y]

    with open(amt_dir / "partial.json", "r") as rf:
        data = json.load(rf)
        for x in data:
            y = deepcopy(x)
            y.update({"label": "partial"})
            all_anns += [y]

    with open(amt_dir / "vague.json", "r") as rf:
        data = json.load(rf)
        for x in data:
            y = deepcopy(x)
            y.update({"label": "vague"})
            all_anns += [y]

    return all_anns


def load_adjudicator_labels(adjudicator_paths: List[Path]):
    data = []
    for file_path in adjudicator_paths:
        with open(file_path, "r") as rf:
            data += json.load(rf)

    adjudicator_labels = {}
    for x in data:
        adjudicator_labels[(x["doc_pair"], x["sentences"][0], x["sentences"][1], x["coref_ann"][0])] = x[
            "adjudicator_label"
        ]

    return adjudicator_labels


def add_adj_labels(all_anns, adjudicator_labels):
    updated_anns = deepcopy(all_anns)
    update_count = 0
    for x in updated_anns:
        if len(x["coref_ann"]) == 1:
            entry = (x["doc_pair"], x["sentences"][0], x["sentences"][1], x["coref_ann"][0])
            if entry in adjudicator_labels:
                assert x["label"] == "vague"
                if adjudicator_labels[entry] in ["full", "partial", "null"]:
                    x["label"] = adjudicator_labels[entry]
                    x["adjudicator_label"] = adjudicator_labels[entry]
                    update_count += 1
    print("updated %d labels" % update_count)
    return updated_anns


if __name__ == "__main__":
    parser = ArgumentParser(description="add adjudicator labels for vague links")
    parser.add_argument("amt_path", type=Path, help="path to amt labels")
    parser.add_argument("adjudicator_paths", nargs="+", type=Path, help="path(s) to adjudicator labels")

    args = parser.parse_args()

    all_anns = load_amt_labels(args.amt_path)
    adjudicator_labels = load_adjudicator_labels(args.adjudicator_paths)
    updated_anns = add_adj_labels(all_anns, adjudicator_labels)

    sorted_updated_anns = sorted(updated_anns, key=lambda x: (x["doc_pair"], x["mention_spans"]))

    with open(args.amt_path / "combined.json", "w") as wf:
        json.dump(sorted_updated_anns, wf, indent=2)
