AI Report Builder

AI Report Builder lets you upload Excel data, ask questions in plain English, and get SQL-backed reports you can download as CSV.
It converts spreadsheets into a DuckDB database and uses an AI agent to safely generate read-only SQL.


Demo
Video walkthrough:



What it does

Upload an Excel file (.xlsx)
Automatically loads sheets into DuckDB
Ask a question in natural language
AI generates safe, read-only SQL
Runs the query and returns results
Download the result as a CSV


How it works (high level)

Excel → DuckDB → AI generates SQL → Query runs → CSV output
No manual schema setup, no writing SQL unless you want to.


Ways to use it

Option 1: Streamlit app (recommended)
streamlit run app/ui.py
Upload an Excel file
Ask questions
see results + SQL
Download CSV

Option 2: CLI
python app/main.py
Place Excel files in data/raw/
Choose:
English question (AI writes SQL)
Manual SQL


Safety by design

Only SELECT / WITH queries allowed
No INSERT, UPDATE, DELETE, DROP, etc.
No multi-statement SQL
Uses detected schema to avoid hallucinated columns


Project structure

ai_report_builder/
  app/
    agent.py        # English → safe DuckDB SQL
    main.py         # CLI pipeline
    ui.py           # Streamlit UI
  data/raw/         # Excel input
  outputs/          # DuckDB + result.csv
  demo/             # Demo video


Tech stack

Python
DuckDB
Pandas
Streamlit
OpenAI (SQL generation)


Why this project matters

This shows how LLMs can augment analytics workflows - speeding up exploration while keeping SQL execution transparent, reviewable, and safe.
