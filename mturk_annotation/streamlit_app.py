"""
Reads latest AMT databases to create summaries
"""

import sys, re
from pandas.core.algorithms import mode
import streamlit as st
import numpy as np
import pandas as pd
from tinydb import TinyDB, where
from collections import Counter, defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
import plotly.express as px
from pathlib import Path

NA_STR = "-"


def get_hit_statistics(hit_table, assignment_table):
    summary = {}

    released_hits = hit_table.search(where("HITId").exists())
    summary["Released HITs"] = len(released_hits)

    completed_hits = hit_table.search(where("HITStatus") == "Unassignable")
    summary["Completed HITs"] = len(completed_hits)

    reviewable_hits = hit_table.search(where("HITStatus") == "Reviewable")
    summary["Reviewable HITs"] = len(reviewable_hits)

    open_hits = hit_table.search((where("HITStatus") == "Assignable"))
    summary["Open HITs"] = len(open_hits)

    submitted_assigns = assignment_table.search(where("SubmitTime").exists())
    avg_times = [
        (
            datetime.fromisoformat(x["SubmitTime"])
            - datetime.fromisoformat(x["AcceptTime"])
        ).seconds
        / 60
        for x in submitted_assigns
    ]
    summary["Avg. time per HIT (mins)"] = f"{np.mean(avg_times):.2f}"
    approved_assigns = assignment_table.search(where("ApprovalTime").exists())
    avg_times = [
        (
            datetime.fromisoformat(x["ApprovalTime"])
            - datetime.fromisoformat(x["SubmitTime"])
        ).seconds
        / 60
        / 60
        for x in approved_assigns
    ]
    summary["Avg. time taken for approval (hours)"] = f"{np.mean(avg_times):.2f}"

    st.table(pd.DataFrame.from_dict(summary, orient="index", columns=[""]))

    # HITs released per day
    release_times = [datetime.fromisoformat(x["CreationTime"]) for x in hit_table.all()]
    release_times = [(x - np.min(release_times)).days for x in release_times]
    release_counter = Counter(release_times)

    # HITs solved per day
    submitted_assigns = assignment_table.search(where("SubmitTime").exists())
    submit_times = [datetime.fromisoformat(x["SubmitTime"]) for x in submitted_assigns]
    submit_times = [(x - np.min(submit_times)).days for x in submit_times]
    submit_counter = Counter(submit_times)

    days = np.arange(0, max(np.max(submit_times), np.max(release_times)) + 1)
    release_values, submit_values = [], []
    for i in days:
        release_values.append(release_counter[i])
        submit_values.append(submit_counter[i])

    st.markdown("## HIT activity")
    fig = px.line(
        x=days,
        y=np.cumsum(release_values),
        labels={"x": "Day X", "y": "# HITs"},
        title="HITs released (cummulative)",
    )
    st.plotly_chart(fig, use_container_width=True)
    fig = px.line(
        x=days,
        y=np.cumsum(submit_values),
        labels={"x": "Day X", "y": "# HITs"},
        title="HITs finished (cummulative)",
    )
    st.plotly_chart(fig, use_container_width=True)


def get_dataset_statistics(round_doc_table):
    summary = {}
    docs_per_round = defaultdict(list)
    for record in round_doc_table.all()[::-1]:
        doc_ids = re.search(r"^pair\_([0-9]+)\_and\_([0-9]+)", record["name"])
        doc1, doc2 = doc_ids.group(1), doc_ids.group(2)
        # docs_per_round[f"Round {record['round_assigned']}"].add(doc1)
        # docs_per_round[f"Round {record['round_assigned']}"].add(doc2)
        docs_per_round[f"Round {record['round_assigned']}"].append(f"({doc1},{doc2})")

    docs_schedule = {}
    for k, v in docs_per_round.items():
        docs_schedule[k] = ",".join(v)

    summary["Documents annotated"] = NA_STR
    summary["Document groups annotated"] = NA_STR
    summary["Links found"] = NA_STR

    st.markdown("## Summary")
    st.table(pd.DataFrame.from_dict(summary, orient="index", columns=[""]))

    st.markdown("## Schedule")
    st.table(
        pd.DataFrame.from_dict(docs_schedule, orient="index", columns=["Documents"],)
    )


