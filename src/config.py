"""Constants shared by the data pipeline and the dashboard."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_PATH = ROOT / "data" / "processed" / "exams.parquet"

# ---- domain constants (taken from the EDA notebook) -------------------------
BRANCHES = [1, 2, 3, 5, 8, 10, 13, 15, 20, 25, 30]

PASS_GRADES = ["ممتاز", "جيد جداً", "جيد", "مقبول"]
FAIL_GRADES = ["راسب", "لم يجتز", "مردود"]
ABSENT_GRADE = "غائب"
GRADE_FIXES = {"جيد جدا": "جيد جداً", "جيدجداً": "جيد جداً", "جيدجدا": "جيد جداً", "جيد//": "جيد"}

MADE_UP_ID_START = 9_990_001
MIN_YEAR, MAX_YEAR = 2002, 2025
MIN_EXAMS_PER_GOOD_YEAR = 500

COVID_START = "2020-03-01"
COVID_END = "2021-12-31"

# ---- look & feel -------------------------------------------------------------
C_PASS, C_FAIL, C_ABSENT = "#2a9d8f", "#e76f51", "#e9c46a"
C_PRIMARY, C_DARK, C_ACCENT, C_SOFT = "#1b6b5f", "#264653", "#e07a5f", "#8ab17d"
OUTCOME_COLORS = {"passed": C_PASS, "failed": C_FAIL, "absent": C_ABSENT}
OUTCOME_LABELS = {"passed": "Passed", "failed": "Failed", "absent": "Absent"}
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
