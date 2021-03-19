"""
Retrive HIT results and run MACE
"""
from argparse import ArgumentParser
from subprocess import call
from tinydb import TinyDB, where
from tinydb.operations import increment
import boto3
import sys, os

from forte.pipeline import Pipeline
from forte.data.readers.stave_readers import StaveMultiDocSqlReader

sys.path.insert(0, os.path.abspath(".."))

from processors.stat_collector import MaceFormatCollector

from credentials import (
    MTURK_ACCESS_KEY,
    MTURK_SECRET_KEY,
    # MTURK_EVENT_BLOCKED_QUAL_ID,
)


class AMTCollector:
    MTURK_SANDBOX = "https://mturk-requester-sandbox.us-east-1.amazonaws.com"

    def __init__(self, stave_db_path, mturk_db_path, mace_code_path, is_sandbox=True):
        self.stave_db_path = stave_db_path
        self.mace_code_path = mace_code_path
        self.mturk_db_path = mturk_db_path

        self.is_sandbox_testing = is_sandbox

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

        self.db = TinyDB(self.mturk_db_path)
        self.stack_target_table = self.db.table("stack_target", cache_size=0)
        self.past_task_table = self.db.table("past_tasks", cache_size=0)
        self.logging_table = self.db.table("logging", cache_size=0)

    def get_hit_assignments(self, hit_id: str):
        results = self.mturk_client.list_assignments_for_hit(HITId=hit_id)
        nextToken = results.get("NextToken", None)
        assignments = results["Assignments"]
        while nextToken:
            results = self.mturk_client.list_assignments_for_hit(
                HITId=hit_id, NextToken=nextToken
            )
            assignments.extend(results["Assignments"])
            nextToken = results.get("NextToken", None)

        return assignments

    def get_all_reviewable_assignments(self):
        results = self.mturk_client.list_reviewable_hits()
        nextToken = results.get("NextToken", None)
        hits = results["HITs"]
        while nextToken:
            results = self.mturk_client.list_reviewable_hits(NextToken=nextToken)
            hits.extend(results["HITs"])
            nextToken = results.get("NextToken", None)

        assignments = []
        for hit in hits:
            hit_assignments = self.get_hit_assignments(hit["HITId"])
            if len(hit_assignments) == 0:
                continue
            assert (
                len(hit_assignments) == 1
            ), f"more than one assignment for hit {hit['HITId']}"
            assignments.append(hit_assignments[0])

        return assignments

    def collect(self):

        # identify latest round
        if len(self.stack_target_table) == 0:
            raise Exception("stack table is empty")

        last_record = self.stack_target_table.all()[-1]
        rnd_num = last_record["round_number"]

        # collect all reviewable HIT assignments
        reviewable_assignments = self.get_all_reviewable_assignments()
        if len(reviewable_assignments) == 0:
            print("no assignments to review!")
            return 0

        for asgn in reviewable_assignments:
            hit_id = asgn["HITId"]
            worker_id = asgn["WorkerId"]
            asgn_id = asgn["AssignmentId"]
            # # only interested in Submitted HITs
            # if asgn["AssignmentStatus"] in ["Approved", "Rejected"]:
            #     continue
            # ! TODO: retrive secret code from answer
            secret_code = None

            # check if the HIT is from current round
            task_record = self.past_task_table.search(
                (where("round_number") == rnd_num) & (where("HITId") == hit_id)
            )
            if len(task_record) == 0:
                # a HIT from previous rounds
                continue
            elif len(task_record) == 1:
                if task_record[0]["completed"]:
                    # already marked as complete
                    continue

            # new assignment from current round, yet to marked as complete
            print("found new assignment")
            print("Round: %s, HIT: %s, Worker: %s" % (rnd_num, hit_id, worker_id))

            self.past_task_table.update(
                {"completed": True, "annotator_id": worker_id},
                (where("round_number") == rnd_num) & (where("HITId") == hit_id),
            )
            task_record = self.past_task_table.get(
                (where("round_number") == rnd_num) & (where("HITId") == hit_id)
            )
            annotator_group_ID = task_record["annotator_group_ID"]
            # assign the qualification to the worker (new or old)
            self.add_qualification(annotator_group_ID, worker_id, False)
            self.logging_table.insert(
                {
                    "action": "hit_completed",
                    "log": "HITID:%s;worker:%s" % (hit_id, worker_id),
                }
            )

            # custom operation in tinydb
            def add_annotator(ann_id):
                def transform(doc):
                    doc["annotator_list"] += [ann_id]

                return transform

            self.stack_target_table.update(
                increment("completed_hit_count"), (where("round_number") == rnd_num),
            )
            self.stack_target_table.update(
                add_annotator(worker_id), (where("round_number") == rnd_num)
            )
            if (last_record["completed_hit_count"] + 1) >= last_record[
                "sent_hit_count"
            ]:
                print("round %.1f complete" % rnd_num)
                self.stack_target_table.update(
                    {"completed": True}, (where("round_number") == rnd_num)
                )
                self.logging_table.insert(
                    {"action": "rnd_completed", "log": "round %.1f" % (rnd_num)}
                )

                # call collect data from processor & run MACE
                # pipeline = Pipeline()
                # pipeline.set_reader(
                #     StaveMultiDocSqlReader(),
                #     config={"stave_db_path": self.stave_db_path},
                # )
                # pipeline.add(MaceFormatCollector(self.mace_code_path))
                # pipeline.run()

                # # TODO: error check whether file exists
                # call(
                #     [
                #         "java -jar %s/MACE.jar %s/mace_coref.csv"
                #         % (self.mace_code_path, self.mace_code_path)
                #     ],
                #     shell=True,
                # )

    def add_qualification(self, qualification_id, worker_id, bool_send_not):
        response = self.mturk_client.associate_qualification_with_worker(
            QualificationTypeId=qualification_id,
            WorkerId=worker_id,
            IntegerValue=1,
            SendNotification=bool_send_not,
        )
        return response


if __name__ == "__main__":
    parser = ArgumentParser(description="collect any new results from AMT")
    parser.add_argument("stave_db", type=str, help="path to stave db")
    parser.add_argument("mturk_db", type=str, help="path to mturk db")
    # parser.add_argument("mace_folder_path", type=str, help="path to the MACE folder")

    args = parser.parse_args()

    collector = AMTCollector(args.stave_db, args.mturk_db, None, False)
    collector.collect()
