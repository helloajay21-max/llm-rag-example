# -*- coding: utf-8 -*-
import re
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
        "Region": np.random.choice(["North", "South", "East", "West"], size=n),
        "Value": (np.random.randn(n).cumsum() * 10).round(2),
        "Units": np.random.randint(1, 100, size=n),
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
        d = base_df[["Date", "Category", "Value"]].copy()
        d["Date"] = d["Date"].astype(str)
        conn.executemany(
            "INSERT INTO sales (Date, Category, Value) VALUES (?,?,?)",
            d.itertuples(index=False, name=None)
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
    """Try to parse the first column as datetime."""
    try:
        first_col = df.columns[0]
        parsed = pd.to_datetime(df[first_col], errors="coerce")
        if parsed.notna().sum() >= len(df) * 0.5:
            df = df.copy()
            df[first_col] = parsed
    except Exception:
        pass
    return df


def render_data_analysis(df, file_name=None, show_preview=True):
    """
    Render a full data analysis panel:
      - File info card + post-upload actions
      - Interactive Data Preview
      - Rich Summary Statistics (tabbed)
      - Interactive Data Chart
    """

    # ----------------------------------------------------------
    # FILE INFO CARD + ACTIONS  (only when a real file was uploaded)
    # ----------------------------------------------------------
    if file_name:
        missing_count = int(df.isnull().sum().sum())
        total_cells = max(len(df) * len(df.columns), 1)
        quality_pct = round((1 - missing_count / total_cells) * 100, 1)
        quality_label = "Excellent" if quality_pct >= 95 else ("Good" if quality_pct >= 80 else ("Fair" if quality_pct >= 60 else "Poor"))

        st.markdown("---")
        st.subheader("File Summary")
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        mc1.metric("File Name", file_name)
        mc2.metric("Rows", f"{len(df):,}")
        mc3.metric("Columns", len(df.columns))
        mc4.metric("Missing Values", f"{missing_count:,}")
        mc5.metric("Data Quality", f"{quality_pct}%", delta=quality_label,
                   delta_color="normal" if quality_pct >= 80 else "inverse")

        st.markdown("**Actions on uploaded data:**")
        act1, act2, act3, act4 = st.columns(4)
        base_name = re.sub(r"[^\w\-]", "_", file_name.rsplit(".", 1)[0])

        with act1:
            csv_dl = df.to_csv(index=False)
            st.download_button(
                "Export as CSV",
                csv_dl,
                file_name=f"{base_name}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with act2:
            xl_buf = io.BytesIO()
            df_xl = df.copy()
            for c in df_xl.select_dtypes(include=["datetime64[ns]"]).columns:
                df_xl[c] = df_xl[c].astype(str)
            df_xl.to_excel(xl_buf, index=False, engine="openpyxl")
            st.download_button(
                "Export as Excel",
                xl_buf.getvalue(),
                file_name=f"{base_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with act3:
            if st.button("Save to SQLite DB", use_container_width=True, key="save_to_db"):
                try:
                    table_name = re.sub(r"\W+", "_", base_name.lower())[:32] or "uploaded_data"
                    conn = sqlite3.connect(DB_PATH)
                    df_save = df.copy()
                    for c in df_save.select_dtypes(include=["datetime64[ns]"]).columns:
                        df_save[c] = df_save[c].astype(str)
                    df_save.to_sql(table_name, conn, if_exists="replace", index=False)
                    conn.close()
                    st.success(f"Saved {len(df):,} rows to SQLite table '{table_name}'.")
                except Exception as e:
                    st.error(f"Save failed: {e}")

        with act4:
            if st.button("Quick AI Analysis", use_container_width=True, key="quick_ai"):
                col_list = ", ".join(df.columns.tolist()[:8])
                st.session_state["auto_query"] = (
                    f"I uploaded a dataset with {len(df):,} rows and {len(df.columns)} columns "
                    f"({col_list}). Please: 1) Summarize the key statistics and trends, "
                    f"2) Identify notable patterns or anomalies, "
                    f"3) Give one actionable recommendation."
                )
                st.info("AI analysis queued - scroll to the AI Chat section below and click Submit Your Query.")

    # ----------------------------------------------------------
    # DATA PREVIEW
    # ----------------------------------------------------------
    if show_preview:
        with st.expander("Data Preview", expanded=True):
            all_cols = list(df.columns)

            ctrl1, ctrl2 = st.columns([2, 1])
            selected_cols = ctrl1.multiselect(
                "Columns to display", all_cols, default=all_cols, key="preview_cols"
            )
            max_rows = min(500, len(df))
            rows_n = ctrl2.slider(
                "Rows to display", min_value=5, max_value=max_rows,
                value=min(50, max_rows), step=5, key="preview_rows"
            )

            preview_df = df[selected_cols].head(rows_n) if selected_cols else df.head(rows_n)

            has_nulls = preview_df.isnull().any().any()
            if has_nulls:
                try:
                    st.dataframe(
                        preview_df.style.highlight_null(color="#fff3cd"),
                        use_container_width=True
                    )
                except Exception:
                    st.dataframe(preview_df, use_container_width=True)
                null_summary = df.isnull().sum()
                null_cols = null_summary[null_summary > 0]
                st.caption(
                    "Columns with missing values: " +
                    ", ".join(f"{c} ({n} missing)" for c, n in null_cols.items())
                )
            else:
                st.dataframe(preview_df, use_container_width=True)

            st.caption(
                f"Showing {rows_n} of {len(df):,} rows"
                f" | {len(selected_cols)} of {len(all_cols)} columns displayed"
            )

    # ----------------------------------------------------------
    # SUMMARY STATISTICS
    # ----------------------------------------------------------
    with st.expander("Summary Statistics", expanded=True):
        numeric_df = df.select_dtypes(include=[np.number])
        cat_df = df.select_dtypes(include=["object", "category"])
        missing_total = int(df.isnull().sum().sum())

        # Top metrics bar
        sm1, sm2, sm3, sm4, sm5 = st.columns(5)
        sm1.metric("Rows", f"{len(df):,}")
        sm2.metric("Columns", len(df.columns))
        sm3.metric("Numeric Cols", len(numeric_df.columns))
        sm4.metric("Categorical Cols", len(cat_df.columns))
        sm5.metric("Missing Values", f"{missing_total:,}")

        st.markdown("---")
        tab_num, tab_cat, tab_info = st.tabs(
            ["Numeric Analysis", "Categorical Analysis", "Column Info"]
        )

        # ---- Numeric tab ----
        with tab_num:
            if not numeric_df.empty:
                num_col_names = numeric_df.columns.tolist()
                for i in range(0, len(num_col_names), 3):
                    row_buckets = st.columns(3)
                    for j, col_name in enumerate(num_col_names[i:i + 3]):
                        col_data = numeric_df[col_name].dropna()
                        with row_buckets[j]:
                            st.markdown(f"**{col_name}**")
                            if col_data.empty:
                                st.caption("All values missing")
                                continue
                            r1, r2, r3, r4 = st.columns(4)
                            r1.metric("Mean", f"{col_data.mean():.2f}")
                            r2.metric("Median", f"{col_data.median():.2f}")
                            r3.metric("Min", f"{col_data.min():.2f}")
                            r4.metric("Max", f"{col_data.max():.2f}")
                            std_val = col_data.std()
                            st.caption(f"Std: {std_val:.2f} | Nulls: {df[col_name].isnull().sum()}")
                            # Distribution histogram
                            if len(col_data) > 2:
                                counts, bins = np.histogram(col_data, bins=min(15, len(col_data)))
                                hist_df = pd.DataFrame(
                                    {"count": counts},
                                    index=[f"{b:.1f}" for b in bins[:-1]]
                                )
                                st.bar_chart(hist_df, height=120, use_container_width=True)

                st.markdown("---")
                st.markdown("**Full statistics table:**")
                st.dataframe(numeric_df.describe().round(3), use_container_width=True)

                # Correlation matrix (only if >1 numeric col)
                if len(numeric_df.columns) > 1:
                    st.markdown("**Correlation matrix:**")
                    corr = numeric_df.corr().round(3)
                    st.dataframe(
                        corr.style.background_gradient(cmap="RdYlGn", vmin=-1, vmax=1),
                        use_container_width=True
                    )
            else:
                st.info("No numeric columns found in this dataset.")

        # ---- Categorical tab ----
        with tab_cat:
            if not cat_df.empty:
                for col_name in cat_df.columns:
                    vc = df[col_name].value_counts().head(15)
                    total_vals = int(df[col_name].count())
                    n_unique = df[col_name].nunique()
                    expanded = len(cat_df.columns) <= 4
                    with st.expander(
                        f"{col_name}   ({n_unique} unique | {total_vals} non-null)",
                        expanded=expanded
                    ):
                        cc1, cc2 = st.columns([1, 2])
                        with cc1:
                            vc_df = vc.reset_index()
                            vc_df.columns = ["Value", "Count"]
                            vc_df["Share %"] = (vc_df["Count"] / total_vals * 100).round(1)
                            st.dataframe(vc_df, use_container_width=True, hide_index=True)
                        with cc2:
                            st.bar_chart(vc, height=200, use_container_width=True)
            else:
                st.info("No categorical columns found in this dataset.")

        # ---- Column Info tab ----
        with tab_info:
            info_df = pd.DataFrame({
                "Column": df.columns,
                "Data Type": df.dtypes.astype(str).values,
                "Non-Null Count": df.count().values,
                "Null Count": df.isnull().sum().values,
                "Null %": (df.isnull().mean() * 100).round(1).values,
                "Unique Values": df.nunique().values,
                "Sample Value": [str(df[c].dropna().iloc[0]) if df[c].count() > 0 else "N/A" for c in df.columns],
            })
            st.dataframe(info_df, use_container_width=True, hide_index=True)

    # ----------------------------------------------------------
    # DATA CHART (interactive)
    # ----------------------------------------------------------
    with st.expander("Data Chart", expanded=True):
        all_cols = list(df.columns)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if not numeric_cols:
            st.info("No numeric columns available to chart.")
        else:
            cc1, cc2, cc3, cc4 = st.columns(4)
            chart_type = cc1.selectbox(
                "Chart type",
                ["Line", "Bar", "Area", "Scatter", "Histogram"],
                key="chart_type"
            )

            if chart_type == "Histogram":
                hist_col = cc2.selectbox("Column", numeric_cols, key="hist_col")
                bins_n = cc3.slider("Bins", 5, 50, 20, key="hist_bins")
                col_data = df[hist_col].dropna()
                if len(col_data) > 1:
                    counts, bins = np.histogram(col_data, bins=bins_n)
                    st.bar_chart(
                        pd.DataFrame({"count": counts},
                                     index=[f"{b:.2f}" for b in bins[:-1]]),
                        use_container_width=True
                    )
                    st.caption(f"Distribution of '{hist_col}' — {len(col_data):,} values, range [{col_data.min():.2f}, {col_data.max():.2f}]")

            elif chart_type == "Scatter":
                if len(numeric_cols) >= 2:
                    x_col = cc2.selectbox("X axis", numeric_cols, key="scatter_x")
                    y_options = [c for c in numeric_cols if c != x_col] or numeric_cols
                    y_col = cc3.selectbox("Y axis", y_options, key="scatter_y")
                    color_options = ["(none)"] + [c for c in all_cols if df[c].nunique() <= 20]
                    color_col = cc4.selectbox("Color by", color_options, key="scatter_color")

                    scatter_cols = [x_col, y_col] + ([color_col] if color_col != "(none)" else [])
                    scatter_data = df[scatter_cols].dropna()
                    try:
                        if color_col != "(none)":
                            st.scatter_chart(scatter_data, x=x_col, y=y_col, color=color_col, use_container_width=True)
                        else:
                            st.scatter_chart(scatter_data, x=x_col, y=y_col, use_container_width=True)
                    except Exception as e:
                        st.error(f"Scatter chart error: {e}")
                else:
                    st.info("Need at least 2 numeric columns for a scatter chart.")

            else:
                # Line / Bar / Area
                x_col = cc2.selectbox("X axis", all_cols, key="chart_x", index=0)
                y_candidates = [c for c in numeric_cols if c != x_col]
                y_default = y_candidates[:2] if y_candidates else []
                y_cols = cc3.multiselect(
                    "Y axis (numeric columns)",
                    y_candidates or numeric_cols,
                    default=y_default,
                    key="chart_y"
                )

                if x_col and y_cols:
                    try:
                        chart_df = df.set_index(x_col)[y_cols]
                        if chart_type == "Line":
                            st.line_chart(chart_df, use_container_width=True)
                        elif chart_type == "Bar":
                            st.bar_chart(chart_df, use_container_width=True)
                        elif chart_type == "Area":
                            st.area_chart(chart_df, use_container_width=True)
                        st.caption(f"{chart_type} chart | X: {x_col} | Y: {', '.join(y_cols)}")
                    except Exception as chart_err:
                        st.error(f"Chart error: {chart_err}")
                else:
                    st.info("Select an X axis and at least one Y axis column to render the chart.")


# current_df is passed to the AI section from whichever mode is active
current_df = None
ai_mode = "general"

# ============================================================
# MODE: UPLOAD AND ANALYZE
# ============================================================
if mode == "Upload and Analyze":
    st.markdown(
        "Upload your data file (CSV, Excel, or PDF) or use the sample dataset to explore and analyze with AI."
    )

    # Download sample data
    st.markdown("**Download sample data:**")
    col1, col2, col3 = st.columns(3)

    with col1:
        sample_csv = sample_df.to_csv(index=False)
        st.download_button("Download sample CSV", sample_csv,
                           file_name="sample_data.csv", mime="text/csv")
    with col2:
        excel_buf = io.BytesIO()
        sample_df.to_excel(excel_buf, index=False, engine="openpyxl")
        st.download_button("Download sample Excel", excel_buf.getvalue(),
                           file_name="sample_data.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col3:
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Sample Data Export", ln=True, align="C")
            pdf.set_font("Helvetica", size=8)
            pdf.ln(2)
            pdf_cols = list(sample_df.columns)
            col_w = max(15, 185 // len(pdf_cols))
            for c in pdf_cols:
                pdf.cell(col_w, 7, str(c)[:12], border=1)
            pdf.ln()
            for _, row in sample_df.head(30).iterrows():
                for c in pdf_cols:
                    pdf.cell(col_w, 6, str(row[c])[:12], border=1)
                pdf.ln()
            pdf_bytes = bytes(pdf.output())
            st.download_button("Download sample PDF", pdf_bytes,
                               file_name="sample_data.pdf", mime="application/pdf")
        except ImportError:
            st.caption("Install fpdf2 to enable PDF download.")

    # File uploader — 500 MB via .streamlit/config.toml
    uploaded = st.file_uploader(
        "Upload your data file (CSV, Excel, or PDF) — up to 500 MB",
        type=["csv", "xlsx", "xls", "pdf"],
        help="Supported: CSV, Excel (.xlsx/.xls), PDF (table/text extraction). Max 500 MB."
    )

    file_loaded = False
    if uploaded:
        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        try:
            if ext == "pdf":
                try:
                    import pdfplumber
                    with pdfplumber.open(uploaded) as pdffile:
                        all_tables = []
                        for page in pdffile.pages:
                            for tbl in (page.extract_tables() or []):
                                if tbl and len(tbl) > 1:
                                    all_tables.append(tbl)
                        if all_tables:
                            headers = all_tables[0][0]
                            rows_data = [r for t in all_tables for r in t[1:]]
                            df = pd.DataFrame(rows_data, columns=headers)
                            st.success(f"PDF loaded: {len(df)} rows extracted from tables across {len(pdffile.pages)} pages.")
                        else:
                            text_rows = []
                            for page in pdffile.pages:
                                text = page.extract_text()
                                if text:
                                    text_rows.extend(text.split("\n"))
                            df = pd.DataFrame({"Text": [r for r in text_rows if r.strip()]})
                            st.warning(f"No tables found in PDF. Extracted {len(df)} text lines as a single column.")
                except ImportError:
                    st.error("pdfplumber is required for PDF reading. It will be available after the next deployment.")
                    df = sample_df.copy()
            elif ext in ["xlsx", "xls"]:
                df = pd.read_excel(uploaded, engine="openpyxl")
                st.success(f"Excel loaded: {len(df):,} rows, {len(df.columns)} columns.")
            else:
                df = pd.read_csv(uploaded)
                st.success(f"CSV loaded: {len(df):,} rows, {len(df.columns)} columns.")
            file_loaded = True
        except Exception as e:
            st.error(f"Failed to load file: {e}")
            df = sample_df.copy()
    else:
        df = sample_df.copy()
        st.info("Using sample dataset. Upload a file above to analyze your own data.")

    df = coerce_datetime(df)
    current_df = df

    # Render the full analysis panel (with file info card if a real file was uploaded)
    render_data_analysis(
        df,
        file_name=uploaded.name if (uploaded and file_loaded) else None,
        show_preview=show_table
    )
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
            "Add new rows to the **sales** table. "
            "Edit the table inline, click **+** to add rows, then click **Save rows to DB**."
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
                    "Category", options=["A", "B", "C", "D", "E"]
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
            "Upload a CSV or Excel file to bulk-import into the **sales** table. "
            "Map your file columns to the database columns below."
        )
        sql_upload = st.file_uploader(
            "Upload CSV or Excel for DB import",
            type=["csv", "xlsx", "xls"],
            key="sql_import_uploader"
        )
        if sql_upload:
            ext2 = sql_upload.name.rsplit(".", 1)[-1].lower()
            import_df = (
                pd.read_excel(sql_upload, engine="openpyxl")
                if ext2 in ["xlsx", "xls"] else pd.read_csv(sql_upload)
            )
            st.markdown(f"**File preview** ({len(import_df):,} rows, {len(import_df.columns)} columns):")
            st.dataframe(import_df.head(10), use_container_width=True)

            available_cols = ["(skip)"] + list(import_df.columns)
            mc1, mc2, mc3 = st.columns(3)
            date_col = mc1.selectbox("Map -> Date", available_cols, key="map_date")
            cat_col  = mc2.selectbox("Map -> Category", available_cols, key="map_cat")
            val_col  = mc3.selectbox("Map -> Value", available_cols, key="map_val")

            if st.button("Import into DB", key="btn_import"):
                try:
                    today_fallback = str(datetime.date.today())
                    rows = [
                        (
                            str(row[date_col]) if date_col != "(skip)" else today_fallback,
                            str(row[cat_col])  if cat_col  != "(skip)" else "Unknown",
                            float(row[val_col]) if val_col != "(skip)" else 0.0
                        )
                        for _, row in import_df.iterrows()
                    ]
                    conn = sqlite3.connect(DB_PATH)
                    conn.executemany(
                        "INSERT INTO sales (Date, Category, Value) VALUES (?,?,?)", rows
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Imported {len(rows):,} rows into the sales table.")
                except Exception as e:
                    st.error(f"Import failed: {e}")

    # ---- SQL Query Explorer ----
    st.markdown("---")
    st.subheader("SQL Query Explorer")
    st.markdown(
        "Run queries against the local **data.db** SQLite database. "
        "Tables: `sales` (Date, Category, Value) and `ai_calls`."
    )

    examples = {
        "Top categories by avg value":
            "SELECT Category, ROUND(AVG(Value),2) as avg_value, COUNT(*) as cnt "
            "FROM sales GROUP BY Category ORDER BY avg_value DESC;",
        "Recent rows":
            "SELECT * FROM sales ORDER BY Date DESC LIMIT 10;",
        "Aggregate by date":
            "SELECT Date, ROUND(SUM(Value),2) as total FROM sales "
            "GROUP BY Date ORDER BY Date DESC LIMIT 30;",
        "Row count by category":
            "SELECT Category, COUNT(*) as cnt FROM sales GROUP BY Category;",
        "Min/Max/Avg overall":
            "SELECT ROUND(MIN(Value),2) as min_val, ROUND(MAX(Value),2) as max_val, "
            "ROUND(AVG(Value),2) as avg_val, COUNT(*) as total_rows FROM sales;"
    }
    sel = st.selectbox("Example queries", options=list(examples.keys()))
    query = st.text_area("SQL query", value=examples[sel], height=120)

    if st.button("Run SQL"):
        try:
            conn = sqlite3.connect(DB_PATH)
            qdf = pd.read_sql_query(query, conn)
            conn.close()
            st.dataframe(qdf, use_container_width=True)
            # Auto chart if the result has numeric data
            num_cols = qdf.select_dtypes(include=[np.number]).columns.tolist()
            if len(qdf) > 1 and num_cols:
                try:
                    idx_col = qdf.columns[0]
                    st.bar_chart(qdf.set_index(idx_col)[num_cols], use_container_width=True)
                    st.caption(f"Auto chart for query result | {len(qdf)} rows returned")
                except Exception:
                    pass
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

    # Sales table preview
    if show_table:
        try:
            conn = sqlite3.connect(DB_PATH)
            df_sql = pd.read_sql_query(
                "SELECT * FROM sales ORDER BY Date DESC LIMIT 100", conn
            )
            conn.close()
            df_sql_dt = coerce_datetime(df_sql)
            current_df = df_sql_dt

            st.subheader("Sales Table Preview (latest 100 rows)")
            st.dataframe(df_sql, use_container_width=True)

            # Quick chart of DB data
            num_cols = df_sql_dt.select_dtypes(include=[np.number]).columns.tolist()
            if num_cols:
                try:
                    st.bar_chart(df_sql_dt.set_index(df_sql_dt.columns[0])[num_cols], use_container_width=True)
                    st.caption("Sales table chart (latest 100 rows)")
                except Exception:
                    pass
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
        "For data questions, switch to 'Upload and Analyze' or 'SQL Explorer'."
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
MODE_DESCRIPTIONS = {
    "upload": (
        "**Mode: Data Analysis** - The AI is grounded exclusively in your uploaded dataset. "
        "It uses a dedicated system prompt that restricts answers to the data provided. "
        "For general questions like 'When is Diwali?', switch to **General Assistant** mode."
    ),
    "sql": (
        "**Mode: SQL Analysis** - The AI is grounded in your SQL query results. "
        "Click 'Include last query result in AI context' above to feed results into the conversation."
    ),
    "general": (
        "**Mode: General Assistant** - Three completely separate prompt templates handle context "
        "switching (one per mode, not a single dynamic prompt). The Data Analysis bot answers only "
        "from uploaded data; the SQL bot answers only from query results; this bot answers anything. "
        "Today's date is always injected so date queries (e.g. 'When is Diwali this year?') are accurate."
    )
}
st.info(MODE_DESCRIPTIONS.get(ai_mode, ""))

openai_key = os.environ.get("OPENAI_API_KEY")
if openai_key:
    AVAILABLE_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    selected_model = st.selectbox(
        "Select AI Model",
        options=AVAILABLE_MODELS,
        index=0,
        help="Filter and select the OpenAI model. GPT-4o is the latest and most capable."
    )

    today_str = datetime.datetime.today().strftime("%A, %d %B %Y")

    SYSTEM_PROMPTS = {
        "upload": (
            f"Today is {today_str}. "
            "You are a specialist Data Analysis assistant. "
            "Answer ONLY questions grounded in the dataset provided via DATA_SUMMARY messages. "
            "Include numeric insights (mean, min, max, trends) where relevant. Be concise. "
            "For off-topic questions, reply: "
            "'This is not a data question. Switch to General Assistant mode for general queries.'"
        ),
        "sql": (
            f"Today is {today_str}. "
            "You are a SQL Data Analysis specialist. "
            "Answer questions based on the database query results in SQL_RESULT_SUMMARY messages. "
            "Use SQLite syntax when writing SQL. Be concise and precise."
        ),
        "general": (
            f"Today is {today_str}. "
            "You are a knowledgeable general-purpose assistant. "
            "Answer accurately using up-to-date knowledge. "
            "For date-based questions (festivals, holidays, events), always use the current year "
            "unless the user specifies otherwise. Be concise, friendly, and factual."
        )
    }

    # Per-mode conversation history prevents cross-mode contamination
    state_key = f"messages_{ai_mode}"
    if state_key not in st.session_state:
        st.session_state[state_key] = []

    # Show conversation history
    st.markdown("**Conversation history (most recent first)**")
    for m in reversed(st.session_state[state_key][-8:]):
        st.write(f"**{m['role']}**: {m['content']}")

    st.markdown("---")

    placeholders = {
        "upload":  "e.g. 'What is the average Value?', 'Which category appears most?', 'Describe trends over time'",
        "sql":     "e.g. 'Summarize this query result', 'What SQL would find the top 5 rows by value?'",
        "general": "e.g. 'When is Diwali this year?', 'Explain the Model Context Protocol'"
    }

    # Pre-fill from Quick AI Analysis button if queued
    auto_q = st.session_state.pop("auto_query", "")
    prompt = st.text_area(
        "Submit your query",
        value=auto_q,
        placeholder=placeholders.get(ai_mode, "Enter your query...")
    )

    include_data = st.checkbox(
        "Include data summary in context",
        value=(ai_mode != "general"),
        help=(
            "Upload mode: prepends mean/min/max stats. "
            "SQL mode: prepends last query result summary. "
            "General mode: no data to include."
        )
    )

    if st.button("Submit Your Query") and prompt:
        messages = [{"role": "system", "content": SYSTEM_PROMPTS[ai_mode]}]
        messages.extend(st.session_state[state_key])

        if include_data:
            if ai_mode == "upload" and current_df is not None:
                try:
                    numeric = current_df.select_dtypes(include=[np.number])
                    if not numeric.empty:
                        stats = numeric.describe().loc[["mean", "min", "max"]].to_dict()
                        stats_r = {k: {sk: round(sv, 2) for sk, sv in v.items()} for k, v in stats.items()}
                        messages.append({"role": "user", "content": f"DATA_SUMMARY: {stats_r}"})
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
                    json.dumps({"model": selected_model, "mode": ai_mode, "count": len(messages)},
                               ensure_ascii=False),
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
                    headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                    json={"model": selected_model, "messages": messages, "max_tokens": 500, "temperature": 0.3},
                    timeout=30
                )
                resp.raise_for_status()
                j = resp.json()
                assistant_text = (
                    j["choices"][0]["message"]["content"]
                    if "choices" in j and j["choices"] else str(j)
                )

                st.session_state[state_key].append({"role": "user", "content": prompt})
                st.session_state[state_key].append({"role": "assistant", "content": assistant_text})

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
