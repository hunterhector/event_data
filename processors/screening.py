"""
Create screening test for MTurk HIT
For each test, we randomly sample 7 from a pool of 20 questions.
"""

import random
from pathlib import Path
from argparse import ArgumentParser
import xml.etree.ElementTree as ET
from copy import deepcopy


def read_questions(file_path):
    questions = []
    with open(file_path, "r") as rf:
        for idx, line in enumerate(rf):
            q, a, qtype = line.strip().split("\t")
            questions.append((idx, q, a, qtype))

    questions = questions[1:]  # removing header line

    return questions


def add_question(q_id, q_txt, q_elm, q_xml):

    q = deepcopy(q_elm)

    q.find("QuestionIdentifier").text = f"Q_{q_id}"
    q.find("QuestionContent").find(
        "FormattedContent"
    ).text = f"<![CDATA[ \
<p> \
{q_txt} \
<br /><br /> \
<i>Question</i>: In the above paragraph, are the highlighted events the same? \
<br /> \
</p> \
]]>"

    q_xml.append(q)


def add_answer(q_id, a_txt, a_elm, a_xml):

    a = deepcopy(a_elm)

    a.find("QuestionIdentifier").text = f"Q_{q_id}"
    a.find("AnswerOption").find("SelectionIdentifier").text = a_txt

    a_xml.append(a)

    cur_score = int(
        a_xml.find("QualificationValueMapping")
        .find("PercentageMapping")
        .find("MaximumSummedScore")
        .text
    )
    a_xml.find("QualificationValueMapping").find("PercentageMapping").find(
        "MaximumSummedScore"
    ).text = f"{cur_score+1}"


def add_meta_info(q_xml, k):
    q_overview = q_xml.find("Overview")
    q_overview.find("Title").text = "Screening Test"
    q_overview.find(
        "FormattedContent"
    ).text = f"<![CDATA[ \
<p> \
In this test, we ask you to identify whether two events (<b>highlighted</b> in each paragraph) indicate the same thing or not. \
Read each paragraph carefully and answer the question by selecting the appropriate option, <i>Yes</i> or <i>No</i>. \
<br /><br /> \
In total, you are presented with {k} questions and time limit for this test is 10 minutes. \
After submitting the test, you are automatically scored. If passed, you can continue to solving any number of our HITs. \
<br /><br /> \
<b>Note</b>: It is important you do this test on your own because our HITs are similar to the questions presented in this test. \
<br /><br /> \
For your reference, we provide two examples below, \
<br /><br /> \
He <b>died</b> of injuries from the accident. His friends were all saddened to hear his <b>death</b>. \
<br /><br /> \
<i>Question</i>: In the above paragraph, are the highlighted events the same? \
<br /> \
<i>Answer</i>: Yes (both words, <b>died</b> and <b>death</b> indicate the person's death) \
<br /><br /> \
He was <b>shot</b> and dead in the <b>shooting</b>. \
<br /><br /> \
<i>Question</i>: In the above paragraph, are the highlighted events the same? \
<br /> \
<i>Answer</i>: No (<b>shot</b> happened during the <b>shooting</b>) \
<br /><br /> \
</p> \
]]>"


def prepare_questionnaire(source_path, qs_path, ans_path, k):

    all_questions = read_questions(source_path / "cdec_screening_test.tsv")
    sampled_questions = random.sample(all_questions, k=k)

    questions_xml = ET.parse(source_path / "questions_template.xml")
    questions_xml_root = questions_xml.getroot()
    answers_xml = ET.parse(source_path / "answers_template.xml")
    answers_xml_root = answers_xml.getroot()
    QUESTION_SCHEMA = "{http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2017-11-06/QuestionForm.xsd}"
    ANSWER_SCHEMA = "{http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/AnswerKey.xsd}"

    question_elm = questions_xml_root.find(f"Question")
    answer_elm = answers_xml_root.find(f"Question")
    questions_xml_root.remove(question_elm)  # remove template question
    answers_xml_root.remove(answer_elm)  # remove template answer

    for sample in sampled_questions:
        add_question(sample[0], sample[1], question_elm, questions_xml_root)
        add_answer(sample[0], sample[2], answer_elm, answers_xml_root)

    add_meta_info(questions_xml_root, k)

    answers_xml_root.attrib["xmlns"] = ANSWER_SCHEMA
    questions_xml_root.attrib["xmlns"] = QUESTION_SCHEMA
    questions_xml.write(qs_path)
    answers_xml.write(ans_path)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="create question and answer key .xml files for use in HITs"
    )
    parser.add_argument(
        "-s",
        type=Path,
        help="path to the directory containing questions and templates for question,answer xml templates",
    )
    parser.add_argument(
        "-q", type=Path, help="path to write sampled questions in .xml format",
    )
    parser.add_argument("-a", type=Path, help="path to write answer key in .xml format")
    parser.add_argument("-n", default=10, help="number of questions to sample")

    args = parser.parse_args()

    prepare_questionnaire(args.s, args.q, args.a, args.n)
