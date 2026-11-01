"""COVID impact (notebook question Q3)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src import analytics as A
from src import ui
from src.config import (C_ABSENT, C_FAIL, C_PASS, C_PRIMARY, COVID_END, COVID_START, OUTCOME_COLORS,
                        OUTCOME_LABELS)


def render() -> None:
    f = ui.current_filters()
    ui.page_header("COVID Impact",
                   "Did the pandemic change how many exams were held, how many students passed, or who showed up?")
    if not A.run("kpis", f)["exams"]:
        return ui.empty_state()

    ui.warn("The COVID window is assumed to be <b>March 2020 - December 2021</b>. The comparison needs data "
            "from 2017-2024, so widen the year range in the sidebar if cells below are empty.", title="Assumption")

    st.subheader("Before / during / after")
    tbl = A.run("covid_table", f)
    ui.table(tbl.style.format("{:.1f}", na_rep="-"))
    ui.how_to_read("Each row is one period. 'Exams per month' makes the periods comparable even though they are "
                   "different lengths. Compare the rows: volume reacts first, then the pass rate, and the "
                   "absent share shows whether students simply did not turn up.")
    if tbl.notna().all().all():
        b, c, a = tbl.iloc[0], tbl.iloc[1], tbl.iloc[2]
        ui.insight(
            f"During COVID the programme held <b>{c.iloc[0]:,.0f}</b> exams a month (vs <b>{b.iloc[0]:,.0f}</b> "
            f"before), the pass rate fell from <b>{b.iloc[1]:.1f}%</b> to <b>{c.iloc[1]:.1f}%</b>, and absences "
            f"rose from <b>{b.iloc[2]:.1f}%</b> to <b>{c.iloc[2]:.1f}%</b>. After COVID the pass rate recovered to "
            f"<b>{a.iloc[1]:.1f}%</b>, but absences stayed high at <b>{a.iloc[2]:.1f}%</b>.")

    st.subheader("Year by year")
    c1, c2 = st.columns(2)
    with c1:
        mix = A.run("outcome_mix_year", f)
        fig = go.Figure()
        for o in ["passed", "failed", "absent"]:
            fig.add_bar(x=mix.index, y=mix[o], name=OUTCOME_LABELS[o], marker_color=OUTCOME_COLORS[o])
        fig.update_layout(barmode="stack", title="Passed, failed, absent: share of each year",
                          yaxis=dict(range=[0, 100], ticksuffix="%"), xaxis=dict(dtick=1))
        ui.show(fig, legend_below=True)
    with c2:
        pr = A.run("pass_rate_year", f)
        fig = go.Figure(go.Scatter(x=pr.index, y=pr.values, mode="lines+markers",
                                   line=dict(color=C_PASS, width=3), name="Pass rate",
                                   hovertemplate="%{x}: %{y:.1f}%<extra></extra>"))
        fig.add_vrect(x0=2019.5, x1=2021.5, fillcolor="grey", opacity=0.15, line_width=0)
        fig.update_layout(title="Pass rate of attended exams", yaxis=dict(ticksuffix="%"), xaxis=dict(dtick=1))
        ui.show(fig, legend_below=True)
    ui.how_to_read("**Left:** bars always add up to 100%. **Right:** pass rate counts only students who actually "
                   "sat the exam (absences are excluded). The grey band marks the COVID years.")

    st.subheader("Month by month")
    ms = A.run("monthly_series", f)
    ms = ms[(ms["month"] >= "2016-01-01") & (ms["month"] <= "2025-10-31")] if len(ms) else ms
    if len(ms):
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                            subplot_titles=("Exams per month", "Pass rate and absent share"))
        fig.add_scatter(x=ms["month"], y=ms["exams"], name="Monthly", line=dict(color=C_PRIMARY, width=1),
                        opacity=0.45, row=1, col=1)
        fig.add_scatter(x=ms["month"], y=ms["exams_12m"], name="12-month average",
                        line=dict(color="#1d3557", width=3), row=1, col=1)
        fig.add_scatter(x=ms["month"], y=ms["pass_rate_6m"], name="Pass rate (6-month avg)",
                        line=dict(color=C_PASS, width=3), row=2, col=1)
        fig.add_scatter(x=ms["month"], y=ms["absent_share_6m"], name="Absent share (6-month avg)",
                        line=dict(color="#b08900", width=3), row=2, col=1)
        for r in (1, 2):
            fig.add_vrect(x0=COVID_START, x1=COVID_END, fillcolor="grey", opacity=0.15, line_width=0, row=r, col=1)
        fig.update_yaxes(ticksuffix="%", row=2, col=1)
        ui.show(fig, height=620, legend_below=True)
        ui.how_to_read("Thin line = the raw month, thick line = a smoothed average that hides the noise. "
                       "The grey band is the COVID window.")
    ui.warn("The pass rate drop in 2021 matches the year of online exams. Possible reasons are exam stress in "
            "the new format and weaker revision without in-person halaqat, but <b>this data cannot test "
            "either explanation</b>. Volume differences can also be seasonal, because the school calendar moved.")
