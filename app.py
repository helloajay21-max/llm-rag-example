import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="MCP Project", layout="wide")
st.title("MCP Project â€” Streamlit UI")
st.markdown("Professional demo: upload your data file (CSV / Excel) or download and try the provided sample dataset.")

# Generate sample dataset
@st.cache_data
def make_sample(n=60):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n)
    df = pd.DataFrame({
        "Date": dates,
        "Category": np.random.choice(["A","B","C"], size=n),
        "Value": (np.random.randn(n).cumsum() * 10).round(2)
    })
    return df

sample_df = make_sample(60)

# --- Download sample data in multiple formats ---
st.markdown("**Download sample data:**")
dl_col1, dl_col2, dl_col3 = st.columns(3)

with dl_col1:
    sample_csv = sample_df.to_csv(index=False)
    st.download_button("â¬‡ Download sample CSV", sample_csv, file_name="sample_data.csv", mime="text/csv")

with dl_col2:
    excel_buffer = io.BytesIO()
    sample_df.to_excel(excel_buffer, index=False, engine='openpyxl')
    st.download_button(
        "â¬‡ Download sample Excel",
        excel_buffer.getvalue(),
        file_name="sample_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with dl_col3:
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Sample Data Export", ln=True, align="C")
        pdf.set_font("Helvetica", size=8)
        pdf.ln(2)
        cols = list(sample_df.columns)
        col_w = max(15, 190 // len(cols))
        for c in cols:
            pdf.cell(col_w, 7, str(c), border=1)
        pdf.ln()
        for _, row in sample_df.head(30).iterrows():
            for c in cols:
                pdf.cell(col_w, 6, str(row[c])[:18], border=1)
            pdf.ln()
        pdf_bytes = bytes(pdf.output())
        st.download_button("â¬‡ Download sample PDF", pdf_bytes, file_name="sample_data.pdf", mime="application/pdf")
    except ImportError:
        st.info("Install fpdf2 to enable PDF download.")

# --- Upload: support CSV and Excel ---
uploaded = st.file_uploader(
    "Upload your data file",
    type=["csv", "xlsx", "xls"],
    help="Supports CSV and Excel (.xlsx / .xls) â€” max 200 MB per file"
)
if uploaded:
    ext = uploaded.name.rsplit('.', 1)[-1].lower()
    if ext in ['xlsx', 'xls']:
        df = pd.read_excel(uploaded, engine='openpyxl')
    else:
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
st.sidebar.markdown(
    "**Show data table** â€” toggle to display the loaded dataset as an interactive table. "
    "Use it to inspect rows, spot outliers, check column types, and verify data before running AI or SQL queries. "
    "Hiding it speeds up rendering for very large files."
)
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
    1. The application builds a `messages` array (roles: system, user, assistant) representing the conversation context.
    2. A **system message** encodes MCP policies — two separate prompt templates keep responses focused:
       - **Data Analysis mode** grounds replies strictly in the uploaded dataset (stats, trends, outliers).
       - **General Assistant mode** answers open-ended questions using the model's full knowledge.
    3. User messages are appended as the user interacts; assistant replies are stored back in the context.
    4. The full `messages` array is sent to the Chat Completions API so the model has full conversational context.
    5. **Today's date is injected** into every system prompt so date-based queries (e.g. "When is Diwali this year?") stay current.
    """
)

openai_key = os.environ.get('OPENAI_API_KEY')
if openai_key:
    st.subheader("Interactive Chat Using Model Context")

    # --- Model selector (dropdown filter — not a freeform text field) ---
    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ]
    selected_model = st.selectbox(
        "Select AI Model",
        options=AVAILABLE_MODELS,
        index=0,
        help="Filter and select the OpenAI model to use. GPT-4o is the latest and most capable."
    )

    # --- Query mode toggle: separate prompt templates keep the bot focused ---
    query_mode = st.radio(
        "Query mode",
        options=["📊 Data Analysis (CSV/Excel grounded)", "💬 General Assistant"],
        index=0,
        horizontal=True,
        help=(
            "Data Analysis mode grounds the AI strictly in your uploaded dataset — it won't speculate beyond the data. "
            "General Assistant mode answers any question using the model's full, up-to-date knowledge."
        )
    )

    today_str = datetime.datetime.today().strftime("%A, %d %B %Y")

    DATA_SYSTEM_PROMPT = (
        f"Today is {today_str}. "
        "You are a specialist Data Analysis assistant. Your ONLY job is to answer questions grounded in the dataset "
        "provided in this conversation. Include numeric insights (mean, min, max, trends) where relevant. "
        "Be concise and data-driven. Do NOT speculate beyond what the data shows. "
        "If the data does not contain enough information to answer, say so clearly rather than guessing."
    )

    GENERAL_SYSTEM_PROMPT = (
        f"Today is {today_str}. "
        "You are a knowledgeable general-purpose assistant. Answer questions accurately using up-to-date knowledge. "
        "For date-based questions (festivals, public holidays, events), always use the current year unless the user "
        "specifies otherwise. Be concise, friendly, and factual. Do not fabricate information."
    )

    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []
    if 'active_mode' not in st.session_state:
        st.session_state['active_mode'] = query_mode

    # Reset context when mode changes to avoid cross-mode contamination
    if st.session_state['active_mode'] != query_mode:
        st.session_state['messages'] = []
        st.session_state['active_mode'] = query_mode
        st.info("Query mode changed — conversation context reset to keep responses focused.")

    # Show conversation history (hide system messages from display)
    st.markdown("**Conversation context (most recent first)**")
    display_msgs = [m for m in st.session_state['messages'] if m['role'] != 'system']
    for m in reversed(display_msgs[-8:]):
        st.write(f"**{m['role']}**: {m['content']}")

    st.markdown("---")
    prompt = st.text_area(
        "Submit your query",
        placeholder="e.g. 'Summarize this dataset and highlight trends', 'When is Diwali this year?', 'What is the highest Value?'"
    )

    include_data_summary = st.checkbox(
        "Include automatic data summary in context",
        value=("Data Analysis" in query_mode),
        help="Prepends a statistical summary (mean, min, max) of the loaded dataset to the prompt. Most useful in Data Analysis mode."
    )

    if st.button("🚀 Submit Your Query") and prompt:
        # Build messages: fresh system prompt + prior history + new user message
        system_content = DATA_SYSTEM_PROMPT if "Data Analysis" in query_mode else GENERAL_SYSTEM_PROMPT
        messages = [{"role": "system", "content": system_content}]
        messages.extend([m for m in st.session_state['messages'] if m['role'] != 'system'])

        if include_data_summary:
            try:
                numeric = df.select_dtypes(include=[np.number])
                if not numeric.empty:
                    stats = numeric.describe().loc[['mean', 'min', 'max']].to_dict()
                    stats_rounded = {k: {sk: round(sv, 2) for sk, sv in v.items()} for k, v in stats.items()}
                    summary = f"DATA_SUMMARY (mean/min/max): {stats_rounded}"
                else:
                    summary = 'DATA_SUMMARY: No numeric columns found.'
                messages.append({"role": "user", "content": summary})
            except Exception:
                messages.append({"role": "user", "content": "DATA_SUMMARY: unavailable"})

        messages.append({"role": "user", "content": prompt})

        # Log outgoing request
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                'INSERT INTO ai_calls (ts, request_json, response_excerpt) VALUES (?,?,?)',
                (
                    datetime.datetime.utcnow().isoformat() + 'Z',
                    json.dumps({"model": selected_model, "mode": query_mode, "messages_count": len(messages)}, ensure_ascii=False),
                    ''
                )
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        # Call OpenAI
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            body = {
                "model": selected_model,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.3
            }
            resp = requests.post(url, headers=headers, json=body, timeout=30)
            resp.raise_for_status()
            j = resp.json()
            assistant_text = j['choices'][0]['message']['content'] if 'choices' in j and j['choices'] else str(j)

            # Persist only user prompt + assistant reply to history (not the data summary)
            st.session_state['messages'].append({"role": "user", "content": prompt})
            st.session_state['messages'].append({"role": "assistant", "content": assistant_text})

            # Log response
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    'INSERT INTO ai_calls (ts, request_json, response_excerpt) VALUES (?,?,?)',
                    (
                        datetime.datetime.utcnow().isoformat() + 'Z',
                        json.dumps({"model": selected_model, "status_code": resp.status_code}, ensure_ascii=False),
                        (assistant_text[:800] + '...') if len(assistant_text) > 800 else assistant_text
                    )
                )
                conn.commit()
                conn.close()
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
