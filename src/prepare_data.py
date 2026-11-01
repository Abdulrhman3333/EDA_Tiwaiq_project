"""Build the dashboard dataset from the two raw exports of the old system.

Usage (from the project root):

    python -m src.prepare_data

Put ``old_system_old.xls`` and ``old_system_new.xls`` in ``data/raw/`` first.
The output is ``data/processed/exams.parquet``.

This is the cleaning pipeline of the EDA notebook, step by step:
  1. the .xls files are really HTML tables -> stream them into CSV
  2. map both exports onto one set of column names and combine them
  3. convert Hijri dates to Gregorian
  4. unify grades, derive the outcome (passed / failed / absent)
  5. keep valid exam branches, rebuild missing student ids, drop repeated passes

Student names are NOT written to the output: the students are mostly children,
and the dashboard only needs the ids.
"""
from __future__ import annotations

import codecs
import csv
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import pandas as pd

from .config import (
    ABSENT_GRADE, BRANCHES, FAIL_GRADES, GRADE_FIXES, MADE_UP_ID_START,
    MAX_YEAR, MIN_YEAR, PASS_GRADES, PROCESSED_PATH, RAW_DIR,
)

OLD_COLS = {
    "ot_id": "exam_id", "ot_stid": "student_id", "ot_stname": "student_name",
    "ot_date": "exam_date_hijri", "ot_branch": "exam_branch", "ot_degree": "exam_degree",
    "ot_takdeer": "exam_grade", "ot_teacherid": "teacher_id", "ot_teachername": "teacher_name",
    "ot_msq": "mosque_name", "ot_sv": "supervisor_name", "ot_ring": "halaqa_name",
    "ot_section": "sector_name", "secmanger": "sector_manager", "ot_comment": "exam_comment",
}
NEW_COLS = {
    "ne_id": "exam_id", "st_id": "student_id", "st_name": "student_name",
    "examdate": "exam_date_hijri", "ne_branchno": "exam_branch", "ne_degree": "exam_degree",
    "nr_desc": "exam_grade", "tf_id": "teacher_id", "teacher": "teacher_name",
    "msq_name": "mosque_name", "supervisor": "supervisor_name", "rg_name": "halaqa_name",
    "sec_name": "sector_name", "secmanger": "sector_manager", "ne_comment": "exam_comment",
}
FINAL_COLS = list(OLD_COLS.values()) + ["data_source"]

# columns kept in the dashboard dataset (no student names, no free-text comments)
OUTPUT_COLS = [
    "exam_id", "student_id", "id_is_made_up", "exam_date", "exam_year", "exam_month",
    "weekday", "exam_branch", "exam_grade", "outcome", "score",
    "teacher_name", "mosque_name", "sector_name",
]


# --------------------------------------------------------------------------- #
# 1. HTML-table .xls  ->  CSV
# --------------------------------------------------------------------------- #
class TableToCSV(HTMLParser):
    """Writes every <tr> of an html table as one csv row."""

    def __init__(self, out_path: str | Path):
        super().__init__()
        self.f = open(out_path, "w", encoding="utf-8-sig", newline="")
        self.writer = csv.writer(self.f)
        self.row, self.cell, self.in_cell = [], [], False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.in_cell, self.cell = True, []

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.in_cell = False
            self.row.append("".join(self.cell).strip())
        elif tag == "tr" and self.row:
            self.writer.writerow(self.row)

    def handle_data(self, data):
        if self.in_cell:
            self.cell.append(data)

    def close(self):
        super().close()
        self.f.close()


def guess_encoding(path: str | Path) -> str:
    """UTF-8 if the whole file decodes, otherwise windows-1256 (checked once up front,
    so an Arabic character is never cut in half at a chunk boundary)."""
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(1 << 20):
                decoder.decode(chunk)
        decoder.decode(b"", final=True)
        return "utf-8"
    except UnicodeDecodeError:
        return "windows-1256"


def html_xls_to_csv(src: Path) -> Path:
    dst = src.with_name(src.stem + "_clean.csv")
    parser = TableToCSV(dst)
    try:
        with open(src, encoding=guess_encoding(src), errors="replace") as f:
            while chunk := f.read(1 << 16):
                parser.feed(chunk)
    finally:
        parser.close()
    return dst


# --------------------------------------------------------------------------- #
# 2-3. Combine + dates
# --------------------------------------------------------------------------- #
def load_and_combine(raw_dir: Path) -> pd.DataFrame:
    frames = []
    for name, cols in (("old_system_old", OLD_COLS), ("old_system_new", NEW_COLS)):
        src = raw_dir / f"{name}.xls"
        csv_path = raw_dir / f"{name}_clean.csv"
        if not csv_path.exists():
            if not src.exists():
                raise FileNotFoundError(f"Missing {src}")
            print(f"converting {src.name} -> {csv_path.name} ...")
            html_xls_to_csv(src)
        df = pd.read_csv(csv_path, on_bad_lines="skip", low_memory=False)
        print(f"{name}: {df.shape}")
        if name == "old_system_new":
            # second export writes DD-MM-YYYY, the first one YYYY/MM/DD
            df["examdate"] = (df["examdate"].astype(str)
                              .str.replace(r"^(\d{2})[-/](\d{2})[-/](\d{4})$", r"\3/\2/\1", regex=True))
        df["data_source"] = name
        frames.append(df.rename(columns=cols).reindex(columns=FINAL_COLS))
    return pd.concat(frames, ignore_index=True)


