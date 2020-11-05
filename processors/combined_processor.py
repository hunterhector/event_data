import logging
import json
import math
import gzip
import os
import sys
from pathlib import Path

from typing import Dict, Any, List

from allennlp.predictors.predictor import Predictor
import tools.brat_tool as brat_tool

from forte.data.data_pack import DataPack
from forte.processors.base import PackProcessor
from ft.onto.base_ontology import Token, Sentence
from forte.common.configuration import Config
from forte.common.resources import Resources
from edu.cmu import EventMention, BodySpan

MODEL2URL = {
    "openie": "https://storage.googleapis.com/allennlp-public-models/openie-model.2020.03.26.tar.gz",
    "srl": "https://storage.googleapis.com/allennlp-public-models/bert-base-srl-2020.03.24.tar.gz",
}

logger = logging.getLogger(__name__)


class LemmaJunNombankOpenIEEventDetector(PackProcessor):
    """
    This is the combined method:
    - lemma-match (Matz)
    - coling2018-event(Araki and Mitamura)
    - Nombank (pruned based on hypernyms)
    - OpenIE (Adithya)
    - No reporting verbs
    - No stative verbs
    """

    def __init__(self, jun_output: Path, tokenizer):

        # lemma-match
        with open('./tools/event_lemma.txt', encoding="utf-8") as f:
            event_lemmas = f.read().splitlines()
            self.event_lemma_list_single = [elm for elm in event_lemmas if " " not in elm]
            self.event_lemma_list_sequence = [elm.split(" ") for elm in event_lemmas if " " in elm]
        self.event_lemma_list_sequence = sorted(self.event_lemma_list_sequence, key=lambda x: len(x), reverse=True)

        # nombank
        with open('./tools/pruned_nombank_propositions_chain_10.json', 'r') as f:
            self.nombank_lemma_list = json.load(f)

        # reporting verbs
        with open('./tools/reporting_verbs.txt', 'r') as f:
            self.reporting_verbs = [x.strip() for x in f.readlines()]

        # stative verbs
        with open('./tools/stative_verbs.txt', 'r') as f:
            self.stative_verbs = [x.strip() for x in f.readlines()]

        # auxiliary verbs
        self.auxiliary_verbs = ['will', 'would', 'could', 'can', 'might', 'may', 'must', 'should', 'have']

        # path to the output of Jun's code
        self.coling2018_event_output_path = jun_output

        # spacy: ToDo) update to use built-in tokenizer
        self.tokenizer = tokenizer

        # document frequency look-up table
        with gzip.open('./tools/idf_table.json.gz', 'rt', encoding='utf-8') as f:
            self.df_table = json.load(f)

        # manually gathering shiftlist(blacklist)
        with open('./tools/shiftlist.txt', 'r') as f:
            self.shiftlist = [x.strip() for x in f.readlines()]


    def initialize(self, resources: Resources, configs: Config):
        """
        initialization for AllenNLP model
        """
        super().initialize(resources, configs)

        model_url = MODEL2URL[configs.model]
        self.predictor = Predictor.from_path(model_url)

    @classmethod
    def default_configs(cls):
        """
        default config for AllenNLPEventProcessor
            uses OpenIE model to identify event mentions
        """
        config = super().default_configs()
        config.update({"model": "openie"})
        return config

    def _process(self, input_pack: DataPack):
        print('pack.pack_name {}'.format(input_pack.pack_name+'.txt'))
        logging.info('pack.pack_name {}'.format(input_pack.pack_name+'.txt'))

        body = list(input_pack.get(BodySpan))[0]
        body_offset = body.begin

        body_tokens = [token for token in input_pack.get(Token)]
        body_lemmas = [token.lemma for token in body_tokens]
        body_events = [False] * len(body_tokens)

        detected_events_lemma_match = list()
        detected_events_coling2018 = list()
        detected_events_openie = list()

        # event detection with lemma-match (domain-specific lemma + nombank) method:
        # sequence match
        for ev_seq in self.event_lemma_list_sequence:
            sub_idx_list = self.subfinder(body_lemmas, ev_seq)
            for sub_idx in sub_idx_list:
                if all([not body_events[idx] for idx in sub_idx]):
                    event_begin = body_tokens[sub_idx[0]].begin
                    event_end = body_tokens[sub_idx[-1]].end

                    detected_events_lemma_match.append({'begin': event_begin, 'end': event_end, 'source': 'L', 'nugget': ev_seq})

                    for idx in sub_idx:
                        body_events[idx] = True

        # single word match
        for token, token_is_event in zip(body_tokens, body_events):

            if (not token_is_event) and (token.lemma in self.event_lemma_list_single):
                detected_events_lemma_match.append({'begin': token.begin, 'end': token.end, 'source': 'L', 'nugget': token.lemma})

            if (not token_is_event) and (token.lemma in self.nombank_lemma_list):
                detected_events_lemma_match.append({'begin': token.begin, 'end': token.end, 'source': 'N', 'nugget': token.lemma})

        # event detection result from coling2018-event
        with open(self.coling2018_event_output_path / f"{input_pack.pack_name}.ann", 'r', encoding="utf-8") as f:
            ann_data = f.read()

        ann = brat_tool.BratAnnotations(ann_data)
        events = ann.getEventAnnotationList()

        # adding `body_offset`
        for event in events:
            detected_events_coling2018.append({'begin': body_offset + event.textbound.start_pos, 'end': body_offset + event.textbound.end_pos, 'source': 'J', 'nugget': event.textbound.text})

        # check & modify alignment of detected events by coling2018-event
        for event in detected_events_coling2018:
            for token in input_pack.annotations:
                if (token.begin == event['begin']) and (token.end == event['end']):
                    # span is okay
                    break
                if (token.begin-5 <= event['begin'] <= token.begin+5) \
                        and ((event['end'] - event['begin']) == (token.end - token.begin)) \
                        and event['nugget'] == token.text:
                    # modify span
                    event['begin'] = token.begin
                    event['end'] = token.end

        # OpenIE
        sentences, sentences_txt = [], []
        for sentence in input_pack.get(Sentence):
            sentences.append(sentence)
            sentences_txt.append({"sentence": sentence.text})

        predictions = self.predictor.predict_batch_json(sentences_txt)

        for sentence, prediction in zip(sentences, predictions):
            detected_events_openie += self.get_event_mentions_openie(input_pack, sentence, prediction)


        # concate all detected events
        detected_event_candidates = sorted(detected_events_lemma_match+detected_events_coling2018+detected_events_openie, key=lambda x:x['begin'])

        # remove not-our-target event candidates
        tmp = list()
        for event in detected_event_candidates:
            lemma = self.get_lemma(input_pack, event)
            if (lemma not in self.reporting_verbs) \
                and (lemma not in self.stative_verbs) \
                and (lemma not in self.auxiliary_verbs) \
                and (lemma not in self.shiftlist):
                tmp.append(event)
        detected_event_candidates = tmp[:]

        # merge redundant
        detected_events = list()
        for event in detected_event_candidates:
            flag_exist = False
            for existing_event in detected_events:
                if event['begin'] == existing_event['begin'] and event['end'] == existing_event['end']:
                    flag_exist = True
                    existing_event['source'] += event['source']
                elif existing_event['begin'] <= event['begin'] and event['end'] <= existing_event['end']:
                    flag_exist = True
                    existing_event['source'] += event['source']
                elif event['begin'] <= existing_event['begin'] and existing_event['end'] <= event['end']:
                    flag_exist = True
                    existing_event['source'] += event['source']
            if not flag_exist:
                detected_events.append(event)

        # parse text w/ spacy
        # ToDo: replace spacy tokenizer with Default one (stanfordcorenlp? stanza?).
        with open(self.coling2018_event_output_path / f"{input_pack.pack_name}.txt", 'r', encoding='utf-8') as f:
            txt_data = f.read()
        doc = self.tokenizer(txt_data)

        # phrase detection
        detected_events = sorted(detected_events, key=lambda x:x['begin'])
        replacements = list()
        skip_idx = list()
        for idx in range(len(detected_events)-1):
            if idx in skip_idx:
                continue
            # if two consecutive events are next to each other,
            if int(detected_events[idx+1]['begin']) - int(detected_events[idx]['end']) <= 2:
                # check dependency
                for idx_ in range(len(doc)-1):
                    if doc[idx_].text == detected_events[idx]['nugget'] and doc[idx_+1].text == detected_events[idx+1]['nugget']:
                        if (doc[idx_].head.text == doc[idx_+1].text) or (doc[idx_].text == doc[idx_+1].head.text):
                            if doc[idx_].dep_ == 'compound' \
                                or (doc[idx_].dep_ == 'prt' or doc[idx_+1].dep_ == 'prt'):
                                new_event = {'begin': detected_events[idx]['begin'],
                                             'end': detected_events[idx+1]['end'],
                                             'source': 'P',
                                             'nugget': detected_events[idx]['nugget']+' '+ detected_events[idx+1]['nugget']}
                                replacements.append((detected_events[idx], detected_events[idx+1], new_event))
                                skip_idx.append(idx+1)
                                break
        for replacement in replacements:
            if replacement[0] not in detected_events:
                logging.info('debug: replacement){} detected_events){}'.format(replacement, detected_events))
                continue
            detected_events.remove(replacement[0])
            detected_events.remove(replacement[1])
            detected_events.append(replacement[2])

        # term frequency calc
        table_word_count = dict()
        special_tokens = ["'", '"', '-', '=']
        for token in doc:
            # condition for term frequency
            if ('\n' in token.text) \
                or (token.pos_ == 'PUNCT') \
                or (token.text in special_tokens) \
                or token.is_stop \
                or (token.pos_ == 'NUM'):
                continue

            if token.lemma_ not in table_word_count:
                table_word_count[token.lemma_] = 1
            else:
                table_word_count[token.lemma_] += 1


        # store events + importance(tf-idf) calculation
        for event in detected_events:
            # set the importance score
            if type(event['nugget']) is list:
                evm = EventMention(input_pack, event['begin'], event['end'])
                evm.importance = - 2.0
                evm.event_source = event['source']
            else:
                doc = self.tokenizer(event['nugget'])
                if len(doc) == 1:
                    lemma = doc[0].lemma_
                    evm = EventMention(input_pack, event['begin'], event['end'])
                    evm.event_source = event['source']
                    if lemma in table_word_count and lemma in self.df_table:
                        tf = table_word_count[lemma] / len(table_word_count)
                        idf = len(self.df_table) / self.df_table[lemma]
                        evm.importance = float('{0:.3g}'.format(tf * math.log(idf)))
                    else:  # the word not found in tables (including stop words)
                        evm.importance = - 1.0
                else:  # multiple words?
                    evm = EventMention(input_pack, event['begin'], event['end'])
                    evm.importance = - 1.0
                    evm.event_source = event['source']

    def subfinder(self, mylist, pattern):
        matches = []
        for i in range(len(mylist)):
            if mylist[i] == pattern[0] and mylist[i:i+len(pattern)] == pattern:
                matches.append(list(range(i, len(pattern) + i, 1)))
        return matches

    def get_lemma(self, input_pack: DataPack, event):
        lemma = None
        for token in input_pack.annotations:
            if (token.begin == event['begin']) and (token.end == event['end']):
                try:
                    lemma = token.lemma
                except:  # Sentence
                    lemma = None
                break
        return lemma

    def get_event_mentions_openie(
        self, input_pack: DataPack, sentence: Sentence, result: Dict[str, Any]
    ) -> List:

        words = result["words"]
        offset = sentence.span.begin

        detected_events = list()

        # TODO: check if len(words) == tokens in sentence

        """ create EventMention instances for all the verb (event) tokens """
        for result_predicate in result["verbs"]:

            tags = result_predicate["tags"]
            if "B-V" not in tags:
                continue

            event_text = result_predicate['verb']

            start_index = tags.index("B-V")
            end_index = len(tags) - 1 - tags[::-1].index("B-V")

            word_end = 0

            event_begin, event_end = None, None
            for i, word in enumerate(words):
                word_begin = sentence.text.find(word, word_end)
                word_end = word_begin + len(word)

                if i == start_index:
                    event_begin = word_begin
                if i == end_index:
                    event_end = word_end

            if event_begin != None and event_end != None:
                detected_events.append({'begin': offset+event_begin, 'end': offset+event_end, 'source': 'A', 'nugget': event_text})

        return detected_events
