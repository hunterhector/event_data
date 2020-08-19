from forte.data.multi_pack import MultiPack
from forte.processors.base import MultiPackProcessor

from edu.cmu import CorefQuestion, SuggestionQuestion


class QuestionCreator(MultiPackProcessor):
    """
        Create questions for the coreference tasks.
    """

    def _process(self, input_pack: MultiPack):
        coref_questions = [
            'Do you find both location are identical?',
            'Do you find the time on both events are identical?',
            'Do you find the participants are the same?',
            'Do you think one of the event may include another one?'
        ]

        for q_t in coref_questions:
            q = CorefQuestion(input_pack)
            q.question_body = q_t
            q.options = [
                'Yes', 'No', 'Probably', 'Cannot determine',
            ]
            input_pack.add_entry(q)

        q = SuggestionQuestion(input_pack)
        q.question_body = 'Why do you think these two events are different?'
        q.options = [
            'They are not really relevant.',
            'There is no enough information to determine that.',
            'Some event details are conflicting.',
        ]
        input_pack.add_entry(q)
