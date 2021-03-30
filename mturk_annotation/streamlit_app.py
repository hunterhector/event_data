"""
Reads latest AMT databases to create summaries
"""

import sys, re

import streamlit as st
import numpy as np
import pandas as pd
from tinydb import TinyDB, where
from collections import Counter, defaultdict
from datetime import datetime
import plotly.express as px
from pathlib import Path
import json

NA_STR = "-"


def get_hit_statistics(hit_table, assignment_table):

    view_options = ["Overview", "Activity", "Duration"]
    view_option = st.radio("Choose a view", options=view_options)

    if view_option == view_options[0]:
        summary = {}

        released_hits = hit_table.search(where("HITId").exists())
        summary["Released HITs"] = len(released_hits)

        completed_hits = hit_table.search(where("ApprovedTime").exists())
        summary["Completed HITs"] = len(completed_hits)

        reviewable_hits = hit_table.search(
            (where("HITStatus") == "Reviewable") & (~where("ApprovedTime").exists())
        )
        summary["Reviewable HITs"] = len(reviewable_hits)

        open_hits = hit_table.search((where("HITStatus") == "Assignable"))
        summary["Open HITs"] = len(open_hits)

        submitted_assigns = assignment_table.search(where("SubmitTime").exists())
        avg_times = [
            (datetime.fromisoformat(x["SubmitTime"]) - datetime.fromisoformat(x["AcceptTime"])).seconds / 60
            for x in submitted_assigns
        ]
        summary["Avg. time per HIT (mins)"] = f"{np.mean(avg_times):.2f}"
        approved_assigns = assignment_table.search(where("ApprovalTime").exists())
        avg_times = [
            (datetime.fromisoformat(x["ApprovalTime"]) - datetime.fromisoformat(x["SubmitTime"])).seconds
            / 60
            / 60
            for x in approved_assigns
        ]
        # print(avg_times)
        summary["Avg. time taken for approval (hours)"] = f"{np.mean(avg_times):.2f}"

        st.table(pd.DataFrame.from_dict(summary, orient="index", columns=[""]))

    elif view_option == view_options[1]:
        # HITs released per day
        release_times = [datetime.fromisoformat(x["CreationTime"]) for x in hit_table.all()]
        release_times = [(x - np.min(release_times)).days for x in release_times]
        release_counter = Counter(release_times)

        # HITs solved per day
        submitted_assigns = assignment_table.search(where("SubmitTime").exists())
        submit_times = [datetime.fromisoformat(x["SubmitTime"]) for x in submitted_assigns]
        submit_times = [(x - np.min(submit_times)).days for x in submit_times]
        submit_counter = Counter(submit_times)

        df = defaultdict(list)
        c_df = defaultdict(list)
        days = np.arange(0, max(np.max(submit_times), np.max(release_times)) + 1)
        release_sum, submit_sum = 0, 0
        for i in days:
            release_sum += release_counter[i]
            submit_sum += submit_counter[i]
            df["Day X"].append(i)
            c_df["Day X"].append(i)
            df["# HITs released"].append(release_counter[i])
            c_df["# HITs released"].append(release_sum)
            df["# HITs finished"].append(submit_counter[i])
            c_df["# HITs finished"].append(submit_sum)

        st.markdown("## HIT activity")
        st.markdown("### Release")
        options = ["HITs released (daily)", "HITs released (cumulative)"]
        option = st.radio("", options=options)
        range_x = [-1, len(days) + 1]
        if option == options[0]:
            fig = px.line(df, x="Day X", y="# HITs released", range_x=range_x)
        elif option == options[1]:
            fig = px.line(c_df, x="Day X", y="# HITs released", range_x=range_x)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Finish")
        options = ["HITs finished (daily)", "HITs finished (cumulative)"]
        option = st.radio("", options=options)
        if option == options[0]:
            fig = px.line(df, x="Day X", y="# HITs finished", range_x=range_x,)
        elif option == options[1]:
            fig = px.line(c_df, x="Day X", y="# HITs finished", range_x=range_x)
        st.plotly_chart(fig, use_container_width=True)

    elif view_option == view_options[2]:
        st.markdown("## HIT durations")
        st.write(
            "Over the timeline of released HITs, below plot shows the trends in time taken for each HIT."
        )
        df = defaultdict(list)
        hit_counter = defaultdict(lambda: len(hit_counter))
        for assign in assignment_table.search(where("SubmitTime").exists()):
            df["WorkerId"].append(assign["WorkerId"])
            df["HITId (timeline)"].append(hit_counter[assign["HITId"]])
            df["Duration (mins) "].append(
                (
                    datetime.fromisoformat(assign["SubmitTime"])
                    - datetime.fromisoformat(assign["AcceptTime"])
                ).seconds
                / 60
            )
            # df["Approval Delay"].append(
            #     (
            #         datetime.fromisoformat(assign["ApprovalTime"])
            #         - datetime.fromisoformat(assign["SubmitTime"])
            #     ).seconds
            #     / 60
            # )
        fig = px.line(
            df,
            x="HITId (timeline)",
            y="Duration (mins) ",
            range_y=[0, 45],
            range_x=[-1, len(hit_counter) + 1],
        )
        st.plotly_chart(fig, use_container_width=True)


