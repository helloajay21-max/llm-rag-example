import datetime
import json
import os
import sqlite3

import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

try:
    import requests
except Exception:
    requests = None

load_dotenv()

st.set_page_config(page_title="MCP Project", layout="wide")
st.title("MCP Project — Streamlit UI")
st.markdown("Professional demo: upload your CSV or download and try the provided sample dataset.")


@st.cache_data
def make_sample(n=30):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n)
    out = pd.DataFrame(
        {
            "Date": dates,
            "Category": np.random.choice(["A", "B", "C"], size=n),
            "Value": (np.random.randn(n).cumsum() * 10).round(2),
        }
    )
    return out


sample_df = make_sample(60)
sample_csv = sample_df.to_csv(index=False)
st.download_button("Download sample CSV", sample_csv, file_name="sample_data.csv", mime="text/csv")

uploaded = st.file_uploader("Upload CSV", type=["csv"])
if uploaded:
    df = pd.read_csv(uploaded)
else:
    df = sample_df.copy()

try:
    first_col = df.columns[0]
    parsed = pd.to_datetime(df[first_col], errors="coerce")
    if parsed.notna().any():
        df[first_col] = parsed
except Exception:
    pass

DB_PATH = os.environ.get("SQLITE_DB_PATH", "data.db")
db_dir = os.path.dirname(DB_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)


def ensure_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS sales (Date TEXT, Category TEXT, Value REAL)")
    exists = pd.read_sql_query("SELECT COUNT(*) as cnt FROM sales", conn)["cnt"].iloc[0]
    if int(exists) == 0:
        d = df.copy()
        if "Date" in d.columns:
            d["Date"] = d["Date"].astype(str)
        conn.executemany(
            "INSERT INTO sales (Date,Category,Value) VALUES (?,?,?)",
            d[["Date", "Category", "Value"]].itertuples(index=False, name=None),
        )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ai_calls (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, request_json TEXT, response_excerpt TEXT)"
    )
    conn.commit()
    conn.close()


try:
    ensure_db()
except Exception:
    pass

st.markdown("---")
st.header("Database Explorer (local SQLite)")
st.markdown("Run SQL on the local `sales` table created from your CSV/sample data.")

examples = {
    "Top categories avg value": "SELECT Category, AVG(Value) as avg_value, COUNT(*) as cnt FROM sales GROUP BY Category ORDER BY avg_value DESC;",
    "Recent rows": "SELECT * FROM sales ORDER BY Date DESC LIMIT 10;",
    "Aggregate by date": "SELECT Date, SUM(Value) as total FROM sales GROUP BY Date ORDER BY Date DESC LIMIT 30;",
}
sel = st.selectbox("Example queries", options=list(examples.keys()))
query = st.text_area("SQL query", value=examples[sel], height=120)

if st.button("Run SQL"):
    try:
        conn = sqlite3.connect(DB_PATH)
        qdf = pd.read_sql_query(query, conn)
        conn.close()
        st.write(qdf)
    except Exception as e:
        st.error(f"SQL error: {e}")

if "last_query" not in st.session_state:
    st.session_state["last_query"] = None

if st.button("Include last query result in AI context"):
    try:
        conn = sqlite3.connect(DB_PATH)
        qdf = pd.read_sql_query(query, conn)
        conn.close()
        st.session_state["last_query"] = qdf.describe(include="all").to_string()
        st.success("Last query result saved for AI context.")
    except Exception as e:
        st.error(f"Failed to include query result: {e}")

st.sidebar.header("Controls")
show_table = st.sidebar.checkbox("Show data table", value=True)

st.subheader("Data preview")
if show_table:
    st.dataframe(df)

st.subheader("Summary")
st.write(df.describe(include="all"))

st.subheader("Chart")
try:
    xcol = df.columns[0]
    if pd.api.types.is_datetime64_any_dtype(df[xcol]):
        chart_df = df.set_index(xcol).groupby(pd.Grouper(freq="D")).sum(numeric_only=True)
        st.line_chart(chart_df["Value"])
    else:
        st.line_chart(df.set_index(xcol)["Value"])
except Exception:
    st.line_chart(df.select_dtypes(include=[np.number]))

st.info("To run locally: python -m streamlit run app.py")

ASSISTANT_MODES = {
    "General Assistant": (
        "You are a professional AI assistant. Answer clearly and accurately. "
        "If context is missing, state assumptions before answering."
    ),
    "Data Analyst": (
        "You are a senior data analyst. Prioritize quantitative reasoning, metrics, and practical recommendations."
    ),
    "SQL Expert": (
        "You are a SQL expert. Explain query logic, performance considerations, and safer alternatives when needed."
    ),
    "Report Writer": (
        "You are an executive report writer. Produce concise, decision-oriented summaries with clear action items."
    ),
}

