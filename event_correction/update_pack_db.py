import sys, os
from argparse import ArgumentParser
from typing import List, Iterator, Set
import sqlite3
from tqdm import tqdm

sys.path.insert(0, os.path.abspath(".."))

from tinydb import TinyDB, where
from forte.data.data_pack import DataPack
from ft.onto.base_ontology import Token, Sentence
from edu.cmu import EventMention, TitleSpan, DateSpan


def check_title(pack: DataPack) -> bool:
    """
    return False if mentions are annotated in the title
    """
    title: TitleSpan = list(pack.get(TitleSpan))[0]
    for mention in pack.get(EventMention):
        if mention.span.begin < title.span.end:
            return False
    return True


def check_mentions(pack: DataPack) -> Set[EventMention]:
    """
    return False if mention span are misaligned with token
    """
    mentions = pack.get(EventMention)
    tokens = pack.get(Token)

    begin_set, end_set = set(), set()
    for token in tokens:
        begin_set.add(token.span.begin)
        end_set.add(token.span.end

    incorrect_mentions = set()
    for mention in mentions:
        if mention.span.begin not in begin_set:
            incorrect_mentions.add(mention.text)
        if mention.span.end not in end_set:
            incorrect_mentions.add(mention.text)

    return list(incorrect_mentions)


def read_packs(stave_db_path: str) -> Iterator[DataPack]:
    conn = sqlite3.connect(stave_db_path)
    cursor = conn.cursor()

    for value in cursor.execute("SELECT textPack from nlpviewer_backend_document"):
        yield DataPack.deserialize(value[0])


if __name__ == "__main__":
    parser = ArgumentParser(description="db to keep track of corrected documents")
    parser.add_argument(
        "stave_db_path", type=str, help="path to stave single document sqlite db"
    )
    parser.add_argument(
        "datapack_db_path", type=str, help="path to tinydb for DataPack(s)"
    )

    args = parser.parse_args()

    packs = read_packs(args.stave_db_path)

    db = TinyDB(args.datapack_db_path)
    finished_table = db.table("complete_table", cache_size=0)
    incorrect_table = db.table("incorrect_table", cache_size=0)
    ongoing_table = db.table("ongoing_table", cache_size=0)

    for _, pack in tqdm(enumerate(packs)):
        finished = True

        # check for any mentions in the title
        validTitle = check_title(pack)
        if not validTitle:
            incorrect_table.upsert(
                {
                    "pack_name": pack.pack_name,
                    "error_type": "TitleMention",
                    "error": [],
                },
                where("pack_name") == pack.pack_name,
            )
            finished = False
        else:
            doc = incorrect_table.get(
                (where("pack_name") == pack.pack_name)
                & (where("error_type") == "TitleMention")
            )
            if doc:
                incorrect_table.remove(doc_ids=[doc.doc_id])

        # check for misaligned mentions in the document
        incorrect_spans = check_mentions(pack)
        if len(incorrect_spans) > 0:
            incorrect_table.upsert(
                {
                    "pack_name": pack.pack_name,
                    "error_type": "SpanMisalignment",
                    "error": incorrect_spans,
                },
                where("pack_name") == pack.pack_name,
            )
            finished = False
        else:
            doc = incorrect_table.get(
                (where("pack_name") == pack.pack_name)
                & (where("error_type") == "SpanMisalignment")
            )
            if doc:
                incorrect_table.remove(doc_ids=[doc.doc_id])

        if finished:
            event_count = len(list(pack.get(EventMention)))
            token_count = len(list(pack.get(Token)))
            sent_count = len(list(pack.get(Sentence)))
            title = list(pack.get(TitleSpan))[0].text
            date = list(pack.get(DateSpan))[0].text
            finished_table.upsert(
                {
                    "pack_name": pack.pack_name,
                    "events": event_count,
                    "sentences": sent_count,
                    "tokens": token_count,
                    "title": title,
                    "date": date,
                },
                where("pack_name") == pack.pack_name,
            )
            # remove the pack from ongoing table
            doc = ongoing_table.get(where("pack_name") == pack.pack_name)
            if doc:
                ongoing_table.remove(doc_ids=[doc.doc_id])
