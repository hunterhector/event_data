import boto3
import sys
import json

sys.path.append("../")
from credentials import MTURK_ACCESS_KEY, MTURK_SECRET_KEY
from processors.screening import QualificationTest
from processors.hit_layout import HITLayout

MTURK_SANDBOX = "https://mturk-requester-sandbox.us-east-1.amazonaws.com"
WORKER_ID = "A2FA52DZEKT1A6"
DUMMY_QUAL_ID = "3AWO4KN9YVPTD3XZ8M9M0YYXIP29I1"
SCREENING_QUAL_ID = "35BVO3HY7ZUYZ9HZ7T85FNORQRY9VY"
HASH_ID = "99f9c010b74843324f0aab6b06df8add65ef03e8c5bda93bdad55283fe8fdf7f"


def add_qualification(
    mturk_client, qualification_id: str, worker_id: str, bool_send_not: bool = False
):
    response = mturk_client.associate_qualification_with_worker(
        QualificationTypeId=qualification_id,
        WorkerId=worker_id,
        SendNotification=bool_send_not,
    )
    return response


def remove_qualification(
    mturk_client, qualification_id: str, worker_id: str, reason: str = "testing"
):
    response = mturk_client.disassociate_qualification_from_worker(
        QualificationTypeId=qualification_id, WorkerId=worker_id, Reason=reason
    )
    return response


def create_dummy_qual(mturk_client):
    global DUMMY_QUAL_ID
    response = mturk_client.create_qualification_type(
        Name="Dummy qualification",
        Description="Dummy qualification",
        QualificationTypeStatus="Active",
    )
    DUMMY_QUAL_ID = response["QualificationType"]["QualificationTypeId"]
    print(DUMMY_QUAL_ID)


def create_screening_test(mturk_client, config):
    global SCREENING_QUAL_ID
    qual_test = QualificationTest(
        config["screening"]["template_path"],
        config["screening"]["questions_path"],
        k=config["screening"]["num_questions"],
    )
    questions = qual_test.get_questions()
    answers = qual_test.get_answers()
    qual_test.write_xml("question.xml", "answer.xml")

    response = mturk_client.create_qualification_type(
        Name=config["screening"]["Name"],
        Description=config["screening"]["Description"],
        QualificationTypeStatus="Active",
        Test=questions,
        AnswerKey=answers,
        TestDurationInSeconds=config["screening"]["TestDurationInSeconds"],
    )
    SCREENING_QUAL_ID = response["QualificationType"]["QualificationTypeId"]
    print(SCREENING_QUAL_ID)


def create_HIT(mturk_client, config, hashID: str):
    hit_layout = HITLayout(
        config["hit_setup"]["HIT_template"], config["stave_url"] % hashID
    )
    hit_string = hit_layout.get_hit_string()
    hit_layout.write_xml("tmp_hit.xml")
    # DUMMY_ID s.t only I can see the task on sandbox
    qualification_requirements = [
        {
            "QualificationTypeId": DUMMY_QUAL_ID,
            "Comparator": "Exists",
            "ActionsGuarded": "DiscoverPreviewAndAccept",
        },
        {
            "QualificationTypeId": SCREENING_QUAL_ID,
            "Comparator": "GreaterThanOrEqualTo",
            "IntegerValues": [config["screening"]["score_percent_threshold"]],
            "ActionsGuarded": "PreviewAndAccept",
        },
    ]

    new_hit = mturk_client.create_hit(
        MaxAssignments=config["hit_setup"]["MaxAssignments"],  # required
        AutoApprovalDelayInSeconds=config["hit_setup"]["AutoApprovalDelayInSeconds"],
        LifetimeInSeconds=config["hit_setup"]["LifetimeInSeconds"],  # life time
        AssignmentDurationInSeconds=config["hit_setup"][
            "AssignmentDurationInSeconds"
        ],  # time to complete the HIT
        Reward=config["hit_setup"]["Reward"],  # string us dollar
        Title=config["hit_setup"]["Title"],  #
        Keywords=config["hit_setup"]["Keywords"],
        Description=config["hit_setup"]["Description"],
        QualificationRequirements=qualification_requirements,
        Question=hit_string,
    )
    print(new_hit["HIT"]["HITId"])


if __name__ == "__main__":

    with open("configs/mturk_test.json", "r") as rf:
        config = json.load(rf)

    mturk_client = boto3.client(
        "mturk",
        aws_access_key_id=MTURK_ACCESS_KEY,
        aws_secret_access_key=MTURK_SECRET_KEY,
        region_name="us-east-1",
        endpoint_url=MTURK_SANDBOX,
    )

    # create_dummy_qual(mturk_client)
    # add_qualification(mturk_client, DUMMY_QUAL_ID, WORKER_ID, False)
    # remove_qualification(mturk_client, DUMMY_QUAL_ID, WORKER_ID)
    # create_screening_test(mturk_client, config)
    create_HIT(mturk_client, config, hashID=HASH_ID)

