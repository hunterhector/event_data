import argparse
import json
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="prepare coreference labels")
    parser.add_argument("-raw_json", type=Path, help="combined.json")
    parser.add_argument("-out", type=Path, help="output coreference labels")

    args = parser.parse_args()

    with open(args.raw_json, "r") as rf:
        data = json.load(rf)

    coreference_data = []
    for x in data:
        if x["label"] == "full" or x["label"] == "partial":
            coreference_data += [
                {
                    "mention_spans": x["mention_spans"],
                    "mention_txt": x["mention_txt"],
                    "sentences": x["sentences"],
                    "label": "coreference",
                }
            ]

    with open(args.out, "w") as wf:
        json.dump(coreference_data, wf, indent=2)
