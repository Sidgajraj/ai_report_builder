import os
from pathlib import Path

import duckdb
import pandas as pd
from rich import print

from dotenv import load_dotenv
from app.agent import generate_sql

RAW_DIR = Path("data/raw")
DB_PATH = Path("outputs/report.duckdb")

def clean_column(col: str) -> str:
    col = str(col).strip().lower()
    col = col.replace(" ", "_").replace("-","_")
    col = "".join(c for c in col if c.isalnum() or c == "_")
    return col or "column"

def load_excel():
    if not RAW_DIR.exists():
        raise FileNotFoundError("data/raw does not exist")
    
    files = list(RAW_DIR.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError("No Excel files found in data/raw")
    
    os.makedirs("outputs", exist_ok=True)
    con = duckdb.connect(str(DB_PATH))

    tables = []

    for file in files:
        print(f"\n[bold]Reading:[/bold] {file.name}")

        xls = pd.ExcelFile(file)
        for sheet in xls.sheet_names:
            df = pd.read_excel(file, sheet_name=sheet)

            # Drop completely empty rows/cols
            df = df.dropna(how="all").dropna(axis=1, how="all")

            # 1) Promote first row to header if it looks like headers
            if df.empty:
                continue

            first_row = df.iloc[0].astype(str).str.strip().str.lower()
            header_keywords = {"date", "callerid", "source", "phone", "duration", "recording"}

            if len(set(first_row.tolist()) & header_keywords) >= 2:
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)

            # 2) Normalize column names
            df.columns = [clean_column(c) for c in df.columns]

            # 3) Drop leftover unnamed columns
            df = df.loc[:, ~df.columns.str.match(r"^unnamed")]

            # 4) Strip whitespace from string cells
            # Strip whitespace only from string/object columns (version-safe)
            obj_cols = df.select_dtypes(include=["object", "string"]).columns
            # Strip whitespace only from string/object columns (preserve NaNs)
            obj_cols = df.select_dtypes(include=["object", "string"]).columns
            for c in obj_cols:
                df[c] = df[c].where(df[c].isna(), df[c].astype(str).str.strip())





            table_name = f"{file.stem}_{sheet}".lower().replace(" ", "_")

            table_name = "".join(c for c in table_name if c.isalnum() or c == "_")

            con.register("df_tmp", df)

            con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df_tmp")

            con.unregister("df_tmp")

            tables.append(table_name)
            print(f"  - Loaded sheet '{sheet}' -> table: {table_name} ({len(df)} rows)")

    return con, tables
        
def main():
    # Load OPENAI_API_KEY from .env into environment variables
    load_dotenv()

    print("[bold green]Starting ai_report_builder...[/bold green]")

    # Load Excel -> DuckDB tables
    con, tables = load_excel()

    # Build schema dict for the AI:
    # { "table": [("col","type"), ...], ... }
    schema = {}
    for t in tables:
        desc = con.execute(f"DESCRIBE {t}").fetchall()
        schema[t] = [(r[0], r[1]) for r in desc]

    print("\n[bold green]Loaded tables:[/bold green]")
    for t in tables:
        print(" -", t)

    print("\nChoose input type:")
    print("1) English prompt (AI writes SQL)")
    print("2) Manual SQL")
    choice = input("> ").strip()

    if choice == "1":
        prompt = input("\nAsk your question in plain English:\n> ").strip()

        # AI generates SQL using schema so it doesn't hallucinate columns
        sql = generate_sql(prompt, schema)

        print("\n[bold cyan]Generated SQL:[/bold cyan]")
        print(sql)
    else:
        print("\nEnter SQL manually (example: SELECT * FROM inbound_phone_calls_sheet1 LIMIT 5)")
        sql = input("SQL > ").strip()

    # Execute query and save results
    try:
        result = con.execute(sql).df()
        print("\n[bold green]Result (top 20):[/bold green]")
        print(result.head(20))

        result.to_csv("outputs/result.csv", index=False)
        print("\nSaved to outputs/result.csv")
    except Exception as e:
        print("[bold red]SQL error:[/bold red]", e)


if __name__ == "__main__":
    main()