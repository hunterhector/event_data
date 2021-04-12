"""
Reads latest AMT databases to create summaries
"""

from os import link
import sys, re

import streamlit as st
import numpy as np
import pandas as pd
from tinydb import TinyDB, where
from collections import Counter, defaultdict
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json

NA_STR = "-"


def get_hit_statistics(hit_table, assignment_table):

    summary = {}

    released_assignments = 0
    completed_assignments = 0
    reviewable_assignments = 0
    available_assignments = 0
    for hit in hit_table.search(where("HITId").exists()):
        released_assignments += hit["MaxAssignments"]
        completed_assignments += hit["NumberOfAssignmentsCompleted"]
        available_assignments += hit["NumberOfAssignmentsAvailable"]
        reviewable_assignments += (
            hit["MaxAssignments"] - hit["NumberOfAssignmentsCompleted"] - hit["NumberOfAssignmentsAvailable"]
        )
    st.markdown("## Overview")
    summary["Released Assignments"] = released_assignments
    summary["Completed Assignments"] = completed_assignments
    summary["Reviewable Assignments"] = reviewable_assignments
    summary["Open Assignments"] = available_assignments

    submitted_assigns = assignment_table.search(where("SubmitTime").exists())
    avg_times = [
        (datetime.fromisoformat(x["SubmitTime"]) - datetime.fromisoformat(x["AcceptTime"])).seconds / 60
        for x in submitted_assigns
    ]
    summary["Mean time per assignment (mins)"] = f"{np.mean(avg_times):.2f}"
    summary["Median time per assignment (mins)"] = f"{np.median(avg_times):.2f}"

    st.table(pd.DataFrame.from_dict(summary, orient="index", columns=[""]))

    # assignments released per day
    release_times = []
    for hit in hit_table.all():
        release_times.extend([datetime.fromisoformat(hit["CreationTime"])] * hit["MaxAssignments"])
    release_times = [(x - np.min(release_times)).days for x in release_times]
    release_counter = Counter(release_times)

    # assignments solved per day
    submitted_assigns = assignment_table.search(where("SubmitTime").exists())
    submit_times = [datetime.fromisoformat(x["SubmitTime"]) for x in submitted_assigns]
    submit_times = [(x - np.min(submit_times)).days for x in submit_times]
    submit_counter = Counter(submit_times)

    daily_release_stats = []
    cummulative_release_stats = []
    daily_finish_stats = []
    cummulative_finish_stats = []
    days = np.arange(0, max(np.max(submit_times), np.max(release_times)) + 1)
    release_sum, submit_sum = 0, 0
    for i in days:
        release_sum += release_counter[i]
        submit_sum += submit_counter[i]
        daily_release_stats.append(release_counter[i])
        daily_finish_stats.append(submit_counter[i])
        cummulative_release_stats.append(release_sum)
        cummulative_finish_stats.append(submit_sum)

    st.markdown("## HIT activity")
    st.markdown("Overview of assignments released/finished per day (and cummulative).")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=daily_release_stats, mode="lines+markers", name="release (daily)"))
    fig.add_trace(
        go.Scatter(x=days, y=cummulative_release_stats, mode="lines+markers", name="release (cummulative)")
    )
    fig.add_trace(go.Scatter(x=days, y=daily_finish_stats, mode="lines+markers", name="finished (daily)"))
    fig.add_trace(
        go.Scatter(x=days, y=cummulative_finish_stats, mode="lines+markers", name="finished (cummulative)")
    )
    fig.update_xaxes(title_text="Day")
    fig.update_yaxes(title_text="# Assignments")

    st.plotly_chart(fig, use_container_width=True)


