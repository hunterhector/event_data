import logging
from typing import Dict

from forte.data.multi_pack import MultiPack
from forte.pipeline import Pipeline
from forte.processors.base import MultiPackProcessor
from forte.processors.writers import DocIdMultiPackWriter
from ft.onto.base_ontology import EventMention, CrossDocEventRelation

from readers.event_reader import TwoDocumentEventReader


class SameTextCoreferencer(MultiPackProcessor):
    """
    Mark some example coreference relations.
    """

    def _process(self, input_pack: MultiPack):
        pack_i = input_pack.get_pack_at(0)
        pack_j = input_pack.get_pack_at(1)

        lemma_events: Dict[str, EventMention] = {}

        for evm in pack_i.get_entries(EventMention):
            lemma_events[evm.text] = evm

        for evm in pack_j.get_entries(EventMention):
            if evm.text in lemma_events:
                link = CrossDocEventRelation(
                    input_pack, lemma_events[evm.text], evm)
                link.rel_type = 'coreference'
                input_pack.add_entry(link)


input_path = 'sample_data/input'
output_path = 'sample_data/output'

pl = Pipeline()
pl.set_reader(TwoDocumentEventReader())
pl.add(SameTextCoreferencer())

pl.add(
    DocIdMultiPackWriter(), {
        'output_dir': output_path,
        'indent': 2,
        'overwrite': True,
    })

pl.initialize()

# Here we specify the pairs of documents to be used.
pairs = [('00_Abstract', '00_Abstract')]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

pl.run(input_path, pairs)
