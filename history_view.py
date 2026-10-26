"""The 'Run history' page of the Streamlit app."""
import pandas as pd
import streamlit as st

from checker.storage import delete_run, get_run, issues_for_run, list_runs


def render(session_factory, store):
    st.subheader("Run history")
    st.caption(
        "Every saved analysis, newest first. The uploaded files themselves are not "
        "stored, only a fingerprint, the summary and where each issue is."
    )

    with session_factory() as session:
        runs = list_runs(session)
        if not runs:
            st.info("No saved runs yet. Analyse a file, then choose Save this run to history.")
            return

        table = pd.DataFrame(
            [
                {
                    "id": r.id,
                    "saved_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
                    "file": r.filename,
                    "records": r.records,
                    "extra_copies": r.extra_copies,
                    "missing_cells": r.missing_cells,
                    "validation_failures": r.validation_failures,
                    "duplicates_removed": r.duplicates_removed,
                }
                for r in runs
            ]
        )
        st.dataframe(table, width="stretch", hide_index=True)

        run_id = st.selectbox("Open a run", [r.id for r in runs])
        run = get_run(session, run_id)

        st.markdown(f"#### Run {run.id}: {run.filename}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Records", f"{run.records:,}")
        c2.metric("Extra duplicate rows", run.extra_copies)
        c3.metric("Missing cells", run.missing_cells)
        c4.metric("Validation failures", run.validation_failures)
        st.caption(f"File fingerprint (SHA-256): {run.file_sha256}")

        kind = st.selectbox("Show issues", ["all", "duplicate", "missing", "invalid"])
        issues = issues_for_run(session, run.id, None if kind == "all" else kind)
        if issues:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "row_number": i.row_number,
                            "column": i.column_name,
                            "type": i.issue_type,
                            "detail": i.detail,
                            "value": i.value,
                        }
                        for i in issues
                    ]
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No issues of this kind in this run.")

        d1, d2 = st.columns(2)
        if run.report_key:
            d1.download_button(
                "Download saved report", data=store.get(run.report_key),
                file_name=f"run_{run.id}_report.md", mime="text/markdown",
            )
        if run.cleaned_key:
            d2.download_button(
                "Download saved cleaned CSV", data=store.get(run.cleaned_key),
                file_name=f"run_{run.id}_cleaned.csv", mime="text/csv",
            )

        confirm = st.checkbox("I want to delete this run permanently")
        if st.button("Delete this run", disabled=not confirm):
            for key in (run.cleaned_key, run.report_key):
                if key:
                    store.delete(key)
            delete_run(session, run.id)
            st.rerun()