def get_dataset_statistics(round_doc_table, dataset_json_path: Path = None):

    view_options = ["Overview", "Document release schedule"]
    view_option = st.radio("Choose a view", options=view_options)

    if dataset_json_path:
        df_pairs = defaultdict(list)
        link_counter = {}
        pair_counter = defaultdict(lambda: len(pair_counter))
        q_counter = {}
        with open(dataset_json_path, "r") as rf:
            dataset_stats = json.load(rf)
            doc_pairs_sorted = sorted(dataset_stats.keys())
            for doc_pair in doc_pairs_sorted:
                for ann in dataset_stats[doc_pair]["annotators"]:
                    df_pairs[ann].append(pair_counter[doc_pair])
                    if ann not in link_counter:
                        link_counter[ann] = defaultdict(int)
                for coref_link in dataset_stats[doc_pair]["links"]:
                    for ann in coref_link["annotators"]:
                        link_counter[ann[0]][pair_counter[doc_pair]] += 1
                        for qidx, answer in enumerate(ann[1]):
                            if qidx not in q_counter:
                                q_counter[qidx] = defaultdict(int)
                            q_counter[qidx][answer] += 1

        idx2pair = {v: k for k, v in pair_counter.items()}

    if view_option == view_options[0]:
        # summary = {}
        if dataset_json_path:
            df_counts = defaultdict(list)
            for ann, doc_pairs in df_pairs.items():
                for doc_pair in doc_pairs:
                    df_counts[ann].append(link_counter[ann][doc_pair])

            fig = go.Figure()
            for ann in df_pairs:
                hover_text = [idx2pair[idx] for idx in df_pairs[ann]]
                fig.add_trace(
                    go.Scatter(
                        x=df_pairs[ann], y=df_counts[ann], mode="lines+markers", text=hover_text, name=ann
                    )
                )
            fig.update_xaxes(title_text="Document pairs")
            fig.update_yaxes(title_text="# coreference links")
            st.markdown("## Coreference links")
            st.plotly_chart(fig, use_container_width=True)

            x_labels = ["Place", "Time", "Participants", "Inclusion"]

            fig = go.Figure()
            for option_idx in range(4):
                fig.add_trace(
                    go.Bar(
                        x=x_labels,
                        y=[q_counter[x_][option_idx] for x_, _ in enumerate(x_labels)],
                        name="Option %s" % option_idx,
                    )
                )
            fig.update_xaxes(title_text="Coreference Question Type")
            fig.update_yaxes(title_text="Response count")
            st.markdown("## Responses to Coreference Questions")
            st.plotly_chart(fig, use_container_width=True)

            # summary["Documents annotated"] = len(all_docs)
            # summary["Document pairs annotated"] = len(dataset_stats.keys())
            # summary["Links found"] = total_link_count

            # st.markdown("## Overview")
            # st.table(pd.DataFrame.from_dict(summary, orient="index", columns=[""]))

            # df = defaultdict(list)
            # for k, v in links2docs.items():
            #     df["Num. of annotators"].append(k)
            #     df["Num. of links"].append(v)

            # fig = px.pie(df, values="Num. of links", names="Num. of annotators")
            # st.markdown("## Agreement")
            # st.write(
            #     "Pie chart showing the distribution of coreference links with the number of unique annotators per link. Higher the number of unique annotators, higher the agreement."
            # )
            # st.plotly_chart(fig, use_container_width=True)

    elif view_option == view_options[1]:
        docs_per_round = defaultdict(list)
        for record in round_doc_table.all()[::-1]:
            doc_ids = re.search(r"^pair\_([0-9]+)\_and\_([0-9]+)", record["name"])
            doc1, doc2 = doc_ids.group(1), doc_ids.group(2)
            docs_per_round[f"Round {record['round_assigned']}"].append(f"({doc1},{doc2})")

        docs_schedule = {}
        for k, v in docs_per_round.items():
            docs_schedule[k] = ",".join(v)
        st.markdown("## Schedule")
        st.write("This table presents our schedule for documents to be released in each annotation round.")
        st.table(pd.DataFrame.from_dict(docs_schedule, orient="index", columns=["Documents"],))


