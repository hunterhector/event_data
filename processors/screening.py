"""
Create screening test for MTurk HIT
For each test, we randomly sample 7 from a pool of 20 questions.
"""

import random
from pathlib import Path
from argparse import ArgumentParser
import xml.etree.ElementTree as ET
from copy import deepcopy


class QualificationTest:
    """
    A qualification test based on a pool of pre-specified questions
    """

    OVERVIEW_FORMAT = (
        "<![CDATA["
        " <p>"
        " In this test, we ask you to identify whether two events (<b>highlighted</b> in each paragraph) indicate the same thing or not."
        " Read each paragraph carefully and answer the question by selecting the appropriate option, <i>Yes</i> or <i>No</i>."
        " <br /><br />"
        " In total, you are presented with %d questions and the time limit for this test is 20 minutes."
        " After submitting the test, you are automatically scored. If passed, you can accept any number of our HITs."
        " <br /><br />"
        " <b>Note</b>: It is important you do this test on your own because our HITs are similar to the questions presented in this test."
        " <br /><br />"
        " For your reference, we provide five examples below,"
        " <br /><br />"
        " He <b>died</b> of injuries from the accident. His friends were all saddened to hear his <b>death</b>."
        " <br /><br />"
        " <i>Question</i>: In the above paragraph, are the highlighted events the same?"
        " <br />"
        " <i>Answer</i>: Yes (both words, <b>died</b> and <b>death</b> indicate the person's death)"
        " <br /><br />"
        " The suspect was <b>shot</b> and killed in the <b>raid</b> by the armed officers."
        " <br /><br />"
        " <i>Question</i>: In the above paragraph, are the highlighted events the same?"
        " <br />"
        " <i>Answer</i>: No (<b>shot</b> happened during the <b>raid</b>)"
        " <br /><br />"
        " The couple had been planning to <b>go</b> to Paris for a long time. They finally <b>went</b> there last month."
        " <br /><br />"
        " <i>Question</i>: In the above paragraph, are the highlighted events the same?"
        " <br />"
        " <i>Answer</i>: Yes (The two events do not have to take place at the same time. Here, <b>go</b> would happen in the future, and <b>went</b> did occur.)"
        " <br /><br />"
        " John <b>gave</b> a gift to Mary. Mary <b>received</b> a gift from John."
        " <br /><br />"
        " <i>Question</i>: In the above paragraph, are the highlighted events the same?"
        " <br />"
        " <i>Answer</i>: Yes (Same events described from different perspectives.)"
        " <br /><br />"
        " Following  the trial of Mahammed Alameh, the first suspect in the <b>bombing</b>, investigators discovered a jumble of chemicals, chemistry implements and detonating materials. The <b>explosion</b> killed at least five people."
        " <br /><br />"
        " <i>Question</i>: In the above paragraph, are the highlighted events the same?"
        " <br />"
        " <i>Answer</i>: No (One event is part of the other larger event. <b>bombing</b> refers to the entire process which starts with making a bomb and ends with destructions, damages and injuries, while <b>explosion</b> is a smaller event that occurs in that processes.)"
        " <br /><br />"
        " </p>"
        " ]]>"
    )
    QUESTION_FORMAT = (
        "<![CDATA["
        " <p>"
        " %s"
        " <br /><br />"
        " <i>Question</i>: In the above paragraph, are the highlighted events the same?"
        " <br />"
        " </p>"
        " ]]>"
    )
    QUESTION_SCHEMA = "http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2017-11-06/QuestionForm.xsd"
    ANSWER_SCHEMA = "http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/AnswerKey.xsd"
    MTURK_SANDBOX = "https://mturk-requester-sandbox.us-east-1.amazonaws.com"

    def __init__(
        self, template_path: Path, questions_path: Path, k: int = 8,
    ):

        self.template_path = Path(template_path)
        self.questions_path = Path(questions_path)
        self.k = k

        self.question_element = None
        self.questions_xml = None
        self.question_xml_root = None
        self.answer_element = None
        self.answers_xml = None
        self.answers_xml_root = None
        self.scorer = None

        self._read_templates()
        self._create_questionnaire()

    def _read_questions(self, file_path):
        questions = []
        with open(file_path, "r") as rf:
            for idx, line in enumerate(rf):
                q, a, qtype = line.strip().split("\t")
                questions.append((idx, q, a, qtype))

        questions = questions[1:]  # removing header line
        return questions

    def _add_question(self, q_id, q_txt):

        q = deepcopy(self.question_element)

        q.find("QuestionIdentifier").text = f"Q_{q_id}"
        q.find("QuestionContent").find("FormattedContent").text = (
            self.QUESTION_FORMAT % q_txt
        )
        self.question_xml_root.append(q)

    def _add_answer(self, q_id, a_txt):

        a = deepcopy(self.answer_element)

        a.find("QuestionIdentifier").text = f"Q_{q_id}"
        a.find("AnswerOption").find("SelectionIdentifier").text = a_txt
        self.answers_xml_root.append(a)

        cur_score = int(
            self.scorer.find("PercentageMapping").find("MaximumSummedScore").text
        )
        self.scorer.find("PercentageMapping").find(
            "MaximumSummedScore"
        ).text = f"{cur_score+1}"

    def _add_meta_info(self):
        q_overview = self.question_xml_root.find("Overview")
        q_overview.find("Title").text = "Screening Test"
        q_overview.find("FormattedContent").text = self.OVERVIEW_FORMAT % self.k
        self.answers_xml_root.append(self.scorer)

    def _read_templates(self):

        self.questions_xml = ET.parse(self.template_path / "questions_template.xml")
        questions_xml_root = self.questions_xml.getroot()
        self.answers_xml = ET.parse(self.template_path / "answers_template.xml")
        answers_xml_root = self.answers_xml.getroot()

        self.question_element = questions_xml_root.find(f"Question")
        self.answer_element = answers_xml_root.find(f"Question")
        self.scorer = answers_xml_root.find("QualificationValueMapping")

        questions_xml_root.remove(self.question_element)  # remove template question
        answers_xml_root.remove(self.answer_element)  # remove template answer
        answers_xml_root.remove(self.scorer)  # remove scorer, to be added later
        self.question_xml_root = questions_xml_root
        self.answers_xml_root = answers_xml_root

    def _create_questionnaire(self):

        all_questions = self._read_questions(self.questions_path)
        sampled_questions = random.sample(all_questions, k=self.k)

        for sample in sampled_questions:
            self._add_question(sample[0], sample[1])
            self._add_answer(sample[0], sample[2])

        self._add_meta_info()

        self.answers_xml_root.attrib["xmlns"] = self.ANSWER_SCHEMA
        self.question_xml_root.attrib["xmlns"] = self.QUESTION_SCHEMA

    def write_xml(self, questions_path, answerkey_path) -> None:

        self.questions_xml.write(questions_path)
        self.answers_xml.write(answerkey_path)

    def get_questions(self) -> str:
        return (
            ET.tostring(self.question_xml_root)
            .decode("utf-8")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )

    def get_answers(self) -> str:
        return (
            ET.tostring(self.answers_xml_root)
            .decode("utf-8")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )


if __name__ == "__main__":
    parser = ArgumentParser(
        description="create question and answer key .xml files for use in HITs"
    )
    parser.add_argument(
        "--templates",
        type=Path,
        help="path to the directory containing templates for question, answer xml",
    )
    parser.add_argument("--questions", type=Path, help="path to questions .tsv")
    parser.add_argument(
        "--out-questions",
        type=Path,
        help="path to write sampled questions in .xml format",
    )
    parser.add_argument(
        "--out-answers", type=Path, help="path to write answer key in .xml format"
    )
    parser.add_argument("-n", type=int, default=8, help="number of questions to sample")

    args = parser.parse_args()

    qual_test = QualificationTest(args.templates, args.questions, k=args.n)
    qual_test.write_xml(args.out_questions, args.out_answers)
