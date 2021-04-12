"""
Load .sqlite3 database from Stave single document interface.
This module updates DataPacks to use expert corrected events.
"""

import sys, os
import argparse
from pathlib import Path
from typing import Iterator, List, Dict
import sqlite3
from tinydb import TinyDB
from tqdm import tqdm

sys.path.insert(0, os.path.abspath(".."))

from forte.data.data_pack import DataPack
from amt_data_utils import custom_sort


def get_pack_dict(packs: Iterator[str]) -> Dict[str, DataPack]:
    name2pack = {}
    for _, pack_str in tqdm(enumerate(packs)):
        pack = DataPack.deserialize(pack_str)
        name2pack[pack.pack_name] = pack
    return name2pack


def read_packs(dir_path: Path) -> Dict[str, DataPack]:
    name2pack = {}
    for pack_path in tqdm(dir_path.iterdir()):
        with open(pack_path, "r") as rf:
            pack: DataPack = DataPack.deserialize(rf.read())
            name2pack[pack.pack_name] = pack
    return name2pack


def get_corrected_pack(pack_name: str, stave_db_path: str, project_name: str = None) -> str:
    conn = sqlite3.connect(stave_db_path)
    cursor = conn.cursor()
    if project_name:
        # select pack_name from project_name
        result = cursor.execute(
            "SELECT * FROM nlpviewer_backend_project WHERE name=:project_name",
            {"project_name": project_name},
        ).fetchone()
        project_id = result[0]
        for value in cursor.execute(
            "SELECT textPack from nlpviewer_backend_document WHERE project_id=:id and name=:pack_name",
            {"id": project_id, "pack_name": pack_name + ".json"},
        ):
            return value[0]
    else:
        # select pack_name from entire database
        for value in cursor.execute(
            "SELECT textPack from nlpviewer_backend_document WHERE name=:pack_name",
            {"pack_name": pack_name + ".json"},
        ):
            return value[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stave_db", type=Path, help="path to read single document SQL database from stave")
    parser.add_argument("packs", type=Path, help="path to machine tagged packs")
    parser.add_argument("pack_db", type=Path, help="path to pack tinydb")
    parser.add_argument("pack_out", type=Path, help="directory path to write Packs")
    parser.add_argument("doc_clusters", type=str, help="path to list of document groups")
    parser.add_argument("ngroups", type=int, help="max number of document groups to add")
    parser.add_argument("--project-name", type=str, default=None, help="target project name in SQL database")
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing output packs")

    args = parser.parse_args()

    name2pack = read_packs(args.packs)
    doc_groups = []
    with open(args.doc_clusters, "r") as rf:
        for line in rf:
            splits = line.strip().split()
            doc_groups.append(splits)

    # sort document groups to prioritize document pairs for annotation
    sorted_groups = sorted(doc_groups, key=lambda x: custom_sort(x, name2pack))

    out_path = args.pack_out
    out_path.mkdir(exist_ok=True, parents=True)

    # only read complete(d) packs
    db = TinyDB(args.pack_db)
    table = db.table("complete_table")
    pack_names = []
    for elm in table.all():
        name = elm["pack_name"]
        pack_names.append(name)

    added = 0
    for doc_group in sorted_groups:
        completed_docs = []
        incomplete = False
        for doc in doc_group:
            if doc not in pack_names:
                # not completed
                incomplete = True
                print("event correction for doc %s is incomplete" % doc)
                break
            completed_docs.append(doc)

        if incomplete:
            print("document group %s is incomplete" % (" ".join(doc_group)))
            continue

        packFound = True
        for doc in completed_docs:
            pack = get_corrected_pack(doc, args.stave_db)
            if pack is None:
                print("document pack %s not in the database" % doc)
                packFound = False
                break

            out_path = args.pack_out / f"{doc}.json"
            if out_path.is_file() and not args.overwrite:
                print("pack %s already exists in the output folder, skipping!" % doc)
                continue
            elif args.overwrite:
                print("overwriting pack %s" % doc)

            with open(out_path, "w") as wf:
                wf.write(pack)

        if not packFound:
            print("added %d groups" % added)
            print("some packs are still missing in the database")
            break

        added += 1
        if added >= args.ngroups:
            print("added %d groups" % added)
            break
