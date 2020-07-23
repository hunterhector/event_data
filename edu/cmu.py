# ***automatically_generated***
# ***source json:../event_data/event_ontology.json***
# flake8: noqa
# mypy: ignore-errors
# pylint: skip-file
"""
An ontology definition for the event relation.
Automatically generated ontology event_coref_ontology. Do not change manually.
"""

from dataclasses import dataclass
from forte.data.data_pack import DataPack
from forte.data.multi_pack import MultiPack
from forte.data.ontology.core import Entry
from forte.data.ontology.core import FList
from forte.data.ontology.top import Annotation
from forte.data.ontology.top import MultiPackGeneric
from ft.onto.base_ontology import CrossDocEventRelation
from ft.onto.base_ontology import EventMention
from typing import List
from typing import Optional

__all__ = [
    "EventMention",
    "EvidenceSpan",
    "Question",
    "CorefQuestion",
    "SuggestionQuestion",
    "CrossEventRelation",
]


@dataclass
class EventMention(EventMention):
    """
    A span based annotation `EventMention`, used to refer to a mention of an event.
    Attributes:
        importance (Optional[float])
    """

    importance: Optional[float]

    def __init__(self, pack: DataPack, begin: int, end: int):
        super().__init__(pack, begin, end)
        self.importance: Optional[float] = None


@dataclass
class EvidenceSpan(Annotation):
    """
    A span based annotation, used to refer to an evidence span.
    """

    def __init__(self, pack: DataPack, begin: int, end: int):
        super().__init__(pack, begin, end)


@dataclass
class Question(MultiPackGeneric):
    """
    Represent questions.
    Attributes:
        question_body (Optional[str])
        options (List[str])
    """

    question_body: Optional[str]
    options: List[str]

    def __init__(self, pack: MultiPack):
        super().__init__(pack)
        self.question_body: Optional[str] = None
        self.options: List[str] = []


@dataclass
class CorefQuestion(Question):
    """
    Represent questions to ask for coreference evidence
    """

    def __init__(self, pack: MultiPack):
        super().__init__(pack)


@dataclass
class SuggestionQuestion(Question):
    """
    Represent questions when providing suggestions.
    """

    def __init__(self, pack: MultiPack):
        super().__init__(pack)


@dataclass
class CrossEventRelation(CrossDocEventRelation):
    """
    Represent relation cross documents.
    Attributes:
        coref_questions (FList[CorefQuestion])
        coref_answers (List[int])
        suggest_questions (FList[SuggestionQuestion])
        suggest_answers (List[int])
    """

    coref_questions: FList[CorefQuestion]
    coref_answers: List[int]
    suggest_questions: FList[SuggestionQuestion]
    suggest_answers: List[int]

    ParentType = EventMention
    ChildType = EventMention

    def __init__(self, pack: MultiPack, parent: Optional[Entry] = None, child: Optional[Entry] = None):
        super().__init__(pack, parent, child)
        self.coref_questions: FList[CorefQuestion] = FList(self)
        self.coref_answers: List[int] = []
        self.suggest_questions: FList[SuggestionQuestion] = FList(self)
        self.suggest_answers: List[int] = []
