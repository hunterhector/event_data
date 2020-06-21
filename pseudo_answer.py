"""
In this file we mimics the answers of those coreference and suggestion
questions. The purpose is to create the data for debugging and front end
development.
"""
import random

from forte.data.multi_pack import MultiPack
from forte.processors.base import MultiPackProcessor

from edu.cmu import CrossEventRelation, CorefQuestion, SuggestionQuestion


class ExampleQuestionAnswerer(MultiPackProcessor):
    """
    This processor tries to answer the questions randomly, as an example.
    """

    def _process(self, input_pack: MultiPack):
        i = 0
        link: CrossEventRelation

        for link in input_pack.get(CrossEventRelation):
            i += 1

            if i > 5:
                # Just arbitrarily take the last 5 as coreference.
                link.rel_type = 'coref'

                # Take all coref questions and answer them.
                q: CorefQuestion
                for q in input_pack.get(CorefQuestion):
                    link.coref_questions.append(q)
                    # Take a random answer.
                    link.coref_answers.append(
                        random.choice(range(len(q.options) - 1)))
            elif i == 5:
                # Let's accept system suggestion on the 5th one.
                for q in input_pack.get(SuggestionQuestion):
                    # First, take the system's suggestion. Use -1 here to
                    #  accept suggestion.
                    link.suggest_questions.append(q)
                    link.suggest_answers.append(-1)

                # Second, answer the coreference questions again
                for q in input_pack.get(CorefQuestion):
                    link.coref_questions.append(q)
                    # Take a random answer.
                    link.coref_answers.append(
                        random.choice(range(len(q.options) - 1)))
            else:
                # And the rest to be not coreference, so reject the suggestion
                #  with random reason.
                for q in input_pack.get(SuggestionQuestion):
                    link.suggest_questions.append(q)
                    link.suggest_answers.append(
                        random.choice(range(len(q.options) - 1))
                    )
