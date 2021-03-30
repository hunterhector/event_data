from tinydb import TinyDB, where
import boto3
from argparse import ArgumentParser
from datetime import datetime, time
from copy import deepcopy
import sys, os

sys.path.insert(0, os.path.abspath(".."))

from credentials import MTURK_ACCESS_KEY, MTURK_SECRET_KEY

MTURK_SANDBOX = "https://mturk-requester-sandbox.us-east-1.amazonaws.com"


def time2str(elm):
    out = deepcopy(elm)
    for x in out:
        if isinstance(out[x], datetime):
            out[x] = datetime.isoformat(out[x])
    return out


def get_hits(mturk_client):
    results = mturk_client.list_hits()
    nextToken = results.get("NextToken", None)
    hits = results["HITs"]
    while nextToken:
        results = mturk_client.list_hits(NextToken=nextToken)
        hits.extend(results["HITs"])
        nextToken = results.get("NextToken", None)
    return hits


def get_hit_assignments(mturk_client, hit_id: str):
    results = mturk_client.list_assignments_for_hit(HITId=hit_id)
    nextToken = results.get("NextToken", None)
    assignments = results["Assignments"]
    while nextToken:
        results = mturk_client.list_assignments_for_hit(HITId=hit_id, NextToken=nextToken)
        assignments.extend(results["Assignments"])
        nextToken = results.get("NextToken")
    return assignments


def get_workers(mturk_client, qual_id: str):
    results = mturk_client.list_workers_with_qualification_type(QualificationTypeId=qual_id)
    nextToken = results.get("NextToken", None)
    workers = results["Qualifications"]
    while nextToken:
        results = mturk_client.list_workers_with_qualification_type(
            QualificationTypeId=qual_id, NextToken=nextToken
        )
        workers.extend(results["Qualifications"])
        nextToken = results.get("NextToken", None)
    return workers


def update_assignment_db(mturk_client, db):
    assign_table = db.table("assignment_table", cache_size=0)
    hit_table = db.table("hit_table", cache_size=0)
    worker_table = db.table("worker_table", cache_size=0)

    hits = get_hits(mturk_client)
    for hit_entry in hits:
        hit = time2str(hit_entry)
        hit_table.upsert(hit, where("HITId") == hit["HITId"])
        assignments = get_hit_assignments(mturk_client, hit["HITId"])
        for assign_entry in assignments:
            assign = time2str(assign_entry)
            assign_table.upsert(assign, where("AssignmentId") == assign["AssignmentId"])
            worker_table.update(
                {"isActive": True, "lastActive": assign["SubmitTime"]},
                where("WorkerId") == assign["WorkerId"],
            )


def update_worker_db(mturk_client, db, qual_id=None):
    table = db.table("worker_table", cache_size=0)

    workers = get_workers(mturk_client, qual_id)
    for worker_entry in workers:
        worker = time2str(worker_entry)
        table.upsert(worker, where("WorkerId") == worker["WorkerId"])


if __name__ == "__main__":
    parser = ArgumentParser(description="update all AMT database for visualization")
    parser.add_argument("mturk_db_path", type=str)
    parser.add_argument("results_db_path", type=str)
    parser.add_argument("--sandbox", action="store_true")

    args = parser.parse_args()
    if args.sandbox:
        mturk_client = boto3.client(
            "mturk",
            aws_access_key_id=MTURK_ACCESS_KEY,
            aws_secret_access_key=MTURK_SECRET_KEY,
            region_name="us-east-1",
            endpoint_url=MTURK_SANDBOX,
        )
    else:
        mturk_client = boto3.client(
            "mturk",
            aws_access_key_id=MTURK_ACCESS_KEY,
            aws_secret_access_key=MTURK_SECRET_KEY,
            region_name="us-east-1",
        )

    # retrieving the screening qualification
    mturk_db = TinyDB(args.mturk_db_path)
    mturk_qual_table = mturk_db.table("mturk_qualifications", cache_size=0)
    s = mturk_qual_table.search(where("qualification_type") == "screening")
    assert len(s) <= 1, "more than one screening qualification"
    if len(s) == 1:
        SCREENING_QUAL_ID = s[0]["id"]

    # stats db
    results_db = TinyDB(args.results_db_path)

    update_worker_db(mturk_client, results_db, qual_id=SCREENING_QUAL_ID)
    update_assignment_db(mturk_client, results_db)
