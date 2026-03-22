import os
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

st.set_page_config(layout="wide")

# ---------- HEADER ----------
st.markdown("""
<div style="
background: linear-gradient(90deg,#4e73df,#1cc88a);
padding:12px;border-radius:8px;color:white;
font-weight:bold;font-size:18px;">
Contact Dashboard
<span style="float:right">admin</span>
</div>
""", unsafe_allow_html=True)

# ---------- DATABASE ----------
db = os.path.join(os.path.dirname(__file__), "contacts.db")
engine = create_engine(f"sqlite:///{db}")

# ---------- INIT ----------
with engine.begin() as conn:

    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS contacts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        city TEXT,
        created_at TIMESTAMP
    )
    """))

    # ✅ FIX NULL TIMESTAMP ONLY (NO DROP)
    conn.execute(text("""
        UPDATE contacts
        SET created_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL
    """))

# ---------- FUNCTIONS ----------
def get_data():
    df = pd.read_sql("SELECT * FROM contacts", engine)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df = df.sort_values("id").reset_index(drop=True)
    df.insert(0, "S.No", df.index + 1)
    return df

def add_contact(name, phone, city):
    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO contacts(name,phone,city,created_at)
        VALUES(:n,:p,:c,CURRENT_TIMESTAMP)
        """), {"n": name, "p": phone, "c": city})

def update_contact(cid, name, phone, city):
    with engine.begin() as conn:
        conn.execute(text("""
        UPDATE contacts
        SET name=:n, phone=:p, city=:c
        WHERE id=:id
        """), {"id": cid, "n": name, "p": phone, "c": city})

def delete_contact(cid):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM contacts WHERE id=:id"), {"id": cid})

# ---------- SIDEBAR ----------
page = st.sidebar.radio("Menu", ["Dashboard","Manage Contacts","Upload Excel"])

df = get_data()

# ---------- DASHBOARD ----------
if page == "Dashboard":

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Contacts", len(df))
    c2.metric("Cities", df["city"].nunique())
    c3.metric("Latest ID", df["id"].max() if len(df) else 0)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("City Distribution")
        if len(df):
            d = df["city"].value_counts().reset_index()
            d.columns = ["City","Count"]
            st.plotly_chart(px.pie(d, values="Count", names="City"), use_container_width=True)

    with col2:
        st.subheader("Growth")
        g = df.dropna(subset=["created_at"])
        if len(g):
            g = g.groupby(g.created_at.dt.date).size().reset_index(name="count")
            st.plotly_chart(px.line(g, x="created_at", y="count"), use_container_width=True)

# ---------- MANAGE ----------
if page == "Manage Contacts":

    st.subheader("➕ Add Contact")

    col1, col2, col3 = st.columns(3)
    name = col1.text_input("Name")
    phone = col2.text_input("Phone")
    city = col3.text_input("City")

    if st.button("Add Contact"):
        if name and phone and city:
            add_contact(name, phone, city)
            st.success("Added")
            st.rerun()

    st.divider()

    # SEARCH
    search = st.text_input("Search")

    filtered_df = df.copy()

    if search:
        filtered_df = filtered_df[
            filtered_df["name"].str.contains(search, case=False, na=False)
        ]

    # PAGINATION
    st.subheader("📄 Pagination")

    page_size = st.selectbox("Rows per page", [5,10,20,50], index=1)

    total_pages = max(1, (len(filtered_df) // page_size) + 1)

    page_number = st.number_input("Page", min_value=1, max_value=total_pages, step=1)

    start = (page_number - 1) * page_size
    end = start + page_size

    page_df = filtered_df.iloc[start:end]

    st.divider()

    # EDIT
    st.subheader("✏ Edit Contacts")

    edited = st.data_editor(page_df, use_container_width=True)

    if st.button("Update Contacts"):
        for _, row in edited.iterrows():
            update_contact(row["id"], row["name"], row["phone"], row["city"])
        st.success("Updated")
        st.rerun()

    st.divider()

    # DELETE
    st.subheader("🗑 Delete Contact")

    options = {
        f"{row['id']} - {row['name']}": row["id"]
        for _, row in df.iterrows()
    }

    if options:
        selected = st.selectbox("Select Contact", list(options.keys()))

        if st.button("Delete Contact"):
            delete_contact(options[selected])
            st.warning("Deleted")
            st.rerun()
    else:
        st.info("No contacts available")

# ---------- UPLOAD ----------
if page == "Upload Excel":

    st.subheader("📂 Upload Excel")

    file = st.file_uploader("Upload Excel", type=["xlsx"])

    if file:
        df_upload = pd.read_excel(file)

        st.dataframe(df_upload)

        if st.button("Import Data"):

            existing = get_data()

            for _, row in df_upload.iterrows():

                # skip duplicates
                if not ((existing["name"] == row["name"]) &
                        (existing["phone"].astype(str) == str(row["phone"]))).any():

                    add_contact(row["name"], str(row["phone"]), row["city"])

            st.success("Imported (duplicates skipped)")
            st.rerun()