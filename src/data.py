"""Loading, demo data and global filters.

The dashboard reads ``data/processed/exams.parquet`` (built by ``src/prepare_data.py``).
If that file does not exist yet, a clearly-labelled SYNTHETIC demo dataset is generated
so the app can still be explored. Demo numbers are invented: they only mimic the
shape of the real data.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import BRANCHES, MADE_UP_ID_START, PROCESSED_PATH

try:
    import streamlit as st
    _cache = st.cache_data(show_spinner="Loading data...")
except Exception:                                   # allows testing without streamlit
    def _cache(fn):
        return fn

MISSING_SECTOR = "(no sector recorded)"

# per-branch pass rate used by the demo generator (shape taken from the real analysis)
_DEMO_PASS = dict(zip(BRANCHES, [0.945, 0.92, 0.857, 0.765, 0.752, 0.734, 0.723, 0.722, 0.737, 0.75, 0.768]))
_DEMO_SECTORS = ["وسط جدة", "شرق جدة", "شمال جدة", "جنوب جدة", "الناطقين بغير العربية",
                 "المراكز المسائية", "التعليم عن بعد"]


def generate_demo(n_students: int = 9000, seed: int = 7) -> pd.DataFrame:
    """Small synthetic dataset with the same columns as the real processed file."""
    rng = np.random.default_rng(seed)
    n_teachers, n_mosques = 260, 70
    teacher_w = rng.pareto(1.4, n_teachers) + 0.2
    teacher_w /= teacher_w.sum()
    mosque_w = rng.pareto(1.2, n_mosques) + 0.2
    mosque_w /= mosque_w.sum()
    mosque_sector = rng.choice(_DEMO_SECTORS, n_mosques, p=[.28, .2, .17, .15, .08, .07, .05])
    mosque_skill = rng.normal(0, 0.05, n_mosques)

    # exam months: two waves per year (Jan/Feb and May/Jun), drifting earlier over time
    def draw_date(year: int) -> pd.Timestamp:
        shift = int(np.clip((year - 2012) * 0.6, 0, 6))
        wave = rng.random() < 0.5
        base = (2 if wave else 6) - (shift // 3 if not wave else 0)
        month = int(np.clip(round(rng.normal(base, 1.0)), 1, 12))
        if rng.random() < 0.18:
            month = int(rng.integers(1, 13))
        day = int(rng.integers(1, 28))
        d = pd.Timestamp(year=year, month=month, day=day)
        # weekend moved from Thu/Fri to Fri/Sat in 2013: skip the weekend days
        banned = {3, 4} if year < 2013 else {4, 5}
        while d.dayofweek in banned:
            d += pd.Timedelta(days=1)
        return d

    rows = []
    exam_id = 1
    start_probs = np.array([.34, .1, .16, .1, .06, .06, .05, .04, .03, .03, .03])
    start_probs /= start_probs.sum()
    for sid in range(1, n_students + 1):
        year = int(rng.choice(np.arange(2008, 2026), p=_year_weights()))
        pos = int(rng.choice(len(BRANCHES), p=start_probs))
        teacher = int(rng.choice(n_teachers, p=teacher_w))
        mosque = int(rng.choice(n_mosques, p=mosque_w))
        made_up = rng.random() < 0.08
        student_id = MADE_UP_ID_START + sid if made_up else sid
        has_sector = rng.random() < (0.35 if year < 2015 else 0.85)
        while pos < len(BRANCHES) and year <= 2025:
            b = BRANCHES[pos]
            covid = 2020 <= year <= 2021
            p_pass = _DEMO_PASS[b] - (0.07 if covid else 0) + mosque_skill[mosque]
            p_pass = float(np.clip(p_pass + (0.03 if year >= 2022 else 0), 0.3, 0.99))
            for attempt in range(6):
                date = draw_date(year)
                absent = rng.random() < (0.2 if covid or year >= 2022 else 0.1)
                if rng.random() < 0.12 and attempt == 0:
                    teacher = int(rng.choice(n_teachers, p=teacher_w))
                if absent:
                    outcome, score, grade = "absent", np.nan, "غائب"
                elif rng.random() < p_pass:
                    score = float(np.clip(rng.normal(95 - pos * 0.7, 5), 60, 100))
                    outcome = "passed"
                    grade = ("ممتاز" if score >= 90 else "جيد جداً" if score >= 80
                             else "جيد" if score >= 70 else "مقبول")
                else:
                    outcome, score, grade = "failed", np.nan, "راسب"
                rows.append((exam_id, student_id, made_up, date, b, grade, outcome, score,
                             f"معلم {teacher + 1:03d}", f"مسجد {mosque + 1:02d}",
                             mosque_sector[mosque] if has_sector else None))
                exam_id += 1
                if outcome == "passed":
                    break
                year = min(year + int(rng.random() < 0.3), 2025)
            if outcome != "passed" or rng.random() > 0.78:   # stops here
                break
            pos += 1
            year += int(rng.random() < 0.5)
    df = pd.DataFrame(rows, columns=["exam_id", "student_id", "id_is_made_up", "exam_date", "exam_branch",
                                     "exam_grade", "outcome", "score", "teacher_name", "mosque_name",
                                     "sector_name"])
    df = df[df["exam_date"] <= "2025-11-27"].copy()
    df["exam_year"] = df["exam_date"].dt.year.astype("int16")
    df["exam_month"] = df["exam_date"].dt.month.astype("int8")
    df["weekday"] = df["exam_date"].dt.dayofweek.astype("int8")
    df["exam_branch"] = df["exam_branch"].astype("int8")
    return df.reset_index(drop=True)


def _year_weights() -> np.ndarray:
    years = np.arange(2008, 2026)
    w = np.where(years < 2020, 1.0, np.where(years < 2022, 0.7, 1.25))
    w[-1] = 0.6
    return w / w.sum()


@_cache
def load_data() -> tuple[pd.DataFrame, bool]:
    """Return (dataframe, is_demo)."""
    if PROCESSED_PATH.exists():
        df = pd.read_parquet(PROCESSED_PATH)
        is_demo = False
    else:
        df = generate_demo()
        is_demo = True
    for col in ("outcome", "teacher_name", "mosque_name", "sector_name", "exam_grade"):
        if col in df and df[col].dtype != "category":
            df[col] = df[col].astype("category")
    df["is_pass"] = df["outcome"].eq("passed")
    df["is_fail"] = df["outcome"].eq("failed")
    df["is_absent"] = df["outcome"].eq("absent")
    return df, is_demo


def sector_options(df: pd.DataFrame) -> list[str]:
    s = df["sector_name"].dropna().astype(str)
    s = s[s.str.strip() != ""]
    return s.value_counts().index.tolist()          # most frequent first


@dataclass(frozen=True)
class Filters:
    """The global sidebar filters. Frozen + hashable, so it can be used as a cache key."""
    year_from: int
    year_to: int
    sectors: tuple = ()
    include_missing_sector: bool = True


@_cache
def get_filtered(f: Filters) -> pd.DataFrame:
    df, _ = load_data()
    out = df[df["exam_year"].between(f.year_from, f.year_to)]
    sec = out["sector_name"].astype("object")
    blank = sec.isna() | (sec.astype(str).str.strip() == "")
    keep = sec.isin(f.sectors) | (blank & f.include_missing_sector)
    return out[keep]
