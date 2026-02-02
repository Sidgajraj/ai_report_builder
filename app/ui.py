import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # ai_report_builder/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import streamlit as st

# Reuse your existing pipeline + agent
from app.main import load_excel  # loads Excel(s) from data/raw -> DuckDB + tables
from app.agent import generate_sql


RAW_DIR = Path("data/raw")
OUTPUTS_DIR = Path("outputs")


def save_uploaded_file_to_raw(uploaded_file) -> Path:
    """
    Save the uploaded Excel file into data/raw so your existing load_excel() can pick it up.
    Returns the saved path.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    saved_path = RAW_DIR / uploaded_file.name
    with open(saved_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return saved_path


def clear_raw_folder():
    """
    Keep UI simple: one file at a time.
    We clear data/raw before saving the new uploaded Excel.
    """
    if RAW_DIR.exists():
        for p in RAW_DIR.glob("*"):
            if p.is_file():
                p.unlink()


def build_schema(con, tables):
    """
    Build schema dict for the agent:
    { "table": [("col","type"), ...], ... }
    """
    schema = {}
    for t in tables:
        desc = con.execute(f'DESCRIBE "{t}"').fetchall()
        schema[t] = [(r[0], r[1]) for r in desc]
    return schema


def main():
    st.set_page_config(page_title="AI Report Builder", layout="wide")

    st.title("AI Report Builder")
    st.caption("Upload Data, ask questions in English, and get SQL + results.")

    # Sidebar: upload + settings
    with st.sidebar:
        uploaded = st.file_uploader("Upload Data", type=["xlsx"])

        st.divider()
        st.header("Mode")
        show_sql = st.checkbox("Show generated SQL", value=True)

    # If no file yet, show instructions and stop
    if uploaded is None:
        st.info("Upload data to begin.")
        st.stop()

    # Step 1: Save uploaded file -> data/raw (single-file mode)
    clear_raw_folder()
    saved_path = save_uploaded_file_to_raw(uploaded)

    st.success(f"Loaded file: {saved_path.name}")

    # Step 2: Load Excel into DuckDB (reusing your existing function)
    try:
        con, tables = load_excel()
    except Exception as e:
        st.error(f"Failed to load Excel into DuckDB: {e}")
        st.stop()

    # Step 3: Show detected tables + schema summary
    schema = build_schema(con, tables)

    with st.expander("Detected tables & columns", expanded=False):
        for t, cols in schema.items():
            st.markdown(f"**{t}**")
            st.write(pd.DataFrame(cols, columns=["column", "type"]))

    # Step 4: Ask question (English)
    st.subheader("Ask a question")
    prompt = st.text_input("", value="")

    run = st.button("Run", type="primary")

    if not run:
        st.stop()

    if not prompt.strip():
        st.warning("Type a question first.")
        st.stop()

    # Step 5: Generate SQL with the agent
    try:
        sql = generate_sql(prompt, schema)
    except Exception as e:
        st.error(f"AI failed to generate SQL: {e}")
        st.stop()

    # Step 6: Run SQL and show result
    try:
        result_df = con.execute(sql).df()
    except Exception as e:
        st.error(f"SQL execution failed: {e}")
        st.stop()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Result")
        st.dataframe(result_df, use_container_width=True)

    with col2:
        if show_sql:
            st.subheader("SQL")
            st.code(sql, language="sql")

        # Save & download CSV (same as your CLI behavior)
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        out_csv = OUTPUTS_DIR / "result.csv"
        result_df.to_csv(out_csv, index=False)

        st.download_button(
            label="Download result.csv",
            data=out_csv.read_bytes(),
            file_name="result.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
