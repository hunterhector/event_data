from forte.data.multi_pack import MultiPack
from forte.processors.base import MultiPackProcessor

from edu.cmu import CrossEventRelation, CorefQuestionAnswers, CorefQuestion, \
    SuggestionQuestionAnswers, SuggestionQuestion


class ExampleQuestionAnswerer(MultiPackProcessor):
    """
    This processor tries to answer the questions randomly, as an example.
    """

    def _process(self, input_pack: MultiPack):
        i = 0
        link: CrossEventRelation
        for link in input_pack.get(CrossEventRelation):
            i += 1
            if i >= 5:
                link.rel_type = 'coref'
                qa = CorefQuestionAnswers(input_pack)
                for q in input_pack.get(CorefQuestion):
                    qa.question = q
                    qa.answer = 0  # always YES.
                link.coref_answers.append(qa)
            else:
                qa = SuggestionQuestionAnswers(input_pack)
                for q in input_pack.get(SuggestionQuestion):
                    qa.question = q
                    qa.answer = 1  # always NO.
                link.suggest_answers.append(qa)