st.markdown("---")
st.header("Professional AI Assistant")
st.markdown("Ask anything. Optionally include CSV/SQL context for grounded answers.")

openai_key = os.environ.get("OPENAI_API_KEY")
default_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

if openai_key and requests is not None:
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    mode = st.selectbox("Assistant mode", options=list(ASSISTANT_MODES.keys()), index=0)
    response_style = st.selectbox("Response style", options=["Concise", "Balanced", "Detailed"], index=1)
    model_name = st.text_input("Model", value=default_model)
    prompt = st.text_area(
        "Enter your prompt",
        placeholder="Ask anything: architecture, planning, writing, coding, strategy, analysis...",
    )

    include_data_summary = st.checkbox("Include CSV data summary in context", value=False)
    include_last_sql_summary = st.checkbox("Include saved SQL summary in context", value=False)

    st.markdown("**Conversation (latest 8 turns)**")
    for m in st.session_state["chat_history"][-8:]:
        st.write(f"**{m['role'].capitalize()}**: {m['content']}")

    if st.button("Send to OpenAI") and prompt:
        style_instruction = {
            "Concise": "Keep the response short and direct.",
            "Balanced": "Provide a clear answer with key supporting points.",
            "Detailed": "Provide a detailed response with examples and tradeoffs.",
        }[response_style]

        output_contract = (
            "Return markdown with these sections in order:\n"
            "1) ## Answer\n"
            "2) ## Key Points\n"
            "3) ## Evidence / Data Context Used\n"
            "4) ## Assumptions\n"
            "5) ## Source Notes (use [1], [2] style when references are provided; otherwise write 'No external sources provided.')"
        )

        messages = [
            {"role": "system", "content": ASSISTANT_MODES[mode]},
            {"role": "system", "content": style_instruction},
            {"role": "system", "content": output_contract},
        ]
        messages.extend(st.session_state["chat_history"][-12:])

        if include_data_summary:
            try:
                numeric = df.select_dtypes(include=[np.number])
                if not numeric.empty:
                    stats = numeric.describe().loc[["mean", "min", "max"]].to_dict()
                    messages.append({"role": "system", "content": f"CSV numeric summary: {stats}"})
                else:
                    messages.append({"role": "system", "content": "CSV has no numeric columns."})
            except Exception:
                messages.append({"role": "system", "content": "CSV summary unavailable due to processing issue."})

        if include_last_sql_summary and st.session_state.get("last_query"):
            messages.append({"role": "system", "content": f"SQL summary context: {st.session_state['last_query']}"})

        messages.append({"role": "user", "content": prompt})

        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO ai_calls (ts, request_json, response_excerpt) VALUES (?,?,?)",
                (
                    datetime.datetime.utcnow().isoformat() + "Z",
                    json.dumps(
                        {"mode": mode, "response_style": response_style, "model": model_name, "messages_count": len(messages)},
                        ensure_ascii=False,
                    ),
                    "",
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            body = {"model": model_name, "messages": messages, "max_tokens": 700, "temperature": 0.2}
            resp = requests.post(url, headers=headers, json=body, timeout=45)
            resp.raise_for_status()
            j = resp.json()
            assistant_text = j["choices"][0]["message"]["content"] if j.get("choices") else str(j)

            st.session_state["chat_history"].append({"role": "user", "content": prompt})
            st.session_state["chat_history"].append({"role": "assistant", "content": assistant_text})

            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    "INSERT INTO ai_calls (ts, request_json, response_excerpt) VALUES (?,?,?)",
                    (
                        datetime.datetime.utcnow().isoformat() + "Z",
                        json.dumps({"status_code": resp.status_code, "mode": mode, "model": model_name}, ensure_ascii=False),
                        (assistant_text[:800] + "...") if len(assistant_text) > 800 else assistant_text,
                    ),
                )
                conn.commit()
                conn.close()
            except Exception:
                pass

            st.markdown("**Assistant**")
            st.write(assistant_text)
        except Exception as e:
            st.error(f"OpenAI call failed: {e}")

    if st.button("Reset conversation"):
        st.session_state["chat_history"] = []
        st.success("Conversation reset.")
else:
    if not openai_key:
        st.info("Set OPENAI_API_KEY to enable the AI Assistant.")
    else:
        st.error("`requests` dependency is missing. Install dependencies from requirements.txt.")

st.subheader("AI call audit (recent)")
try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, ts, response_excerpt FROM ai_calls ORDER BY id DESC LIMIT 10")
    rows = cur.fetchall()
    conn.close()
    if rows:
        for r in rows:
            st.code(json.dumps({"id": r[0], "ts": r[1], "response_excerpt": r[2]}, ensure_ascii=False), language="json")
    else:
        st.write("No AI audit records yet.")
except Exception as e:
    st.write(f"Unable to read AI audit from DB: {e}")
