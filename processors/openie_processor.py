"""
Adapted from `forte/forte/processors/allennlp_processors.py`
"""

import logging

from allennlp.predictors.predictor import Predictor

from forte.data.data_pack import DataPack
from forte.processors.base import PackProcessor
from ft.onto.base_ontology import Token, Sentence
from forte.common.configuration import Config
from forte.common.resources import Resources

from typing import Dict, Any, List

logger = logging.getLogger(__name__)

__all__ = [
    "AllenNLPEventProcessor",
]

MODEL2URL = {
    "openie": "https://storage.googleapis.com/allennlp-public-models/openie-model.2020.03.26.tar.gz",
    "srl": "https://storage.googleapis.com/allennlp-public-models/bert-base-srl-2020.03.24.tar.gz",
}


class AllenNLPEventProcessor(PackProcessor):
    """
    Event detection processor
    """

    def initialize(self, resources: Resources, configs: Config):
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
        # TODO: handle existing entries?

        sentences, sentences_txt = [], []
        for sentence in input_pack.get(Sentence):
            sentences.append(sentence)
            sentences_txt.append({"sentence": sentence.text})

        # skipping title and date
        sentences = sentences[2:]
        sentences_txt = sentences_txt[2:]

        predictions = self.predictor.predict_batch_json(sentences_txt)

        for sentence, prediction in zip(sentences, predictions):
            self._create_event_mentions(input_pack, sentence, prediction)

    def _create_event_mentions(
        self, input_pack: DataPack, sentence: Sentence, result: Dict[str, Any]
    ) -> None:

        words = result["words"]
        offset = sentence.span.begin

        # TODO: check if len(words) == tokens in sentence

        """ create EventMention instances for all the verb (event) tokens """
        for result_predicate in result["verbs"]:

            tags = result_predicate["tags"]
            if "B-V" not in tags:
                continue

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
                evm = EventMention(input_pack, offset + event_begin, offset + event_end)
                evm.importance = 1.0
                evm.event_type = "OpenIE"
