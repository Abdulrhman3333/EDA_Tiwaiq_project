"""All the numbers behind the charts. Pure pandas, no plotting.

Every function takes the *filtered* exams DataFrame and returns small tables.
Use ``run("function_name", filters, **kwargs)`` from the views: it is cached, so
changing a filter recomputes only what is needed and re-visiting a page is instant.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BRANCHES, COVID_END, COVID_START, MIN_EXAMS_PER_GOOD_YEAR
from .data import Filters, get_filtered

try:
    import streamlit as st
    _cache = st.cache_data(show_spinner=False)
except Exception:                                   # allows testing without streamlit
    def _cache(fn):
        return fn


def _attended(df: pd.DataFrame) -> pd.DataFrame:
    """Exams where the student showed up and got a result."""
    return df[df["is_pass"] | df["is_fail"]]


def good_years(df: pd.DataFrame) -> list[int]:
    """Years with enough exams to be compared (drops years of lost data)."""
    counts = df.groupby("exam_year").size()
    return counts[counts >= MIN_EXAMS_PER_GOOD_YEAR].index.tolist()


# --------------------------------------------------------------------------- #
# Overview
# --------------------------------------------------------------------------- #
def kpis(df: pd.DataFrame) -> dict:
    att = _attended(df)
    return {
        "exams": len(df),
        "attended": len(att),
        "students": int(df["student_id"].nunique()),
        "teachers": int(df["teacher_name"].nunique()),
        "mosques": int(df["mosque_name"].nunique()),
        "pass_rate": float(att["is_pass"].mean() * 100) if len(att) else np.nan,
        "absent_share": float(df["is_absent"].mean() * 100) if len(df) else np.nan,
        "mean_score": float(df["score"].mean()) if df["score"].notna().any() else np.nan,
        "first": df["exam_date"].min(), "last": df["exam_date"].max(),
    }


def grade_counts(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["exam_grade", "outcome"], observed=True).size().reset_index(name="exams")
    return g[g["exams"] > 0].sort_values("exams")


def missing_by_year(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["teacher_name", "mosque_name", "sector_name"]
    blank = df[cols].astype("object").apply(lambda s: s.isna() | (s.astype(str).str.strip() == ""))
    miss = blank.groupby(df["exam_year"]).mean().mul(100)
    return miss.loc[miss.index.isin(good_years(df))]


# --------------------------------------------------------------------------- #
# Volume and seasonality
# --------------------------------------------------------------------------- #
def yearly_volume(df: pd.DataFrame) -> pd.DataFrame:
    per_year = df.groupby("exam_year").size()
    if per_year.empty:
        return pd.DataFrame(columns=["year", "exams"])
    full = per_year.reindex(range(int(per_year.index.min()), int(per_year.index.max()) + 1), fill_value=0)
    return full.rename_axis("year").reset_index(name="exams")


def month_year_heat(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["exam_year"].isin(good_years(df))]
    heat = d.pivot_table(index="exam_year", columns="exam_month", values="exam_id",
                         aggfunc="count", fill_value=0, observed=True)
    return heat.reindex(columns=range(1, 13), fill_value=0)


def month_stats(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("exam_month", observed=True)
              .agg(exams=("exam_id", "size"), mean_score=("score", "mean"))
              .reindex(range(1, 13)))


def new_vs_returning(df: pd.DataFrame) -> pd.DataFrame:
    first_year = df.groupby("student_id")["exam_year"].min()
    active = df.groupby("exam_year")["student_id"].nunique()
    new = first_year.value_counts().reindex(active.index, fill_value=0)
    out = pd.DataFrame({"new": new, "returning": active - new})
    return out.loc[out.index.isin(good_years(df))].rename_axis("year").reset_index()


def weekday_share(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["exam_year"].isin(good_years(df)) & (df["exam_year"] >= 2008)]
    wd = (d.groupby("exam_year")["weekday"].value_counts(normalize=True).unstack(fill_value=0)
           .reindex(columns=range(7), fill_value=0).mul(100))
    return wd


# --------------------------------------------------------------------------- #
# COVID
# --------------------------------------------------------------------------- #
def outcome_mix_year(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["exam_year"].isin(good_years(df))]
    mix = d.groupby("exam_year")["outcome"].value_counts(normalize=True).unstack(fill_value=0)
    return mix.reindex(columns=["passed", "failed", "absent"], fill_value=0).mul(100)


def pass_rate_year(df: pd.DataFrame) -> pd.Series:
    s = _attended(df).groupby("exam_year")["is_pass"].mean().mul(100)
    return s.loc[s.index.isin(good_years(df))]


def monthly_series(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    m = df.set_index("exam_date").sort_index()
    n = m.resample("MS").size()
    att = m[m["is_pass"] | m["is_fail"]]
    rate = att["is_pass"].resample("MS").mean().mul(100)
    absent = m["is_absent"].resample("MS").mean().mul(100)
    out = pd.DataFrame({"exams": n, "pass_rate": rate, "absent_share": absent})
    out["exams_12m"] = out["exams"].rolling(12, center=True).mean()
    out["pass_rate_6m"] = out["pass_rate"].rolling(6, center=True).mean()
    out["absent_share_6m"] = out["absent_share"].rolling(6, center=True).mean()
    return out.rename_axis("month").reset_index()


def covid_table(df: pd.DataFrame) -> pd.DataFrame:
    periods = {
        "Before (2017-2019)": ("2017-01-01", "2019-12-31"),
        "COVID (Mar 2020 - Dec 2021)": (COVID_START, COVID_END),
        "After (2022-2024)": ("2022-01-01", "2024-12-31"),
    }
    rows = []
    for name, (start, end) in periods.items():
        p = df[(df["exam_date"] >= start) & (df["exam_date"] <= end)]
        n_months = (pd.Timestamp(end).to_period("M") - pd.Timestamp(start).to_period("M")).n + 1
        seen = _attended(p)
        rows.append({
            "Period": name,
            "Exams per month": len(p) / n_months if len(p) else np.nan,
            "Pass rate of attended (%)": seen["is_pass"].mean() * 100 if len(seen) else np.nan,
            "Absent share (%)": p["is_absent"].mean() * 100 if len(p) else np.nan,
            "Mean passing score": p["score"].mean() if len(p) else np.nan,
        })
    return pd.DataFrame(rows).set_index("Period")


# --------------------------------------------------------------------------- #
# Branches
# --------------------------------------------------------------------------- #
def branch_stats(df: pd.DataFrame) -> pd.DataFrame:
    att = _attended(df)
    by = att.groupby("exam_branch").agg(attempts=("is_pass", "size"), pass_rate=("is_pass", "mean"))
    by["pass_rate"] *= 100
    sb = att.groupby(["student_id", "exam_branch"]).agg(fails=("is_fail", "sum"), passes=("is_pass", "sum"))
    passers = sb[sb["passes"] > 0]
    by["attempts_to_pass"] = (passers["fails"] + 1).groupby("exam_branch").mean()
    by["first_try_pct"] = (passers["fails"] == 0).groupby("exam_branch").mean().mul(100)
    return by.reindex(BRANCHES)


def reached_and_continuation(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    passed = df[df["is_pass"]]
    sets = {b: set(passed.loc[passed["exam_branch"] == b, "student_id"]) for b in BRANCHES}
    reached = pd.Series({b: len(s) for b, s in sets.items()})
    cont = pd.Series({
        f"{a} → {b}": len(sets[a] & sets[b]) / max(len(sets[a]), 1) * 100
        for a, b in zip(BRANCHES[:-1], BRANCHES[1:])})
    return reached, cont


def _first_pass(df: pd.DataFrame) -> pd.DataFrame:
    return (df[df["is_pass"]].groupby(["student_id", "exam_branch"])["exam_date"].min().unstack())


def step_times(df: pd.DataFrame) -> pd.DataFrame:
    fp = _first_pass(df)
    rows = []
    for a, b in zip(BRANCHES[:-1], BRANCHES[1:]):
        if a in fp and b in fp:
            gap = (fp[b] - fp[a]).dt.days.dropna()
            gap = gap[gap >= 0]
        else:
            gap = pd.Series(dtype=float)
        rows.append({"step": f"{a} → {b}", "students": len(gap),
                     "median_days": gap.median() if len(gap) else np.nan,
                     "same_day_pct": (gap == 0).mean() * 100 if len(gap) else np.nan})
    return pd.DataFrame(rows).set_index("step")


def span_years(df: pd.DataFrame) -> pd.Series:
    fp = _first_pass(df)
    if 1 not in fp or 30 not in fp:
        return pd.Series(dtype=float)
    s = ((fp[30] - fp[1]).dt.days / 365.25).dropna()
    return s[s > 0]


def scores_by_branch(df: pd.DataFrame, sample: int = 60000) -> pd.DataFrame:
    p = df.loc[df["is_pass"] & df["score"].notna(), ["exam_branch", "score"]]
    if len(p) > sample:                         # box plots do not need every row
        p = p.sample(sample, random_state=0)
    return p


def score_summary(df: pd.DataFrame) -> pd.DataFrame:
    p = df[df["is_pass"] & df["score"].notna()]
    return (p.groupby("exam_branch")["score"].agg(["count", "mean", "median", "min"])
              .reindex(BRANCHES))


# --------------------------------------------------------------------------- #
# Teachers, mosques, sectors
# --------------------------------------------------------------------------- #
def teacher_tables(df: pd.DataFrame, min_passed: int = 50) -> dict:
    passed = df[df["is_pass"] & df["teacher_name"].notna()]
    top_volume = passed["teacher_name"].value_counts().head(10)
    stats = passed.groupby("teacher_name", observed=True).agg(passed=("exam_id", "size"),
                                                              mean_score=("score", "mean"))
    top_score = stats[stats["passed"] >= min_passed].sort_values("mean_score", ascending=False).head(10)

    load = df.dropna(subset=["teacher_name"]).groupby("teacher_name", observed=True).size()
    load = load[load > 0].sort_values(ascending=False)
    out = {"top_volume": top_volume, "top_score": top_score, "n_teachers": len(load)}
    if len(load):
        cum = (load.cumsum() / load.sum() * 100).to_numpy()
        share = np.arange(1, len(load) + 1) / len(load) * 100
        step = max(len(load) // 400, 1)                     # thin the curve for the browser
        out["lorenz"] = pd.DataFrame({"teachers_pct": share[::step], "exams_pct": cum[::step]})
        cut = int(np.ceil(len(load) * 0.10))
        out["top10_share"] = float(cum[cut - 1])
        out["median_load"] = float(load.median())
        out["under20_share"] = float((load < 20).mean() * 100)
    return out


def mosque_table(df: pd.DataFrame, min_exams: int = 500) -> pd.DataFrame:
    att = _attended(df).dropna(subset=["mosque_name"])
    m = att.groupby("mosque_name", observed=True).agg(
        exams=("is_pass", "size"), pass_rate=("is_pass", "mean"), students=("student_id", "nunique"))
    m["pass_rate"] *= 100
    return m[m["exams"] >= min_exams].reset_index()


def sector_table(df: pd.DataFrame) -> pd.DataFrame:
    att = _attended(df)
    att = att[att["sector_name"].notna() & (att["sector_name"].astype(str).str.strip() != "")]
    s = att.groupby("sector_name", observed=True).agg(
        attended=("is_pass", "size"), passed=("is_pass", "sum"),
        pass_rate=("is_pass", "mean"), mean_score=("score", "mean"))
    s["pass_rate"] *= 100
    return s[s["attended"] > 0].sort_values("attended", ascending=False)


# --------------------------------------------------------------------------- #
# Students (ids only, never names)
# --------------------------------------------------------------------------- #
def branches_passed_dist(df: pd.DataFrame) -> dict:
    bp = df[df["is_pass"]].groupby("student_id")["exam_branch"].nunique()
    dist = bp.value_counts().sort_index()
    completed = bp[bp == len(BRANCHES)].index
    flags = df.groupby("student_id")[["is_fail", "is_absent"]].max().any(axis=1)
    return {"dist": dist, "completed": len(completed),
            "perfect": int((~flags.loc[completed]).sum()) if len(completed) else 0,
            "students": int(bp.size)}


def top_excellent(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    exc = df[df["exam_grade"].astype(str) == "ممتاز"]
    if exc.empty:
        return pd.DataFrame()
    top = exc["student_id"].value_counts().head(n)
    sub = df[df["student_id"].isin(top.index) & df["teacher_name"].notna()]
    t = sub.groupby("student_id").agg(
        exams=("exam_id", "size"), teachers=("teacher_name", "nunique"),
        share_with_main_teacher=("teacher_name", lambda s: s.value_counts(normalize=True).iloc[0] * 100))
    t.insert(0, "excellent_exams", top.reindex(t.index))
    return t.sort_values("excellent_exams", ascending=False).round(0).astype(int)


def most_failed(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    t = df.groupby("student_id").agg(failed=("is_fail", "sum"), absent=("is_absent", "sum"),
                                     passed=("is_pass", "sum"), exams=("exam_id", "size"))
    return t.sort_values("failed", ascending=False).head(n)


# --------------------------------------------------------------------------- #
# Cached entry point used by the views
# --------------------------------------------------------------------------- #
@_cache
def run(name: str, f: Filters, **kwargs):
    """Compute ``analytics.<name>`` on the data selected by the sidebar filters (cached)."""
    return globals()[name](get_filtered(f), **kwargs)