def get_annotator_statistics(assignment_table, worker_table):

    qualified = worker_table.search(where("Status") == "Granted")
    st.write(
        "Number of qualified workers (i.e., passed the screening test): ",
        len(qualified),
    )

    active = worker_table.search(where("isActive") == True)
    st.write("Number of active workers (i.e., solved at least one task): ", len(active))

    st.markdown("## Statistics of every active worker")
    worker_summary = {}
    active = worker_table.search(where("isActive") == True)
    for worker in active:
        worker_id = worker["WorkerId"]
        worker_summary[worker_id] = {}
        worker_summary[worker_id]["Qualification Score"] = worker["IntegerValue"]
        worker_summary[worker_id]["Qualification Date"] = datetime.strftime(
            datetime.fromisoformat(worker["GrantTime"]), "%b %d"
        )
        worker_summary[worker_id]["Location"] = (
            worker["LocaleValue"]["Subdivision"]
            + ", "
            + worker["LocaleValue"]["Country"]
        )
        assigns = assignment_table.search(where("WorkerId") == worker_id)
        worker_summary[worker_id]["HITs"] = len(assigns)
        # ! todo: uniq document pairs annotated
        times = [
            (
                datetime.fromisoformat(x["SubmitTime"])
                - datetime.fromisoformat(x["AcceptTime"])
            ).seconds
            / 60
            for x in assigns
        ]
        worker_summary[worker_id]["Total HIT time (mins)"] = np.sum(times)
        worker_summary[worker_id]["Avg. HIT time (mins)"] = f"{np.mean(times):.2f}"
        # ! todo: add a summary of feedback obtained
        worker_summary[worker_id]["# doc pairs"] = NA_STR
        worker_summary[worker_id]["last Active"] = datetime.strftime(
            datetime.fromisoformat(worker["lastActive"]), "%b %d"
        )

    st.table(pd.DataFrame.from_dict(worker_summary, orient="index"))


def get_hit_schedule(stack_target_table, past_task_table):

    rounds = {}
    for rnd in stack_target_table.all()[::-1]:
        rnd_name = f"Round {rnd['round_number']}"
        rounds[rnd_name] = {}
        rounds[rnd_name][
            "Progress"
        ] = f"{rnd['completed_hit_count']}/{rnd['sent_hit_count']}"
        rounds[rnd_name]["Status"] = "Complete" if rnd["completed"] else "Ongoing"
        rounds[rnd_name]["Annotators"] = rnd["annotator_list"]
    st.markdown("## Round progress")
    st.table(pd.DataFrame.from_dict(rounds, orient="index"))

    tasks = {}
    task_count = len(past_task_table.all())
    for idx, task in enumerate(past_task_table.all()[::-1]):
        task_id = task_count - idx
        tasks[f"Task {task_id}"] = {}
        tasks[f"Task {task_id}"]["Round"] = str(task["round_number"])
        tasks[f"Task {task_id}"]["Status"] = (
            "Complete" if task["completed"] else "Ongoing"
        )
        tasks[f"Task {task_id}"]["HITId"] = task["HITID"]
        tasks[f"Task {task_id}"]["Annotator Group"] = task["annotator_group_ID"]
    st.markdown("## Task progress")
    st.table(pd.DataFrame.from_dict(tasks, orient="index"))


def get_quality_statistics():
    st.markdown("**pending**")


def show(option: str, overview_db_path, scheduler_db_path):
    # this db is updated via explicit API calls to MTurk
    overview_db = TinyDB(overview_db_path)
    hit_table = overview_db.table("hit_table", cache_size=0)
    assignment_table = overview_db.table("assignment_table", cache_size=0)
    worker_table = overview_db.table("worker_table", cache_size=0)

    # this db is updated by the HIT scheduler
    scheduler_db = TinyDB(scheduler_db_path)
    stack_target_table = scheduler_db.table("stack_target", cache_size=0)
    past_task_table = scheduler_db.table("past_tasks", cache_size=0)
    round_doc_table = scheduler_db.table("round_doc", cache_size=0)

    return {
        "HIT Summary": lambda: get_hit_statistics(hit_table, assignment_table),
        "Dataset": lambda: get_dataset_statistics(round_doc_table),
        "Annotators": lambda: get_annotator_statistics(assignment_table, worker_table),
        "HIT Schedule": lambda: get_hit_schedule(stack_target_table, past_task_table),
        "Quality Control": lambda: get_quality_statistics(),
    }[option]()


overview_db_path = sys.argv[1]
scheduler_db_path = sys.argv[2]

overview_edit_time = datetime.fromtimestamp(Path(overview_db_path).stat().st_mtime)
scheduler_edit_time = datetime.fromtimestamp(Path(scheduler_db_path).stat().st_mtime)
latest = max(overview_edit_time, scheduler_edit_time)
st.write("last updated on ", latest.ctime())

sidebar_options = [
    "HIT Summary",
    "Dataset",
    "Annotators",
    "HIT Schedule",
    "Quality Control",
]
# option = st.selectbox("Choose an option from the dropdown", sidebar_options)
option = st.sidebar.radio("Choose an option", sidebar_options)

st.markdown(f"## {option}")
st.markdown("---")

show(option, overview_db_path, scheduler_db_path)
