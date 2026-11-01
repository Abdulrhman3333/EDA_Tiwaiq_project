"""Volume and seasonality (notebook questions Q1 and Q2)."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src import analytics as A
from src import ui
from src.config import C_ACCENT, C_DARK, C_PRIMARY, C_SOFT, MONTH_NAMES, WEEKDAY_NAMES


def render() -> None:
    f = ui.current_filters()
    ui.page_header("Volume & Seasonality",
                   "How many exams happen, when in the year, and does timing say anything about scores?")
    if not A.run("kpis", f)["exams"]:
        return ui.empty_state()

    tab1, tab2, tab3, tab4 = st.tabs(["Exams per year", "Month by year", "Month vs score", "Students & weekdays"])

    with tab1:
        yv = A.run("yearly_volume", f)
        fig = go.Figure(go.Bar(x=yv["year"], y=yv["exams"], marker_color=C_PRIMARY,
                               hovertemplate="%{x}: %{y:,} exams<extra></extra>"))
        fig.update_layout(title="Exams per year", yaxis_title="exams", xaxis=dict(dtick=1))
        ui.show(fig)
        ui.how_to_read("Each bar is one calendar year. Very short bars are usually missing data, not quiet years.")
        ui.insight(
            "Volume is low before 2008 (and almost empty in 2007: the cloud database was corrupted), "
            "sits around 25-30k exams a year in the 2010s, dips in 2020-2022, and peaks in 2023-2024. "
            "The 2025 bar looks like a drop, but the data ends on 27 November 2025, and the newer Classera "
            "system (not included here) took over part of the exams.")

    with tab2:
        heat = A.run("month_year_heat", f)
        fig = go.Figure(go.Heatmap(
            z=heat.values, x=MONTH_NAMES, y=heat.index.astype(str), colorscale="YlGnBu",
            hovertemplate="%{y} %{x}: %{z:,} exams<extra></extra>", colorbar=dict(title="exams")))
        fig.update_layout(title="Exams by month and year", yaxis=dict(autorange="reversed", type="category"))
        ui.show(fig, height=max(420, 26 * len(heat) + 120))
        ui.how_to_read("Darker = more exams. Read across a row to see which months a year is busy; "
                       "read down a column to see how that month changes over the years.")
        ui.insight("Exams come in <b>two waves per year</b>, at the end of each school semester. The waves "
                   "slide earlier over the years because the school calendar started earlier "
                   "(visible as a diagonal band).")

    with tab3:
        ms = A.run("month_stats", f)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_bar(x=MONTH_NAMES, y=ms["exams"], name="Exams", marker_color="#d5dcda", secondary_y=False)
        fig.add_scatter(x=MONTH_NAMES, y=ms["mean_score"], name="Mean passing score", mode="lines+markers",
                        line=dict(color=C_ACCENT, width=3), secondary_y=True)
        fig.update_yaxes(title_text="exams", secondary_y=False)
        fig.update_yaxes(title_text="mean score of passed exams", secondary_y=True)
        fig.update_layout(title="Volume and mean passing score by month")
        ui.show(fig, legend_below=True)
        corr = ms["exams"].corr(ms["mean_score"])
        ui.how_to_read("Grey bars = number of exams in the month. Orange line = average score of the exams "
                       "that were passed. The score line only moves a few points.")
        if np.isfinite(corr):
            ui.insight(
                f"The correlation between monthly volume and mean score is <b>{corr:.2f}</b>. The busiest "
                "months (end of semester) tend to have slightly <i>lower</i> scores: teachers sometimes "
                "examine at the deadline whether or not students are fully ready. The effect is small "
                "(two to three points), so treat it as a pattern to watch, not a strong result.")

    with tab4:
        nr = A.run("new_vs_returning", f)
        fig = go.Figure()
        fig.add_bar(x=nr["year"], y=nr["new"], name="First year in the data", marker_color=C_DARK)
        fig.add_bar(x=nr["year"], y=nr["returning"], name="Already seen before", marker_color=C_SOFT)
        fig.update_layout(barmode="stack", title="Students examined per year: new vs returning",
                          yaxis_title="students", xaxis=dict(dtick=1))
        ui.show(fig, legend_below=True)
        ui.how_to_read("Dark = students appearing for the first time in the selected data, light = students "
                       "who were already examined in an earlier year. The first years always look 'new' "
                       "because there is nothing earlier to compare with.")

        wd = A.run("weekday_share", f)
        fig = go.Figure(go.Heatmap(
            z=wd.values, x=WEEKDAY_NAMES, y=wd.index.astype(str), colorscale="Blues",
            text=np.round(wd.values).astype(int), texttemplate="%{text}", colorbar=dict(title="% of year"),
            hovertemplate="%{y} %{x}: %{z:.0f}%<extra></extra>"))
        fig.update_layout(title="Share of each year's exams by weekday", yaxis=dict(autorange="reversed", type="category"))
        ui.show(fig, height=max(420, 26 * len(wd) + 120))
        ui.insight("Saudi Arabia moved its weekend from Thursday-Friday to Friday-Saturday around 2013, "
                   "so the weekday columns shift between early and later years. That confirms the date "
                   "conversion is right, and shows which days examiners are actually needed.")
