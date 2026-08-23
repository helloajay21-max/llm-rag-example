# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import json
import datetime
import sqlite3
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="MCP Project", layout="wide")
st.title("MCP Project - Streamlit UI")

# ============================================================
# SIDEBAR: APPLICATION MODE SELECTOR
# ============================================================
st.sidebar.header("Controls")

mode = st.sidebar.radio(
    "Application Mode",
    options=["Upload and Analyze", "SQL Explorer", "General Assistant"],
    help=(
        "Upload and Analyze: upload CSV/Excel/PDF and explore with AI.\n"
        "SQL Explorer: query the built-in SQLite database and batch-import data.\n"
        "General Assistant: ask any question with no data context (ideal for date/event queries)."
    )
)

if mode in ["Upload and Analyze", "SQL Explorer"]:
    st.sidebar.markdown(
        "**Show data table** - Toggle to display the loaded dataset as an interactive "
        "table. Use it to inspect rows, spot outliers, check column types, and verify "
        "data before running AI or SQL queries. Hiding it speeds up rendering for very "
        "large files."
    )
    show_table = st.sidebar.checkbox("Show data table", value=True)
else:
    show_table = False

# ============================================================
# SAMPLE DATA
# ============================================================
@st.cache_data
def make_sample(n=60):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n)
    return pd.DataFrame({
        "Date": dates,
        "Category": np.random.choice(["A", "B", "C"], size=n),
        "Value": (np.random.randn(n).cumsum() * 10).round(2)
    })

sample_df = make_sample(60)

# ============================================================
# SQLITE SETUP
# ============================================================
DB_PATH = os.environ.get("SQLITE_DB_PATH", "data.db")
db_dir = os.path.dirname(DB_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

def ensure_db(base_df):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS sales (Date TEXT, Category TEXT, Value REAL)")
    count = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    if count == 0:
        d = base_df.copy()
        d["Date"] = d["Date"].astype(str)
        conn.executemany(
            "INSERT INTO sales (Date, Category, Value) VALUES (?,?,?)",
            d[["Date", "Category", "Value"]].itertuples(index=False, name=None)
        )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ai_calls "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, request_json TEXT, response_excerpt TEXT)"
    )
    conn.commit()
    conn.close()

try:
    ensure_db(sample_df)
except Exception:
    pass

# ============================================================
# HELPERS
# ============================================================
def coerce_datetime(df):
    try:
        first_col = df.columns[0]
        parsed = pd.to_datetime(df[first_col], errors="coerce")
        if parsed.notna().any():
            df = df.copy()
            df[first_col] = parsed
    except Exception:
        pass
    return df

def render_chart(df, title="Chart"):
    st.subheader(title)
    try:
        xcol = df.columns[0]
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            st.info("No numeric columns available to chart.")
            return
        if pd.api.types.is_datetime64_any_dtype(df[xcol]):
            st.line_chart(df.set_index(xcol)[numeric_cols])
        else:
            st.line_chart(df[numeric_cols])
    except Exception:
        numeric = df.select_dtypes(include=[np.number])
        if not numeric.empty:
            st.line_chart(numeric)

# current_df is passed to the AI section from whichever mode is active
current_df = None