def get_annotator_statistics(assignment_table, worker_table):

    view_options = [
        "Overview",
        "Screening Activity",
        "HIT duration (trends)",
    ]
    view_option = st.radio("Choose a view", options=view_options)

    THRESHOLD = 75
    if view_option == view_options[0]:
        attempted = worker_table.search(where("Status") == "Granted")
        qualified = worker_table.search((where("Status") == "Granted") & (where("IntegerValue") >= THRESHOLD))
        st.write(
            "Number of qualified workers (test passed / test attempted): ",
            len(qualified),
            "/",
            len(attempted),
        )

        active = worker_table.search(where("isActive") == True)
        st.write("Number of active workers (i.e., solved at least one task): ", len(active))

        st.markdown("---")
        st.markdown("## Active Workers")
        worker_summary = {}
        active = worker_table.search(where("isActive") == True)
        for worker in active:
            worker_id = worker["WorkerId"]
            worker_summary[worker_id] = {}
            assigns = assignment_table.search(where("WorkerId") == worker_id)
            worker_summary[worker_id]["HITs"] = len(assigns)
            # ! todo: uniq document pairs annotated
            times = [
                (datetime.fromisoformat(x["SubmitTime"]) - datetime.fromisoformat(x["AcceptTime"])).seconds
                / 60
                for x in assigns
            ]
            worker_summary[worker_id]["Total HIT time (mins)"] = np.sum(times)
            worker_summary[worker_id]["Mean HIT time (mins)"] = f"{np.mean(times):.2f}"
            worker_summary[worker_id]["Median HIT time (mins)"] = f"{np.median(times):.2f}"
            # ! todo: add a summary of feedback obtained
            worker_summary[worker_id]["last Active"] = datetime.strftime(
                datetime.fromisoformat(worker["lastActive"]), "%b %d"
            )
            worker_summary[worker_id]["Qualification Score"] = worker["IntegerValue"]
            worker_summary[worker_id]["Qualification Date"] = datetime.strftime(
                datetime.fromisoformat(worker["GrantTime"]), "%b %d"
            )

        worker_summary = {
            k: v for k, v in sorted(worker_summary.items(), key=lambda x: x[1]["HITs"], reverse=True)
        }
        st.table(pd.DataFrame.from_dict(worker_summary, orient="index"))

        st.markdown("---")
        st.markdown("## Qualification Statistics")
        worker_summary = {}
        for worker in attempted:
            worker_id = worker["WorkerId"]
            worker_summary[worker_id] = {}
            worker_summary[worker_id]["Qualification Score"] = worker["IntegerValue"]
            worker_summary[worker_id]["Qualification Date"] = datetime.strftime(
                datetime.fromisoformat(worker["GrantTime"]), "%b %d"
            )

        def highlight_worker(val):
            if val.item() >= THRESHOLD:
                s = worker_table.search((where("WorkerId") == val.name) & (where("isActive") == True))
                if len(s) > 0:
                    return ["background-color: green"]
                return ["background-color: yellow"]
            else:
                return [""]

        df = pd.DataFrame.from_dict(worker_summary, orient="index")
        st.dataframe(df.style.apply(highlight_worker, subset="Qualification Score", axis=1))

    elif view_option == view_options[1]:
        df = defaultdict(list)
        attempted = worker_table.search(where("Status") == "Granted")
        passed = worker_table.search((where("Status") == "Granted") & (where("IntegerValue") >= THRESHOLD))
        attempt_times = [datetime.fromisoformat(w["GrantTime"]) for w in attempted]
        attempt_times = [(t - np.min(attempt_times)).days for t in attempt_times]
        attempt_counter = Counter(attempt_times)
        pass_times = [datetime.fromisoformat(w["GrantTime"]) for w in passed]
        pass_times = [(t - np.min(pass_times)).days for t in pass_times]
        pass_counter = Counter(pass_times)
        days = np.arange(0, np.max(attempt_times), 1)
        for i in days:
            df["Day X"].append(i)
            df["# Tests"].append(attempt_counter[i])
            df["Type"].append("Attempted")
        for i in days:
            df["Day X"].append(i)
            df["# Tests"].append(pass_counter[i])
            df["Type"].append("Passed")

        range_x = [0, len(days)]
        fig = px.line(df, x="Day X", y="# Tests", range_x=range_x, color="Type")
        st.plotly_chart(fig, use_container_width=True)

    elif view_option == view_options[2]:
        df_hits = defaultdict(list)
        df_durations = defaultdict(list)
        hit_counter = defaultdict(lambda: len(hit_counter))
        all_assignments = sorted(
            assignment_table.search(where("SubmitTime").exists()), key=lambda x: x["SubmitTime"]
        )
        for assign in all_assignments:
            df_hits[assign["WorkerId"]].append(hit_counter[assign["HITId"]])
            df_durations[assign["WorkerId"]].append(
                (
                    datetime.fromisoformat(assign["SubmitTime"])
                    - datetime.fromisoformat(assign["AcceptTime"])
                ).seconds
                / 60
            )
        fig = go.Figure()
        for worker_id in df_hits:
            fig.add_trace(
                go.Scatter(
                    x=df_hits[worker_id], y=df_durations[worker_id], mode="lines+markers", name=worker_id
                )
            )
        fig.update_xaxes(title_text="HITs")
        fig.update_yaxes(title_text="Duration (in mins)")
        st.plotly_chart(fig, use_container_width=True)


