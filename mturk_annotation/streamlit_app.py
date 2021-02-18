"""
Reads latest AMT databases to create summaries
"""

import sys
import streamlit as st
import numpy as np
import pandas as pd
from tinydb import TinyDB, where
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path

NA_STR = "-"


def get_overall_statistics(hit_table, worker_table):
    summary = {}

    released_hits = hit_table.search(where("HITId").exists())
    summary["Released HITs"] = len(released_hits)

    completed_hits = hit_table.search(where("HITStatus") == "Unassignable")
    summary["Completed HITs"] = len(completed_hits)

    # ! todo
    summary["Documents annotated"] = NA_STR
    summary["Document groups annotated"] = NA_STR

    qualified = worker_table.search(where("Status") == "Granted")
    summary["Qualified workers"] = len(qualified)
    active = worker_table.search(where("isActive") == True)
    summary["Active workers"] = len(active)

    # balance related info
    # ! todo

    st.table(pd.DataFrame.from_dict(summary, orient="index", columns=[""]))


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

    st.markdown("## Overview")
    st.table(pd.DataFrame.from_dict(summary, orient="index", columns=[""]))

    # HITs solved per day
    submitted_assigns = assignment_table.search(where("SubmitTime").exists())
    abs_times = [datetime.fromisoformat(x["SubmitTime"]) for x in submitted_assigns]
    abs_times = [(x - np.min(abs_times)).days for x in abs_times]
    counter = Counter(abs_times)
    days = np.arange(0, np.max(abs_times) + 1)
    values = []
    for i in days:
        values.append(counter[i])
    st.markdown("## Annotation Progress")
    fig, ax = plt.subplots()
    ax.bar(days, values)
    ax.set_xticks(days)
    ax.set_xlabel("Day X")
    ax.set_ylabel("HITs submitted")
    ax.set_title("Statistics of HITs submitted by workers per day")
    st.pyplot(fig)


def get_dataset_statistics():
    summary = {}
    summary["Documents annotated"] = NA_STR
    summary["Document groups annotated"] = NA_STR
    summary["Links found"] = NA_STR

    st.table(pd.DataFrame.from_dict(summary, orient="index", columns=[""]))


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


def show(option: str, hit_table, assignment_table, worker_table):
    return {
        "Summary": lambda: get_overall_statistics(hit_table, worker_table),
        "HITs": lambda: get_hit_statistics(hit_table, assignment_table),
        "Dataset": lambda: get_dataset_statistics(),
        "Annotators": lambda: get_annotator_statistics(assignment_table, worker_table),
    }[option]()


db_path = sys.argv[1]
db = TinyDB(db_path)
hit_table = db.table("hit_table", cache_size=0)
assignment_table = db.table("assignment_table", cache_size=0)
worker_table = db.table("worker_table", cache_size=0)

fname = Path(db_path)
st.write("last updated on ", datetime.fromtimestamp(fname.stat().st_mtime).ctime())
sidebar_options = ["Summary", "HITs", "Dataset", "Annotators"]
option = st.selectbox("Choose an option from the dropdown", sidebar_options)

show(option, hit_table, assignment_table, worker_table)
