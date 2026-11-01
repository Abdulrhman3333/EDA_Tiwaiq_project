"""Overview: the whole programme at a glance."""
import plotly.graph_objects as go
import streamlit as st

from src import analytics as A
from src import ui
from src.config import C_ABSENT, C_FAIL, C_PASS, C_PRIMARY, OUTCOME_COLORS, OUTCOME_LABELS


def render() -> None:
    f = ui.current_filters()
    ui.page_header("Quran Exams Dashboard",
                   "A plain-language look at 20+ years of Quran memorization exams in Jeddah.")
    k = A.run("kpis", f)
    if not k["exams"]:
        return ui.empty_state()

    ui.kpi_row([
        ("Exams recorded", ui.n(k["exams"]), f"{ui.n(k['attended'])} where the student attended"),
        ("Students", ui.n(k["students"]), "unique student ids"),
        ("Pass rate", ui.pct(k["pass_rate"]), "of exams the student sat"),
        ("Absent", ui.pct(k["absent_share"]), "of all scheduled exams"),
        ("Mean passing score", f"{k['mean_score']:.1f}", "out of 100, passed exams only"),
    ])
    st.write("")
    ui.insight(
        f"Between <b>{k['first']:%b %Y}</b> and <b>{k['last']:%b %Y}</b> the programme recorded "
        f"<b>{ui.n(k['exams'])}</b> exams from <b>{ui.n(k['students'])}</b> students, taught by "
        f"<b>{ui.n(k['teachers'])}</b> teachers in <b>{ui.n(k['mosques'])}</b> mosques. "
        f"Of the students who actually sat an exam, <b>{ui.pct(k['pass_rate'], 0)}</b> passed.",
        title="In one sentence")

    left, right = st.columns([3, 2])
    with left:
        yv = A.run("yearly_volume", f)
        colors = [C_PRIMARY] * len(yv)
        if len(colors):
            colors[-1] = "#9fc9c2"                         # last year is usually partial
        fig = go.Figure(go.Bar(x=yv["year"], y=yv["exams"], marker_color=colors,
                               hovertemplate="%{x}: %{y:,} exams<extra></extra>"))
        fig.update_layout(title="Exams per year", yaxis_title="exams", xaxis=dict(dtick=2))
        ui.show(fig, height=380)
    with right:
        counts = A.run("grade_counts", f)
        totals = counts.groupby("outcome", observed=True)["exams"].sum()
        order = [o for o in ["passed", "failed", "absent"] if o in totals.index]
        fig = go.Figure(go.Pie(
            labels=[OUTCOME_LABELS[o] for o in order], values=[totals[o] for o in order], hole=0.58,
            marker=dict(colors=[OUTCOME_COLORS[o] for o in order]), sort=False,
            textinfo="percent", hovertemplate="%{label}: %{value:,} exams<extra></extra>"))
        fig.update_layout(title="What happened to the exams", showlegend=True)
        ui.show(fig, height=380)

    ui.how_to_read(
        "- **Left:** each bar is one calendar year. The lighter last bar is a year that is not finished "
        "yet (the data stops at the end of November 2025).\n"
        "- **Right:** every exam ends in one of three ways: the student **passed**, **failed**, or "
        "did not show up (**absent**).")

    st.subheader("Where to go next")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**📈 Volume & Seasonality**  \nHow many exams per year, and which months are busiest?")
    c2.markdown("**🦠 COVID Impact**  \nDid the pandemic change volume, pass rate or absences?")
    c3.markdown("**🪜 Branch Progression**  \nWhich exam levels are hardest, and where do students stop?")
    c1.markdown("**🕌 Teachers, Mosques & Sectors**  \nWho carries the workload, and how do results differ?")
    c2.markdown("**🎓 Students**  \nHow far do students get? Standout and struggling cases.")
    c3.markdown("**🔎 Data Quality & Notes**  \nWhat is missing, what was cleaned, and what to trust.")