def get_hit_schedule(round_doc_table, stack_target_table, past_task_table, hit_table):

    view_options = ["Round progress", "Task progress"]
    view_option = st.radio("Choose a view", options=view_options)
    hash2pair = {}
    for doc in round_doc_table.all():
        hash2pair[doc["hashed"]] = doc["name"]

    if view_option == view_options[0]:
        rounds = {}
        for rnd in stack_target_table.all()[::-1]:
            rnd_name = f"Round {rnd['round_number']}"
            rounds[rnd_name] = {}
            rounds[rnd_name]["Progress"] = f"{rnd['completed_hit_count']}/{rnd['sent_hit_count']}"
            rounds[rnd_name]["Status"] = "Complete" if rnd["completed"] else "Ongoing"
            rounds[rnd_name]["Annotators"] = rnd["annotator_list"]
        st.markdown("## Round progress")
        st.write("Below table shows the progress of HITs in each annotation round.")
        st.table(pd.DataFrame.from_dict(rounds, orient="index"))

    elif view_option == view_options[1]:
        tasks = {}
        task_count = len(past_task_table.all())
        for idx, task in enumerate(past_task_table.all()[::-1]):
            task_id = task_count - idx
            tasks[f"Task {task_id}"] = {}
            tasks[f"Task {task_id}"]["Round"] = str(task["round_number"])
            tasks[f"Task {task_id}"]["Status"] = "Complete" if task["completed"] else "Ongoing"
            tasks[f"Task {task_id}"]["Doc pair"] = hash2pair[task["hash_pair"]]
            tasks[f"Task {task_id}"]["HITId"] = task["HITId"]
            tasks[f"Task {task_id}"]["Annotators"] = task.get("annotators", [])
            hit_entry = hit_table.search(where("HITId") == task["HITId"])[0]
            tasks[f"Task {task_id}"]["HIT Expiry"] = hit_entry["Expiration"]

        st.markdown("## Task progress")
        st.write("Below table shows the progress of each released HIT.")
        st.table(pd.DataFrame.from_dict(tasks, orient="index"))


def get_quality_statistics():
    st.markdown("**pending**")


def show(option: str, overview_db_path, scheduler_db_path, dataset_json_path=None):
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
        "Dataset": lambda: get_dataset_statistics(round_doc_table, dataset_json_path),
        "Annotators": lambda: get_annotator_statistics(assignment_table, worker_table),
        "HIT Schedule": lambda: get_hit_schedule(
            round_doc_table, stack_target_table, past_task_table, hit_table
        ),
        "Quality Control": lambda: get_quality_statistics(),
    }[option]()


overview_db_path = sys.argv[1]
scheduler_db_path = sys.argv[2]
dataset_json_path = sys.argv[3]

overview_edit_time = datetime.fromtimestamp(Path(overview_db_path).stat().st_mtime)
scheduler_edit_time = datetime.fromtimestamp(Path(scheduler_db_path).stat().st_mtime)
dataset_edit_time = datetime.fromtimestamp(Path(dataset_json_path).stat().st_mtime)
latest = max(overview_edit_time, scheduler_edit_time, dataset_edit_time)
latest = max(overview_edit_time, scheduler_edit_time,)
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

st.markdown(f"# {option}")

show(option, overview_db_path, scheduler_db_path, dataset_json_path)