def get_dataset_statistics(round_doc_table, dataset_json_path: Path = None):

    view_options = ["Overview", "Document release schedule"]
    view_option = st.radio("Choose a view", options=view_options)

    if dataset_json_path:
        with open(dataset_json_path, "r") as rf:
            dataset_stats = json.load(rf)
            all_docs = set()
            ann2docs = defaultdict(int)
            links2docs = defaultdict(int)
            total_link_count = 0
            for doc_pair, values in dataset_stats.items():
                all_docs.update(doc_pair.split("_"))
                ann2docs[len(values["annotators"])] += 1
                for k, c in values["links"].items():
                    links2docs[k] += c
                    total_link_count += c

    if view_option == view_options[0]:
        summary = {}
        if dataset_json_path:
            summary["Documents annotated"] = len(all_docs)
            summary["Document pairs annotated"] = len(dataset_stats.keys())
            summary["Links found"] = total_link_count

            st.markdown("## Overview")
            st.table(pd.DataFrame.from_dict(summary, orient="index", columns=[""]))

            df = defaultdict(list)
            for k, v in links2docs.items():
                df["Num. of annotators"].append(k)
                df["Num. of links"].append(v)

            fig = px.pie(df, values="Num. of links", names="Num. of annotators")
            st.markdown("## Agreement")
            st.write(
                "Pie chart showing the distribution of coreference links with the number of unique annotators per link. Higher the number of unique annotators, higher the agreement."
            )
            st.plotly_chart(fig, use_container_width=True)

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
        "Worker statistics",
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

        st.markdown("## Overall worker statistics")
        df = pd.DataFrame.from_dict(worker_summary, orient="index")
        st.dataframe(df.style.apply(highlight_worker, subset="Qualification Score", axis=1))

    elif view_option == view_options[1]:
        worker_summary = {}
        active = worker_table.search(where("isActive") == True)
        for worker in active:
            worker_id = worker["WorkerId"]
            worker_summary[worker_id] = {}
            worker_summary[worker_id]["Qualification Score"] = worker["IntegerValue"]
            worker_summary[worker_id]["Qualification Date"] = datetime.strftime(
                datetime.fromisoformat(worker["GrantTime"]), "%b %d"
            )
            assigns = assignment_table.search(where("WorkerId") == worker_id)
            worker_summary[worker_id]["HITs"] = len(assigns)
            # ! todo: uniq document pairs annotated
            times = [
                (datetime.fromisoformat(x["SubmitTime"]) - datetime.fromisoformat(x["AcceptTime"])).seconds
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

        st.markdown("## Worker statistics")
        st.table(pd.DataFrame.from_dict(worker_summary, orient="index"))

    elif view_option == view_options[2]:
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

    elif view_option == view_options[3]:
        df = defaultdict(list)
        worker_hit_count = defaultdict(int)
        # for assign in assignment_table.search(where("ApprovalTime").exists()):
        for assign in assignment_table.search(where("SubmitTime").exists()):
            df["WorkerId"].append(assign["WorkerId"])
            worker_hit_count[assign["WorkerId"]] += 1
            df["Worker HIT counter"].append(f"hit{worker_hit_count[assign['WorkerId']]}")
            df["HITId"].append(assign["HITId"])
            df["Duration (mins) "].append(
                (
                    datetime.fromisoformat(assign["SubmitTime"])
                    - datetime.fromisoformat(assign["AcceptTime"])
                ).seconds
                / 60
            )
            # df["Approval Delay"].append(
            #     (
            #         datetime.fromisoformat(assign["ApprovalTime"])
            #         - datetime.fromisoformat(assign["SubmitTime"])
            #     ).seconds
            #     / 60
            # )

        fig = px.line(df, x="Worker HIT counter", y="Duration (mins) ", color="WorkerId", range_y=[0, 30],)
        st.markdown("## HIT duration (trends)")
        st.write("For each worker, this plot shows the timeline of HIT durations.")
        st.plotly_chart(fig, use_container_width=True)


def get_hit_schedule(stack_target_table, past_task_table):

    view_options = ["Round progress", "Task progress"]
    view_option = st.radio("Choose a view", options=view_options)

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
            tasks[f"Task {task_id}"]["HITId"] = task["HITId"]
            tasks[f"Task {task_id}"]["Annotators"] = task["annotators"]
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
        "HIT Schedule": lambda: get_hit_schedule(stack_target_table, past_task_table),
        "Quality Control": lambda: get_quality_statistics(),
    }[option]()


overview_db_path = sys.argv[1]
scheduler_db_path = sys.argv[2]
# dataset_json_path = sys.argv[3]

overview_edit_time = datetime.fromtimestamp(Path(overview_db_path).stat().st_mtime)
scheduler_edit_time = datetime.fromtimestamp(Path(scheduler_db_path).stat().st_mtime)
# dataset_edit_time = datetime.fromtimestamp(Path(dataset_json_path).stat().st_mtime)
# latest = max(overview_edit_time, scheduler_edit_time, dataset_edit_time)
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

show(option, overview_db_path, scheduler_db_path, None)
