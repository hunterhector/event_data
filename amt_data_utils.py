from typing import Dict, List
from itertools import combinations
import numpy as np


from forte.data.data_pack import DataPack
from ft.onto.base_ontology import Sentence
from edu.cmu import EventMention


def custom_sort(doc_group: List[str], name2pack: Dict[str, DataPack]):
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
