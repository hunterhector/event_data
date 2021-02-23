"""
Read the CDEC dataset from Stave SQL database and generate statistics to display in streamlit app
Adapted from processors/stat_collector.py, that generates inputs for MACE algorithm
"""

import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import json
from collections import Counter

from forte.pipeline import Pipeline
from forte.data.data_pack import DataPack
from forte.data.multi_pack import MultiPack
from forte.processors.base import MultiPackProcessor
from forte.data.readers.stave_readers import StaveMultiDocSqlReader
from ft.onto.base_ontology import Token, Sentence

from edu.cmu import EventMention, CrossEventRelation


class CorefEventCollector(MultiPackProcessor):
    def __init__(self, out_path: Path = None):
        super().__init__()
        self.documents: Dict[int, DataPack] = {}
        self.events: Dict[Tuple[int, int], EventMention] = {}
        self.event_pair_indices: List[Tuple[str, Tuple[int, int], Tuple[int, int]]] = []
        self.out_path = out_path

    def _process(self, input_pack: MultiPack):
        for annotator in input_pack.get_all_creator():
            for relation in input_pack.get(CrossEventRelation, annotator):
                if relation.rel_type != "coref":
                    continue

                parent_pack_id = relation.parent_pack_id()
                parent_mention_id = relation.parent_id()
                child_pack_id = relation.child_pack_id()
                child_mention_id = relation.child_id()

                if parent_pack_id not in self.documents:
                    parent_doc: DataPack = input_pack.get_pack_at(
                        input_pack.get_pack_index(str(parent_pack_id))
                    )
                    self.documents[parent_pack_id] = parent_doc
                parent_event_id = (parent_pack_id, parent_mention_id)
                if parent_event_id not in self.events:
                    parent_mention: EventMention = relation.get_parent()
                    self.events[parent_event_id] = parent_mention

                if child_pack_id not in self.documents:
                    child_doc: DataPack = input_pack.get_pack_at(
                        input_pack.get_pack_index(str(child_pack_id))
                    )
                    self.documents[child_pack_id] = child_doc
                child_event_id = (child_pack_id, child_mention_id)
                if child_event_id not in self.events:
                    child_mention: EventMention = relation.get_child()
                    self.events[child_event_id] = child_mention

                self.event_pair_indices.append(
                    (annotator, parent_event_id, child_event_id)
                )

    def finish(self, _):
        """
        Write the CDEC dataset in XML format
        """
        if self.out_path != None:
            self.out_path.mkdir(exist_ok=True, parents=True)
            for doc_pack_id in self.documents:
                dp: DataPack = self.documents[doc_pack_id]
                file_out_path = f"{self.out_path}/{dp.pack_name}.json"
                print(f"writing to file {file_out_path}")
                doc = {}
                doc["doc_id"] = dp.pack_name
                doc["tokens"] = []
                # add tokens
                for token in dp.get(Token):
                    doc["tokens"].append(
                        {
                            "tid": len(doc["tokens"]),
                            "start": token.begin,
                            "end": token.end,
                            "text": token.text,
                        }
                    )
                # add event mentions as markables
                doc["events"] = []
                for event in dp.get(EventMention):
                    doc["events"].append(
                        {
                            "mid": len(doc["events"]),
                            "start": event.begin,
                            "end": event.end,
                            "text": event.text,
                        }
                    )
                with open(file_out_path, "w") as wf:
                    json.dump(doc, wf, indent=2)
            # add relations, cross_doc_coref
            coref_links = []
            for ann, parent_event, child_event in self.event_pair_indices:
                parent_mention: EventMention = self.events[parent_event]
                child_mention: EventMention = self.events[child_event]

                parent_pack_id, _ = parent_event
                child_pack_id, _ = child_event
                parent_doc_id = self.documents[parent_pack_id].pack_name
                child_doc_id = self.documents[child_pack_id].pack_name

                coref_links.append(
                    {
                        "doc1": parent_doc_id,
                        "doc2": child_doc_id,
                        "mention1_start": parent_mention.begin,
                        "mention1_end": parent_mention.end,
                        "mention2_start": child_mention.begin,
                        "mention2_end": child_mention.end,
                        "mention1_text": parent_mention.text,
                        "mention2_text": child_mention.text,
                        "annotator": ann,
                    }
                )
            coref_links_path = f"{self.out_path}/coref_links.json"
            print(f"writing coref links to {coref_links_path}")
            with open(coref_links_path, "w") as wf:
                json.dump(coref_links, wf, indent=2)

        db = {}
        for ann, parent_event, child_event in self.event_pair_indices:
            parent_pack_id, parent_token_id = parent_event
            child_pack_id, child_token_id = child_event
            parent_doc: DataPack = self.documents[parent_pack_id]
            child_doc: DataPack = self.documents[child_pack_id]
            parent_mention: EventMention = self.events[parent_event]
            child_mention: EventMention = self.events[child_event]

            doc_pair = f"{parent_doc.pack_name}_{child_doc.pack_name}"
            if doc_pair not in db:
                db[doc_pair] = {
                    "annotators": set(),
                    "links": [],
                    "sentences": [
                        len(list(parent_doc.get(Sentence))),
                        len(list(child_doc.get(Sentence))),
                    ],
                    "events": [
                        len(list(parent_doc.get(EventMention))),
                        len(list(child_doc.get(EventMention))),
                    ],
                }

            db[doc_pair]["annotators"].add(ann)
            db[doc_pair]["links"].append((parent_token_id, child_token_id))

        for doc_pair in db:
            db[doc_pair]["annotators"] = list(db[doc_pair]["annotators"])
            links = Counter(db[doc_pair]["links"])
            link_counts = Counter(links.values())
            db[doc_pair]["links"] = link_counts

        with open(f"{self.out_path}/db_stats.json", "w") as wf:
            json.dump(db, wf, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stave-db", type=Path)
    args = parser.parse_args()

    pipeline = Pipeline()
    pipeline.set_reader(
        StaveMultiDocSqlReader(), config={"stave_db_path": str(args.stave_db)}
    )
    pipeline.add(CorefEventCollector(Path("tmp_json")))

    pipeline.run()
