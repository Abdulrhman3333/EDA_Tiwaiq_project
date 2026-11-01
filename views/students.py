"""Students (notebook question Q6). Only ids are shown, never names."""
import plotly.graph_objects as go
import streamlit as st

from src import analytics as A
from src import ui
from src.config import BRANCHES, C_PRIMARY


def render() -> None:
    f = ui.current_filters()
    ui.page_header("Students",
                   "How far do students get through the 11 branches, and who stands out?")
    if not A.run("kpis", f)["exams"]:
        return ui.empty_state()
    ui.warn("Part of the student ids were rebuilt from names, and one common name can hide several people, so "
            "everything here is <b>indicative</b>. Only ids are shown, never names, because most students are children.",
            title="Privacy and accuracy")

    bp = A.run("branches_passed_dist", f)
    dist = bp["dist"]
    ui.kpi_row([
        ("Students who passed ≥1 branch", ui.n(bp["students"]), ""),
        (f"Passed all {len(BRANCHES)} branches", ui.n(bp["completed"]), "completed the full path"),
        ("…without ever failing or missing", ui.n(bp["perfect"]), "perfect record"),
    ])
    st.write("")
    fig = go.Figure(go.Bar(x=dist.index.astype(str), y=dist.values, marker_color=C_PRIMARY,
                           text=[f"{v:,}" for v in dist.values], textposition="outside",
                           hovertemplate="%{x} branches: %{y:,} students<extra></extra>"))
    fig.update_layout(title="Students by number of different branches passed",
                      xaxis_title="branches passed", yaxis_title="students")
    ui.show(fig, height=420)
    ui.how_to_read("Each bar is a group of students. The bar at '1' is students who passed exactly one branch, and "
                   "so on up to 11, the full path.")
    if len(dist) and bp["students"]:
        share_one = dist.get(1, 0) / bp["students"] * 100
        ui.insight(f"<b>{share_one:.0f}%</b> of students passed just one branch, and only "
                   f"<b>{bp['completed'] / bp['students'] * 100:.1f}%</b> completed all {len(BRANCHES)}. "
                   "Most students join at a single level or stop early. Reaching the end is rare, "
                   "which makes the full path a real achievement.")

    st.subheader("Standout cases")
    tab1, tab2 = st.tabs(["Most 'Excellent' results", "Most failed attempts"])
    with tab1:
        ex = A.run("top_excellent", f)
        if ex.empty:
            st.info("No excellent grades in the current selection.")
        else:
            ui.table(ex.rename(columns={
                "excellent_exams": "Excellent exams", "exams": "Total exams", "teachers": "Different teachers",
                "share_with_main_teacher": "% exams with main teacher"}))
            ui.warn("Counting excellent exams favours students who sat many exams, so this list is partly a list of "
                    "long-running students. Several teachers per student is common; a student who kept one teacher "
                    "has 100% in the last column.")
    with tab2:
        mf = A.run("most_failed", f)
        ui.table(mf.rename(columns={"failed": "Failed", "absent": "Absent", "passed": "Passed", "exams": "Total exams"}))
        ui.how_to_read("Students with the most failed attempts. Many of them eventually pass: persistence also "
                       "shows up here, so a long failed count is not always a bad sign.")
