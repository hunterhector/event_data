"""
load stave data and prepare document pairs for Mturk annotation
"""
import sys, os
import hashlib
from argparse import ArgumentParser
from collections import Counter, defaultdict
import re
from typing import List, Dict
import numpy as np
from itertools import combinations
import json

import sqlite3
from tinydb import TinyDB, where

from forte.data.data_pack import DataPack
from ft.onto.base_ontology import Sentence


def get_reward(sent_count):
    if sent_count <= 25:
        return 2.3
    elif sent_count <= 40:
        return 2.48
    elif sent_count <= 60:
        return 2.68
    else:
        return 2.91


def load_multipacks(stave_db_path: str):
    """
    read all the multipacks from the stave db
    """
    conn = sqlite3.connect(stave_db_path)
    cursor = conn.cursor()
    for value in cursor.execute("SELECT textPack FROM nlpviewer_backend_crossdoc"):
        yield json.loads(value[0])


def load_packs(stave_db_path: str):
    """
    read all the data packs from the stave db
    """
    conn = sqlite3.connect(stave_db_path)
    cursor = conn.cursor()
    for value in cursor.execute("SELECT textPack FROM nlpviewer_backend_document"):
        yield json.loads(value[0])


def get_datapack_stats(datapacks: List[Dict]) -> Dict[str, int]:
    name2count = {}
    for pack_dict in datapacks:
        pack: DataPack = DataPack.deserialize(json.dumps(pack_dict))
        sent_count = len(list(pack.get(Sentence)))
        pack_name = pack_dict["py/state"]["_meta"]["py/state"]["pack_name"]
        name2count[pack_name] = sent_count

    return name2count


def get_doc_groups(multipacks) -> List:
    """ load all multipacks and reconstruct document groups """

    doc2index = {}
    index2doc = defaultdict(set)
    mp_names = {}
    name2pack = {}

    for mp in multipacks:
        name = mp["py/state"]["_meta"]["py/state"]["pack_name"]
        name2pack[name] = mp
        s = re.search(r"pair_([0-9]+)_and_([0-9]+)", name)
        doc1, doc2 = s.group(1), s.group(2)
        mp_names[(doc1, doc2)] = name

        if doc1 not in doc2index and doc2 not in doc2index:
            doc2index[doc1] = len(doc2index)
            doc2index[doc2] = doc2index[doc1]
        elif doc2 not in doc2index:
            doc2index[doc2] = doc2index[doc1]
        elif doc1 not in doc2index:
            doc2index[doc1] = doc2index[doc2]

        index2doc[doc2index[doc1]].add(doc1)
        index2doc[doc2index[doc2]].add(doc2)

    doc_groups = []
    for _, docs in index2doc.items():
        doc_groups.append([])
        for d1, d2 in combinations(list(docs), 2):
            pack_name = mp_names.get((d1, d2), None)
            if pack_name == None:
                pack_name = mp_names[(d2, d1)]
            doc_groups[-1].append(pack_name)

    return doc_groups, name2pack


def get_next_round(n):
    if int(n) % 2 == 0:
        if (n * 10) % 10 == 1:
            return int(n) + 0.2
        else:
            return int(n) + 1
    else:
        return int(n) + 1 + 0.1


def assign_rounds(stave_db_path: str, mturk_db_path: str):
    multipacks = load_multipacks(stave_db_path)
    datapacks = load_packs(stave_db_path)
    pack2sents = get_datapack_stats(datapacks)

    mturk_db = TinyDB(mturk_db_path)

    # assign round for new document pairs
    # we used a fixed schema for assigning document pairs to rounds

    # identify the last assigned round
    table = mturk_db.table("round_doc", cache_size=0)
    pairs_assigned = table.search(where("round_assigned") != -1)
    round_nums = [elm["round_assigned"] for elm in pairs_assigned]

    # sanity check, we schedule 6/9/12 pairs per round. It can be 3 if documents are limited
    if len(round_nums) > 0:
        for elm, c in Counter(round_nums).items():
            assert c in [3, 6, 9, 12], f"error! round {elm} has {c} pairs"
        most_recent_round = sorted(round_nums)[-1]
        most_recent_count = len(
            table.search(where("round_assigned") == most_recent_round)
        )
        if most_recent_count < 6:
            next_round = most_recent_round
            next_round_count = most_recent_count
        else:
            next_round = get_next_round(most_recent_round)
            next_round_count = 0
    else:
        most_recent_round = 0
        next_round = get_next_round(most_recent_round)
        next_round_count = 0

    all_groups, name2pack = get_doc_groups(multipacks)

    while True:
        # assigning next rounds using all the remaining available documents
        # identify partially annotated (1 < anns < 3) pairs from last round
        partial_pairs = table.search(
            (where("round_assigned") == most_recent_round)
            & (where("annotation_index") < 3)
        )
        for doc_pair in partial_pairs:
            s = re.search(r"pair_([0-9]+)_and_([0-9]+)", doc_pair["name"])
            doc1, doc2 = s.group(1), s.group(2)
            sent_count = pack2sents[doc1] + pack2sents[doc2]
            reward = get_reward(sent_count)
            table.insert(
                {
                    "name": doc_pair["name"],
                    "hashed": doc_pair["hashed"],
                    "round_assigned": next_round,
                    "annotation_index": doc_pair["annotation_index"] + 1,
                    "pack_names": doc_pair["pack_names"],
                    "reward": reward,
                    "num_sentences": sent_count,
                }
            )
            next_round_count += 1

        if next_round_count >= 6:
            # finished next round assignment
            most_recent_round = next_round
            next_round = get_next_round(next_round)
            next_round_count = 0
            continue

        assigned_multipacks = [
            elm["name"] for elm in table.search(where("name").exists())
        ]

        if len(set(assigned_multipacks)) == len(name2pack):
            # exhausted documents
            break

        # identify unassigned and unannotated pairs
        def is_unassigned(db_table, names):
            unassigned = True
            for n in names:
                if len(db_table.search(where("name") == n)) > 0:
                    unassigned = False
            return unassigned

        for doc_group in all_groups:
            if is_unassigned(table, doc_group):
                for name in doc_group:
                    mp = name2pack[name]
                    pack_names = mp["py/state"]["_pack_names"]
                    hashed = hashlib.sha256(str.encode(name)).hexdigest()
                    s = re.search(r"pair_([0-9]+)_and_([0-9]+)", name)
                    doc1, doc2 = s.group(1), s.group(2)
                    sent_count = pack2sents[doc1] + pack2sents[doc2]
                    reward = get_reward(sent_count)
                    table.insert(
                        {
                            "name": name,
                            "hashed": hashed,
                            "round_assigned": next_round,
                            "annotation_index": 1,
                            "pack_names": pack_names,
                            "reward": reward,
                            "num_sentences": sent_count,
                        }
                    )
                    next_round_count += 1

                # finished next round
                # assigning a maximum of one new group per round
                most_recent_round = next_round
                next_round = get_next_round(next_round)
                next_round_count = 0
                break


if __name__ == "__main__":
    parser = ArgumentParser(description="load stave db, and prepare mturk db")
    parser.add_argument("stave_db_path", type=str, help="path to stave sqlite database")
    parser.add_argument(
        "mturk_db_path", type=str, help="path to mturk annotator module"
    )
    args = parser.parse_args()

    assign_rounds(args.stave_db_path, args.mturk_db_path)
