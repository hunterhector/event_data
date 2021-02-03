import json
import sys
import argparse
from pathlib import Path
import shutil


def prepare_dir(args):

    all_docs = set()
    with open(args.doc_clusters, "r") as rf:
        for line in rf:
            splits = line.strip().split()
            all_docs.update(splits)

    with open(args.wikinews, "r") as rf:
        data = json.load(rf)

    id2page = {}
    for page in data:
        id2page[page["id"]] = page

    args.out.mkdir(exist_ok=True)
    batch_json_path = args.out / "json"
    batch_json_path.mkdir(exist_ok=True)
    batch_coling2018_path = args.out / "coling2018_out"
    batch_coling2018_path.mkdir(exist_ok=True)

    for doc_id in all_docs:
        shutil.copy(args.coling2018 / f"{doc_id}.ann", batch_coling2018_path)
        shutil.copy(args.coling2018 / f"{doc_id}.txt", batch_coling2018_path)
        with open(batch_json_path / f"{doc_id}.json", "w") as wf:
            json.dump(id2page[doc_id], wf, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="prepare a batch of Wikinews documents"
    )
    parser.add_argument(
        "--wikinews",
        type=Path,
        default="cdec_wikinews/wikinews_similar.json",
        help="path to wikinews json",
    )
    parser.add_argument(
        "--coling2018",
        type=Path,
        default="cdec_wikinews/coling2018_out",
        help="path to Araki et al. outputs on wikinews",
    )
    parser.add_argument(
        "--doc-clusters",
        type=Path,
        required=True,
        help="path to doc clusters in the batch",
    )
    parser.add_argument("--out", type=Path, help="path to write files")

    args = parser.parse_args()
    prepare_dir(args)
