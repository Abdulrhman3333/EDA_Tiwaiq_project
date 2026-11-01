"""Progress through the exam branches (notebook question Q4)."""
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import analytics as A
from src import ui
from src.config import BRANCHES, C_ACCENT, C_FAIL, C_PASS, C_PRIMARY, C_SOFT


def render() -> None:
    f = ui.current_filters()
    ui.page_header("Branch Progression",
                   "Students climb through 11 exam levels (branches 1 to 30). How hard is each step, how long "
                   "does it take, and where do students stop?")
    if not A.run("kpis", f)["exams"]:
        return ui.empty_state()
    ui.warn("The branch numbers (1, 2, 3, 5 ... 30) are treated as ordered levels. They probably mean the amount "
            "of Quran covered, but that is an assumption to confirm with the charity.", title="Assumption")

    tab1, tab2, tab3, tab4 = st.tabs(["How hard is each branch?", "Where do students drop out?",
                                      "How long does it take?", "Scores"])

    with tab1:
        bs = A.run("branch_stats", f)
        x = [str(b) for b in BRANCHES]
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Bar(x=x, y=bs["pass_rate"], marker_color=C_PASS,
                                   text=bs["pass_rate"].round(0).astype("Int64").astype(str) + "%",
                                   textposition="outside",
                                   hovertemplate="Branch %{x}: %{y:.1f}%<extra></extra>"))
            fig.update_layout(title="Pass rate by branch", xaxis_title="exam branch",
                              yaxis=dict(range=[0, 108], ticksuffix="%"))
            ui.show(fig)
        with c2:
            fig = go.Figure(go.Bar(x=x, y=bs["attempts_to_pass"], marker_color=C_FAIL,
                                   text=bs["attempts_to_pass"].round(2), textposition="outside",
                                   hovertemplate="Branch %{x}: %{y:.2f} attempts<extra></extra>"))
            fig.update_layout(title="Attempts needed to pass", xaxis_title="exam branch",
                              yaxis=dict(range=[1, float(np.nanmax(bs["attempts_to_pass"])) * 1.1 if bs["attempts_to_pass"].notna().any() else 2]))
            ui.show(fig)
        ui.how_to_read("**Left:** of the students who sat the exam, how many passed. **Right:** for students who "
                       "eventually passed, how many tries it took on average (1.00 = everyone passed first time). "
                       "Students who never passed are not in the right chart, so it understates the difficulty.")
        valid = bs["pass_rate"].dropna()
        if len(valid):
            hard = valid.idxmin()
            ui.insight(f"Difficulty is not a straight line. The pass rate falls from <b>{valid.iloc[0]:.0f}%</b> in "
                       f"branch {valid.index[0]} to a low of <b>{valid.min():.0f}%</b> at branch <b>{hard}</b>, "
                       "then partly recovers in the last branches. Students who reach the later branches are a "
                       "filtered, stronger group. The branches with a low pass rate <i>and</i> more attempts "
                       "are where extra revision support would help most.")
        show = bs.rename(columns={"attempts": "Attempts", "pass_rate": "Pass rate %",
                                  "attempts_to_pass": "Attempts to pass", "first_try_pct": "Passed on first try %"})
        ui.table(show.round(1))

    with tab2:
        reached, cont = A.run("reached_and_continuation", f)
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Bar(x=[str(b) for b in reached.index], y=reached.values, marker_color=C_PRIMARY,
                                   text=[f"{v:,}" for v in reached.values], textposition="outside"))
            fig.update_layout(title="Students who passed each branch", xaxis_title="exam branch")
            ui.show(fig)
        with c2:
            fig = go.Figure(go.Bar(x=cont.index, y=cont.values, marker_color=C_SOFT,
                                   text=[f"{v:.0f}%" for v in cont.values], textposition="outside"))
            fig.update_layout(title="Continuation: % who also pass the next branch",
                              yaxis=dict(range=[0, 110], ticksuffix="%"), xaxis_tickangle=-45)
            ui.show(fig)
        ui.how_to_read("**Left:** how many different students passed each branch. Students can join at any branch, "
                       "so the first bars are not a ceiling. **Right:** of those who passed a branch, the "
                       "share who went on to pass the next one. The lowest bar is where most students stop.")
        if cont.notna().any():
            worst = cont.idxmin()
            ui.insight(f"The step with the lowest continuation is <b>{worst}</b> (only <b>{cont.min():.0f}%</b> "
                       "go on). That is where most students stop, either because the step is hard or because the "
                       "programme ends for them (for example, leaving school). Recent students have not had "
                       "time to move on, which pulls the right chart down a little.")

    with tab3:
        st_df = A.run("step_times", f)
        fig = go.Figure(go.Bar(y=st_df.index[::-1], x=st_df["median_days"][::-1], orientation="h",
                               marker_color=C_ACCENT, text=st_df["median_days"][::-1].round(0), textposition="outside",
                               customdata=st_df["students"][::-1],
                               hovertemplate="%{y}: %{x:.0f} days (%{customdata:,} students)<extra></extra>"))
        fig.update_layout(title="Median days between passing one branch and the next", xaxis_title="days")
        ui.show(fig, height=480)
        ui.how_to_read("For each student, the first date they passed each branch is used. Pairs passed out of order "
                       "are ignored. A long bar means a slow step. Hover to see how many students it is based on.")
        ui.table(st_df.rename(columns={"students": "Students", "median_days": "Median days",
                                       "same_day_pct": "Same day %"}).round(1))

        span = A.run("span_years", f)
        st.subheader("From the first branch to the last")
        if len(span) >= 5:
            fig = px.histogram(x=span, nbins=30, color_discrete_sequence=["#6a4c93"])
            fig.add_vline(x=float(span.median()), line_dash="dash", line_color="black",
                          annotation_text=f"median {span.median():.1f} years")
            fig.update_layout(title=f"Years between passing branch 1 and branch 30 ({len(span):,} students)",
                              xaxis_title="years", yaxis_title="students", showlegend=False)
            ui.show(fig, height=380)
            ui.insight(f"Only <b>{len(span):,}</b> students passed both the first and the last branch. They took a "
                       f"median of <b>{span.median():.1f} years</b>. This is the most committed group, "
                       "not the typical student.")
        else:
            st.info("Not enough students who passed both branch 1 and branch 30 in the current selection.")

    with tab4:
        sc = A.run("scores_by_branch", f)
        fig = px.box(sc, x=sc["exam_branch"].astype(str), y="score", category_orders={"x": [str(b) for b in BRANCHES]},
                     color_discrete_sequence=["#8ecae6"], points=False)
        fig.update_layout(title="Scores of passed exams by branch", xaxis_title="exam branch", yaxis_title="score")
        ui.show(fig, height=440)
        ui.how_to_read("Each box covers the middle half of the scores; the line inside is the median; "
                       "whiskers show the usual range. Only passed exams have real marks.")
        ui.insight("The median score slides from the mid-90s in the first branches to about 90 in later ones. "
                   "The lowest passing score is around 70 for branches 1-2 and 60 for the rest, which suggests "
                   "the pass mark differs by branch. Worth confirming with the charity.")
        ui.table(A.run("score_summary", f).round(1).rename(columns={"count": "Passed exams", "mean": "Mean",
                                                                     "median": "Median", "min": "Lowest"}))
