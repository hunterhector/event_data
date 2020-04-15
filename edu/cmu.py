# ***automatically_generated***
# ***source json:../event_data/event_ontology.json***
# flake8: noqa
# mypy: ignore-errors
# pylint: skip-file
"""
An ontology definition for the event relation.
Automatically generated ontology event_coref_ontology. Do not change manually.
"""

from forte.data.data_pack import DataPack
from forte.data.multi_pack import MultiPack
from forte.data.ontology.core import Entry
from ft.onto.base_ontology import CrossDocEventRelation
from ft.onto.base_ontology import EventMention
from typing import Optional


__all__ = [
    "EventMention",
    "CrossEventRelation",
]


class EventMention(EventMention):
    """
    A span based annotation `EventMention`, used to refer to a mention of an event.
    Attributes:
        _is_valid (Optional[bool])
    """
    def __init__(self, pack: DataPack, begin: int, end: int):
        super().__init__(pack, begin, end)
        self._is_valid: Optional[bool] = None

    def __getstate__(self): 
        state = super().__getstate__()
        state['is_valid'] = state.pop('_is_valid')
        return state

    def __setstate__(self, state): 
        super().__setstate__(state)
        self._is_valid = state.get('is_valid', None) 

    @property
    def is_valid(self):
        return self._is_valid

    @is_valid.setter
    def is_valid(self, is_valid: Optional[bool]):
        self.set_fields(_is_valid=is_valid)


class CrossEventRelation(CrossDocEventRelation):
    """
    Represent relation cross documents.
    Attributes:
        _evidence (Optional[str])
    """
    ParentType = EventMention

    ChildType = EventMention

    def __init__(self, pack: MultiPack, parent: Optional[Entry] = None, child: Optional[Entry] = None):
        super().__init__(pack, parent, child)
        self._evidence: Optional[str] = None

    def __getstate__(self): 
        state = super().__getstate__()
        state['evidence'] = state.pop('_evidence')
        return state

    def __setstate__(self, state): 
        super().__setstate__(state)
        self._evidence = state.get('evidence', None) 

    @property
    def evidence(self):
        return self._evidence

    @evidence.setter
    def evidence(self, evidence: Optional[str]):
        self.set_fields(_evidence=evidence)
