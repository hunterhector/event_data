from forte.data.multi_pack import MultiPack
from forte.processors.base import MultiPackProcessor

from edu.cmu import EventMention, CrossEventRelation


class BaseSuggestionProvider(MultiPackProcessor):
    """
    Base class to mark example coreference relations.
    """

    def _process(self, input_pack: MultiPack):
        pack_i = input_pack.get_pack_at(0)
        pack_j = input_pack.get_pack_at(1)

        for evm_i in pack_i.get(EventMention):
            for evm_j in pack_j.get(EventMention):
                if self.use_this_pair(evm_i, evm_j):
                    link = CrossEventRelation(input_pack, evm_i, evm_j)
                    link.rel_type = 'suggested'
                    input_pack.add_entry(link)

    def use_this_pair(self, evm_i, evm_j) -> bool:
        raise NotImplementedError


class SameLemmaSuggestionProvider(BaseSuggestionProvider):
    """
    Mark some example coreference relations using lemma.
    """

    def use_this_pair(self, evm_i, evm_j) -> bool:
        if evm_i.text == evm_j.text:
            return True


import spacy
nlp = spacy.load("en_core_web_md")
class EmbeddingSimilaritySuggestionProvider(BaseSuggestionProvider):
    """
    Mark some example coreference relations using embedding.
    """
    def __init__(self, threshold=0.45):
        super().__init__()
        self.threshold = threshold

    def use_this_pair(self, evm_i, evm_j) -> bool:
        sim = nlp(evm_i.text).similarity(nlp(evm_j.text))
        if sim >= self.threshold:
            return True
