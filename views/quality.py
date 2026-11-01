"""Data quality, cleaning steps and limits."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import analytics as A
from src import ui
from src.config import OUTCOME_COLORS


def render() -> None:
    f = ui.current_filters()
    ui.page_header("Data Quality & Notes", "What is missing, what was cleaned, and how far the numbers can be trusted.")
    if not A.run("kpis", f)["exams"]:
        return ui.empty_state()

    st.subheader("How complete is the data?")
    miss = A.run("missing_by_year", f)
    nice = {"teacher_name": "Teacher", "mosque_name": "Mosque", "sector_name": "Sector"}
    fig = go.Figure(go.Heatmap(
        z=miss.values, x=[nice[c] for c in miss.columns], y=miss.index.astype(str), colorscale="Reds",
        zmin=0, zmax=100, text=miss.round(0).astype(int).values, texttemplate="%{text}",
        colorbar=dict(title="% missing"), hovertemplate="%{y} · %{x}: %{z:.0f}% missing<extra></extra>"))
    fig.update_layout(title="Share of exams with the value missing", yaxis=dict(autorange="reversed", type="category"))
    ui.show(fig, height=max(420, 26 * len(miss) + 120))
    ui.how_to_read("Darker red = more of that year's exams have the field empty. Any chart split by sector only "
                   "represents the years where the sector is filled in.")

    st.subheader("Grades")
    g = A.run("grade_counts", f)
    fig = go.Figure(go.Bar(y=g["exam_grade"].astype(str), x=g["exams"], orientation="h",
                           marker_color=[OUTCOME_COLORS[o] for o in g["outcome"].astype(str)],
                           hovertemplate="%{y}: %{x:,} exams<extra></extra>"))
    fig.update_layout(title="Exams by grade (colour = outcome: green passed, orange failed, yellow absent)")
    ui.show(fig, height=380)

    st.subheader("What was cleaned")
    st.caption("Counts below come from the original notebook run on the full data, not from the current filters.")
    ui.table(pd.DataFrame([
        ("Combine the two exports", "595,157 rows", "Different column names mapped onto one set; Hijri dates converted to Gregorian"),
        ("Remove repeated exams", "-58,886", "The same exam_id sat in both exports"),
        ("Remove unusable outcomes", "-809 (0.15%)", "Grade was none of passed / failed / absent"),
        ("Invalid exam branch", "-2", "Only the 11 known branches are kept"),
        ("Missing student ids", "43,657 rows", "5,048 filled from matching names; 38,609 rows got a made-up id (23,382 names)"),
        ("Repeated passes", "-1,234", "A student passes a branch once; the first pass is kept"),
        ("Impossible dates", "2002-2025 only", "Hijri-year typos produce impossible dates; they are left out"),
        ("Final table", "534,226 exams", "459,993 of them attended (passed + failed)"),
    ], columns=["Step", "Effect", "Why"]), hide_index=True)

    st.subheader("Limits to keep in mind")
    ui.warn("""
<ul>
<li><b>2007</b> is lost data (a corrupted cloud database), and <b>2025</b> stops on 27 November. The Classera system, which took over exams in 2025, is not included, so recent volume is understated.</li>
<li>Many early <b>student ids were rebuilt from names</b>. Common names can merge different students; spelling variants can split one student into two.</li>
<li>The <b>sector</b> columns are empty for a large share of exams, so sector comparisons cover only part of the data.</li>
<li>A failed attempt is stored with a placeholder score, so <b>scores are only meaningful for passed exams</b>.</li>
<li><b>Teacher quality cannot be judged from marks alone</b>: marking standards may differ between teachers.</li>
</ul>""", title="Limits")

    st.subheader("Glossary")
    st.markdown("""
- **Halaqa (halaqat):** a Quran memorization circle run by a teacher at a mosque.
- **Branch:** an exam level (1, 2, 3, 5, 8, 10, 13, 15, 20, 25, 30), treated here as ordered steps.
- **Attended exam:** the student sat the exam and got a result (passed or failed). Absent exams are excluded from pass rates.
- **Pass rate:** passed ÷ attended exams.
- **Sector:** a geographic or programme grouping of mosques (for example North Jeddah, Evening Centres).
""")
