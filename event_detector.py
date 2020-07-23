from forte.data.data_pack import DataPack
from forte.processors.base import PackProcessor
from ft.onto.base_ontology import Token
from edu.cmu import EventMention


class EventDetector(PackProcessor):
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
