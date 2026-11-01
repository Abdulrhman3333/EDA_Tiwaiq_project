"""Quran Exams Dashboard: entry point.

Run with:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="Quran Exams Dashboard", page_icon="📖", layout="wide",
                   initial_sidebar_state="expanded")

from src import data, ui                      # noqa: E402  (after set_page_config on purpose)
from views import branches, covid, overview, people, quality, students, trends   # noqa: E402

ui.inject_css()

df, is_demo = data.load_data()

# ---- navigation -------------------------------------------------------------
pages = [
    st.Page(overview.render, title="Overview", icon="🏠", url_path="overview", default=True),
    st.Page(trends.render, title="Volume & Seasonality", icon="📈", url_path="trends"),
    st.Page(covid.render, title="COVID Impact", icon="🦠", url_path="covid"),
    st.Page(branches.render, title="Branch Progression", icon="🪜", url_path="branches"),
    st.Page(people.render, title="Teachers, Mosques & Sectors", icon="🕌", url_path="people"),
    st.Page(students.render, title="Students", icon="🎓", url_path="students"),
    st.Page(quality.render, title="Data Quality & Notes", icon="🔎", url_path="quality"),
]
nav = st.navigation(pages)

# ---- global filters (apply to every page) -----------------------------------
with st.sidebar:
    st.markdown("### Filters")
    if is_demo:
        st.markdown('<div class="demo-banner"><b>Demo data.</b> The processed dataset was not found, so '
                    'invented sample data is shown. Run <code>python -m src.prepare_data</code> '
                    'to use the real exams.</div>', unsafe_allow_html=True)

    lo, hi = int(df["exam_year"].min()), int(df["exam_year"].max())
    year_from, year_to = st.slider("Years", lo, hi, (lo, hi), help="Gregorian years of the exam date.")

    all_sectors = data.sector_options(df)
    sectors = st.multiselect("Sectors", all_sectors, default=all_sectors,
                             help="Leave all selected to include every sector.")
    include_missing = st.checkbox("Include exams with no sector recorded", value=True,
                                  help="The sector is empty for a large share of older exams.")
    st.caption(f"Data covers {df['exam_date'].min():%b %Y} – {df['exam_date'].max():%b %Y}.")

st.session_state["filters"] = data.Filters(year_from, year_to, tuple(sectors), include_missing)

nav.run()
