"""
load stave data and prepare document pairs for Mturk annotation
"""
import itertools
import hashlib
from argparse import ArgumentParser
from typing import Dict, Iterator
from itertools import combinations
from pathlib import Path
from tqdm import tqdm

import sqlite3
from tinydb import TinyDB, where

from forte.data.data_pack import DataPack
from forte.data.multi_pack import MultiPack
from ft.onto.base_ontology import Sentence

from amt_data_utils import custom_sort


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
        yield value[0]


def load_packs(stave_db_path: str):
    """
    read all the data packs from the stave db
    """
    conn = sqlite3.connect(stave_db_path)
    cursor = conn.cursor()
    for value in cursor.execute("SELECT textPack FROM nlpviewer_backend_document"):
        yield value[0]


def get_pack_dict(packs: Iterator[str]) -> Dict[str, DataPack]:
    name2pack = {}
    for pack_str in packs:
        pack = DataPack.deserialize(pack_str)
        name2pack[pack.pack_name] = pack
    return name2pack


def get_multipack_dict(multipacks: Iterator[str]) -> Dict[str, MultiPack]:
    name2mp = {}
    for mp_str in multipacks:
        mp = MultiPack.deserialize(mp_str)
        name2mp[mp.pack_name] = mp
    return name2mp


def isAssigned(doc_group, round_table):
    for doc1, doc2 in itertools.combinations(doc_group, 2):
        mp_name = "pair_%s_and_%s" % (doc1, doc2)
        result = round_table.search(where("name") == mp_name)
        if len(result) == 0:
            return False
    return True


def read_packs_dir(dir_path: str) -> Dict[str, DataPack]:
    name2pack = {}
    for pack_path in tqdm(dir_path.iterdir()):
        with open(pack_path, "r") as rf:
            pack: DataPack = DataPack.deserialize(rf.read())
            name2pack[pack.pack_name] = pack
    return name2pack


def assign_rounds(args):
    # loading files from multidoc stave db
    multipacks = load_multipacks(args.stave_db_path)
    name2mp = get_multipack_dict(multipacks)
    datapacks = load_packs(args.stave_db_path)
    name2pack = get_pack_dict(datapacks)

    doc_groups = []
    with open(args.doc_clusters, "r") as rf:
        for line in rf:
            splits = line.strip().split()
            doc_groups.append(splits)
    all_datapacks = read_packs_dir(args.packs)
    # sort document groups to prioritize document pairs for annotation
    sorted_groups = sorted(doc_groups, key=lambda x: custom_sort(x, all_datapacks))

    mturk_db = TinyDB(args.mturk_db_path)
    round_table = mturk_db.table("round_doc", cache_size=0)

    if len(round_table.all()) == 0:
        lastRound = 0
    else:
        lastRound = round_table.all()[-1]["round_assigned"]
    nextRound = lastRound + 1
    round_count, group_count = 0, 0

    for doc_group in sorted_groups:
        if len(doc_group) >= 4:
            continue

        if isAssigned(doc_group, round_table):
            # doc_group already assigned
            continue

        for doc1, doc2 in combinations(doc_group, 2):
            mp_name = "pair_%s_and_%s" % (doc1, doc2)
            assert mp_name in name2mp, "multipack is missing the DB"

        for doc1, doc2 in combinations(doc_group, 2):
            sent_count = len(list(name2pack[doc1].get(Sentence))) + len(list(name2pack[doc2].get(Sentence)))
            reward = get_reward(sent_count)
            mp_name = "pair_%s_and_%s" % (doc1, doc2)
            hashed = hashlib.sha256(str.encode(mp_name)).hexdigest()
            round_table.insert(
                {
                    "name": mp_name,
                    "hashed": hashed,
                    "round_assigned": nextRound,
                    "reward": reward,
                    "num_sentences": sent_count,
                }
            )
        # added new group
        group_count += 1
        if group_count >= args.ngroups:
            nextRound += 1
            round_count += 1
            group_count = 0

        if round_count >= args.nrounds:
            break

    return


if __name__ == "__main__":
    parser = ArgumentParser(description="load stave db, and prepare mturk db")
    parser.add_argument("stave_db_path", type=str, help="path to stave sqlite database (multidoc)")
    parser.add_argument("mturk_db_path", type=str, help="path to mturk annotator module")
    parser.add_argument("packs", type=Path, help="path to machine tagged packs")
    parser.add_argument("doc_clusters", type=str, help="path to list of document groups")
    parser.add_argument("-nrounds", type=int, help="number of rounds to assign")
    parser.add_argument("-ngroups", type=int, help="number of document groups per round")
    args = parser.parse_args()

    assign_rounds(args)
