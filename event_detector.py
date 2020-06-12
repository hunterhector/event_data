from forte.data.data_pack import DataPack
from forte.processors.base import PackProcessor
from ft.onto.base_ontology import Token
from edu.cmu import EventMention


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
