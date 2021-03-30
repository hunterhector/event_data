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
            results = self.mturk_client.list_assignments_for_hit(HITId=hit_id, NextToken=nextToken)
            assignments.extend(results["Assignments"])
            nextToken = results.get("NextToken", None)

        return assignments

    def get_all_assignments(self):
        results = self.mturk_client.list_hits()
        nextToken = results.get("NextToken", None)
        hits = results["HITs"]
        while nextToken:
            results = self.mturk_client.list_hits(NextToken=nextToken)
            hits.extend(results["HITs"])
            nextToken = results.get("NextToken", None)

        assignments = []
        for hit in hits:
            hit_assignments = self.get_hit_assignments(hit["HITId"])
            if len(hit_assignments) == 0:
                continue
            # assert len(hit_assignments) == 1, f"more than one assignment for hit {hit['HITId']}"
            assignments.append(hit_assignments[0])

        return assignments

    def collect(self):

        # identify latest round
        if len(self.stack_target_table) == 0:
            raise Exception("stack table is empty")

        # collect all reviewable HIT assignments
        assignments = self.get_all_assignments()
        if len(assignments) == 0:
            print("no assignments to review!")
            return 0

        foundAssignment = False
        for asgn in assignments:
            hit_id = asgn["HITId"]
            worker_id = asgn["WorkerId"]
            asgn_id = asgn["AssignmentId"]

            # # only interested in Submitted HITs
            # if asgn["AssignmentStatus"] in ["Approved", "Rejected"]:
            #     continue
            # ! TODO: retrive secret code from answer
            secret_code = None

            # get the HIT task record
            task_record = self.past_task_table.search((where("HITId") == hit_id))
            if not task_record:
                continue
            task_record = task_record[0]
            rnd_num = task_record["round_number"]
            if task_record["completed"]:
                # hit already marked as complete
                continue
            if "finished_assignments" in task_record:
                if asgn_id in task_record["finished_assignments"]:
                    # hit assignment was previously noted
                    continue

            # new assignment from current round, yet to marked as complete
            print("found new assignment")
            print("Round: %s, HIT: %s, Worker: %s" % (rnd_num, hit_id, worker_id))
            foundAssignment = True

            def add_assignment(id_):
                def transform(doc):
                    if "finished_assignments" not in doc:
                        doc["finished_assignments"] = []
                    doc["finished_assignments"] += [id_]

                return transform

            def add_annotator(id_):
                def transform(doc):
                    if "annotators" not in doc:
                        doc["annotators"] = []
                    doc["annotators"] += [id_]

                return transform

            # custom operation in tinydb
            def add_annotator_round(ann_id):
                def transform(doc):
                    doc["annotator_list"] += [ann_id]

                return transform

            self.past_task_table.update(add_assignment(asgn_id), where("HITId") == hit_id)
            self.past_task_table.update(add_annotator(worker_id), where("HITId") == hit_id)

            task_record = self.past_task_table.get((where("HITId") == hit_id))
            if len(task_record["finished_assignments"]) == 3:
                print("all assignments completed for HIT: %s" % hit_id)
                self.past_task_table.update(
                    {"completed": True}, (where("round_number") == rnd_num) & (where("HITId") == hit_id),
                )
                self.stack_target_table.update(
                    increment("completed_hit_count"), (where("round_number") == rnd_num),
                )

            self.logging_table.insert(
                {
                    "action": "hit_assignment_completed",
                    "log": "HITID:%s;worker:%s;assignment:%s" % (hit_id, worker_id, asgn_id),
                }
            )
            self.stack_target_table.update(add_annotator_round(worker_id), (where("round_number") == rnd_num))

            stack_record = self.stack_target_table.get(where("round_number") == rnd_num)
            if (stack_record["completed_hit_count"] + 1) >= stack_record["sent_hit_count"]:
                print("round %.1f complete" % rnd_num)
                self.stack_target_table.update({"completed": True}, (where("round_number") == rnd_num))
                self.logging_table.insert({"action": "rnd_completed", "log": "round %.1f" % (rnd_num)})

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
        if not foundAssignment:
            print("no new assignments found!")


if __name__ == "__main__":
    parser = ArgumentParser(description="collect any new results from AMT")
    parser.add_argument("stave_db", type=str, help="path to stave db")
    parser.add_argument("mturk_db", type=str, help="path to mturk db")
    # parser.add_argument("mace_folder_path", type=str, help="path to the MACE folder")

    args = parser.parse_args()

    collector = AMTCollector(args.stave_db, args.mturk_db, None, False)
    collector.collect()
