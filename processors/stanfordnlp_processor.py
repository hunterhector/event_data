# Copyright 2019 The Forte Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
adapted from forte.processors.stanfordnlp_processor
only runs on the text part of BodySpan
"""
import logging
from typing import List, Any, Dict

import stanza
from forte.common.configuration import Config
from forte.common.resources import Resources
from forte.data.data_pack import DataPack
from forte.processors.base import PackProcessor
from ft.onto.base_ontology import Token, Sentence, Dependency

from edu.cmu import BodySpan

__all__ = [
    "StandfordNLPProcessor",
]


class StandfordNLPProcessor(PackProcessor):
    def __init__(self):
        super().__init__()
        self.nlp = None
        self.processors = set()

    def set_up(self):
        stanza.download(self.configs.lang, self.configs.dir)
        self.processors = set(self.configs.processors.split(","))

    # pylint: disable=unused-argument
    def initialize(self, resources: Resources, configs: Config):
        super().initialize(resources, configs)
        self.set_up()
        self.nlp = stanza.Pipeline(
            lang=self.configs.lang,
            dir=self.configs.dir,
            use_gpu=self.configs.use_gpu,
            processors=self.configs.processors,
        )

    @classmethod
    def default_configs(cls) -> Dict[str, Any]:
        """
        This defines a basic config structure for StanfordNLP.
        :return:
        """
        config = super().default_configs()
        config.update(
            {
                "processors": "tokenize,pos,lemma,depparse",
                "lang": "en",
                # Language code for the language to build the Pipeline
                "use_gpu": False,
                "dir": ".",
            }
        )
        return config

    def _process(self, input_pack: DataPack):

        # document "body" is different document "text"
        # "body" constitutes the part of a document that should be processed into Tokens, Sentences
        # potential content outside of "body" can include title, document date etc.,
        # such information is still visible as the part of document "text"
        body = list(input_pack.get(BodySpan))[0]
        doc = body.text
        doc_offset = body.begin

        if len(doc) == 0:
            logging.warning("Find empty text in doc.")

        # sentence parsing
        sentences = self.nlp(doc).sentences

        # Iterating through stanfordnlp sentence objects
        for sentence in sentences:
            Sentence(
                input_pack,
                doc_offset + sentence.tokens[0].start_char,
                doc_offset + sentence.tokens[-1].end_char,
            )

            tokens: List[Token] = []
            if "tokenize" in self.processors:
                # Iterating through stanfordnlp word objects
                for word in sentence.words:
                    misc = word.misc.split("|")

                    t_start = -1
                    t_end = -1
                    for m in misc:
                        k, v = m.split("=")
                        if k == "start_char":
                            t_start = int(v)
                        elif k == "end_char":
                            t_end = int(v)

                    if t_start < 0 or t_end < 0:
                        raise ValueError(
                            "Cannot determine word start or end for " "stanfordnlp."
                        )

                    token = Token(input_pack, doc_offset + t_start, doc_offset + t_end)

                    if "pos" in self.processors:
                        token.pos = word.pos
                        token.ud_xpos = word.xpos

                    if "lemma" in self.processors:
                        token.lemma = word.lemma

                    tokens.append(token)

            # For each sentence, get the dependency relations among tokens
            if "depparse" in self.processors:
                # Iterating through token entries in current sentence
                for token, word in zip(tokens, sentence.words):
                    child = token  # current token
                    parent = tokens[word.head - 1]  # Head token
                    relation_entry = Dependency(input_pack, parent, child)
                    relation_entry.rel_type = word.deprel
