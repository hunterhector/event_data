"""
Read the CDEC dataset from Stave SQL database and generate statistics to display in streamlit app
Adapted from processors/stat_collector.py, that generates inputs for MACE algorithm
"""

import argparse
import re
from pathlib import Path
from typing import List, Dict, Tuple
import json
import csv
from tinydb import TinyDB

from forte.pipeline import Pipeline
from forte.data.data_pack import DataPack
from forte.data.multi_pack import MultiPack
from forte.processors.base import MultiPackProcessor
from forte.data.readers.stave_readers import StaveMultiDocSqlReader
from ft.onto.base_ontology import CrossDocEventRelation, Token, Sentence

from edu.cmu import EventMention, CrossEventRelation, CorefQuestion


class CorefEventCollector(MultiPackProcessor):

    IGNORE_ANNOTATORS = ["adithya", "A2FA52DZEKT1A6", "A9ITQZP6TDLLC", "A3I2PT6W0FP7BR"]
    COREF_QUESTIONS = [
        [
            "Place: Do you think the two events happen at the same place?",
            ["Exactly the same", "The places overlap", "Not at all", "Cannot determine",],
        ],
        [
            "Time: Do you think the two events happen at the same time?",
            ["Exactly the same", "They overlap in time", "Not at all", "Cannot determine",],
        ],
        [
            "Participants: Do you think the two events have the same participants?",
            ["Exactly the same", "They share some participants", "Not at all", "Cannot determine",],
        ],
        [
            "Inclusion: Do you think one of the events is part of the other?",
            [
                "Yes, the left event is part of right one",
                "Yes, the right event is part of left one",
                "No, they are exactly the same",
                "Cannot determine",
            ],
        ],
    ]

    def __init__(self, mturk_db_path: str, out_path: Path):
        super().__init__()
        self.documents: Dict[int, DataPack] = {}
        self.events: Dict[Tuple[int, int], EventMention] = {}
        self.event_sents: Dict[Tuple[int, int], Sentence] = {}
        self.event_pair_indices: List[Tuple[str, Tuple[int, int], Tuple[int, int]]] = []
        self.mturk_db_path = mturk_db_path
        self.out_path = out_path

        self.collect_meta()

    def collect_meta(self):
        # loading list of (relevant) document pairs, and corresponding annotators
        annotators = set()
        pairs = []
        hash2name = {}

        db = TinyDB(self.mturk_db_path)
        round_doc_table = db.table("round_doc")
        for doc_pair in round_doc_table.all():
            hash2name[doc_pair["hashed"]] = doc_pair["name"]
        past_tasks_table = db.table("past_tasks")
        for task in past_tasks_table.all():
            if "annotators" in task:
                annotators.update(task["annotators"])
                pairs.append(hash2name[task["hash_pair"]])

        self.relevant_annotators = annotators
        self.relevant_doc_pairs = pairs

    def _load_mentions(self, input_pack: MultiPack, mention: EventMention, pack_id, mention_id):

        # get DataPack
        if pack_id not in self.documents:
            doc: DataPack = input_pack.get_pack_at(input_pack.get_pack_index(str(pack_id)))
            self.documents[pack_id] = doc

        # get EventMention
        event_id = (pack_id, mention_id)
        if event_id not in self.events:
            self.events[event_id] = mention

        # get Sentence
        doc = self.documents[pack_id]
        mention = self.events[event_id]
        for sent in doc.get(Sentence):
            if (sent.span.begin <= mention.span.begin) and (sent.span.end >= mention.span.end):
                self.event_sents[event_id] = sent

        return

    def _process(self, input_pack: MultiPack):
        for stave_annotator in input_pack.get_all_creator():
            annotator = re.search(r"^stave\.(.*)$", stave_annotator).group(1)
            if annotator not in self.relevant_annotators or annotator in self.IGNORE_ANNOTATORS:
                print("skipping annotations of worker: %s" % annotator)
                continue

            for relation in input_pack.get(CrossEventRelation, stave_annotator):
                if relation.rel_type != "coref":
                    continue

                self._load_mentions(
                    input_pack, relation.get_parent(), relation.parent_pack_id(), relation.parent_id()
                )
                self._load_mentions(
                    input_pack, relation.get_child(), relation.child_pack_id(), relation.child_id()
                )

                pair_name = "pair_%s_and_%s" % (
                    self.documents[relation.parent_pack_id()].pack_name,
                    self.documents[relation.child_pack_id()].pack_name,
                )
                if pair_name not in self.relevant_doc_pairs:
                    print("skipping document pair: %s" % pair_name)
                    continue

                self.event_pair_indices.append(
                    (
                        annotator,
                        (relation.parent_pack_id(), relation.parent_id()),
                        (relation.child_pack_id(), relation.child_id()),
                        relation.coref_questions,
                        relation.coref_answers,
                    )
                )

    def _get_ann_sent(self, sent: Sentence, mention: EventMention) -> str:
        begin = mention.span.begin - sent.span.begin
        end = mention.span.end - sent.span.begin
        sent_str = sent.text[:begin] + "<E> " + sent.text[begin:end] + " </E>" + sent.text[end:]
        return sent_str

    def finish(self, _):
        """
        Write the CDEC dataset in XML format
        """
        self.out_path.mkdir(exist_ok=True, parents=True)

        # add relations, cross_doc_coref
        coref_links = {}
        for (
            ann,
            parent_event_tuple,
            child_event_tuple,
            coref_questions,
            coref_answers,
        ) in self.event_pair_indices:
            parent_mention: EventMention = self.events[parent_event_tuple]
            child_mention: EventMention = self.events[child_event_tuple]

            parent_pack_id, parent_mention_id = parent_event_tuple
            child_pack_id, child_mention_id = child_event_tuple
            parent_doc_name = self.documents[parent_pack_id].pack_name
            child_doc_name = self.documents[child_pack_id].pack_name

            pair_name = "pair_%s_and_%s" % (parent_doc_name, child_doc_name)
            mention_pair_id = f"{parent_pack_id}_{parent_mention_id}_{child_pack_id}_{child_mention_id}"
            if pair_name not in coref_links:
                coref_links[pair_name] = {}
                coref_links[pair_name]["annotators"] = set()
                coref_links[pair_name]["links"] = {}

            if mention_pair_id not in coref_links[pair_name]["links"]:
                info = {}
                # TODO: show event mentions in sentence context
                info["event1"] = self._get_ann_sent(self.event_sents[parent_event_tuple], parent_mention)
                info["event2"] = self._get_ann_sent(self.event_sents[child_event_tuple], child_mention)
                info["annotators"] = []
                coref_links[pair_name]["links"][mention_pair_id] = info

            coref_links[pair_name]["annotators"].add(ann)
            coref_links[pair_name]["links"][mention_pair_id]["annotators"].append([ann, coref_answers])

        coref_links_out = {}
        for pair_name, content in coref_links.items():
            coref_links_out[pair_name] = {}
            coref_links_out[pair_name]["annotators"] = list(content["annotators"])
            out_links = []
            for mention_pair_id, link in content["links"].items():
                out_links.append(
                    {"event1": link["event1"], "event2": link["event2"], "annotators": link["annotators"]}
                )
            coref_links_out[pair_name]["links"] = out_links

        coref_links_path = f"{self.out_path}/coref_links.json"
        print(f"writing coref links to {coref_links_path}")
        with open(coref_links_path, "w") as wf:
            json.dump(coref_links_out, wf, indent=2)

        coref_links_path = f"{self.out_path}/coref_links.tsv"
        print(f"writing coref links to {coref_links_path}")
        # print(len(coref_questions))
        # print(coref_questions.get(CorefQuestion))
        # print(coref_questions.get(0).options)
        with open(coref_links_path, "w") as wf:
            csvwriter = csv.writer(wf, delimiter="\t")
            csvwriter.writerow(
                [
                    "Document pair",
                    "Annotator",
                    "Event 1",
                    "Event 2",
                    self.COREF_QUESTIONS[0][0],
                    self.COREF_QUESTIONS[1][0],
                    self.COREF_QUESTIONS[2][0],
                    self.COREF_QUESTIONS[3][0],
                ]
            )
            for pair_name, content in coref_links_out.items():
                for link in content["links"]:
                    for ann, coref_answers in link["annotators"]:
                        csvwriter.writerow(
                            [
                                pair_name,
                                ann,
                                link["event1"],
                                link["event2"],
                                self.COREF_QUESTIONS[0][1][coref_answers[0]],
                                self.COREF_QUESTIONS[1][1][coref_answers[1]],
                                self.COREF_QUESTIONS[2][1][coref_answers[2]],
                                self.COREF_QUESTIONS[3][1][coref_answers[3]],
                            ]
                        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stave_db", type=str)
    parser.add_argument("mturk_db", type=str)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()

    pipeline = Pipeline()
    pipeline.set_reader(StaveMultiDocSqlReader(), config={"stave_db_path": args.stave_db})
    pipeline.add(CorefEventCollector(args.mturk_db, args.out_dir))

    pipeline.run()
