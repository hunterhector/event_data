from forte.data.multi_pack import MultiPack
from forte.processors.base import MultiPackProcessor

from edu.cmu import CorefQuestion, SuggestionQuestion


class QuestionCreator(MultiPackProcessor):
    """
        Create questions for the coreference tasks.
    """

    def _process(self, input_pack: MultiPack):
        q = CorefQuestion(input_pack)
        q.question_body = 'Place: Do you think the two events ' \
                          'happen at the same place?'
        q.options = [
            'Exactly the same', 'The places overlap',
            'Not at all', 'Cannot determine',
        ]
        input_pack.add_entry(q)

        q = CorefQuestion(input_pack)
        q.question_body = 'Time: Do you think the two events ' \
                          'happen at the same time?'
        q.options = [
            'Exactly the same', 'They overlap in time',
            'Not at all', 'Cannot determine',
        ]
        input_pack.add_entry(q)

        q = CorefQuestion(input_pack)
        q.question_body = 'Participants: Do you think the two events' \
                          ' have the same participants?'
        q.options = [
            'Exactly the same', 'They share some participants',
            'Not at all', 'Cannot determine',
        ]
        input_pack.add_entry(q)

        q = CorefQuestion(input_pack)
        q.question_body = 'Inclusion: Do you think one of the events' \
                          ' contain the other?'
        q.options = [
            'Yes, left fully contains right',
            'Yes, right fully contains left',
            'No, they are exactly the same',
            'Cannot determine',
        ]
        input_pack.add_entry(q)

        q = SuggestionQuestion(input_pack)
        q.question_body = 'You consider these two to be different, ' \
                          'could you tell us why?'
        q.options = [
            'One event contains the other.',
            'Some event details (e.g. time, location, participants) '
            'are conflicting.',
            'There is no enough information.',
            'The two events are completely un-related.'
            'Other reasons',
        ]
        input_pack.add_entry(q)
