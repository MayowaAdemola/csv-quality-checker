import pandas as pd
import streamlit as st

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