import pandas as pd
import streamlit as st
from pathlib import Path

from checker.validation import load_rules, validate
from checker.duplicates import find_duplicates
from checker.missing import DEFAULT_MARKERS, find_missing

st.set_page_config(page_title="CSV Data Quality Checker", layout="wide")
st.title("CSV Data Quality Checker")
st.caption("Upload a CSV to preview it. Nothing is changed or stored.")

uploaded = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded is None:
    st.info("Upload a CSV file to begin.")
    st.stop()

try:
    # Read everything as text and don't convert anything to NaN,
    # so the checker sees the raw values exactly as they appear in the file.
    df = pd.read_csv(uploaded, dtype=str, keep_default_na=False)
except pd.errors.EmptyDataError:
    st.error("The file is empty or has no header row.")
    st.stop()
except Exception as e:
    st.error(f"Could not read this file as a CSV: {e}")
    st.stop()

if df.empty:
    st.warning("The file has column headers but no data rows.")
    st.stop()

col1, col2 = st.columns(2)
col1.metric("Records", f"{len(df):,}")
col2.metric("Columns", len(df.columns))

st.subheader("Preview (first 20 rows)")
st.dataframe(df.head(20), use_container_width=True)

st.subheader("Columns")
st.write(", ".join(df.columns))

st.subheader("Duplicate rows")
dup = find_duplicates(df)

d1, d2 = st.columns(2)
d1.metric("Extra copies (would be removed)", dup["extra_copies"])
d2.metric("Duplicate groups", dup["groups"])

if dup["extra_copies"] == 0:
    st.success("No exact duplicate rows found.")
else:
    st.caption("Row numbers match the line numbers in your CSV file (header is line 1).")
    st.dataframe(dup["details"], use_container_width=True)

st.subheader("Missing values")
marker_text = st.text_input(
    "Values treated as missing (comma-separated). Blank cells are always included.",
    value=", ".join(DEFAULT_MARKERS),
)
markers = [m.strip() for m in marker_text.split(",") if m.strip()]
missing = find_missing(df, markers)

st.metric("Total missing cells", missing["total_missing"])
st.dataframe(missing["summary"], use_container_width=True)

if missing["total_missing"] == 0:
    st.success("No missing values found.")
else:
    with st.expander("Show every missing cell"):
        st.caption("Row numbers match the line numbers in your CSV file (header is line 1).")
        st.dataframe(missing["details"], use_container_width=True)
st.subheader("Format and validity checks")
rules_file = st.file_uploader(
    "Rules file (JSON), optional", type=["json"], key="rules_upload"
)
default_rules_path = Path(__file__).parent / "rules" / "example_rules.json"

rules = []
try:
    if rules_file is not None:
        rules = load_rules(rules_file.getvalue())
    else:
        rules = load_rules(default_rules_path.read_text(encoding="utf-8"))
        st.caption("Using rules/example_rules.json. Upload your own rules file to override it.")
except (ValueError, OSError) as e:
    st.error(f"Could not load the rules: {e}")

with st.expander("Show active rules"):
    st.json(rules)

validation = validate(df, rules, markers)
for msg in validation["config_errors"]:
    st.warning(msg)

st.metric("Validation failures", validation["total_failures"])
if not validation["summary"].empty:
    st.dataframe(validation["summary"], width="stretch")

if rules and validation["total_failures"] == 0:
    st.success("All checked values passed the rules.")
elif validation["total_failures"] > 0:
    with st.expander("Show every failing cell"):
        st.caption("Row numbers match the line numbers in your CSV file (header is line 1).")
        st.dataframe(validation["details"], width="stretch")