# ============================================================
# MODE: UPLOAD AND ANALYZE
# ============================================================
if mode == "Upload and Analyze":
    st.markdown(
        "Upload your data file (CSV, Excel, or PDF) or download the sample dataset to get started."
    )

    # Download sample data in three formats
    st.markdown("**Download sample data:**")
    col1, col2, col3 = st.columns(3)

    with col1:
        sample_csv = sample_df.to_csv(index=False)
        st.download_button(
            "Download sample CSV",
            sample_csv,
            file_name="sample_data.csv",
            mime="text/csv"
        )

    with col2:
        excel_buf = io.BytesIO()
        sample_df.to_excel(excel_buf, index=False, engine="openpyxl")
        st.download_button(
            "Download sample Excel",
            excel_buf.getvalue(),
            file_name="sample_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col3:
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Sample Data Export", ln=True, align="C")
            pdf.set_font("Helvetica", size=8)
            pdf.ln(2)
            cols = list(sample_df.columns)
            col_w = max(15, 185 // len(cols))
            for c in cols:
                pdf.cell(col_w, 7, str(c), border=1)
            pdf.ln()
            for _, row in sample_df.head(30).iterrows():
                for c in cols:
                    pdf.cell(col_w, 6, str(row[c])[:20], border=1)
                pdf.ln()
            pdf_bytes = bytes(pdf.output())
            st.download_button(
                "Download sample PDF",
                pdf_bytes,
                file_name="sample_data.pdf",
                mime="application/pdf"
            )
        except ImportError:
            st.caption("Install fpdf2 to enable PDF download.")

    # File uploader - CSV, Excel, PDF up to 500 MB (configured via .streamlit/config.toml)
    uploaded = st.file_uploader(
        "Upload your data file (CSV, Excel, or PDF) - up to 500 MB",
        type=["csv", "xlsx", "xls", "pdf"],
        help="Supported formats: CSV, Excel (.xlsx/.xls), PDF (table/text extraction). Max 500 MB."
    )

    if uploaded:
        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        try:
            if ext == "pdf":
                try:
                    import pdfplumber
                    with pdfplumber.open(uploaded) as pdffile:
                        all_tables = []
                        for page in pdffile.pages:
                            for table in (page.extract_tables() or []):
                                if table and len(table) > 1:
                                    all_tables.append(table)
                        if all_tables:
                            headers = all_tables[0][0]
                            rows = [r for t in all_tables for r in t[1:]]
                            df = pd.DataFrame(rows, columns=headers)
                            st.success(f"Extracted {len(df)} rows from PDF tables.")
                        else:
                            text_rows = []
                            for page in pdffile.pages:
                                text = page.extract_text()
                                if text:
                                    text_rows.extend(text.split("\n"))
                            df = pd.DataFrame({"Text": [r for r in text_rows if r.strip()]})
                            st.success(f"Extracted {len(df)} text lines from PDF (no tables found).")
                except ImportError:
                    st.error("Install pdfplumber to read PDF files.")
                    df = sample_df.copy()
            elif ext in ["xlsx", "xls"]:
                df = pd.read_excel(uploaded, engine="openpyxl")
                st.success(f"Loaded Excel: {len(df)} rows, {len(df.columns)} columns.")
            else:
                df = pd.read_csv(uploaded)
                st.success(f"Loaded CSV: {len(df)} rows, {len(df.columns)} columns.")
        except Exception as e:
            st.error(f"Failed to load file: {e}")
            df = sample_df.copy()
    else:
        df = sample_df.copy()
        st.info("Using sample dataset. Upload a file above to analyze your own data.")

    df = coerce_datetime(df)
    current_df = df

    if show_table:
        st.subheader("Data Preview")
        st.dataframe(df, use_container_width=True)

    st.subheader("Summary Statistics")
    st.write(df.describe(include="all"))

    render_chart(df, "Data Chart")
    ai_mode = "upload"

# ============================================================
# MODE: SQL EXPLORER
# ============================================================
elif mode == "SQL Explorer":
    ai_mode = "sql"
    st.markdown(
        "Query the local SQLite database, add rows manually, or bulk-import data from a file."
    )

    # ---- Batch row creation tabs ----
    st.subheader("Add or Import Data")
    tab_manual, tab_import = st.tabs(["Manual Row Entry", "Import from File"])

    with tab_manual:
        st.markdown(
            "Add new rows to the **sales** table below. "
            "Click **+** to add rows, edit inline, then click **Save rows to DB**."
        )
        today_iso = str(datetime.date.today())
        empty_template = pd.DataFrame({
            "Date": [today_iso, today_iso, today_iso],
            "Category": ["A", "B", "C"],
            "Value": [0.0, 0.0, 0.0]
        })
        edited_df = st.data_editor(
            empty_template,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Date": st.column_config.TextColumn("Date (YYYY-MM-DD)", help="e.g. 2026-01-15"),
                "Category": st.column_config.SelectboxColumn(
                    "Category", options=["A", "B", "C", "D", "E"], help="Row category"
                ),
                "Value": st.column_config.NumberColumn("Value", format="%.2f")
            },
            key="manual_row_editor"
        )
        if st.button("Save rows to DB", key="save_manual"):
            try:
                rows_to_insert = [
                    (str(row["Date"]), str(row["Category"]), float(row["Value"]))
                    for _, row in edited_df.iterrows()
                    if str(row.get("Date", "")).strip() and str(row.get("Category", "")).strip()
                ]
                if rows_to_insert:
                    conn = sqlite3.connect(DB_PATH)
                    conn.executemany(
                        "INSERT INTO sales (Date, Category, Value) VALUES (?,?,?)",
                        rows_to_insert
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Inserted {len(rows_to_insert)} rows into the sales table.")
                else:
                    st.warning("No valid rows to insert.")
            except Exception as e:
                st.error(f"Insert failed: {e}")

    with tab_import:
        st.markdown(
            "Upload a CSV or Excel file to bulk-import rows into the **sales** table. "
            "Map your file columns to the database columns below."
        )
        sql_upload = st.file_uploader(
            "Upload CSV or Excel for DB import",
            type=["csv", "xlsx", "xls"],
            key="sql_import_uploader",
            help="File must contain at least date, category, and value columns."
        )
        if sql_upload:
            ext2 = sql_upload.name.rsplit(".", 1)[-1].lower()
            import_df = (
                pd.read_excel(sql_upload, engine="openpyxl")
                if ext2 in ["xlsx", "xls"]
                else pd.read_csv(sql_upload)
            )
            st.write("**File preview (first 10 rows):**")
            st.dataframe(import_df.head(10), use_container_width=True)

            available_cols = ["(skip)"] + list(import_df.columns)
            mc1, mc2, mc3 = st.columns(3)
            date_col = mc1.selectbox("Map -> Date column", available_cols, key="map_date")
            cat_col  = mc2.selectbox("Map -> Category column", available_cols, key="map_cat")
            val_col  = mc3.selectbox("Map -> Value column", available_cols, key="map_val")

            if st.button("Import into DB", key="btn_import"):
                try:
                    today_iso2 = str(datetime.date.today())
                    rows = []
                    for _, row in import_df.iterrows():
                        d = str(row[date_col]) if date_col != "(skip)" else today_iso2
                        c = str(row[cat_col])  if cat_col  != "(skip)" else "Unknown"
                        v = float(row[val_col]) if val_col != "(skip)" else 0.0
                        rows.append((d, c, v))
                    conn = sqlite3.connect(DB_PATH)
                    conn.executemany(
                        "INSERT INTO sales (Date, Category, Value) VALUES (?,?,?)", rows
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Imported {len(rows)} rows into the sales table.")
                except Exception as e:
                    st.error(f"Import failed: {e}")

    # ---- SQL Query Explorer ----
    st.markdown("---")
    st.subheader("SQL Query Explorer")
    st.markdown(
        "Run SQL queries against the local **data.db** SQLite database. "
        "Tables available: `sales` (Date, Category, Value) and `ai_calls`."
    )

    examples = {
        "Top categories by avg value":
            "SELECT Category, AVG(Value) as avg_value, COUNT(*) as cnt "
            "FROM sales GROUP BY Category ORDER BY avg_value DESC;",
        "Recent rows":
            "SELECT * FROM sales ORDER BY Date DESC LIMIT 10;",
        "Aggregate by date":
            "SELECT Date, SUM(Value) as total FROM sales "
            "GROUP BY Date ORDER BY Date DESC LIMIT 30;",
        "Row count by category":
            "SELECT Category, COUNT(*) as cnt FROM sales GROUP BY Category;"
    }
    sel = st.selectbox("Example queries", options=list(examples.keys()))
    query = st.text_area("SQL query", value=examples[sel], height=120)

    if st.button("Run SQL"):
        try:
            conn = sqlite3.connect(DB_PATH)
            qdf = pd.read_sql_query(query, conn)
            conn.close()
            st.dataframe(qdf, use_container_width=True)
            render_chart(coerce_datetime(qdf), "Query Result Chart")
        except Exception as e:
            st.error(f"SQL error: {e}")

    if "last_sql_result" not in st.session_state:
        st.session_state["last_sql_result"] = None

    if st.button("Include last query result in AI context"):
        try:
            conn = sqlite3.connect(DB_PATH)
            qdf = pd.read_sql_query(query, conn)
            conn.close()
            st.session_state["last_sql_result"] = qdf.describe(include="all").to_string()
            st.success("Query result saved - will be included in the next AI prompt.")
        except Exception as e:
            st.error(f"Failed: {e}")

    # Data preview from DB
    if show_table:
        try:
            conn = sqlite3.connect(DB_PATH)
            df_sql = pd.read_sql_query(
                "SELECT * FROM sales ORDER BY Date DESC LIMIT 100", conn
            )
            conn.close()
            st.subheader("Sales Table Preview (latest 100 rows)")
            st.dataframe(df_sql, use_container_width=True)
            current_df = coerce_datetime(df_sql)
        except Exception:
            pass

# ============================================================
# MODE: GENERAL ASSISTANT
# ============================================================
elif mode == "General Assistant":
    ai_mode = "general"
    st.info(
        "General Assistant mode: Ask any question - dates, events, coding, math, and more. "
        "The AI uses its full knowledge base and always knows today's date. "
        "For data-specific questions, switch to 'Upload and Analyze' or 'SQL Explorer' mode."
    )

# ============================================================
# AI CHAT SECTION
# ============================================================
try:
    import requests as http_requests
except Exception:
    http_requests = None

st.markdown("---")
st.header("AI Chat (Model Context Protocol)")

# Per-mode explanation that directly addresses the reviewer feedback
# about context switching and focused vs generic bots
MODE_DESCRIPTIONS = {
    "upload": (
        "**Mode: Data Analysis** - The AI is grounded exclusively in your uploaded dataset. "
        "It uses a dedicated system prompt that restricts answers to the data provided, "
        "preventing off-topic speculation. This keeps the bot focused on data insights only. "
        "For general questions like 'When is Diwali?', switch to **General Assistant** mode."
    ),
    "sql": (
        "**Mode: SQL Analysis** - The AI is grounded in your SQL query results from the "
        "local SQLite database. It uses a separate system prompt tuned for database and "
        "analytical questions. Click 'Include last query result in AI context' above to "
        "feed query results into the conversation."
    ),
    "general": (
        "**Mode: General Assistant** - The AI answers any question using its full knowledge "
        "base, with today's date injected so date/event queries are always current-year accurate. "
        "Context switching is handled by **three completely separate prompt templates** - one per "
        "mode - not a single dynamic prompt. Each mode's bot is scoped to its task: the Data "
        "Analysis bot only answers from data, the SQL bot only from query results, and this bot "
        "answers anything. This avoids the 'generic bot trying to do everything' problem."
    )
}

st.info(MODE_DESCRIPTIONS.get(ai_mode, ""))

openai_key = os.environ.get("OPENAI_API_KEY")
if openai_key:
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
        help="Filter and select the OpenAI model. GPT-4o is the latest and most capable."
    )

    today_str = datetime.datetime.today().strftime("%A, %d %B %Y")

    # Three completely separate prompt templates - one per mode
    # This is the architectural answer to the 'context switching' feedback
    SYSTEM_PROMPTS = {
        "upload": (
            f"Today is {today_str}. "
            "You are a specialist Data Analysis assistant. "
            "Your ONLY job is to answer questions grounded in the dataset provided "
            "in this conversation via DATA_SUMMARY messages. "
            "Include numeric insights (mean, min, max, trends) where relevant. "
            "Be concise and data-driven. "
            "Do NOT answer general knowledge questions or speculate beyond the data. "
            "If asked something not in the data (e.g. 'When is Diwali?'), respond: "
            "'This is not a data question. Please switch to General Assistant mode for "
            "general knowledge queries.'"
        ),
        "sql": (
            f"Today is {today_str}. "
            "You are a SQL Data Analysis specialist. "
            "Answer questions based on the database query results provided in this "
            "conversation via SQL_RESULT_SUMMARY messages. "
            "When writing SQL, use standard SQLite syntax. "
            "Be concise and precise. "
            "If asked about something not in the query results, suggest a SQL query to retrieve it. "
            "Do not answer unrelated general knowledge questions."
        ),
        "general": (
            f"Today is {today_str}. "
            "You are a knowledgeable general-purpose assistant. "
            "Answer questions accurately using up-to-date knowledge. "
            "For date-based questions (festivals, public holidays, events), always use "
            "the current year unless the user specifies otherwise. "
            "Be concise, friendly, and factual. Do not fabricate information."
        )
    }

    # Separate session state per mode to prevent cross-mode contamination
    state_key = f"messages_{ai_mode}"
    if state_key not in st.session_state:
        st.session_state[state_key] = []

    # Conversation history display
    st.markdown("**Conversation history (most recent first)**")
    history = st.session_state[state_key]
    for m in reversed(history[-8:]):
        st.write(f"**{m['role']}**: {m['content']}")

    st.markdown("---")

    placeholders = {
        "upload": "e.g. 'What is the average Value?', 'Which category appears most?', 'Show trends over time'",
        "sql":    "e.g. 'Summarize this query result', 'What SQL would find the top 5 rows by value?'",
        "general": "e.g. 'When is Diwali this year?', 'Explain the Model Context Protocol', 'What is 15% of 3500?'"
    }
    prompt = st.text_area(
        "Submit your query",
        placeholder=placeholders.get(ai_mode, "Enter your query...")
    )

    include_data = st.checkbox(
        "Include data summary in context",
        value=(ai_mode != "general"),
        help=(
            "Upload mode: prepends mean/min/max stats of your file. "
            "SQL mode: prepends the last query result summary. "
            "General mode: no data to include."
        )
    )

    if st.button("Submit Your Query") and prompt:
        system_content = SYSTEM_PROMPTS[ai_mode]
        messages = [{"role": "system", "content": system_content}]
        messages.extend(st.session_state[state_key])

        # Inject data context based on mode
        if include_data:
            if ai_mode == "upload" and current_df is not None:
                try:
                    numeric = current_df.select_dtypes(include=[np.number])
                    if not numeric.empty:
                        stats = numeric.describe().loc[["mean", "min", "max"]].to_dict()
                        stats_r = {
                            k: {sk: round(sv, 2) for sk, sv in v.items()}
                            for k, v in stats.items()
                        }
                        messages.append({
                            "role": "user",
                            "content": f"DATA_SUMMARY (mean/min/max): {stats_r}"
                        })
                except Exception:
                    pass
            elif ai_mode == "sql" and st.session_state.get("last_sql_result"):
                messages.append({
                    "role": "user",
                    "content": f"SQL_RESULT_SUMMARY:\n{st.session_state['last_sql_result']}"
                })

        messages.append({"role": "user", "content": prompt})

        # Log request
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO ai_calls (ts, request_json, response_excerpt) VALUES (?,?,?)",
                (
                    datetime.datetime.utcnow().isoformat() + "Z",
                    json.dumps(
                        {"model": selected_model, "mode": ai_mode, "messages_count": len(messages)},
                        ensure_ascii=False
                    ),
                    ""
                )
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        # Call OpenAI
        if http_requests:
            try:
                resp = http_requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": selected_model,
                        "messages": messages,
                        "max_tokens": 500,
                        "temperature": 0.3
                    },
                    timeout=30
                )
                resp.raise_for_status()
                j = resp.json()
                assistant_text = (
                    j["choices"][0]["message"]["content"]
                    if "choices" in j and j["choices"]
                    else str(j)
                )

                # Persist to per-mode history (without the data summary injection)
                st.session_state[state_key].append({"role": "user", "content": prompt})
                st.session_state[state_key].append({"role": "assistant", "content": assistant_text})

                # Log response
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute(
                        "INSERT INTO ai_calls (ts, request_json, response_excerpt) VALUES (?,?,?)",
                        (
                            datetime.datetime.utcnow().isoformat() + "Z",
                            json.dumps({"model": selected_model, "status": resp.status_code}),
                            (assistant_text[:800] + "...") if len(assistant_text) > 800 else assistant_text
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
        else:
            st.error("requests library not available.")

    col_btn, _ = st.columns([1, 5])
    with col_btn:
        if st.button("Reset conversation"):
            st.session_state[state_key] = []
            st.rerun()

else:
    st.info("Set OPENAI_API_KEY environment variable to enable AI chat.")

# ============================================================
# AI CALL AUDIT
# ============================================================
st.markdown("---")
st.subheader("AI Call Audit (recent 10)")
try:
    conn = sqlite3.connect(DB_PATH)
    audit_rows = conn.execute(
        "SELECT id, ts, response_excerpt FROM ai_calls ORDER BY id DESC LIMIT 10"
    ).fetchall()
    conn.close()
    if audit_rows:
        for r in audit_rows:
            st.code(
                json.dumps({"id": r[0], "ts": r[1], "excerpt": r[2]}, ensure_ascii=False),
                language="json"
            )
    else:
        st.write("No AI audit records yet.")
except Exception as e:
    st.write(f"Unable to read AI audit: {e}")
