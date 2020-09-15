from forte.data.data_pack import DataPack
from forte.processors.base import PackProcessor
from ft.onto.base_ontology import Token
from edu.cmu import EventMention
import json
import tools.brat_tool as brat_tool
import math
import gzip
import os
import sys
import logging

class KeywordEventDetector(PackProcessor):
    """
    An example event proposer that propose events based on a dictionary.
    """
    event_dict = {
        'bomb', 'detonate', 'kill', 'injure', 'kidnap', 'shootout', 'die',
        'explode', 'death'
    }

    def _process(self, pack: DataPack):
        for token in pack.get(Token):
            if token.lemma in self.event_dict:
                evm = EventMention(pack, token.begin, token.end)
                # You can set the importance score easily.
                evm.importance = 0.9

class LemmaJunNombankEventDetector(PackProcessor):
    """
    This is the combined method: 
    - lemma-match (Matz) 
    - coling2018-event(Araki and Mitamura)
    - Nombank
    - No reporting verbs
    """
    
    def __init__(
        self, 
        event_lemma_list_filename, 
        jun_output, 
        nombank_propositions, 
        df_file, 
        reporting_verbs,
        tokenizer):
        
        # lemma-match
        with open(event_lemma_list_filename, encoding="utf-8") as f:
            event_lemmas = f.read().splitlines()
            self.event_lemma_list_single = [elm for elm in event_lemmas if " " not in elm]
            self.event_lemma_list_sequence = [elm.split(" ") for elm in event_lemmas if " " in elm]
        
        # nombank
        with open(nombank_propositions, 'r') as f:
            self.nombank_lemma_list = json.load(f)
        
        # reporting verbs
        with open(reporting_verbs, 'r') as f:
            self.reporting_verbs = [x.strip() for x in f.readlines()]
            
        # path to the output of Jun's code
        self.coling2018_event_output_path = jun_output
        
        # spacy: to be removed
        self.tokenizer = tokenizer
        
        # document frequency look-up table
        with gzip.open(df_file, 'rt', encoding='utf-8') as f:
            self.df_table = json.load(f)

        self.event_lemma_list_sequence = sorted(self.event_lemma_list_sequence, key=lambda x: len(x), reverse=True)

    def _process(self, pack: DataPack):
        print('pack.pack_name {}'.format(pack.pack_name+'.txt'))
        logging.info('pack.pack_name {}'.format(pack.pack_name+'.txt'))
        
        body_tokens = [token for token in pack.get(Token)]
        body_lemmas = [token.lemma for token in body_tokens]
        body_events = [False] * len(body_tokens)
        detected_events_lemma_match = list()
        detected_events_coling2018 = list()
        
        # event detection with lemma-match (domain lemma + nombank) method: 
        # sequence match
        for ev_seq in self.event_lemma_list_sequence:
            sub_idx_list = self.subfinder(body_lemmas, ev_seq) 
            for sub_idx in sub_idx_list:
                if all([not body_events[idx] for idx in sub_idx]):
                    detected_events_lemma_match.append((body_tokens[sub_idx[0]].begin, body_tokens[sub_idx[-1]].end, 'lemma', ev_seq))
                    for idx in sub_idx:
                        body_events[idx] = True
        # single word match
        for token, token_is_event in zip(body_tokens, body_events):
            if (not token_is_event) and (token.lemma in self.event_lemma_list_single):
                detected_events_lemma_match.append((token.begin, token.end, 'lemma', token.lemma))
            if (not token_is_event) and (token.lemma in self.nombank_lemma_list): 
                detected_events_lemma_match.append((token.begin, token.end, 'nombank', token.lemma))
        
        # event detection result from coling2018-event
        with open(self.coling2018_event_output_path+pack.pack_name+'.ann', 'r', encoding="utf-8") as f:
            ann_data = f.read()
        ann = brat_tool.BratAnnotations(ann_data)
        events = ann.getEventAnnotationList()
        for event in events:
            detected_events_coling2018.append((event.textbound.start_pos, event.textbound.end_pos, 'jun', event.textbound.text))
        
        # remove redundant
        detected_events = detected_events_coling2018[:]
        for d in detected_events_lemma_match:
            flag_found = False
            for d_ in detected_events_coling2018:
                if d[0] == d_[0] and d[1] == d_[1]:
                    flag_found = True
                if d_[0] <= d[0] and d[1] <= d_[1]:
                    flag_found = True
            if not flag_found:
                detected_events.append(d)
        
        # parse text w/ spacy 
        # ToDo: replace spacy tokenizer with Default one (stanfordcorenlp? stanza?).
        with open(self.coling2018_event_output_path+pack.pack_name+'.txt', 'r', encoding='utf-8') as f:
            txt_data = f.read()
        doc = self.tokenizer(txt_data)
        
        # phrase detection
        detected_events = sorted(detected_events, key=lambda x:x[0])
        replacements = list()
        skip_idx = list()
        for idx in range(len(detected_events)-1):
            if idx in skip_idx:
                continue
            # if two consecutive events are next to each other, 
            if int(detected_events[idx+1][0]) - int(detected_events[idx][1]) <= 2:
                # check dependency 
                for idx_ in range(len(doc)-1):
                    if doc[idx_].text == detected_events[idx][-1] and doc[idx_+1].text == detected_events[idx+1][-1]:
                        if doc[idx_].dep_ == 'compound' \
                            or (doc[idx_].dep_ == 'prt' or doc[idx_+1].dep_ == 'prt') \
                            or (doc[idx_].dep_ == 'dobj' or doc[idx_+1].dep_ == 'dobj'):
                            new_event = (detected_events[idx][0], 
                                         detected_events[idx+1][1], 
                                         'phrase', 
                                         detected_events[idx][-1]+' '+ detected_events[idx+1][-1])
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
            if type(event[-1]) is list:
                evm = EventMention(pack, event[0], event[1])  # event[0]: start, event[1]: end
                evm.importance = - 2.0
                evm.event_type = event[2]
            else:
                doc = self.tokenizer(event[-1])
                if len(doc) == 1:
                    lemma = doc[0].lemma_
                    if lemma not in self.reporting_verbs:
                        evm = EventMention(pack, event[0], event[1])  # event[0]: start, event[1]: end
                        evm.event_type = event[2]
                        if lemma in table_word_count and lemma in self.df_table:
                            tf = table_word_count[lemma] / len(table_word_count)
                            idf = len(self.df_table) / self.df_table[lemma]
                            evm.importance = float('{0:.3g}'.format(tf * math.log(idf)))
                        else:  # the word not found in tables (including stop words)
                            evm.importance = - 1.0
                else:  # multiple words?
                    evm = EventMention(pack, event[0], event[1])  # event[0]: start, event[1]: end
                    evm.importance = - 1.0
                    evm.event_type = event[2]

    def subfinder(self, mylist, pattern):
        matches = []
        for i in range(len(mylist)):
            if mylist[i] == pattern[0] and mylist[i:i+len(pattern)] == pattern:
                matches.append(list(range(i, len(pattern) + i, 1)))
        return matches