def add_gregorian_date(master: pd.DataFrame) -> pd.DataFrame:
    from hijridate import Hijri  # imported here: only the pipeline needs it

    def convert(text):
        try:
            y, m, d = (int(p) for p in text.split("/"))
            return pd.Timestamp(Hijri(y, m, d).to_gregorian())
        except Exception:
            return pd.NaT

    distinct = master["exam_date_hijri"].dropna().unique()
    date_map = {d: convert(d) for d in distinct}          # a few thousand conversions only
    master["exam_date"] = pd.to_datetime(master["exam_date_hijri"].map(date_map))
    print(f"distinct hijri dates: {len(distinct):,} | rows without a usable date: {master['exam_date'].isna().sum():,}")
    return master


# --------------------------------------------------------------------------- #
# 4-5. Cleaning
# --------------------------------------------------------------------------- #
def clean(master: pd.DataFrame) -> pd.DataFrame:
    for col in ["student_id", "exam_branch", "exam_degree", "teacher_id"]:
        master[col] = pd.to_numeric(master[col], errors="coerce")

    # the exports overlap: same exam_id in both files -> keep the first copy
    before = len(master)
    master = master.drop_duplicates(subset="exam_id").reset_index(drop=True)
    print(f"{before:,} -> {len(master):,} rows after removing repeated exam_id")

    # grades + outcome
    master["exam_grade"] = master["exam_grade"].astype("string").str.strip().replace(GRADE_FIXES).astype(object)
    g = master["exam_grade"]
    master["outcome"] = np.select(
        [g.isin(PASS_GRADES), g.isin(FAIL_GRADES), g.eq(ABSENT_GRADE)],
        ["passed", "failed", "absent"], default="unknown")

    master.loc[master["exam_degree"] > 100, "exam_degree"] = 100.0           # entry mistakes
    odd_pass = (master["outcome"] == "passed") & (master["exam_degree"] < 50)  # contradicting rows
    master.loc[odd_pass, "outcome"] = "unknown"
    master = master[master["outcome"] != "unknown"].copy()
    master["score"] = master["exam_degree"].where(master["outcome"].eq("passed"))  # real marks only

    # branches
    master = master[master["exam_branch"].isin(BRANCHES)].copy()
    master["exam_branch"] = master["exam_branch"].astype(int)

    # student ids
    master.loc[master["student_id"] == 0, "student_id"] = np.nan
    master = master.dropna(subset=["student_id", "student_name"], how="all").copy()
    known = master.dropna(subset=["student_id", "student_name"]).drop_duplicates("student_name")
    name_to_id = known.set_index("student_name")["student_id"]
    no_id = master["student_id"].isna()
    master.loc[no_id, "student_id"] = master.loc[no_id, "student_name"].map(name_to_id)
    still = master["student_id"].isna()
    new_names = master.loc[still, "student_name"].unique()
    made_up = {n: MADE_UP_ID_START + i for i, n in enumerate(new_names)}
    master.loc[still, "student_id"] = master.loc[still, "student_name"].map(made_up)
    master["student_id"] = master["student_id"].astype("int64")
    master["id_is_made_up"] = master["student_id"] >= MADE_UP_ID_START

    # a student passes a branch once: keep the first passed record (by date)
    passes = master[master["outcome"].eq("passed")].sort_values("exam_date", na_position="last")
    repeat = passes.duplicated(["student_id", "exam_branch"], keep="first") & ~passes["id_is_made_up"]
    master = master.drop(index=passes.index[repeat.values]).reset_index(drop=True)
    print(f"extra passed rows removed: {repeat.sum():,} | rows left: {len(master):,}")

    # dates used by the dashboard
    master["exam_year"] = master["exam_date"].dt.year
    master = master[master["exam_year"].between(MIN_YEAR, MAX_YEAR)].copy()   # typos in hijri year
    master["exam_year"] = master["exam_year"].astype("int16")
    master["exam_month"] = master["exam_date"].dt.month.astype("int8")
    master["weekday"] = master["exam_date"].dt.dayofweek.astype("int8")
    return master


def to_output(master: pd.DataFrame) -> pd.DataFrame:
    out = master[OUTPUT_COLS].copy()
    out["exam_branch"] = out["exam_branch"].astype("int8")
    out["score"] = out["score"].astype("float32")
    for col in ["outcome", "exam_grade", "teacher_name", "mosque_name", "sector_name"]:
        out[col] = out[col].astype("category")
    return out.reset_index(drop=True)


def main() -> None:
    master = load_and_combine(RAW_DIR)
    master = add_gregorian_date(master)
    master = clean(master)
    out = to_output(master)
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROCESSED_PATH, index=False)
    print(f"\nsaved {len(out):,} exams -> {PROCESSED_PATH}")


if __name__ == "__main__":
    main()
