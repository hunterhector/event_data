#!/usr/bin/python3
import boto3
from tinydb import TinyDB, Query, where
import sys, os
import sqlite3
import hashlib
from argparse import ArgumentParser
import json

sys.path.insert(0, os.path.abspath(".."))

# need file credentials.py
# need file .yaml? for configuration --- include

from credentials import (
    MTURK_ACCESS_KEY,
    MTURK_SECRET_KEY,
    # SNS_TOPIC_ID,
    # MTURK_EVENT_BLOCKED_QUAL_ID,
    SPECIAL_QUAL_ID,
)
from screening import QualificationTest
from hit_layout import HITLayout


class CrowdSourceAnnotationModule:
    """
    This class is used for .....
    """

    STACK_TABLE_NAME = "stack_target"
    PAST_TASKS_TABLE_NAME = "past_tasks"
    LOGGING_TABLE_NAME = "logging"
    ROUND_DOC_TABLE_NAME = "round_doc"
    QUAL_TABLE_NAME = "mturk_qualifications"
    MTURK_SANDBOX = "https://mturk-requester-sandbox.us-east-1.amazonaws.com"
    ANNOTATOR_GROUP_DESCRIPTION = "Qualification created for task logistics"

    def __init__(self, stave_db_path, mturk_db_path, config):  # config_file?
        # config
        self.config = config
        # read input files
        self.stave_db_path = stave_db_path
        self.number_of_copys = 3
        self.participant_criterion = {}
        self.screened_participants = []  # list of participantIDs
        self.task_distributor = []  # could take several formats
        self.is_sandbox_testing = self.config["sandbox"]
        self.debug_flag = True
        db = TinyDB(mturk_db_path)  # store all part list
        self.stack_target_table = db.table(self.STACK_TABLE_NAME, cache_size=0)
        self.past_task_table = db.table(self.PAST_TASKS_TABLE_NAME, cache_size=0)
        self.logging_table = db.table(self.LOGGING_TABLE_NAME, cache_size=0)
        self.round_doc_table = db.table(self.ROUND_DOC_TABLE_NAME, cache_size=0)
        self.mturk_qual_table = db.table(self.QUAL_TABLE_NAME, cache_size=0)
        # region_name ???

        self.SCREENING_QUAL_ID = None
        s = self.mturk_qual_table.search(where("qualification_type") == "screening")
        assert len(s) <= 1, "more than one screening qualification"
        if len(s) == 1:
            self.SCREENING_QUAL_ID = s[0]["id"]

        if self.is_sandbox_testing:
            print("running sandbox")
            self.mturk_client = boto3.client(
                "mturk",
                aws_access_key_id=MTURK_ACCESS_KEY,
                aws_secret_access_key=MTURK_SECRET_KEY,
                region_name="us-east-1",
                endpoint_url=self.MTURK_SANDBOX,  # this uses Mturk's sandbox
            )
        else:
            print("running on actual AMT")
            self.mturk_client = boto3.client(
                "mturk",
                aws_access_key_id=MTURK_ACCESS_KEY,
                aws_secret_access_key=MTURK_SECRET_KEY,
                region_name="us-east-1",
            )
        # might need to load from static if groups created ahead
        base_query = Query()
        if db.search(base_query.annotator_group_IDs.exists()) == []:
            self.annotator_group_IDs = self.create_annotator_groups()
            db.insert({"annotator_group_IDs": self.annotator_group_IDs})
        else:
            record = db.search(base_query.annotator_group_IDs.exists())[0]
            self.annotator_group_IDs = record["annotator_group_IDs"]

        # load round_size from db or query seed set size from stave_db
        if db.search(base_query.round_size.exists()) == []:
            # need to query for seed set size
            print(self.round_doc_table.search(base_query.round_assigned == 0))
            self.round_size = len(
                self.round_doc_table.search(base_query.round_assigned == 0)
            )
            db.insert({"round_size": self.round_size})
        else:
            record = db.search(base_query.round_size.exists())[0]
            self.round_size = record["round_size"]

    def create_annotator_groups(
        self, name="ANNOTATORGROUP%02d", description=ANNOTATOR_GROUP_DESCRIPTION
    ):
        annotator_group_IDs = []
        for i in range(self.number_of_copys):
            # annotator_group_IDs += [name % i]
            try:
                response = self.mturk_client.create_qualification_type(
                    Name=(name % i),
                    Description=description,
                    QualificationTypeStatus="Active",
                )
                # TODO: try catch here?
                qual_id = response["QualificationType"]["QualificationTypeId"]
                annotator_group_IDs += [qual_id]
            except:
                e = sys.exc_info()[0]
                print(e)

        return annotator_group_IDs

    def add_qualification(self, qualification_id, worker_id, bool_send_not):
        response = self.mturk_client.associate_qualification_with_worker(
            QualificationTypeId=qualification_id,
            WorkerId=worker_id,
            IntegerValue=1,
            SendNotification=bool_send_not,
        )
        return response

    def _get_annotation_pairs_for_round_prefixed(self, round_num):
        """
        document pairs are pre-assigned rounds
        here, we just load the pairs assigned to `round_num`
        """
        pairs = self.round_doc_table.search(where("round_assigned") == round_num)
        round_hash_reward_values = []
        for pair in pairs:
            round_hash_reward_values += [(pair["hashed"], str(pair["reward"]))]
        return round_hash_reward_values

    def publish_hit(
        self, website_url, annotator_group_ID, reward, is_first_round=False
    ):

        # preparing the hit_layout
        hit_layout = HITLayout(self.config["hit_setup"]["HIT_template"], website_url)
        hit_string = hit_layout.get_hit_string()

        qualification_requirements = [
            {  # location
                "QualificationTypeId": "00000000000000000071",
                "Comparator": "In",
                "LocaleValues": [{"Country": self.config["qualification"]["country"]}],
                "ActionsGuarded": "PreviewAndAccept",
            },
            {  # # of hit approved
                "QualificationTypeId": "00000000000000000040",
                "Comparator": "GreaterThanOrEqualTo",
                "IntegerValues": [self.config["qualification"]["hits_approved"]],
                "ActionsGuarded": "PreviewAndAccept",  #'Accept'|'DiscoverPreviewAndAccept'
            },
            {  # approval percent
                "QualificationTypeId": "000000000000000000L0",
                "Comparator": "GreaterThanOrEqualTo",
                "IntegerValues": [self.config["qualification"]["percent_approval"]],
                "ActionsGuarded": "PreviewAndAccept",
            },
            {  # screening test
                "QualificationTypeId": self.SCREENING_QUAL_ID,
                "Comparator": "GreaterThanOrEqualTo",
                "IntegerValues": [self.config["screening"]["score_percent_threshold"]],
                "ActionsGuarded": "PreviewAndAccept",
            },
            # {  # not in temporary block
            #     "QualificationTypeId": MTURK_EVENT_BLOCKED_QUAL_ID,
            #     "Comparator": "DoesNotExist",
            #     "ActionsGuarded": "PreviewAndAccept",
            # },
            # {
            #     "QualificationTypeId": SPECIAL_QUAL_ID,
            #     "Comparator": "Exists",
            #     "ActionsGuarded": "DiscoverPreviewAndAccept",
            # },
        ]
        if not is_first_round:
            # annotator groups are empty in the first round
            # annotators from other groups should not be allowed to do this task
            # i.e, only annotators with ID `annotator_group_ID` or new annotators are allowed
            # other annotators can't even discover the HIT
            disallowed_IDs = [
                x for x in self.annotator_group_IDs if x != annotator_group_ID
            ]
            for group_ID in disallowed_IDs:
                qualification_requirements.append(
                    {
                        "QualificationTypeId": group_ID,
                        "Comparator": "DoesNotExist",
                        "ActionsGuarded": "DiscoverPreviewAndAccept",
                    }
                )
        new_hit = self.mturk_client.create_hit(
            MaxAssignments=self.config["hit_setup"]["MaxAssignments"],  # required
            AutoApprovalDelayInSeconds=self.config["hit_setup"][
                "AutoApprovalDelayInSeconds"
            ],
            LifetimeInSeconds=self.config["hit_setup"][
                "LifetimeInSeconds"
            ],  # life time
            AssignmentDurationInSeconds=self.config["hit_setup"][
                "AssignmentDurationInSeconds"
            ],  # time to complete the HIT
            Reward=str(reward),  # string us dollar
            Title=self.config["hit_setup"]["Title"],  #
            Keywords=self.config["hit_setup"]["Keywords"],
            Description=self.config["hit_setup"]["Description"],
            QualificationRequirements=qualification_requirements,
            Question=hit_string,
        )

        # hit_type_id = new_hit["HIT"]["HITTypeId"]
        # notification = {
        #     "Destination": SNS_TOPIC_ID,
        #     "Transport": "SNS",
        #     "Version": "2014-08-15",
        #     "EventTypes": [
        #         "AssignmentSubmitted",
        #         # HITReviewable|AssignmentAccepted|AssignmentAbandoned|AssignmentReturned
        #         # AssignmentRejected|AssignmentApproved|HITCreated|HITExtended|HITDisposed|HITExpired
        #     ],
        # }
        # # Configure Notification settings using the HITTypeId
        # self.mturk_client.update_notification_settings(
        #     HITTypeId=hit_type_id, Notification=notification,
        # )
        if self.debug_flag:
            if self.is_sandbox_testing:
                print(
                    "https://workersandbox.mturk.com/mturk/preview?groupId="
                    + new_hit["HIT"]["HITGroupId"]
                )
            else:
                print(
                    "https://worker.mturk.com/mturk/preview?groupId="
                    + new_hit["HIT"]["HITGroupId"]
                )
            print("HITID = " + new_hit["HIT"]["HITId"] + " (Use to Get Results)")

        # keeping a log of HIT layout
        hit_layout.write_xml(
            f"{self.config['hit_setup']['HIT_template']}/hit_{new_hit['HIT']['HITId']}.xml"
        )

        return new_hit["HIT"]["HITId"]

    def run_round(self):
        annotator_group_idx = 0
        is_first_round = False
        if len(self.stack_target_table) == 0:
            # first round
            nxt_rnd_num = 1
            is_first_round = True
        else:
            last_record = self.stack_target_table.all()[-1]
            if last_record["completed"]:
                # all previous round completed ; start new round
                rnd_num_int = int(last_record["round_number"])
                rnd_num_frc = int(last_record["round_number"] * 10 % 10)
                if rnd_num_int % 2 == 0:
                    if rnd_num_frc == 1:
                        nxt_rnd_num = rnd_num_int + 0.2
                        annotator_group_idx = 2
                    else:  # rnd_num_frc == 2
                        nxt_rnd_num = rnd_num_int + 1
                        annotator_group_idx = 0
                else:
                    annotator_group_idx = 1
                    nxt_rnd_num = rnd_num_int + 1 + 0.1
            else:
                # complete current round
                nxt_rnd_num = last_record["round_number"]
                # TODO: under what circumstances would round not complete?
                print("last round# %.1f not finished" % nxt_rnd_num)
                return

        if self.debug_flag:
            print("running round# %.1f" % nxt_rnd_num)

        annotation_pairs = self._get_annotation_pairs_for_round_prefixed(nxt_rnd_num)
        print(annotation_pairs)

        # publish tasks with #nxt_rnd_num, and take from the article pairs
        self.stack_target_table.insert(
            {
                "round_number": nxt_rnd_num,
                "completed": False,
                "annotator_list": [],
                "completed_hit_count": 0,
                "sent_hit_count": len(annotation_pairs),
            }
        )
        for hash_value, reward in annotation_pairs:
            # prepare qualification test
            self.update_qualification_test(round_number=nxt_rnd_num)
            hit_id = self.publish_hit(
                self.config["stave_url"] % (hash_value),
                self.annotator_group_IDs[annotator_group_idx],
                reward,
                is_first_round=is_first_round,
            )
            # hit_id = f"{nxt_rnd_num}_{hash_value}"
            # additionally storing annotator group ID to assign the necessary qualification for new workers
            self.past_task_table.insert(
                {
                    "round_number": nxt_rnd_num,
                    "completed": False,
                    "hash_pair": hash_value,
                    "HITId": hit_id,
                    "annotator_group_ID": self.annotator_group_IDs[annotator_group_idx],
                }
            )
            self.logging_table.insert(
                {
                    "action": "hit_created",
                    "log": "HITID:%s;hash_value:%s" % (hit_id, hash_value),
                }
            )

        return

    def update_qualification_test(self, round_number):
        """
        qualification test to screen workers
        """

        # create a new qualification test
        qual_test = QualificationTest(
            self.config["screening"]["template_path"],
            self.config["screening"]["questions_path"],
            k=self.config["screening"]["num_questions"],
        )
        questions = qual_test.get_questions()
        answers = qual_test.get_answers()

        if self.SCREENING_QUAL_ID == None:
            # creating the screening qualification type for the first time
            response = self.mturk_client.create_qualification_type(
                Name=self.config["screening"]["Name"],
                Description=self.config["screening"]["Description"],
                QualificationTypeStatus="Active",
                Test=questions,
                AnswerKey=answers,
                TestDurationInSeconds=self.config["screening"]["TestDurationInSeconds"],
                RetryDelayInSeconds=self.config["screening"]["RetryDelayInSeconds"],
            )
            self.SCREENING_QUAL_ID = response["QualificationType"][
                "QualificationTypeId"
            ]
            self.mturk_qual_table.insert(
                {"qualification_type": "screening", "id": self.SCREENING_QUAL_ID}
            )
        else:
            # updating the qualification type to use new questionaire
            response = self.mturk_client.update_qualification_type(
                QualificationTypeId=self.SCREENING_QUAL_ID,
                QualificationTypeStatus="Active",
                Test=questions,
                AnswerKey=answers,
                TestDurationInSeconds=self.config["screening"]["TestDurationInSeconds"],
                RetryDelayInSeconds=self.config["screening"]["RetryDelayInSeconds"],
            )

        # to keep a log, write questions and answers used in the current round
        Q_XML = (
            f"{self.config['screening']['template_path']}/questions_{round_number}.xml"
        )
        ANS_XML = (
            f"{self.config['screening']['template_path']}/answers_{round_number}.xml"
        )
        qual_test.write_xml(Q_XML, ANS_XML)


def _delete_db(mturk_db_path):
    db = TinyDB(mturk_db_path)  # store all part list
    tables = ["stack_target", "past_tasks", "logging", "round_doc"]
    for t_name in tables:
        db.drop_table(t_name)


if __name__ == "__main__":
    parser = ArgumentParser(description="run a round of annotation on MTurk")
    parser.add_argument("stave_db", type=str, help="path to stave db")
    parser.add_argument("mturk_db", type=str, help="path to mturk db")
    parser.add_argument("config", type=str, help="path to config json")

    args = parser.parse_args()
    with open(args.config, "r") as rf:
        config = json.load(rf)

    # _delete_db(args.mturk_db)
    mturk = CrowdSourceAnnotationModule(args.stave_db, args.mturk_db, config)
    mturk.run_round()

