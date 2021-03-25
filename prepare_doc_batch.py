import json
import argparse
from pathlib import Path
import shutil
from itertools import combinations
import numpy as np
from tqdm import tqdm
from typing import Dict

from tinydb import TinyDB, where

from forte.data.data_pack import DataPack
from ft.onto.base_ontology import Sentence

from edu.cmu import EventMention


def read_packs(dir_path: Path) -> Dict[str, DataPack]:
    name2pack = {}
    for pack_path in tqdm(dir_path.iterdir()):
        with open(pack_path, "r") as rf:
            pack: DataPack = DataPack.deserialize(rf.read())
            name2pack[pack.pack_name] = pack
    return name2pack


def custom_sort(doc_group, name2pack):
    doc2sents = {}
    doc2events = {}
    for doc in doc_group:
        events = [x.text for x in name2pack[doc].get(EventMention)]
        sents = [x.text for x in name2pack[doc].get(Sentence)]
        doc2sents[doc] = sents
        doc2events[doc] = events

    event_counts, sent_counts, event_overlap = [], [], []
    for doc1, doc2 in combinations(doc_group, 2):
        event_counts.append(len(doc2events[doc1]) + len(doc2events[doc2]))
        sent_counts.append(len(doc2sents[doc1]) + len(doc2sents[doc2]))
        event_overlap.append(
            len([x for x in doc2events[doc1] if x in doc2events[doc2]])
        )

    return (np.mean(event_counts), np.mean(sent_counts), 1 / np.mean(event_overlap))


def prepare_batch(args):

    db = TinyDB(args.pack_db)
    complete_table = db.table("complete_table", cache_size=0)
    incorrect_table = db.table("incorrect_table", cache_size=0)
    ongoing_table = db.table("ongoing_table", cache_size=0)

    if len(ongoing_table) >= args.count:
        print(f"{len(ongoing_table)} documents are pending!")
        return

    # read document groups
    doc_groups = []
    with open(args.doc_clusters, "r") as rf:
        for line in rf:
            splits = line.strip().split()
            doc_groups.append(splits)

    # read (machine tagged) packs
    name2pack = read_packs(args.packs)

    # sort document groups to prioritize docs for event correction
    sorted_groups = sorted(doc_groups, key=lambda x: custom_sort(x, name2pack))
    with open(args.out, "w") as wf:
        for g in sorted_groups:
            wf.write(" ".join(g) + "\n")

    for g in sorted_groups:
        for doc in g:
            if len(ongoing_table) >= args.count:
                print(f"{len(ongoing_table)} documents are pending!")
                return

            result = complete_table.search(where("pack_name") == doc)
            if len(result) > 0:
                # document already corrected
                continue
            result = ongoing_table.search(where("pack_name") == doc)
            if len(result) > 0:
                # already in current tasks
                continue
            result = incorrect_table.search(where("pack_name") == doc)
            if len(result) > 0:
                # mistakes, need additional correction
                ongoing_table.insert({"pack_name": doc})
                continue
            ongoing_table.insert({"pack_name": doc})

    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="prepare a batch of Wikinews documents for event correction"
    )
    parser.add_argument("-packs", type=Path, help="path to machine tagged packs")
    parser.add_argument("-doc_clusters", help="path to document clusters")
    parser.add_argument(
        "-pack_db", help="path to tinydb that keeps track of corrected docs"
    )
    parser.add_argument(
        "-count",
        default=20,
        type=int,
        help="max docs to include for each batch of event correction",
    )
    parser.add_argument("-out", help="write sorted document groups")

    args = parser.parse_args()
    prepare_batch(args)
