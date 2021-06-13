import sys, os
import logging
import argparse
import re
from pathlib import Path
from threading import Event
from typing import List, Dict, Tuple
import json
import csv
from numpy.lib.function_base import place
from tinydb import TinyDB
import itertools
from collections import Counter, defaultdict
import numpy as np
from nltk.metrics.agreement import AnnotationTask
import krippendorff

from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, os.path.abspath(".."))

from forte.pipeline import Pipeline
from forte.data.data_pack import DataPack
from forte.data.multi_pack import MultiPack
from forte.processors.base import MultiPackProcessor
from forte.data.readers.stave_readers import StaveMultiDocSqlReader
from ft.onto.base_ontology import CrossDocEventRelation, Token, Sentence

from edu.cmu import EventMention, CrossEventRelation, CorefQuestion


class CorefEventCollector(MultiPackProcessor):

    # TODO: complete this list
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

    def __init__(
        self, mturk_db_path: str, ignore_set_path: str, out_path: Path = None, out_docs_path: Path = None
    ):
        super().__init__()
        self.documents: Dict[int, DataPack] = {}
        self.events: Dict[Tuple[int, int], EventMention] = {}
        self.event_sents = {}
        self.mention_pairs = []
        self.docpair2links = defaultdict(list)
        self.mturk_db_path = mturk_db_path
        self.ignore_set_path = ignore_set_path
        self.out_path = out_path
        self.out_docs_path = out_docs_path
        self.mention_pair_set = set()

        self.collect_meta()

    def collect_meta(self):
        # loading list of (relevant) document pairs, and corresponding annotators

        self.ignore_set = set()
        with open(self.ignore_set_path, "r") as rf:
            data = json.load(rf)
            for x in data:
                self.ignore_set.add((x["ann"], x["doc_pair"]))

        annotators = set()
        ann_pairs = defaultdict(list)
        doc_pairs = set()
        docs = set()

        hash2name = {}

        db = TinyDB(self.mturk_db_path)
        round_doc_table = db.table("round_doc")
        for doc_pair in round_doc_table.all():
            hash2name[doc_pair["hashed"]] = doc_pair["name"]
        past_tasks_table = db.table("past_tasks")
        for task in past_tasks_table.all():
            if "annotators" in task:
                annotators.update(task["annotators"])
                doc_pairs.add(hash2name[task["hash_pair"]])
                s = re.search(r"pair_([0-9]+)_and_([0-9]+)", hash2name[task["hash_pair"]])
                docs.add(s.group(1))
                docs.add(s.group(2))
                for ann in task["annotators"]:
                    if (ann, hash2name[task["hash_pair"]]) in self.ignore_set:
                        continue
                    ann_pairs[ann].append(hash2name[task["hash_pair"]])

        self.relevant_annotators = annotators
        self.relevant_doc_pairs = ann_pairs
        self.relevant_docs = docs

        logging.info(f"annotators: {len(self.relevant_annotators)}")
        logging.info(f"document pairs: {len(doc_pairs)}")
        logging.info(f"documents: {len(self.relevant_docs)}")

    def _load_doc(self, input_pack: MultiPack, pack_id):
        """ load the specified document and its events from a MultiPack """

        doc: DataPack = input_pack.get_pack_at(input_pack.get_pack_index(str(pack_id)))
        pack_name = doc.pack_name

        if pack_name not in self.relevant_docs:
            return None

        if pack_name not in self.documents:
            self.documents[pack_name] = doc
            for mention_ in doc.get(EventMention):
                self.events[(pack_name, mention_.span.begin, mention_.span.end)] = mention_
                for sent in doc.get(Sentence):
                    if (sent.span.begin <= mention_.span.begin) and (sent.span.end >= mention_.span.end):
                        self.event_sents[(pack_name, mention_.span.begin, mention_.span.end)] = sent

        return doc

    def _process(self, input_pack: MultiPack):
        for stave_annotator in input_pack.get_all_creator():
            annotator = re.search(r"^stave\.(.*)$", stave_annotator).group(1)
            if annotator not in self.relevant_annotators or annotator in self.IGNORE_ANNOTATORS:
                logging.debug("skipping annotations of worker: %s" % annotator)
                continue

            for relation in input_pack.get(CrossEventRelation, stave_annotator):
                if relation.rel_type != "coref":
                    continue

                parent_pack = self._load_doc(input_pack, relation.parent_pack_id())
                child_pack = self._load_doc(input_pack, relation.child_pack_id())
                parent_mention = relation.get_parent()
                child_mention = relation.get_child()

                if parent_pack is None or child_pack is None:
                    continue

                pair_name = "pair_%s_and_%s" % (parent_pack.pack_name, child_pack.pack_name,)
                if pair_name not in self.relevant_doc_pairs[annotator]:
                    logging.debug("skipping document pair: %s for annotator: %s" % (pair_name, annotator))
                    continue
                # ignoring specific annotations
                if (annotator, pair_name) in self.ignore_set:
                    logging.debug("skipping document pair: %s for annotator: %s" % (pair_name, annotator))
                    continue

                mention_pair = (
                    annotator,
                    (parent_pack.pack_name, parent_mention.span.begin, parent_mention.span.end),
                    (child_pack.pack_name, child_mention.span.begin, child_mention.span.end),
                )
                if mention_pair not in self.mention_pair_set:
                    self.mention_pair_set.add(mention_pair)
                    self.mention_pairs.append(
                        (
                            annotator,
                            (parent_pack.pack_name, parent_mention.span.begin, parent_mention.span.end),
                            (child_pack.pack_name, child_mention.span.begin, child_mention.span.end),
                            relation.coref_answers,
                        )
                    )
                    self.docpair2links[(parent_pack.pack_name, child_pack.pack_name)].append(
                        (
                            annotator,
                            (parent_pack.pack_name, parent_mention.span.begin, parent_mention.span.end),
                            (child_pack.pack_name, child_mention.span.begin, child_mention.span.end),
                            relation.coref_answers,
                        )
                    )

    def _load_links(self):

        """ annotator agreement """
        logging.info(f"computing annotator agreement")
        docpair2anns = defaultdict(set)
        for link in self.mention_pairs:
            docpair2anns[(link[1][0], link[2][0])].add(link[0])

        # to make sure annotators with zero links for a specific document pair are accounted for
        for ann, doc_pairs in self.relevant_doc_pairs.items():
            for doc_pair in doc_pairs:
                s = re.search(r"pair_([0-9]+)_and_([0-9]+)", doc_pair)
                doc1 = s.group(1)
                doc2 = s.group(2)
                docpair2anns[(doc1, doc2)].add(ann)

        n_anns2doc_pairs = defaultdict(list)
        n_anns2count = defaultdict(int)
        for docpair, anns in docpair2anns.items():
            n_anns2doc_pairs[len(anns)].append(docpair)
            n_anns2count[len(anns)] += 1

        logging.info("--------------------------------------------------")
        logging.info("distribution of # annotators per document pair")
        logging.info(n_anns2count)
        logging.info("--------------------------------------------------")

        mp2idx = defaultdict(lambda: len(mp2idx))
        idx2mp = {}
        ann2idx = defaultdict(lambda: len(ann2idx))
        idx2ann = {}
        mp2txt = {}
        for (doc1, doc2), anns in docpair2anns.items():
            doc1_pack: DataPack = self.documents[doc1]
            doc2_pack: DataPack = self.documents[doc2]
            for m1 in doc1_pack.get(EventMention):
                for m2 in doc2_pack.get(EventMention):
                    mp = (
                        (doc1, m1.span.begin, m1.span.end),
                        (doc2, m2.span.begin, m2.span.end),
                    )
                    idx2mp[mp2idx[mp]] = mp
                    mp2txt[mp2idx[mp]] = (m1.text, m2.text)

            for ann in anns:
                idx2ann[ann2idx[ann]] = ann

        # 0: not-annotated
        ann_table = np.zeros((len(idx2mp), len(idx2ann)))
        Q_DEFAULT = -2
        ann_table_qs = [
            np.full((len(idx2mp), len(idx2ann)), Q_DEFAULT),
            np.full((len(idx2mp), len(idx2ann)), Q_DEFAULT),
            np.full((len(idx2mp), len(idx2ann)), Q_DEFAULT),
            np.full((len(idx2mp), len(idx2ann)), Q_DEFAULT),
        ]
        for (doc1, doc2), anns in docpair2anns.items():
            doc1_pack: DataPack = self.documents[doc1]
            doc2_pack: DataPack = self.documents[doc2]
            for ann in anns:
                for m1 in doc1_pack.get(EventMention):
                    for m2 in doc2_pack.get(EventMention):
                        mp = (
                            (doc1, m1.span.begin, m1.span.end),
                            (doc2, m2.span.begin, m2.span.end),
                        )
                        # default is non-coreference
                        ann_table[mp2idx[mp]][ann2idx[ann]] = -1

        for ann, m1, m2, answers in self.mention_pairs:
            # coreference
            ann_table[mp2idx[(m1, m2)]][ann2idx[ann]] = 1
            for idx, ans in enumerate(answers):
                ann_table_qs[idx][mp2idx[(m1, m2)]][ann2idx[ann]] = ans

        return idx2mp, mp2idx, idx2ann, ann2idx, mp2txt, ann_table, ann_table_qs

    def _compute_agreement(self, idx2mp, ann_table, ann_table_qs, Q_DEFAULT=-2):
        obs_agr = []
        obs_agr_pos = []
        obs_agr_qs = [[], [], [], []]
        for mp_idx in range(len(idx2mp)):
            values = ann_table[mp_idx]
            if ann_table_qs:
                values_qs = []
                for q_idx in range(len(ann_table_qs)):
                    values_qs.append(ann_table_qs[q_idx][mp_idx])

            n_anns = np.count_nonzero(values)
            assert n_anns > 0, "zero anns for a mention pair"
            if n_anns == 1:
                continue
            else:
                values = values[np.nonzero(values)[0]]
                item_obs_agr = []
                for i, j in itertools.combinations(values, 2):
                    item_obs_agr += [(i == j)]
                item_mean = np.mean(item_obs_agr)
                obs_agr += [item_mean]
                if 1 in values:
                    # at least one annotator marked as a coreference
                    obs_agr_pos += [item_mean]

                if ann_table_qs:
                    if np.count_nonzero(values == 1) > 1:
                        # only check questions if at least 2 annotators says its coreference
                        for q_idx in range(len(ann_table_qs)):
                            values_ = [x for x in values_qs[q_idx] if x != Q_DEFAULT]
                            assert len(values_) > 0
                            item_obs_agr = []
                            for i, j in itertools.combinations(values_, 2):
                                item_obs_agr += [(i == j)]
                            item_mean = np.mean(item_obs_agr)
                            obs_agr_qs[q_idx] += [item_mean]

        logging.info("--------------------------------------------------")
        logging.info(f"number of items: {len(obs_agr)}")
        logging.info(f"observed percentage agreement: {np.mean(obs_agr):.3f}")
        logging.info("--------------------------------------------------")
        logging.info(f"number of (approx. pos) items: {len(obs_agr_pos)}")
        logging.info(f"observed percentage agreement (approx. pos): {np.mean(obs_agr_pos):.3f}")
        logging.info("--------------------------------------------------")

        if ann_table_qs:
            for q_idx in range(len(obs_agr_qs)):
                logging.info(f"number of items for Q{q_idx+1}: {len(obs_agr_qs[q_idx])}")
                logging.info(
                    f"observed percentage agreement for Q{q_idx+1}: {np.mean(obs_agr_qs[q_idx]):.3f}"
                )
            logging.info("--------------------------------------------------")

        """ computing Krippendorff's alpha """
        coder_data = []
        n_items, n_coders = ann_table.shape
        for i in range(n_items):
            for j in range(n_coders):
                if ann_table[i][j] != 0:
                    # annotation exists (coref or non-coref)
                    # (coder, item, label)
                    coder_data += [(j, i, ann_table[i][j])]

        logging.info("--------------------------------------------------")
        logging.info(f"number of entries (alpha): {len(coder_data)}")
        ann_task = AnnotationTask(data=coder_data)
        # logging.info(f"avg Ao: {ann_task.avg_Ao():.3f}")
        logging.info(f"Krippendorff's alpha: {ann_task.alpha():.3f}")
        logging.info("--------------------------------------------------")

        if ann_table_qs:
            """ computing Krippendorff's alpha (questions) """
            for q_idx in range(len(ann_table_qs)):
                coder_data = []
                n_items, n_coders = ann_table_qs[q_idx].shape
                for i in range(n_items):
                    # below ann count check is not needed, alpha computation takes care of it
                    values = ann_table[i]
                    if np.count_nonzero(values) <= 1:
                        # less than 2 annotators
                        continue
                    values = values[np.nonzero(values)[0]]
                    if np.count_nonzero(values == 1) <= 1:
                        # less than 2 annotators say its coreference
                        continue

                    for j in range(n_coders):
                        if ann_table_qs[q_idx][i][j] != Q_DEFAULT:
                            # annotation exists (coref or non-coref)
                            # (coder, item, label)
                            coder_data += [(j, i, ann_table_qs[q_idx][i][j])]

                logging.info(f"number of entries (alpha) for Q{q_idx}: {len(coder_data)}")
                ann_task = AnnotationTask(data=coder_data)
                # logging.info(f"avg Ao: {ann_task.avg_Ao():.3f}")
                logging.info(f"Krippendorff's alpha for Q{q_idx}: {ann_task.alpha():.3f}")

                # # alternate way of computing alpha
                # reliability_data = []
                # n_items, n_anns = ann_table_qs[q_idx].shape

                # for j in range(n_anns):
                #     reliability_data.append([])
                #     for i in range(n_items):
                #         if ann_table_qs[q_idx][i][j] == -2:
                #             reliability_data[-1].append(np.nan)
                #         else:
                #             reliability_data[-1].append(ann_table_qs[q_idx][i][j])

                # logging.info(
                #     f"(alt) Krippendorff's alpha for Q{q_idx}: {krippendorff.alpha(reliability_data=reliability_data, level_of_measurement='nominal')}"
                # )
        logging.info("--------------------------------------------------")
        return

    def _get_ann_sent(self, sent: Sentence, mention: EventMention) -> str:
        begin = mention.span.begin - sent.span.begin
        end = mention.span.end - sent.span.begin
        sent_str = sent.text[:begin] + "<E> " + sent.text[begin:end] + " </E>" + sent.text[end:]
        return sent_str

    def write_samples(
        self,
        file_path,
        mp_indices,
        idx2mp,
        idx2ann,
        ann2idx,
        mp2txt,
        ann_table,
        ann_table_qs,
        sample_size=None,
    ):
        if sample_size:
            np.random.seed(23)
            sampled_indices = np.random.choice(mp_indices, 50)
        else:
            sampled_indices = mp_indices
        out_data = []
        for mp_idx in sampled_indices:
            mp = idx2mp[mp_idx]
            mp_anns = np.nonzero(ann_table[mp_idx])[0]
            mp_anns = [idx2ann[ann_idx] for ann_idx in mp_anns]
            sent1 = self._get_ann_sent(self.event_sents[mp[0]], self.events[mp[0]])
            sent2 = self._get_ann_sent(self.event_sents[mp[1]], self.events[mp[1]])
            coref_anns = [idx2ann[x] for x in np.nonzero(ann_table[mp_idx] == 1)[0]]
            # MCQ responses by coref annotators
            coref_anns_dict = defaultdict(list)
            for ann in coref_anns:
                for q_idx in range(4):
                    coref_anns_dict[ann] += [int(ann_table_qs[q_idx][mp_idx][ann2idx[ann]])]

            null_coref_anns = [idx2ann[x] for x in np.nonzero(ann_table[mp_idx] == -1)[0]]
            out_data.append(
                {
                    "doc_pair": "pair_%s_and_%s" % (mp[0][0], mp[1][0]),
                    "anns": mp_anns,
                    "mention_spans": mp,
                    "mention_txt": mp2txt[mp_idx],
                    "sentences": (sent1, sent2),
                    "coref_ann": coref_anns,
                    "null_coref_ann": null_coref_anns,
                    "coref_ann_responses": coref_anns_dict,
                    "adjudicator_label": "",
                }
            )

        with open(file_path, "w") as wf:
            json.dump(out_data, wf, indent=2)

    def write_docs(self):
        if self.out_docs_path is None:
            return

        self.out_docs_path.mkdir(exist_ok=True)
        for pack_name, doc_pack in self.documents.items():
            doc_data = {}
            doc_data["text"] = doc_pack.text
            doc_data["sentences"] = []
            doc_data["mentions"] = []
            for sent in doc_pack.get(Sentence):
                doc_data["sentences"] += [{"text": sent.text, "begin": sent.span.begin, "end": sent.span.end}]
            for mention in doc_pack.get(EventMention):
                doc_data["mentions"] += [
                    {
                        "text": mention.text,
                        "begin": mention.span.begin,
                        "end": mention.span.end,
                        "sentence": self._get_ann_sent(
                            self.event_sents[(pack_name, mention.span.begin, mention.span.end)],
                            self.events[(pack_name, mention.span.begin, mention.span.end)],
                        ),
                    }
                ]

            with open(self.out_docs_path / f"{pack_name}.json", "w") as wf:
                json.dump(doc_data, wf, indent=2)

    def finish(self, _):
        """
        Write the CDEC dataset in XML format
        """
        logging.info("--------------------------------------------------")
        logging.info(f"# documents: {len(self.documents)}")
        logging.info(f"# mentions: {len(self.events)}")

        """ document level statistics """
        sents = []
        tokens = []
        for _, doc_pack in self.documents.items():
            sents += [len([x for x in doc_pack.get(Sentence)])]
            tokens += [len([x for x in doc_pack.get(Token)])]
        logging.info(f"avg. sentences per document: {np.mean(sents):.2f} ({np.std(sents):.3f})")
        logging.info(f"avg. tokens per document: {np.mean(tokens):.2f} ({np.std(tokens):.3f})")
        logging.info("--------------------------------------------------")

        idx2mp, mp2idx, idx2ann, ann2idx, mp2txt, ann_table, ann_table_qs = self._load_links()

        self._compute_agreement(idx2mp, ann_table, ann_table_qs, Q_DEFAULT=-2)

        """
        Identify gold links
        labels are full, partial, null, vague
        """

        full, partial, null, vague = [], [], [], []
        partial_inclusion, partial_arguments = [], []
        vague_anns = defaultdict(int)
        vague_anns_mp = defaultdict(set)
        for mp_idx in range(len(idx2mp)):
            # for each mention pair, select a label
            coref_values = ann_table[mp_idx]
            place_values = ann_table_qs[0][mp_idx]
            time_values = ann_table_qs[1][mp_idx]
            participant_values = ann_table_qs[2][mp_idx]
            inclusion_values = ann_table_qs[3][mp_idx]

            n_anns = np.count_nonzero(coref_values)
            if n_anns >= 3:
                # # full
                # if (
                #     np.count_nonzero(coref_values == 1) >= 2
                #     and np.count_nonzero(place_values == 0) >= 2
                #     and np.count_nonzero(time_values == 0) >= 2
                #     and np.count_nonzero(participant_values == 0) >= 2
                #     and np.count_nonzero(inclusion_values == 2) >= 2
                # ):
                #     full += [mp_idx]
                # # partial
                # elif np.count_nonzero(coref_values == 1) >= 2:
                #     partial += [mp_idx]
                if np.count_nonzero(coref_values == 1) >= 2:
                    # calculating non-identity percentages
                    place_nonidentity = (
                        np.count_nonzero(place_values == 1) + np.count_nonzero(place_values == 2)
                    ) / np.count_nonzero(coref_values == 1)
                    time_nonidentity = (
                        np.count_nonzero(time_values == 1) + np.count_nonzero(time_values == 2)
                    ) / np.count_nonzero(coref_values == 1)
                    participant_nonidentity = (
                        np.count_nonzero(participant_values == 1) + np.count_nonzero(participant_values == 2)
                    ) / np.count_nonzero(coref_values == 1)
                    inclusion_nonidentity = (
                        np.count_nonzero(inclusion_values == 0) + np.count_nonzero(inclusion_values == 1)
                    ) / np.count_nonzero(coref_values == 1)

                    if inclusion_nonidentity > 0.5:
                        partial += [mp_idx]
                        partial_inclusion += [mp_idx]
                    elif place_nonidentity > 0.5 or time_nonidentity > 0.5 or participant_nonidentity > 0.5:
                        partial += [mp_idx]
                        partial_arguments += [mp_idx]
                    else:
                        full += [mp_idx]
                # null
                elif np.count_nonzero(coref_values == 1) == 0:
                    null += [mp_idx]
                # vague
                else:
                    vague += [mp_idx]
                    ann = np.nonzero(coref_values == 1)[0]
                    assert len(ann) == 1
                    vague_anns[idx2ann[ann[0]]] += 1
                    mp_val = idx2mp[mp_idx]
                    vague_anns_mp[idx2ann[ann[0]]].add("pair_%s_and_%s" % (mp_val[0][0], mp_val[1][0]))

        logging.info("--------------------------------------------------")
        logging.info(f"full coref:\t\t{len(full)}")
        logging.info(f"partial coref:\t\t{len(partial)}")
        logging.info(f"partial_inclusion coref:\t\t{len(partial_inclusion)}")
        logging.info(f"partial_arguments coref:\t\t{len(partial_arguments)}")
        logging.info(f"null coref:\t\t{len(null)}")
        logging.info(f"vague coref:\t\t{len(vague)}")
        logging.info("--------------------------------------------------")

        # # digging further into partial labels
        # subevent_count = 0
        # participant_overlap_count = 0
        # place_overlap_count = 0
        # time_overlap_count = 0
        # for mp_idx in partial:
        #     coref_values = ann_table[mp_idx]
        #     place_values = ann_table_qs[0][mp_idx]
        #     time_values = ann_table_qs[1][mp_idx]
        #     participant_values = ann_table_qs[2][mp_idx]
        #     subevent_values = ann_table_qs[3][mp_idx]

        #     if np.count_nonzero(subevent_values == 0) >= 2 or np.count_nonzero(subevent_values == 1) >= 2:
        #         subevent_count += 1

        #     if np.count_nonzero(participant_values == 1) >= 2:
        #         participant_overlap_count += 1

        #     if np.count_nonzero(place_values == 1) >= 2:
        #         place_overlap_count += 1

        #     if np.count_nonzero(time_values == 1) >= 2:
        #         time_overlap_count += 1

        # logging.info("--------------------------------------------------")
        # logging.info("statistics of partial label")
        # logging.info(f"subevent structure count: {subevent_count}")
        # logging.info(f"participant overlap count: {participant_overlap_count}")
        # logging.info(f"place overlap count: {place_overlap_count}")
        # logging.info(f"time overlap count: {time_overlap_count}")
        # logging.info("--------------------------------------------------")

        # # digging further into vague labels
        # subevent_count = 0
        # participant_overlap_count = 0
        # place_overlap_count = 0
        # time_overlap_count = 0
        # for mp_idx in vague:
        #     coref_values = ann_table[mp_idx]
        #     place_values = ann_table_qs[0][mp_idx]
        #     time_values = ann_table_qs[1][mp_idx]
        #     participant_values = ann_table_qs[2][mp_idx]
        #     subevent_values = ann_table_qs[3][mp_idx]

        #     if np.count_nonzero(subevent_values == 0) > 0 or np.count_nonzero(subevent_values == 1) > 0:
        #         subevent_count += 1

        #     if np.count_nonzero(participant_values == 1) > 0:
        #         participant_overlap_count += 1

        #     if np.count_nonzero(place_values == 1) > 0:
        #         place_overlap_count += 1

        #     if np.count_nonzero(time_values == 1) > 0:
        #         time_overlap_count += 1

        # logging.info("--------------------------------------------------")
        # logging.info("statistics of vague label")
        # logging.info(f"subevent structure count: {subevent_count}")
        # logging.info(f"participant overlap count: {participant_overlap_count}")
        # logging.info(f"place overlap count: {place_overlap_count}")
        # logging.info(f"time overlap count: {time_overlap_count}")
        # logging.info("--------------------------------------------------")

        self.write_samples(
            self.out_path / "full.json",
            full,
            idx2mp,
            idx2ann,
            ann2idx,
            mp2txt,
            ann_table,
            ann_table_qs,
            sample_size=None,
        )
        self.write_samples(
            self.out_path / "partial.json",
            partial,
            idx2mp,
            idx2ann,
            ann2idx,
            mp2txt,
            ann_table,
            ann_table_qs,
            sample_size=None,
        )
        self.write_samples(
            self.out_path / "partial_inclusion.json",
            partial_inclusion,
            idx2mp,
            idx2ann,
            ann2idx,
            mp2txt,
            ann_table,
            ann_table_qs,
            sample_size=None,
        )
        self.write_samples(
            self.out_path / "partial_arguments.json",
            partial_arguments,
            idx2mp,
            idx2ann,
            ann2idx,
            mp2txt,
            ann_table,
            ann_table_qs,
            sample_size=None,
        )
        self.write_samples(
            self.out_path / "vague.json",
            vague,
            idx2mp,
            idx2ann,
            ann2idx,
            mp2txt,
            ann_table,
            ann_table_qs,
            sample_size=None,
        )
        self.write_docs()
        # for ann, count in vague_anns.items():
        #     print("%s\t%s\t%d" % (ann, count, len(vague_anns_mp[ann])))
        # total_vague_doc_pairs = set()
        # for ann, doc_pairs in vague_anns_mp.items():
        #     total_vague_doc_pairs.update(doc_pairs)
        # print("total vague doc pairs: %d" % len(total_vague_doc_pairs))


if __name__ == "__main__":

    logging.basicConfig(
        format="%(message)s", level=logging.INFO, handlers=[logging.StreamHandler()],
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("stave_db", type=str)
    parser.add_argument("mturk_db", type=str)
    parser.add_argument("ignore_set", type=str, help="annotations to ignore")
    parser.add_argument("-out_dir", type=Path, default=None)
    parser.add_argument("-docs_dir", type=Path, default=None, help="write docs in json format")
    args = parser.parse_args()

    if args.out_dir:
        args.out_dir.mkdir(exist_ok=True)

    pipeline = Pipeline()
    pipeline.set_reader(StaveMultiDocSqlReader(), config={"stave_db_path": args.stave_db})
    pipeline.add(CorefEventCollector(args.mturk_db, args.ignore_set, args.out_dir, args.docs_dir))

    pipeline.run()
