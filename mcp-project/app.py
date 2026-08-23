import streamlit as st
import pandas as pd
import numpy as np
import io
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="MCP Project", layout="wide")
st.title("MCP Project — Streamlit UI")
st.markdown("Professional demo: upload your CSV or download and try the provided sample dataset.")

# Generate sample dataset
@st.cache_data
def make_sample(n=30):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n)
    df = pd.DataFrame({
        "Date": dates,
        "Category": np.random.choice(["A","B","C"], size=n),
        "Value": (np.random.randn(n).cumsum() * 10).round(2)
    })
    return df

sample_df = make_sample(60)
sample_csv = sample_df.to_csv(index=False)

st.download_button("Download sample CSV", sample_csv, file_name="sample_data.csv", mime="text/csv")

uploaded = st.file_uploader("Upload CSV", type=["csv"])
if uploaded:
    df = pd.read_csv(uploaded)
else:
    df = sample_df.copy()

# Try to coerce the first column to datetime if it looks like dates to avoid pyarrow conversion warnings
try:
    first_col = df.columns[0]
    parsed = pd.to_datetime(df[first_col], errors='coerce')
    # If parsing produced at least one non-NaT value, use it
    if parsed.notna().any():
        df[first_col] = parsed
except Exception:
    pass

# --- Lightweight local SQLite DB (data.db) ---
import sqlite3
DB_PATH = os.environ.get('SQLITE_DB_PATH', 'data.db')
db_dir = os.path.dirname(DB_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

def ensure_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        d = df.copy()
        # Ensure Date column is text for SQLite
        d['Date'] = d['Date'].astype(str)
        conn.execute('CREATE TABLE IF NOT EXISTS sales (Date TEXT, Category TEXT, Value REAL)')
        conn.executemany('INSERT INTO sales (Date,Category,Value) VALUES (?,?,?)', d[['Date','Category','Value']].itertuples(index=False, name=None))
        conn.commit()
        conn.close()

# Create DB if missing and ensure ai_calls table
try:
    ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS ai_calls (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, request_json TEXT, response_excerpt TEXT)')
    conn.commit()
    conn.close()
except Exception:
    pass

st.markdown("---")
st.header("Database Explorer (local SQLite)")
st.markdown("The app creates a local SQLite DB at data.db with a 'sales' table. Use the SQL box below to run queries against it.")

# Example queries
examples = {
    'Top categories avg value': "SELECT Category, AVG(Value) as avg_value, COUNT(*) as cnt FROM sales GROUP BY Category ORDER BY avg_value DESC;",
    'Recent rows': "SELECT * FROM sales ORDER BY Date DESC LIMIT 10;",
    'Aggregate by date': "SELECT Date, SUM(Value) as total FROM sales GROUP BY Date ORDER BY Date DESC LIMIT 30;"
}
sel = st.selectbox('Example queries', options=list(examples.keys()))
query = st.text_area('SQL query', value=examples[sel], height=120)
if st.button('Run SQL'):
    try:
        conn = sqlite3.connect(DB_PATH)
        qdf = pd.read_sql_query(query, conn)
        st.write(qdf)
        conn.close()
    except Exception as e:
        st.error(f'SQL error: {e}')

# Option to include last query result in AI context
if 'last_query' not in st.session_state:
    st.session_state['last_query'] = None
if st.button('Include last query result in AI context'):
    try:
        conn = sqlite3.connect(DB_PATH)
        qdf = pd.read_sql_query(query, conn)
        conn.close()
        summary = qdf.describe(include='all').to_string()
        st.session_state['last_query'] = summary
        st.success('Last query result saved to session state and can be included in AI prompts')
    except Exception as e:
        st.error(f'Failed to include query result: {e}')

# When building AI messages elsewhere, you can append st.session_state['last_query'] if present

st.sidebar.header("Controls")
show_table = st.sidebar.checkbox("Show data table", value=True)

st.subheader("Data preview")
if show_table:
    st.dataframe(df)

st.subheader("Summary")
st.write(df.describe(include='all'))

st.subheader("Chart")
try:
    xcol = df.columns[0]
    if pd.api.types.is_datetime64_any_dtype(df[xcol]):
        chart_df = df.set_index(xcol).groupby(pd.Grouper(freq='D')).sum()
        st.line_chart(chart_df["Value"])
    else:
        st.line_chart(df.set_index(xcol)["Value"])
except Exception:
    st.line_chart(df.select_dtypes(include=[np.number]))

st.info("To run locally: python -m streamlit run app.py")

# Optional: OpenAI demo (requires OPENAI_API_KEY environment variable)
import json
import datetime
try:
    import requests
except Exception:
    requests = None

st.markdown("---")
st.header("How MCP uses Generative AI (Model Context Protocol)")
st.markdown(
    """
    This demo shows the Model Context Protocol in practice:
    1) The application builds a `messages` array (roles: system, user, assistant) that represents the conversation context.
    2) A system message encodes MCP policies and the assistant's role (e.g., summarize data, be concise, include numeric insights).
    3) User messages are appended as the user interacts; assistant replies are appended back to the context, preserving history.
    4) The full `messages` array is sent to the Chat Completions API so the model has conversational context when generating responses.
    """
)

openai_key = os.environ.get('OPENAI_API_KEY')
if openai_key:
    st.subheader("Interactive Chat Using Model Context")

    # Initialize session state for messages
    if 'messages' not in st.session_state:
        st.session_state['messages'] = [
            {"role": "system", "content": "You are an assistant that summarizes CSV data and provides clear, concise insights. When asked, include a short numeric summary (mean, min, max) and one sentence recommendation."}
        ]

    # Show conversation history
    st.markdown("**Conversation context (most recent first)**")
    for m in reversed(st.session_state['messages'][-8:]):
        st.write(f"**{m['role']}**: {m['content']}")

    st.markdown("---")
    prompt = st.text_area("Enter your prompt (example: 'Summarize this dataset and give one recommendation')")

    include_data_summary = st.checkbox("Include automatic data summary in context", value=True)

    if st.button("Send to OpenAI") and prompt:
        # Build messages payload from session state and current input
        messages = list(st.session_state['messages'])

        # Optionally include a short auto-generated data summary as a user-level context message
        if include_data_summary:
            try:
                df_preview = df.head(20)
                numeric = df.select_dtypes(include=[np.number])
                summary = ''
                if not numeric.empty:
                    stats = numeric.describe().loc[['mean','min','max']].to_dict()
                    summary = f"Numeric summary (showing mean/min/max for numeric cols): { {k: v for k,v in stats.items()} }"
                else:
                    summary = 'No numeric columns to summarize.'
                messages.append({"role": "user", "content": f"DATA_SUMMARY: {summary}"})
            except Exception:
                # fallback if df not available
                messages.append({"role": "user", "content": "DATA_SUMMARY: unavailable"})

        # Add the user's prompt
        messages.append({"role": "user", "content": prompt})

        # Log the outgoing request (without API key)
        try:
            log_entry = {
                "ts": datetime.datetime.utcnow().isoformat() + 'Z',
                "messages_count": len(messages),
                "preview_messages": messages[-4:]
            }
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute('INSERT INTO ai_calls (ts, request_json, response_excerpt) VALUES (?,?,?)', (
                    datetime.datetime.utcnow().isoformat() + 'Z',
                    json.dumps({"messages_count": len(messages), "preview": messages[-4:]}, ensure_ascii=False),
                    ''
                ))
                conn.commit()
                conn.close()
            except Exception:
                pass
        except Exception:
            pass

        # Call OpenAI
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            body = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.2
            }
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            resp = requests.post(url, headers=headers, json=body, timeout=30)
            resp.raise_for_status()
            j = resp.json()
            assistant_text = j['choices'][0]['message']['content'] if 'choices' in j and j['choices'] else str(j)

            # Append assistant reply to session context
            st.session_state['messages'].append({"role": "assistant", "content": assistant_text})

            # Log compact response
            try:
                resp_summary = {
                    "ts": datetime.datetime.utcnow().isoformat() + 'Z',
                    "status_code": resp.status_code,
                    "response_excerpt": (assistant_text[:800] + '...') if len(assistant_text) > 800 else assistant_text
                }
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute('INSERT INTO ai_calls (ts, request_json, response_excerpt) VALUES (?,?,?)', (
                        datetime.datetime.utcnow().isoformat() + 'Z',
                        json.dumps({"status_code": resp.status_code}, ensure_ascii=False),
                        resp_summary.get('response_excerpt','')
                    ))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
            except Exception:
                pass

            st.markdown("**Assistant**")
            st.write(assistant_text)

        except Exception as e:
            st.error(f"OpenAI call failed: {e}")

    st.markdown("---")
    st.button("Reset conversation", on_click=lambda: st.session_state.clear())

else:
    st.info("Set OPENAI_API_KEY environment variable to enable OpenAI demo.")

# AI call audit: read recent entries from ai_calls table
st.subheader("AI call audit (recent)")
try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, ts, response_excerpt FROM ai_calls ORDER BY id DESC LIMIT 10')
    rows = cur.fetchall()
    conn.close()
    if rows:
        for r in rows:
            st.code(json.dumps({"id": r[0], "ts": r[1], "response_excerpt": r[2]}, ensure_ascii=False), language='json')
    else:
        st.write("No AI audit records yet.")
except Exception as e:
    st.write(f"Unable to read AI audit from DB: {e}")
