from forte.data.data_pack import DataPack
from forte.processors.base import PackProcessor
from ft.onto.base_ontology import Token
from edu.cmu import EventMention
import brat_tool
import sys
import math
import gzip
import json

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

class SameLemmaEventDetector(PackProcessor):
    """
    An example event proposer that propose events based on a dictionary.
    """

    def __init__(self, event_lemma_list_filename):
        with open(event_lemma_list_filename, encoding="utf-8") as f:
            event_lemmas = f.read().splitlines()
            self.event_lemma_list_single = [elm for elm in event_lemmas if " " not in elm]
            self.event_lemma_list_sequence = [elm.split(" ") for elm in event_lemmas if " " in elm]
            
            # debug purpose
            # self.event_lemma_list_single = ["detonate", "killing", "shoot"]
            # self.event_lemma_list_sequence = [["Boston", "Marathon"]]

        self.event_lemma_list_sequence = sorted(self.event_lemma_list_sequence, key=lambda x: len(x), reverse=True)

    def _process(self, pack: DataPack):

        body_tokens = [token for token in pack.get(Token)]
        body_lemmas = [token.lemma for token in body_tokens]
        body_events = [False] * len(body_tokens)

        for ev_seq in self.event_lemma_list_sequence:
            sub_idx_list = self.subfinder(body_lemmas, ev_seq) # sequence match
            for sub_idx in sub_idx_list:
                if all([not body_events[idx] for idx in sub_idx]):
                    evm = EventMention(pack, body_tokens[sub_idx[0]].begin, body_tokens[sub_idx[-1]].end)
                    # pack.add_entry(evm)
                    for idx in sub_idx:
                        body_events[idx] = True

        for token, token_is_event in zip(body_tokens, body_events):
            if not token_is_event and token.lemma in self.event_lemma_list_single: # single word match
                evm = EventMention(pack, token.begin, token.end)
                # pack.add_entry(evm)

    def subfinder(self, mylist, pattern):
        matches = []
        for i in range(len(mylist)):
            if mylist[i] == pattern[0] and mylist[i:i+len(pattern)] == pattern:
                matches.append(list(range(i, len(pattern) + i, 1)))
        return matches

    
class LemmaMatchAndCOLING2018OEDEventDetector(PackProcessor):
    """
    This is the combined method: lemma-match (Matz) and coling2018-event(Araki and Mitamura).
    """
    
    def __init__(self, event_lemma_list_filename, coling2018_event_output_path, df_file, tokenizer):
        with open(event_lemma_list_filename, encoding="utf-8") as f:
            event_lemmas = f.read().splitlines()
            self.event_lemma_list_single = [elm for elm in event_lemmas if " " not in elm]
            self.event_lemma_list_sequence = [elm.split(" ") for elm in event_lemmas if " " in elm]
        self.coling2018_event_output_path = coling2018_event_output_path
        self.tokenizer = tokenizer
        with gzip.open(df_file, 'rt', encoding='utf-8') as f:
            self.df_table = json.load(f)

        self.event_lemma_list_sequence = sorted(self.event_lemma_list_sequence, key=lambda x: len(x), reverse=True)

    def _process(self, pack: DataPack):
        print('pack.pack_name', pack.pack_name+'.txt')

        body_tokens = [token for token in pack.get(Token)]
        body_lemmas = [token.lemma for token in body_tokens]
        body_events = [False] * len(body_tokens)
        detected_events_lemma_match = list()
        detected_events_coling2018 = list()
        
        # event detection with lemma-match method: 
        for ev_seq in self.event_lemma_list_sequence:
            sub_idx_list = self.subfinder(body_lemmas, ev_seq) # sequence match
            for sub_idx in sub_idx_list:
                if all([not body_events[idx] for idx in sub_idx]):
                    detected_events_lemma_match.append((body_tokens[sub_idx[0]].begin, body_tokens[sub_idx[-1]].end, ev_seq))
                    for idx in sub_idx:
                        body_events[idx] = True

        for token, token_is_event in zip(body_tokens, body_events):
            if not token_is_event and token.lemma in self.event_lemma_list_single: # single word match
                detected_events_lemma_match.append((token.begin, token.end, token.lemma))
        
        # event detection result from coling2018-event
        with open(self.coling2018_event_output_path+pack.pack_name+'.ann', 'r', encoding="utf-8") as f:
            ann_data = f.read()
        ann = brat_tool.BratAnnotations(ann_data)
        events = ann.getEventAnnotationList()
        for event in events:
            detected_events_coling2018.append((event.textbound.start_pos, event.textbound.end_pos, event.textbound.text))
        
        # remove redundant 
        for d in detected_events_lemma_match:
            flag_found = False
            for d_ in detected_events_coling2018:
                if d[0] == d_[0] and d[1] == d_[1]:
                    flag_found = True
            if not flag_found:
                detected_events_coling2018.append(d)
        
        # parse text w/ spacy for term frequency calc
        with open(self.coling2018_event_output_path+pack.pack_name+'.txt', 'r', encoding='utf-8') as f:
            txt_data = f.read()
        doc = self.tokenizer(txt_data)
        table_word_frequency = dict()  # todo: rename to table_term_count
        special_tokens = ["'", '"', '-', '=']
        for token in doc:
            condition = ('\n' in token.text) or (token.pos_ == 'PUNCT') \
                            or (token.text in special_tokens) or token.is_stop or (token.pos_ == 'NUM')
            if condition:
                continue
            if token.lemma_ not in table_word_frequency:
                table_word_frequency[token.lemma_] = 1
            else:
                table_word_frequency[token.lemma_] += 1
        
        
        # store events + importance(tf-idf) calculation
        for event in detected_events_coling2018:
            evm = EventMention(pack, event[0], event[1])  # event[0]: start, event[1]: end
            print('evm:', evm)
            # set the importance score
            if type(event[-1]) is list:
                print('seq:', event[-1])
                evm.importance = - 2.0
            else:
                doc = self.tokenizer(event[-1])
                assert len(doc) == 1
                lemma = doc[0].lemma_
                if lemma in table_word_frequency and lemma in self.df_table:
                    tf = table_word_frequency[lemma] / len(table_word_frequency)
                    idf = len(self.df_table) / self.df_table[lemma]
                    evm.importance = tf * math.log(idf)
                    print('single:', event[-1])
                    print('importance', evm.importance)
                else:  # the word not found in tables
                    print('single not found:', event[-1])
                    evm.importance = - 1.0

    def subfinder(self, mylist, pattern):
        matches = []
        for i in range(len(mylist)):
            if mylist[i] == pattern[0] and mylist[i:i+len(pattern)] == pattern:
                matches.append(list(range(i, len(pattern) + i, 1)))
        return matches