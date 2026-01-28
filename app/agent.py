import os
import re
from typing import Dict, List, Tuple

from openai import OpenAI

BANNED = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke"
]

def _is_safe_sql(sql: str) -> None:

    s = sql.strip().lower()

    if not (s.startswith("select") or s.startswith("with")):
        raise ValueError("Only SELECT/WITH queries are allowed.")
    
    if ";" in s.rstrip(";"):
        raise ValueError("Multiple statements are not allowed.")
    
    for kw in BANNED:
        if re.search(rf"\b{kw}\b", s):
            raise ValueError(f"Disallowed SQL keyword detected: {kw}")
        
def _schema_to_text(schema: Dict[str, List[Tuple[str, str]]]) -> str:
    lines = []

    for table, cols in schema.items():
        lines.append(f"Table: {table}")
        for col, col_type in cols:
            lines.append(f"  - {col} ({col_type})")

    return "\n".join(lines)

def generate_sql(user_prompt: str, schema: Dict[str, List[Tuple[str, str]]]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env file."
        )
    
    client = OpenAI(api_key=api_key)

    system_message = (
        "You are a senior data scientist. " 
        "Your job is to write DuckDB SQL queries.\n"
        "Rules: \n"
        "- Output Only raw SQL (no explanations)\n"
        "- Only SELECT or WITH queries\n"
        "- No semicolons\n"
        "- No DDL or DML (no CREATE, DROP, DELETE, etc.)\n"
        "- Use ONLY the tables and columns provided\n"
        "- Add LIMIT 200 unless the user explicitly asks for more\n"
        "- If you compute aggregates (COUNT/SUM/AVG), include ORDER BY the main metric DESC"
    )

    user_message = f"""
user request:
{user_prompt}

Database schema:
{_schema_to_text(schema)}
"""
    
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
    )

    sql = response.choices[0].message.content.strip()

    _is_safe_sql(sql)

    return sql