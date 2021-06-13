import json
from pathlib import Path
from argparse import ArgumentParser
from typing import List
from copy import deepcopy


def load_adjudicator_labels(adjudicator_path: Path):
    # adjudicator correction (stage 1 and stage 2)
    data = []
    with open(adjudicator_path, "r") as rf:
        data = json.load(rf)

    adjudicator_labels = []
    for x in data:
        if "corrected_label" in x:
            if x["coref_ann"] == "A25XQ0GFZ57PPU":
                continue
            adjudicator_labels += [
                {
                    "doc_pair": x["doc_pair"],
                    "sentences": x["sentences"],
                    "coref_ann": [x["coref_ann"]],
                    "adjudicator_label": x["corrected_label"],
                }
            ]
        elif x["label"] == "vague" and x["adjudicator_label"] != "":
            adjudicator_labels += [
                {
                    "doc_pair": x["doc_pair"],
                    "sentences": x["sentences"],
                    "coref_ann": x["coref_ann"],
                    "adjudicator_label": x["adjudicator_label"],
                }
            ]

    return adjudicator_labels


if __name__ == "__main__":
    parser = ArgumentParser(description="prepare adjudicator labels for vague links")
    parser.add_argument("adjudicator_path", type=Path, help="path to adjudicator labels")
    parser.add_argument("out", type=Path, help="path to output adjudicator labels")

    args = parser.parse_args()

    adjudicator_labels = load_adjudicator_labels(args.adjudicator_path)

    with open(args.out, "w") as wf:
        json.dump(adjudicator_labels, wf, indent=2)
