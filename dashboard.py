# dashboard.py (DEBUG VERSION)

import streamlit as st
import pandas as pd
import os

BASE_DOWNLOAD_PATH = r"C:\Download"
LATEST_FILE = os.path.join(BASE_DOWNLOAD_PATH, "latest_data.csv")

st.set_page_config(page_title="Dashboard", layout="wide")
st.title("📊 Email Attachment Dashboard")

# ==============================
# DEBUG SECTION
# ==============================
st.subheader("🔍 Debug Info")

st.write("File path:", LATEST_FILE)
st.write("File exists:", os.path.exists(LATEST_FILE))

if not os.path.exists(LATEST_FILE):
    st.error("❌ File NOT found")
    st.stop()

# File size check
file_size = os.path.getsize(LATEST_FILE)
st.write("File size (bytes):", file_size)

# ==============================
# LOAD DATA (SAFE)
# ==============================
try:
    df = pd.read_csv(LATEST_FILE, encoding="utf-8")
except:
    df = pd.read_csv(LATEST_FILE, encoding="latin1")

st.write("Rows loaded:", len(df))
st.write("Columns:", list(df.columns))

if df.empty:
    st.warning("⚠️ DataFrame is EMPTY")
    st.stop()

# ==============================
# DISPLAY DATA
# ==============================
st.subheader("📄 Data")
st.dataframe(df)

# ==============================
# KPI
# ==============================
col1, col2, col3 = st.columns(3)
col1.metric("Rows", len(df))
col2.metric("Columns", len(df.columns))
col3.metric("Missing", df.isnull().sum().sum())

# ==============================
# CHART
# ==============================
numeric_cols = df.select_dtypes(include=['number']).columns

if len(numeric_cols) > 0:
    col = st.selectbox("Select column", numeric_cols)
    st.bar_chart(df[col])
else:
    st.warning("No numeric columns")