import truststore
truststore.inject_into_ssl()

import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
import re

# ==========================================
# CONFIG
# ==========================================

st.set_page_config(page_title="Airtel Enterprise Dashboard", layout="wide")

st.title("📊 Airtel Bill Intelligence Dashboard")

# ==========================================
# SESSION STATE
# ==========================================

if "files" not in st.session_state:
    st.session_state.files = []

# ==========================================
# SIDEBAR - FILE MANAGER
# ==========================================

st.sidebar.header("📂 File Manager")

uploaded_file = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file:
    if st.sidebar.button("➕ Add File"):
        names = [f.name for f in st.session_state.files]
        if uploaded_file.name not in names:
            st.session_state.files.append(uploaded_file)

if st.session_state.files:
    st.sidebar.subheader("Files")
    for f in st.session_state.files:
        st.sidebar.write(f"📄 {f.name}")

    if st.sidebar.button("🗑 Clear All"):
        st.session_state.files = []
        st.rerun()

# ==========================================
# EXTRACTION
# ==========================================

def extract_bill(file):

    result = {
        "email": None,
        "phone": None,
        "plan": None,
        "airtel_id": None,
        "statement_date": None,
        "statement_period": None,
        "amount": None,
        "due_date": None,
        "file": file.name
    }

    try:
        file.seek(0)

        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

        email = re.search(r"[\w\.-]+@[\w\.-]+", text)
        if email:
            result["email"] = email.group(0)

        phone = re.search(r"\b\d{10}\b", text)
        if phone:
            result["phone"] = phone.group(0)

        plan = re.search(r"Airtel Black.*", text)
        if plan:
            result["plan"] = plan.group(0)

        aid = re.search(r"\b\d{12,}\b", text)
        if aid:
            result["airtel_id"] = aid.group(0)

        dates = re.findall(r"\d{1,2}\s\w+\s\d{4}", text)
        if len(dates) >= 1:
            result["statement_date"] = dates[0]
        if len(dates) >= 2:
            result["due_date"] = dates[-1]

        period = re.search(r"\d{1,2}\s\w+\s\d{4}\s-\s\d{1,2}\s\w+\s\d{4}", text)
        if period:
            result["statement_period"] = period.group(0)

        amt = re.search(r"₹\s?([\d,]+\.\d{2})", text)
        if amt:
            result["amount"] = float(amt.group(1).replace(",", ""))

    except:
        pass

    return result

# ==========================================
# PROCESS
# ==========================================

def process_all(files):
    return pd.DataFrame([extract_bill(f) for f in files])

# ==========================================
# AI INSIGHTS
# ==========================================

def generate_insights(df):

    insights = []

    df = df.sort_values("Month")

    values = df["amount"].dropna().values

    if len(values) < 2:
        return ["Not enough data for insights"]

    if values[-1] > values[0]:
        insights.append("📈 Overall trend is increasing")
    elif values[-1] < values[0]:
        insights.append("📉 Overall trend is decreasing")

    changes = df["amount"].pct_change() * 100

    for i, change in enumerate(changes):
        if pd.notna(change):
            if change > 15:
                insights.append(f"🔺 Spike detected: +{change:.1f}% in {df.iloc[i]['Month']}")
            elif change < -15:
                insights.append(f"🔻 Drop detected: {change:.1f}% in {df.iloc[i]['Month']}")

    max_row = df.loc[df["amount"].idxmax()]
    min_row = df.loc[df["amount"].idxmin()]

    insights.append(f"💰 Highest bill: ₹{max_row['amount']:,.2f} ({max_row['Month']})")
    insights.append(f"💸 Lowest bill: ₹{min_row['amount']:,.2f} ({min_row['Month']})")

    return insights

# ==========================================
# MAIN DASHBOARD
# ==========================================

if st.session_state.files:

    if st.button("🚀 Generate Dashboard"):

        df = process_all(st.session_state.files)

        if df.empty:
            st.error("No data extracted")

        else:

            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

            # Month & Year
            df["Month"] = df["statement_period"].str.extract(r"-\s\d{1,2}\s(\w+)")
            df["Year"] = df["statement_period"].str.extract(r"(\d{4})$")

            month_order = ["Jan","Feb","Mar","Apr","May","Jun",
                           "Jul","Aug","Sep","Oct","Nov","Dec"]

            df["Month"] = pd.Categorical(df["Month"], categories=month_order, ordered=True)

            # Anomaly Detection
            df["pct_change"] = df["amount"].pct_change() * 100

            df["Anomaly"] = df["pct_change"].apply(
                lambda x: "🔺 Spike" if x > 15 else ("🔻 Drop" if x < -15 else "Normal")
            )

            # ======================================
            # FILTERS
            # ======================================
            st.sidebar.header("🔍 Filters")

            selected_months = st.sidebar.multiselect(
                "Month",
                df["Month"].dropna().unique(),
                default=df["Month"].dropna().unique()
            )

            filtered_df = df[df["Month"].isin(selected_months)]

            # ======================================
            # KPIs
            # ======================================
            st.subheader("📊 Overview")

            c1, c2, c3, c4 = st.columns(4)

            c1.metric("📄 Bills", len(filtered_df))
            c2.metric("💰 Total Spend", f"₹ {filtered_df['amount'].sum():,.2f}")
            c3.metric("📊 Avg Bill", f"₹ {filtered_df['amount'].mean():,.2f}")
            c4.metric("📈 Max Bill", f"₹ {filtered_df['amount'].max():,.2f}")

            st.markdown("---")

            # ======================================
            # AI INSIGHTS
            # ======================================
            st.subheader("🤖 AI Insights")

            insights = generate_insights(filtered_df)

            for ins in insights:
                st.write(ins)

            st.markdown("---")

            # ======================================
            # CHARTS
            # ======================================
            tab1, tab2, tab3 = st.tabs(["📈 Trend", "📊 Comparison", "📦 Distribution"])

            with tab1:
                fig1 = px.line(filtered_df, x="Month", y="amount", markers=True)
                st.plotly_chart(fig1, use_container_width=True)

            with tab2:
                fig2 = px.bar(
                    filtered_df,
                    x="Month",
                    y="amount",
                    color="Anomaly",
                    text="amount"
                )
                st.plotly_chart(fig2, use_container_width=True)

            with tab3:
                fig3 = px.pie(filtered_df, names="Month", values="amount")
                st.plotly_chart(fig3, use_container_width=True)

            # ======================================
            # TABLE
            # ======================================
            st.subheader("📋 Data Table")
            st.dataframe(filtered_df, use_container_width=True)

            # Download
            csv = filtered_df.to_csv(index=False).encode("utf-8")

            st.download_button(
                "⬇ Download CSV",
                csv,
                "airtel_dashboard.csv",
                "text/csv"
            )