"""Teachers, mosques and sectors (notebook question Q5)."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from src import analytics as A
from src import ui
from src.config import C_ACCENT, C_DARK, C_FAIL, C_PASS, C_PRIMARY


def render() -> None:
    f = ui.current_filters()
    ui.page_header("Teachers, Mosques & Sectors",
                   "Who carries the workload, and do results differ between teachers, mosques and sectors?")
    k = A.run("kpis", f)
    if not k["exams"]:
        return ui.empty_state()

    tab1, tab2, tab3 = st.tabs(["Teachers", "Mosques", "Sectors"])

    with tab1:
        min_passed = st.slider("Minimum passed exams for the 'highest score' list", 10, 200, 50, step=10)
        t = A.run("teacher_tables", f, min_passed=min_passed)
        c1, c2 = st.columns(2)
        with c1:
            tv = t["top_volume"].iloc[::-1]
            fig = go.Figure(go.Bar(y=tv.index.astype(str), x=tv.values, orientation="h", marker_color=C_PRIMARY,
                                   hovertemplate="%{y}: %{x:,} passed exams<extra></extra>"))
            fig.update_layout(title="Most passed exams (workload)", xaxis_title="passed exams")
            ui.show(fig, height=440)
        with c2:
            ts = t["top_score"].iloc[::-1]
            if len(ts):
                fig = go.Figure(go.Bar(y=ts.index.astype(str), x=ts["mean_score"], orientation="h",
                                       marker_color=C_ACCENT, customdata=ts["passed"],
                                       hovertemplate="%{y}: %{x:.1f} (%{customdata:,} exams)<extra></extra>"))
                fig.update_layout(title=f"Highest mean passing score ({min_passed}+ passed exams)",
                                  xaxis=dict(range=[85, 100], title="mean score"))
                ui.show(fig, height=440)
            else:
                st.info("No teacher has that many passed exams in the current selection.")
        ui.warn("A high mean score can mean strong students <b>or</b> lenient marking. The data cannot tell them "
                "apart, so the right-hand chart is <b>not</b> a ranking of teaching quality. The left chart is "
                "about workload.", title="Read carefully")

        if "lorenz" in t:
            c1, c2 = st.columns([3, 2])
            with c1:
                lz = t["lorenz"]
                fig = go.Figure()
                fig.add_scatter(x=[0, 100], y=[0, 100], mode="lines", name="Everyone equal",
                                line=dict(color="grey", dash="dash"))
                fig.add_scatter(x=lz["teachers_pct"], y=lz["exams_pct"], mode="lines", name="Actual",
                                line=dict(color=C_DARK, width=3), fill="tonexty", fillcolor="rgba(38,70,83,0.08)")
                fig.add_scatter(x=[10], y=[t["top10_share"]], mode="markers", name="Top 10% of teachers",
                                marker=dict(color=C_FAIL, size=11))
                fig.update_layout(title="How concentrated is the work?",
                                  xaxis=dict(title="% of teachers (busiest first)", ticksuffix="%"),
                                  yaxis=dict(title="% of exams", ticksuffix="%"))
                ui.show(fig, height=430, legend_below=True)
            with c2:
                st.write("")
                ui.kpi_row([("Top 10% of teachers", f"{t['top10_share']:.0f}%", "of all exams")])
                st.write("")
                ui.kpi_row([("Median per teacher", f"{t['median_load']:.0f}", "exams")])
                st.write("")
                ui.kpi_row([("Under 20 exams", f"{t['under20_share']:.0f}%", "of teachers")])
            ui.how_to_read("Teachers are sorted from busiest to least busy. The further the curve bends away from "
                           "the dashed diagonal, the more a small group carries the exams.")
            ui.insight(f"The busiest <b>10%</b> of teachers handle <b>{t['top10_share']:.0f}%</b> of all exams, while "
                       f"<b>{t['under20_share']:.0f}%</b> of teachers examine fewer than 20 students (often people who "
                       "covered a halaqa briefly). Losing a few core teachers would hit the programme hard.")

    with tab2:
        min_exams = st.slider("Minimum attended exams per mosque", 100, 2000, 500, step=100)
        m = A.run("mosque_table", f, min_exams=min_exams)
        if m.empty:
            st.info("No mosque reaches that many attended exams in the current selection. Lower the minimum.")
        else:
            overall = k["pass_rate"]
            size = 12 + m["students"] / m["students"].max() * 38
            fig = go.Figure(go.Scatter(
                x=m["exams"], y=m["pass_rate"], mode="markers", text=m["mosque_name"].astype(str),
                marker=dict(size=size, color=C_PASS, opacity=0.55, line=dict(color="white", width=1)),
                customdata=m["students"],
                hovertemplate="<b>%{text}</b><br>%{x:,} attended exams<br>pass rate %{y:.1f}%<br>"
                              "%{customdata:,} students<extra></extra>"))
            fig.add_hline(y=overall, line_dash="dash", line_color="grey",
                          annotation_text=f"overall {overall:.0f}%", annotation_position="bottom right")
            fig.update_layout(title=f"{len(m)} mosques: volume vs pass rate (bubble size = students)",
                              xaxis=dict(title="attended exams (log scale)", type="log"),
                              yaxis=dict(title="pass rate", ticksuffix="%"))
            ui.show(fig, height=520)
            ui.how_to_read("Each bubble is a mosque. Hover to see its name. **Right** = more exams; **up** = higher "
                           "pass rate; **bigger bubble** = more students.")
            ui.insight("Big bubbles far <b>below</b> the dashed line are mosques where many students struggle. They "
                       "matter more than small bubbles with a low rate, which can be chance. Small bubbles near the "
                       "top are mosques with few exams, where a high pass rate can easily be luck.")
            with st.expander("Show the table"):
                ui.table(m.sort_values("exams", ascending=False).rename(
                    columns={"mosque_name": "Mosque", "exams": "Attended exams", "pass_rate": "Pass rate %",
                             "students": "Students"}).round(1), hide_index=True)

    with tab3:
        s = A.run("sector_table", f)
        if s.empty:
            st.info("No sector information in the current selection.")
        else:
            min_att = st.slider("Minimum attended exams for the pass-rate chart", 50, 1000, 100, step=50)
            c1, c2 = st.columns(2)
            with c1:
                v = s.sort_values("passed", ascending=False).head(10).iloc[::-1]
                fig = go.Figure(go.Bar(y=v.index.astype(str), x=v["passed"], orientation="h", marker_color=C_PRIMARY))
                fig.update_layout(title="Sectors with the most passed exams", xaxis_title="passed exams")
                ui.show(fig, height=420)
            with c2:
                r = s[s["attended"] >= min_att].sort_values("pass_rate", ascending=False).head(10).iloc[::-1]
                fig = go.Figure(go.Bar(y=r.index.astype(str), x=r["pass_rate"], orientation="h", marker_color=C_ACCENT))
                fig.update_layout(title=f"Highest pass rate ({min_att}+ attended exams)",
                                  xaxis=dict(title="pass rate", ticksuffix="%"))
                ui.show(fig, height=420)
            ui.warn("The sector column is empty for a large share of exams (see <i>Data Quality & Notes</i>), so "
                    "this comparison covers only the exams that have a sector, not the whole history.")
            ui.table(s.head(15).rename(columns={"attended": "Attended", "passed": "Passed",
                                                "pass_rate": "Pass rate %", "mean_score": "Mean score"}).round(1))
