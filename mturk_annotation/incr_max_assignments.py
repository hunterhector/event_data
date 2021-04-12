"""
Increase max assignments for existing HITs
"""
import sys, os
import boto3
from typing import List, Tuple
import logging

sys.path.insert(0, os.path.abspath(".."))

from credentials import MTURK_ACCESS_KEY, MTURK_SECRET_KEY


def incr_assignments(mturk_client, HITs: List[Tuple[str, int]]):
    for HITId, n_assign in HITs:
        logging.info(f"releasing {n_assign} new assignments for HITId: {HITId}")
        mturk_client.create_additional_assignments_for_hit(
            HITId=HITId, NumberOfAdditionalAssignments=n_assign,
        )
        response = mturk_client.get_hit(HITId=HITId)
        logging.info(f"MaxAssignments={response['HIT']['MaxAssignments']} for HITId: {HITId}")


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s:\t%(message)s",
        level=logging.INFO,
        filename="../amt_logs/new_assignments.log",
    )
    mturk_client = boto3.client(
        "mturk",
        aws_access_key_id=MTURK_ACCESS_KEY,
        aws_secret_access_key=MTURK_SECRET_KEY,
        region_name="us-east-1",
    )
    HITs = [
        ("33KMQD9OGQ1ZNC62JMUA6DDXU4077A", 2),
        ("30U1YOGZHHJ1NJR4Y2V71WJP3UVDSD", 2),
        ("3AQN9REUUM3YJ53DX8NWJI7QK6NYDQ", 1),
    ]
    incr_assignments(mturk_client, HITs)
