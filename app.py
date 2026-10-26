from pathlib import Path

import pandas as pd
import streamlit as st

import history_view
from checker import artifacts
from checker.duplicates import find_duplicates
from checker.missing import DEFAULT_MARKERS, find_missing
from checker.report import build_report, remove_duplicates, summarise, to_csv_bytes
from checker.storage import (
    attach_artifacts, init_db, list_rule_sets, make_engine, new_session_factory,
    rules_of, save_rule_set, save_run,
)
from checker.validation import load_rules, validate

st.set_page_config(page_title="CSV Data Quality Checker", layout="wide")
st.title("CSV Data Quality Checker")


@st.cache_resource
def get_services():
    """Created once per server: the database session factory and the file store."""
    engine = make_engine()
    init_db(engine)
    return new_session_factory(engine), artifacts.make_store()


SessionFactory, store = get_services()

page = st.sidebar.radio("Page", ["Analyse a file", "Run history"])
if page == "Run history":
    history_view.render(SessionFactory, store)
    st.stop()

st.caption("Upload a CSV to analyse it. Nothing is saved unless you choose to save the run.")

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
st.dataframe(df.head(20), width="stretch")

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
    st.dataframe(dup["details"], width="stretch")

st.subheader("Missing values")
marker_text = st.text_input(
    "Values treated as missing (comma-separated). Blank cells are always included.",
    value=", ".join(DEFAULT_MARKERS),
)
markers = [m.strip() for m in marker_text.split(",") if m.strip()]
missing = find_missing(df, markers)

st.metric("Total missing cells", missing["total_missing"])
st.dataframe(missing["summary"], width="stretch")

if missing["total_missing"] == 0:
    st.success("No missing values found.")
else:
    with st.expander("Show every missing cell"):
        st.caption("Row numbers match the line numbers in your CSV file (header is line 1).")
        st.dataframe(missing["details"], width="stretch")

st.subheader("Format and validity checks")
with SessionFactory() as session:
    saved_rules = {r.id: (f"{r.name} (v{r.version})", rules_of(r)) for r in list_rule_sets(session)}

options = {"Default rules (rules/example_rules.json)": None}
for rule_set_id, (label, _) in saved_rules.items():
    options[label] = rule_set_id
choice = st.selectbox("Rule set", list(options))
selected_rule_set_id = options[choice]

rules_file = st.file_uploader(
    "Or upload a rules file (JSON). It overrides the selection above.",
    type=["json"], key="rules_upload",
)
default_rules_path = Path(__file__).parent / "rules" / "example_rules.json"

rules = []
active_rule_set_id = None
try:
    if rules_file is not None:
        rules = load_rules(rules_file.getvalue())
    elif selected_rule_set_id is not None:
        rules = saved_rules[selected_rule_set_id][1]
        active_rule_set_id = selected_rule_set_id
    else:
        rules = load_rules(default_rules_path.read_text(encoding="utf-8"))
        st.caption("Using rules/example_rules.json.")
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

st.subheader("Data-quality summary")
summary = summarise(df, dup, missing, validation)

s1, s2, s3, s4 = st.columns(4)
s1.metric("Records analysed", f"{summary['records']:,}")
s2.metric("Extra duplicate rows", summary["extra_copies"])
s3.metric("Missing cells", summary["missing_cells"])
s4.metric("Validation failures", summary["validation_failures"])
st.write(f"Rows with at least one issue: **{summary['affected_rows']}**")
st.write(
    "Columns with missing values or validation failures: "
    + (", ".join(summary["affected_columns"]) or "none")
)

st.subheader("Cleaning and export")
st.caption(
    "Only exact duplicate rows can be removed. Missing values and invalid "
    "entries are never filled or edited."
)
remove_dups = st.checkbox(
    "Remove exact duplicate rows (keep the first occurrence)", value=False
)

if remove_dups:
    details = dup["details"]
    to_remove = details[details["is_extra_copy"].astype(bool)]
    if to_remove.empty:
        st.info("There are no exact duplicates to remove.")
    else:
        st.write(f"These {len(to_remove)} row(s) will be removed:")
        st.dataframe(to_remove, width="stretch")

cleaned = remove_duplicates(df) if remove_dups else df
st.write(f"Cleaned file: **{len(cleaned):,}** of {len(df):,} rows kept.")

report_text = build_report(
    uploaded.name, df, dup, missing, validation, markers, rules, remove_dups
)

b1, b2 = st.columns(2)
b1.download_button(
    "Download cleaned CSV",
    data=to_csv_bytes(cleaned),
    file_name=f"cleaned_{uploaded.name}",
    mime="text/csv",
)
b2.download_button(
    "Download data-quality report",
    data=report_text.encode("utf-8"),
    file_name="data_quality_report.md",
    mime="text/markdown",
)

with st.expander("Save the active rules as a named rule set"):
    new_name = st.text_input("Rule set name", key="rule_set_name")
    if st.button("Save rule set"):
        try:
            with SessionFactory() as session:
                saved = save_rule_set(session, new_name, rules)
            st.success(
                f"Saved as {saved.name} v{saved.version}. It appears in the Rule set "
                "list on your next interaction."
            )
        except ValueError as e:
            st.error(str(e))

st.subheader("Save this analysis")
st.caption(
    "Saving keeps the summary and the location of every issue in the database. "
    "The uploaded file is not stored, only its SHA-256 fingerprint. Cell values are "
    "stored only if STORE_VALUES is enabled."
)
keep_files = st.checkbox(
    "Also keep the cleaned CSV and the report in storage (they contain cell values)",
    value=False,
)
if st.button("Save this run to history"):
    with SessionFactory() as session:
        run = save_run(
            session,
            filename=uploaded.name,
            file_bytes=uploaded.getvalue(),
            summary=summary,
            markers=markers,
            rule_set_id=active_rule_set_id,
            duplicates_removed=remove_dups,
            dup=dup,
            missing=missing,
            validation=validation,
        )
        if keep_files:
            cleaned_key = store.put(
                artifacts.run_key(run.id, "cleaned.csv"), to_csv_bytes(cleaned), "text/csv"
            )
            report_key = store.put(
                artifacts.run_key(run.id, "report.md"), report_text.encode("utf-8"), "text/markdown"
            )
            attach_artifacts(session, run.id, cleaned_key, report_key)
    st.success(f"Saved as run {run.id}. Open Run history in the sidebar to find it.")